import logging
from datetime import timedelta

from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .generator import (
    generate_itinerary, ensure_lahore_places_seeded,
    _normalize_interests, _budget_rank, _score_place, _pick_nearby, _pace_target,
    regenerate_day, regenerate_full_trip, _get_mood_tags, _build_day_items,
)
from .ai_service import AIItineraryService
from .models import Itinerary, Place
from .serializers import ItinerarySerializer, ItineraryGenerateSerializer, PlaceSerializer

logger = logging.getLogger(__name__)


class PlaceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        city = request.query_params.get('city', 'Lahore')
        ensure_lahore_places_seeded()
        places = Place.objects.filter(city=city).order_by('category', 'name')
        return Response({'success': True, 'count': places.count(), 'places': PlaceSerializer(places, many=True).data})


class ItineraryGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _slot_for_index(index: int, total: int) -> str:
        if index == 0:
            return 'morning'
        if index < max(2, total - 1):
            return 'afternoon'
        return 'evening'

    @classmethod
    def _normalize_ai_days(cls, ai_itinerary: dict, city: str, start_date):
        """
        Convert AI response days to the existing frontend/backend contract:
        days[].items where each item has place_* fields.
        """
        days = ai_itinerary.get('days', []) if isinstance(ai_itinerary, dict) else []

        # Collect place IDs up front for enrichment from DB.
        place_ids = []
        for day in days:
            for place in (day.get('places') or []):
                pid = place.get('id')
                if pid is not None:
                    place_ids.append(pid)

        place_map = {p.id: p for p in Place.objects.filter(id__in=place_ids, city=city)}

        normalized_days = []
        for day_idx, day in enumerate(days):
            day_date = day.get('date')
            if day_date is None and start_date is not None:
                day_date = (start_date + timedelta(days=day_idx)).isoformat()

            # If AI already returned items in expected shape, keep them.
            existing_items = day.get('items') or []
            if existing_items:
                items = existing_items
            else:
                places = day.get('places') or []
                items = []
                total = len(places)
                for idx, place in enumerate(places):
                    pid = place.get('id')
                    db_place = place_map.get(pid)
                    items.append({
                        'type': 'place',
                        'slot': cls._slot_for_index(idx, total),
                        'place_id': pid,
                        'name': place.get('name') or (db_place.name if db_place else 'Unknown place'),
                        'category': place.get('category') or (db_place.category if db_place else ''),
                        'estimated_visit_minutes': (
                            place.get('estimated_visit_minutes')
                            or (db_place.estimated_visit_minutes if db_place else 90)
                        ),
                        'budget_level': place.get('budget_level') or (db_place.budget_level if db_place else ''),
                        'latitude': place.get('latitude') if place.get('latitude') is not None else (db_place.latitude if db_place else None),
                        'longitude': place.get('longitude') if place.get('longitude') is not None else (db_place.longitude if db_place else None),
                        'average_rating': (
                            place.get('average_rating')
                            if place.get('average_rating') is not None
                            else (db_place.average_rating if db_place else None)
                        ),
                        'tags': place.get('tags') or (db_place.tags if db_place else []),
                        'ideal_hours': {
                            'start': place.get('ideal_start_hour') if place.get('ideal_start_hour') is not None else (db_place.ideal_start_hour if db_place else None),
                            'end': place.get('ideal_end_hour') if place.get('ideal_end_hour') is not None else (db_place.ideal_end_hour if db_place else None),
                        },
                    })

            normalized_days.append({
                'date': day_date,
                'title': day.get('title') or f"Day {day_idx + 1} - {city}",
                'items': items,
            })

        return normalized_days

    def post(self, request):
        serializer = ItineraryGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # AI-first path for itinerary generation (fallback to existing generator on any failure).
        use_ai = bool(getattr(settings, 'USE_AI_ITINERARY_PLANNER', True))
        if use_ai:
            try:
                ai_service = AIItineraryService(
                    enable_emotion_detection=bool(getattr(settings, 'USE_EMOTION_DETECTION', True)),
                    enable_ml_ranking=bool(getattr(settings, 'USE_ML_RANKING', True)),
                    enable_llm_enhancement=bool(getattr(settings, 'USE_LLM_ENHANCEMENT', False)),
                    fallback_confidence_threshold=float(getattr(settings, 'AI_CONFIDENCE_THRESHOLD', 0.6)),
                )

                trip_days = max(1, (data['end_date'] - data['start_date']).days)
                trip_params = {
                    'mood': data.get('mood', ''),
                    'interests': data.get('interests', []),
                    'budget': str(data.get('budget_level', Itinerary.Budget.MEDIUM)).lower(),
                    'pace': data.get('pace', Itinerary.Pace.BALANCED),
                    'num_days': trip_days,
                    'trip_start_date': data['start_date'],
                    'city': data.get('city', 'Lahore'),
                    'travelers': data.get('travelers', 1),
                }

                ai_itinerary = ai_service.generate_itinerary_ai(
                    user_id=str(request.user.id),
                    trip_params=trip_params,
                    user=request.user,
                    preferences_text=str(request.data.get('preferences_text', '')),
                )

                normalized_days = self._normalize_ai_days(
                    ai_itinerary=ai_itinerary,
                    city=data.get('city', 'Lahore'),
                    start_date=data['start_date'],
                )

                itinerary = Itinerary.objects.create(
                    user=request.user,
                    city=data.get('city', 'Lahore'),
                    start_date=data['start_date'],
                    end_date=data['end_date'],
                    travelers=max(1, int(data.get('travelers', 1) or 1)),
                    budget_level=data.get('budget_level', Itinerary.Budget.MEDIUM),
                    interests=_normalize_interests(data.get('interests', [])),
                    pace=data.get('pace', Itinerary.Pace.BALANCED),
                    mood=data.get('mood', ''),
                    days=normalized_days,
                    saved=True,
                )

                try:
                    from authentication.models import Notification
                    Notification.itinerary_ready(request.user, data.get('city', 'Lahore'))
                except Exception:
                    pass

                return Response(
                    {'success': True, 'itinerary': ItinerarySerializer(itinerary).data, 'ai_powered': True},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as exc:
                logger.warning(f"AI itinerary generation failed, falling back to rule-based: {exc}")

        itinerary = generate_itinerary(
            user=request.user,
            city=data.get('city', 'Lahore'),
            start_date=data['start_date'],
            end_date=data['end_date'],
            travelers=data.get('travelers', 1),
            budget_level=data.get('budget_level', Itinerary.Budget.MEDIUM),
            interests=data.get('interests', []),
            pace=data.get('pace', Itinerary.Pace.BALANCED),
            mood=data.get('mood', ''),
        )

        # Create notification
        try:
            from authentication.models import Notification
            Notification.itinerary_ready(request.user, data.get('city', 'Lahore'))
        except Exception:
            pass

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data}, status=status.HTTP_201_CREATED)


class ItineraryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Itinerary.objects.filter(user=request.user).order_by('-created_at')
        return Response({'success': True, 'count': qs.count(), 'itineraries': ItinerarySerializer(qs, many=True).data})


class ItineraryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})

    def patch(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)

        budget_level = request.data.get('budget_level')
        pace = request.data.get('pace')
        interests = request.data.get('interests')
        mood = request.data.get('mood')
        notes = request.data.get('notes')
        should_regenerate = bool(request.data.get('regenerate', False))

        with transaction.atomic():
            if budget_level:
                itinerary.budget_level = budget_level
            if pace:
                itinerary.pace = pace
            if interests is not None:
                itinerary.interests = _normalize_interests(interests)
            if mood is not None:
                itinerary.mood = mood
            if notes is not None:
                itinerary.notes = str(notes)

            if should_regenerate:
                # Full trip regeneration with smart diversity
                new_days, new_excluded = regenerate_full_trip(itinerary)
                itinerary.days = new_days
                itinerary.excluded_place_ids = new_excluded

            itinerary.save()

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})

    def delete(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        itinerary.delete()
        return Response({'success': True, 'message': 'Itinerary deleted'}, status=status.HTTP_204_NO_CONTENT)


class ItineraryRegenerateDayView(APIView):
    """
    POST /api/itineraries/{id}/regenerate-day/
    Regenerate a single day with smart exclusion and mood preservation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        day_index = int(request.data.get('day_index', -1))
        if day_index < 0 or day_index >= len(itinerary.days or []):
            return Response({'success': False, 'error': 'Invalid day_index'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            new_items, new_excluded = regenerate_day(itinerary, day_index)
            itinerary.days[day_index]['items'] = new_items
            itinerary.excluded_place_ids = new_excluded
            itinerary.save(update_fields=['days', 'excluded_place_ids', 'updated_at'])

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})


class ItineraryRegenerateFullView(APIView):
    """
    POST /api/itineraries/{id}/regenerate-full/
    Regenerate the entire trip with maximum diversity.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)

        # Allow changing mood/budget/pace during regeneration
        new_mood = request.data.get('mood')
        new_budget = request.data.get('budget_level')
        new_pace = request.data.get('pace')

        with transaction.atomic():
            if new_mood is not None:
                itinerary.mood = new_mood
            if new_budget:
                itinerary.budget_level = new_budget
            if new_pace:
                itinerary.pace = new_pace

            new_days, new_excluded = regenerate_full_trip(itinerary)
            itinerary.days = new_days
            itinerary.excluded_place_ids = new_excluded
            itinerary.save()

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})


class ItineraryReplacePlaceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        day_index = int(request.data.get('day_index', -1))
        item_index = int(request.data.get('item_index', -1))
        new_place_id = request.data.get('new_place_id')

        if day_index < 0 or day_index >= len(itinerary.days or []):
            return Response({'success': False, 'error': 'Invalid day_index'}, status=status.HTTP_400_BAD_REQUEST)
        items = itinerary.days[day_index].get('items', [])
        if item_index < 0 or item_index >= len(items):
            return Response({'success': False, 'error': 'Invalid item_index'}, status=status.HTTP_400_BAD_REQUEST)
        if items[item_index].get('type') != 'place':
            return Response({'success': False, 'error': 'Only place items can be replaced'}, status=status.HTTP_400_BAD_REQUEST)

        ensure_lahore_places_seeded()

        if new_place_id:
            new_place = get_object_or_404(Place, id=new_place_id, city=itinerary.city)
        else:
            # Auto-pick replacement from same category within budget
            old_category = items[item_index].get('category')
            budget_cap = _budget_rank(itinerary.budget_level)
            used = set()
            for day in itinerary.days or []:
                for it in day.get('items', []):
                    if it.get('type') == 'place' and it.get('place_id'):
                        used.add(it['place_id'])
            qs = Place.objects.filter(city=itinerary.city, category=old_category)
            qs = [p for p in qs if _budget_rank(p.budget_level) <= budget_cap and p.id not in used]
            qs.sort(key=lambda p: p.average_rating or 0, reverse=True)
            if not qs:
                return Response({'success': False, 'error': 'No replacement place available'}, status=status.HTTP_400_BAD_REQUEST)
            new_place = qs[0]

        new_item = {
            'type': 'place',
            'slot': items[item_index].get('slot'),
            'place_id': new_place.id,
            'name': new_place.name,
            'category': new_place.category,
            'estimated_visit_minutes': new_place.estimated_visit_minutes,
            'budget_level': new_place.budget_level,
            'latitude': new_place.latitude,
            'longitude': new_place.longitude,
            'average_rating': new_place.average_rating,
            'tags': new_place.tags or [],
            'ideal_hours': {'start': new_place.ideal_start_hour, 'end': new_place.ideal_end_hour},
        }

        with transaction.atomic():
            # Add old place to exclusion history
            old_pid = items[item_index].get('place_id')
            if old_pid:
                excluded = list(itinerary.excluded_place_ids or [])
                if old_pid not in excluded:
                    excluded.append(old_pid)
                itinerary.excluded_place_ids = excluded

            itinerary.days[day_index]['items'][item_index] = new_item
            itinerary.save(update_fields=['days', 'excluded_place_ids', 'updated_at'])

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})


class ItineraryRemovePlaceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        day_index = int(request.data.get('day_index', -1))
        item_index = int(request.data.get('item_index', -1))

        if day_index < 0 or day_index >= len(itinerary.days or []):
            return Response({'success': False, 'error': 'Invalid day_index'}, status=status.HTTP_400_BAD_REQUEST)
        items = itinerary.days[day_index].get('items', [])
        if item_index < 0 or item_index >= len(items):
            return Response({'success': False, 'error': 'Invalid item_index'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            itinerary.days[day_index]['items'].pop(item_index)
            itinerary.save(update_fields=['days', 'updated_at'])

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})


class ItineraryLockPlaceView(APIView):
    """
    POST /api/itineraries/{id}/lock-place/
    Lock a place so it survives regeneration.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        place_id = request.data.get('place_id')
        lock = request.data.get('lock', True)  # True to lock, False to unlock

        if not place_id:
            return Response({'success': False, 'error': 'place_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        locked = list(itinerary.locked_place_ids or [])

        if lock and place_id not in locked:
            locked.append(place_id)
        elif not lock and place_id in locked:
            locked.remove(place_id)

        itinerary.locked_place_ids = locked
        itinerary.save(update_fields=['locked_place_ids', 'updated_at'])

        return Response({
            'success': True,
            'locked_place_ids': locked,
            'itinerary': ItinerarySerializer(itinerary).data
        })


class ItineraryReorderView(APIView):
    """
    POST /api/itineraries/{id}/reorder/
    Reorder places within a day via drag & drop.
    
    Body: { "day_index": 0, "item_order": [2, 0, 1, 3] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        day_index = int(request.data.get('day_index', -1))
        item_order = request.data.get('item_order', [])

        if day_index < 0 or day_index >= len(itinerary.days or []):
            return Response({'success': False, 'error': 'Invalid day_index'}, status=status.HTTP_400_BAD_REQUEST)

        items = itinerary.days[day_index].get('items', [])
        if len(item_order) != len(items):
            return Response(
                {'success': False, 'error': f'item_order must have {len(items)} elements'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate indices
        if sorted(item_order) != list(range(len(items))):
            return Response({'success': False, 'error': 'Invalid item_order indices'}, status=status.HTTP_400_BAD_REQUEST)

        # Reorder
        new_items = [items[i] for i in item_order]

        # Re-assign slots
        per_day = len(new_items)
        for idx, item in enumerate(new_items):
            if idx == 0:
                item['slot'] = 'morning'
            elif idx < max(2, per_day - 1):
                item['slot'] = 'afternoon'
            else:
                item['slot'] = 'evening'

        with transaction.atomic():
            itinerary.days[day_index]['items'] = new_items
            itinerary.save(update_fields=['days', 'updated_at'])

        return Response({'success': True, 'itinerary': ItinerarySerializer(itinerary).data})


class ItineraryEmailView(APIView):
    """
    POST /api/itineraries/{id}/email/
    Send itinerary summary email to the authenticated user's email.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, itinerary_id):
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)

        recipient = (request.user.email or '').strip()
        if not recipient:
            return Response(
                {'success': False, 'error': 'No email found on your account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subject = str(request.data.get('subject') or f"Your {itinerary.city} itinerary")
        body = str(request.data.get('body') or '').strip()

        if not body:
            lines = [
                f"{itinerary.city} Itinerary",
                f"{itinerary.start_date} -> {itinerary.end_date}",
                f"Pace: {itinerary.pace}",
                f"Budget: {itinerary.budget_level}",
                "",
            ]
            for idx, day in enumerate(itinerary.days or [], start=1):
                lines.append(f"Day {idx} ({day.get('date', '')}) - {day.get('title', '')}")
                for item in day.get('items', []):
                    if item.get('type') != 'place':
                        continue
                    slot = item.get('slot') or 'Visit'
                    name = item.get('name') or 'Place'
                    category = item.get('category') or ''
                    lines.append(f"  - [{slot}] {name} ({category})")
                lines.append('')

            if itinerary.notes:
                lines.extend(['Notes:', str(itinerary.notes), ''])

            body = "\n".join(lines)

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            return Response({'success': True, 'email_sent': True, 'recipient': recipient})
        except Exception as exc:
            logger.warning(f"Failed to send itinerary email for itinerary {itinerary.id}: {exc}")
            return Response(
                {'success': False, 'email_sent': False, 'error': 'Email sending failed. Please try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class MoodListView(APIView):
    """
    GET /api/itineraries/moods/
    Returns available moods with descriptions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        moods = [
            {'value': 'RELAXING', 'label': 'Relaxing', 'emoji': '🧘', 'description': 'Parks, gardens, calm spots'},
            {'value': 'SPIRITUAL', 'label': 'Spiritual', 'emoji': '🕌', 'description': 'Mosques, shrines, sacred places'},
            {'value': 'HISTORICAL', 'label': 'Historical', 'emoji': '🏛️', 'description': 'Forts, museums, old city'},
            {'value': 'FOODIE', 'label': 'Foodie', 'emoji': '🍛', 'description': 'Food streets, restaurants, local cuisine'},
            {'value': 'FUN', 'label': 'Fun & Entertainment', 'emoji': '🎢', 'description': 'Malls, parks, shows'},
            {'value': 'SHOPPING', 'label': 'Shopping', 'emoji': '🛍️', 'description': 'Bazaars, malls, markets'},
            {'value': 'NATURE', 'label': 'Nature', 'emoji': '🌿', 'description': 'Gardens, parks, greenery'},
            {'value': 'ROMANTIC', 'label': 'Romantic', 'emoji': '💕', 'description': 'Scenic spots, dinner venues'},
            {'value': 'FAMILY', 'label': 'Family', 'emoji': '👨‍👩‍👧‍👦', 'description': 'Kid-friendly attractions'},
        ]
        return Response({'success': True, 'moods': moods})

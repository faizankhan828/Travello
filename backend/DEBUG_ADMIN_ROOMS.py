#!/usr/bin/env python
"""
Debug script to diagnose admin-added room booking issues.

This script will:
1. List all hotels and their room types
2. Show admin-added vs regular rooms
3. Test the availability calculation
4. Identify why "Not enough rooms" error occurs
"""

import os
import sys
import django

# Add backend to path
sys.path.insert(0, '/f:/FYP/Travello/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
django.setup()

from hotels.models import Hotel, RoomType, Booking
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_subheader(text):
    print(f"\n--- {text} ---")

print_header("ADMIN ROOMS BOOKING DIAGNOSTICS")

# 1. List all hotels and rooms
print_subheader("1. ALL HOTELS AND THEIR ROOM TYPES")
hotels = Hotel.objects.all().prefetch_related('room_types')
if not hotels:
    print("❌ No hotels found in database!")
else:
    for hotel in hotels:
        print(f"\n🏨 Hotel: {hotel.name} (ID: {hotel.id})")
        print(f"   City: {hotel.city}")
        print(f"   Total rooms across all types: {hotel.total_rooms}")
        
        room_types = hotel.room_types.all()
        if not room_types:
            print(f"   ❌ No room types defined!")
        else:
            for rt in room_types:
                print(f"\n   Room Type: {rt.get_type_display()} (ID: {rt.id})")
                print(f"   - Total rooms: {rt.total_rooms}")
                print(f"   - Price: PKR {rt.price_per_night}/night")
                print(f"   - Max occupancy: {rt.max_occupancy}")
                print(f"   - Created: {rt.created_at}")
                
                # Check if total_rooms is 0 or None
                if not rt.total_rooms or rt.total_rooms <= 0:
                    print(f"   ❌ ERROR: total_rooms is {rt.total_rooms} (should be >= 1)")
                else:
                    print(f"   ✓ total_rooms: {rt.total_rooms}")

# 2. Check bookings
print_subheader("2. EXISTING BOOKINGS")
bookings = Booking.objects.all().select_related('hotel', 'room_type', 'user')
if not bookings:
    print("✓ No bookings in system")
else:
    for booking in bookings:
        print(f"\nBooking ID: {booking.id} ({booking.booking_reference})")
        print(f"  Hotel: {booking.hotel.name}")
        print(f"  Room Type: {booking.room_type.get_type_display()}")
        print(f"  Rooms Booked: {booking.rooms_booked}")
        print(f"  Check-in: {booking.check_in}")
        print(f"  Check-out: {booking.check_out}")
        print(f"  Status: {booking.status}")
        print(f"  User: {booking.user.username if booking.user else 'N/A'}")

# 3. Test availability calculation
print_subheader("3. TEST AVAILABILITY CALCULATIONS")
check_in = timezone.now().date() + timedelta(days=1)
check_out = check_in + timedelta(days=3)

for hotel in hotels:
    print(f"\n🏨 Hotel: {hotel.name}")
    print(f"   Testing availability for: {check_in} to {check_out}")
    
    for room_type in hotel.room_types.all():
        print(f"\n   Room Type: {room_type.get_type_display()}")
        print(f"   - Total rooms: {room_type.total_rooms}")
        
        # Calculate manually
        from django.db.models import Sum
        overlapping = Booking.objects.filter(
            room_type=room_type,
            status__in=['PENDING', 'PAID', 'CONFIRMED'],
            check_in__lt=check_out,
            check_out__gt=check_in
        )
        
        booked_count = overlapping.aggregate(total=Sum('rooms_booked'))['total'] or 0
        available = max(0, room_type.total_rooms - booked_count)
        
        print(f"   - Overlapping bookings: {overlapping.count()}")
        print(f"   - Total rooms booked in period: {booked_count}")
        print(f"   - Available rooms: {available}")
        
        # Use the model method
        available_method = room_type.get_available_rooms(check_in, check_out)
        print(f"   - get_available_rooms() returns: {available_method}")
        
        if available != available_method:
            print(f"   ❌ ERROR: Mismatch! Manual: {available}, Method: {available_method}")
        else:
            print(f"   ✓ Calculations match")

# 4. Test the API response format
print_subheader("4. TEST AVAILABILITY API RESPONSE")
from hotels.models import RoomType as RT
from hotels.serializers import AvailabilityCheckSerializer

for hotel in hotels:
    print(f"\n🏨 Hotel: {hotel.name} (ID: {hotel.id})")
    
    # Test the availability check serializer
    request_data = {
        'hotel': hotel.id,
        'check_in': str(check_in),
        'check_out': str(check_out),
        'rooms_needed': 1
    }
    
    serializer = AvailabilityCheckSerializer(data=request_data)
    if serializer.is_valid():
        availability = serializer.get_availability()
        print(f"   API Response Status: ✓ Valid")
        print(f"   Has availability: {availability.get('has_availability')}")
        print(f"   Room types in response: {len(availability.get('room_types', []))}")
        
        for rt in availability.get('room_types', []):
            print(f"\n   - {rt['type_display']}")
            print(f"     Total: {rt['total_rooms']}")
            print(f"     Available: {rt['available_rooms']}")
            print(f"     Is available: {rt['is_available']}")
            
            if rt['total_rooms'] == 0 or rt['total_rooms'] is None:
                print(f"     ❌ ERROR: total_rooms is {rt['total_rooms']}")
    else:
        print(f"   ❌ API Error: {serializer.errors}")

# 5. Summary and recommendations
print_subheader("5. DIAGNOSTIC SUMMARY")

issues_found = []

# Check for zero total_rooms
for hotel in hotels:
    for room_type in hotel.room_types.all():
        if not room_type.total_rooms or room_type.total_rooms <= 0:
            issues_found.append(
                f"Room type '{room_type.get_type_display()}' in '{hotel.name}' "
                f"has total_rooms={room_type.total_rooms}"
            )

if issues_found:
    print("\n❌ ISSUES FOUND:")
    for i, issue in enumerate(issues_found, 1):
        print(f"   {i}. {issue}")
else:
    print("\n✓ No obvious data issues found")
    print("  If the issue persists, check:")
    print("  1. Frontend is using correct hotel ID")
    print("  2. API endpoint is returning room_types array")
    print("  3. Browser DevTools shows what API response contains")

print_header("END OF DIAGNOSTICS")
print("\nNext steps:")
print("1. Check Django shell: python manage.py shell")
print("2. Run: from hotels.models import Hotel, RoomType")
print("3. Then: Hotel.objects.all().values()")
print("4. Then: RoomType.objects.all().values()")

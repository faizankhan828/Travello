"""Check actual itinerary structure to understand data format"""

import sys
sys.path.insert(0, r'f:\FYP\Travello\backend\travello_backend')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')

import django
django.setup()

from itineraries.models import Itinerary

# Get a sample itinerary
itinerary = Itinerary.objects.filter(city='Lahore').first()

if itinerary:
    print("=" * 70)
    print("SAMPLE ITINERARY STRUCTURE")
    print("=" * 70)
    print(f"\nItinerary ID: {itinerary.id}")
    print(f"Mood: {itinerary.mood}")
    print(f"Budget: {itinerary.budget_level}")
    print(f"Pace: {itinerary.pace}")
    print(f"Start: {itinerary.start_date}, End: {itinerary.end_date}")
    print(f"Interests: {itinerary.interests}")
    print(f"\nDays structure (type={type(itinerary.days)}):")
    print(f"  Length: {len(itinerary.days)}")
    
    if itinerary.days:
        print(f"\n  Day 0 (type={type(itinerary.days[0])}):")
        day = itinerary.days[0]
        print(f"    Keys: {day.keys() if isinstance(day, dict) else 'N/A'}")
        print(f"    Full content: {day}")
        
        if isinstance(day, dict) and 'items' in day:
            print(f"\n    Items (count={len(day['items'])}):")
            for i, item in enumerate(day['items'][:3]):  # Show first 3
                print(f"      Item {i}: {item}")
else:
    print("No itineraries found")

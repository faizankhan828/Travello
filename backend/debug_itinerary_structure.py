#!/usr/bin/env python
"""Debug script to check itinerary data structure"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
django.setup()

from itineraries.models import Itinerary, Place
import json

print("="*80)
print("DEBUGGING ITINERARY DATA STRUCTURE")
print("="*80)

# Get first few itineraries
itineraries = Itinerary.objects.all()[:3]
print(f"\nFound {Itinerary.objects.count()} total itineraries")
print(f"Checking first 3 itineraries:\n")

for it in itineraries:
    print(f"\n{'-'*80}")
    print(f"Itinerary ID: {it.id}, User: {it.user.username if it.user else 'None'}")
    print(f"Days type: {type(it.days).__name__}")
    print(f"Days is None: {it.days is None}")
    print(f"Days is empty: {len(it.days) == 0 if it.days else 'N/A'}")
    
    if it.days:
        print(f"\nDays (pretty print):")
        if isinstance(it.days, list):
            print(f"  List with {len(it.days)} elements")
            if len(it.days) > 0:
                print(f"  First day type: {type(it.days[0])}")
                print(f"  First day: {json.dumps(it.days[0], indent=4, default=str)[:500]}")
        else:
            print(f"  Value: {it.days[:500]}")

# Check places count
places_count = Place.objects.count()
print(f"\n{'-'*80}")
print(f"\nTotal places in database: {places_count}")

if places_count > 0:
    sample_place = Place.objects.first()
    print(f"Sample place: {sample_place.name} (ID: {sample_place.id})")
    print(f"  Category: {sample_place.category}")
    print(f"  Rating: {sample_place.average_rating}")

print(f"\n{'='*80}")

#!/usr/bin/env python
"""
Verification script to test the fix for admin rooms booking.

This script tests that the API now returns consistent response format.
"""

import os
import sys
import django

sys.path.insert(0, '/f:/FYP/Travello/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
django.setup()

from hotels.models import Hotel, RoomType, Booking
from hotels.serializers import AvailabilityCheckSerializer
from django.utils import timezone
from datetime import timedelta

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_subheader(text):
    print(f"\n--- {text} ---")

print_header("ADMIN ROOMS BOOKING FIX VERIFICATION")

check_in = (timezone.now().date() + timedelta(days=1)).isoformat()
check_out = (timezone.now().date() + timedelta(days=4)).isoformat()

# Test 1: Get all hotels
hotels = Hotel.objects.all().prefetch_related('room_types')
if not hotels:
    print("❌ No hotels found!")
    sys.exit(1)

print(f"✅ Found {hotels.count()} hotels")

# Test 2: Test API response format consistency
print_subheader("TESTING API RESPONSE FORMAT CONSISTENCY")

test_results = []

for hotel in hotels[:3]:  # Test first 3 hotels
    if not hotel.room_types.exists():
        continue
    
    room_type = hotel.room_types.first()
    
    print(f"\n🏨 Hotel: {hotel.name} (ID: {hotel.id})")
    
    # Test Case 1: No specific room type (get all)
    print(f"   Test 1: No specific room type (get all)")
    request_data_all = {
        'hotel': hotel.id,
        'check_in': check_in,
        'check_out': check_out,
    }
    
    serializer_all = AvailabilityCheckSerializer(data=request_data_all)
    if serializer_all.is_valid():
        response_all = serializer_all.get_availability()
        has_room_types_key = 'room_types' in response_all
        is_room_types_list = isinstance(response_all.get('room_types'), list)
        
        print(f"      ✓ Has 'room_types' key: {has_room_types_key}")
        print(f"      ✓ room_types is list: {is_room_types_list}")
        print(f"      ✓ Number of room types: {len(response_all.get('room_types', []))}")
        
        if has_room_types_key and is_room_types_list:
            test_results.append(("All rooms", True))
        else:
            test_results.append(("All rooms", False))
    else:
        print(f"      ❌ Serializer error: {serializer_all.errors}")
        test_results.append(("All rooms", False))
    
    # Test Case 2: Specific room type
    print(f"\n   Test 2: Specific room type (room_id: {room_type.id})")
    request_data_specific = {
        'hotel': hotel.id,
        'room_type': room_type.id,
        'check_in': check_in,
        'check_out': check_out,
    }
    
    serializer_specific = AvailabilityCheckSerializer(data=request_data_specific)
    if serializer_specific.is_valid():
        response_specific = serializer_specific.get_availability()
        has_room_types_key = 'room_types' in response_specific
        is_room_types_list = isinstance(response_specific.get('room_types'), list)
        num_rooms = len(response_specific.get('room_types', []))
        
        print(f"      ✓ Has 'room_types' key: {has_room_types_key}")
        print(f"      ✓ room_types is list: {is_room_types_list}")
        print(f"      ✓ Number of room types: {num_rooms}")
        
        # Verify it's exactly 1 room type
        if has_room_types_key and is_room_types_list and num_rooms == 1:
            print(f"      ✓ Response contains exactly 1 room type (correct)")
            test_results.append(("Specific room", True))
        elif num_rooms != 1:
            print(f"      ⚠️ Expected 1 room type, got {num_rooms}")
            test_results.append(("Specific room", False))
        else:
            print(f"      ❌ Response format incorrect")
            test_results.append(("Specific room", False))
    else:
        print(f"      ❌ Serializer error: {serializer_specific.errors}")
        test_results.append(("Specific room", False))

# Test 3: Verify structure matches frontend expectations
print_subheader("VERIFYING FRONTEND COMPATIBILITY")

hotel = hotels.first()
room_type = hotel.room_types.first()

request_data = {
    'hotel': hotel.id,
    'room_type': room_type.id,
    'check_in': check_in,
    'check_out': check_out,
    'rooms_needed': 1,
}

serializer = AvailabilityCheckSerializer(data=request_data)
if serializer.is_valid():
    response = serializer.get_availability()
    
    # Simulate frontend code
    print(f"\nSimulating frontend HotelDetailPage.js code:")
    print(f"  availability = {response}\n")
    
    # This is the exact code from frontend (line 294)
    test_room = room_type  # The room being rendered
    liveAvailability = response.get('room_types', [])  # This is what gets extracted
    found_room = None
    for rt in liveAvailability:
        if rt['id'] == test_room.id:
            found_room = rt
            break
    
    if found_room:
        print(f"  ✓ Frontend can find room in response: {test_room.type}")
        print(f"  ✓ Available rooms: {found_room['available_rooms']}")
        print(f"  ✓ Display will show: Available: {found_room['available_rooms']}")
        test_results.append(("Frontend compat", True))
    else:
        print(f"  ❌ Frontend CANNOT find room in response!")
        test_results.append(("Frontend compat", False))
else:
    print(f"❌ Serializer error: {serializer.errors}")
    test_results.append(("Frontend compat", False))

# Summary
print_subheader("TEST SUMMARY")
all_passed = True
for test_name, passed in test_results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if not passed:
        all_passed = False

print_subheader("CONCLUSION")
if all_passed:
    print("✅ ALL TESTS PASSED!")
    print("\nThe fix is working correctly:")
    print("  • API response format is now consistent")
    print("  • Frontend can parse both single and multiple room responses")
    print("  • Room availability data will display correctly")
    print("  • Booking should now work for admin-added rooms")
else:
    print("❌ SOME TESTS FAILED")
    print("Please review the failures above")

print_header("END OF VERIFICATION")

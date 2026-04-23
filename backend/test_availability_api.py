"""
Test the hotel availability API to verify it's working correctly
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.settings')
django.setup()

from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from authentication.models import User
from hotels.models import Hotel, RoomType, Booking
import json


def test_availability_api():
    """Test the availability API endpoint"""
    
    print("\n" + "="*80)
    print(" HOTEL AVAILABILITY API TEST")
    print("="*80)
    
    # Clean up test data
    Hotel.objects.filter(name="Test Hotel API").delete()
    
    # Create test data
    print("\n1. Creating test hotel and room types...")
    hotel = Hotel.objects.create(
        name="Test Hotel API",
        city="Lahore",
        address="Test St",
        description="For API testing",
        rating=4.5
    )
    print(f"   ✓ Hotel created: {hotel.id}")
    
    room_type = RoomType.objects.create(
        hotel=hotel,
        type='double',
        price_per_night=Decimal('100.00'),
        total_rooms=50,
        max_occupancy=2
    )
    print(f"   ✓ Room type created: {room_type.id} (50 total rooms)")
    
    # Test 1: No bookings - should show 50 available
    print("\n2. Test Case 1: No bookings")
    check_in = date.today() + timedelta(days=5)
    check_out = check_in + timedelta(days=3)
    
    available = room_type.get_available_rooms(check_in, check_out)
    print(f"   Check-in: {check_in}")
    print(f"   Check-out: {check_out}")
    print(f"   Available rooms: {available}")
    print(f"   Expected: 50")
    print(f"   ✓ PASS" if available == 50 else f"   ✗ FAIL")
    
    # Test 2: Create a booking
    print("\n3. Test Case 2: After creating 5 room booking")
    user = User.objects.create_user(username='testuser', email='test@test.com', password='test')
    
    booking = Booking.objects.create(
        user=user,
        hotel=hotel,
        room_type=room_type,
        rooms_booked=5,
        check_in=check_in,
        check_out=check_out,
        total_price=Decimal('500.00'),
        status='CONFIRMED'
    )
    print(f"   Created booking with 5 rooms")
    
    available = room_type.get_available_rooms(check_in, check_out)
    print(f"   Available rooms now: {available}")
    print(f"   Expected: 45")
    print(f"   ✓ PASS" if available == 45 else f"   ✗ FAIL")
    
    # Test 3: Non-overlapping dates
    print("\n4. Test Case 3: Non-overlapping dates")
    later_check_in = check_out + timedelta(days=1)
    later_check_out = later_check_in + timedelta(days=2)
    
    available = room_type.get_available_rooms(later_check_in, later_check_out)
    print(f"   Check-in: {later_check_in} (after booking ends)")
    print(f"   Check-out: {later_check_out}")
    print(f"   Available rooms: {available}")
    print(f"   Expected: 50")
    print(f"   ✓ PASS" if available == 50 else f"   ✗ FAIL")
    
    # Test 4: Cancel booking
    print("\n5. Test Case 4: After cancellation")
    booking.status = 'CANCELLED'
    booking.save()
    
    available = room_type.get_available_rooms(check_in, check_out)
    print(f"   Booking cancelled")
    print(f"   Available rooms: {available}")
    print(f"   Expected: 50")
    print(f"   ✓ PASS" if available == 50 else f"   ✗ FAIL")
    
    # Test 5: Get inventory status
    print("\n6. Test Case 5: Inventory status report")
    booking.status = 'CONFIRMED'  # Re-enable for test
    booking.save()
    
    status = room_type.get_inventory_status(check_in, check_out)
    print(f"   Total rooms: {status['total_rooms']}")
    print(f"   Booked rooms: {status['booked_rooms']}")
    print(f"   Available rooms: {status['available_rooms']}")
    print(f"   Active bookings: {status['active_bookings']}")
    print(f"   Sanity check: {status['sanity_check']}")
    
    expected_booked = 5
    expected_available = 45
    booked_ok = status['booked_rooms'] == expected_booked
    available_ok = status['available_rooms'] == expected_available
    print(f"   Booked: {'✓ PASS' if booked_ok else '✗ FAIL'}")
    print(f"   Available: {'✓ PASS' if available_ok else '✗ FAIL'}")
    
    # Test 6: Multiple bookings
    print("\n7. Test Case 6: Multiple overlapping bookings")
    booking2 = Booking.objects.create(
        user=user,
        hotel=hotel,
        room_type=room_type,
        rooms_booked=3,
        check_in=check_in,
        check_out=check_out,
        total_price=Decimal('300.00'),
        status='PENDING'
    )
    
    available = room_type.get_available_rooms(check_in, check_out)
    print(f"   Created 2nd booking with 3 rooms (1st has 5 rooms)")
    print(f"   Available rooms: {available}")
    print(f"   Expected: 42 (50 - 5 - 3)")
    print(f"   ✓ PASS" if available == 42 else f"   ✗ FAIL")
    
    # Test 7: Check availability for specific room type via API
    print("\n8. Test Case 7: API response format check")
    availability_data = RoomType.check_availability_for_hotel(hotel, check_in, check_out)
    
    print(f"   Response contains room_types: {bool(availability_data)}")
    if availability_data:
        for room_id, info in availability_data.items():
            print(f"   - Room {room_id}:")
            print(f"     total_rooms: {info['total_rooms']}")
            print(f"     available_rooms: {info['available_rooms']}")
            print(f"     is_available: {info['is_available']}")
    
    print("\n" + "="*80)
    print(" API TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    try:
        test_availability_api()
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

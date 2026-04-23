"""
Hotel Room Inventory System - Comprehensive Tests
Tests for booking creation, cancellation, and inventory integrity
"""

import pytest
from django.test import TestCase, TransactionTestCase, Client
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from authentication.models import User
from hotels.models import Hotel, RoomType, Booking


class HotelInventoryTestCase(TransactionTestCase):
    """Transaction-based tests to properly test database locking and inventory"""
    
    def setUp(self):
        """Create test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        # Create hotel
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            city='Lahore',
            address='123 Main St',
            description='Test hotel for inventory tests',
            rating=4.5
        )
        
        # Create room types
        self.room_double = RoomType.objects.create(
            hotel=self.hotel,
            type='double',
            price_per_night=Decimal('100.00'),
            total_rooms=5,
            max_occupancy=2
        )
        
        self.room_suite = RoomType.objects.create(
            hotel=self.hotel,
            type='suite',
            price_per_night=Decimal('200.00'),
            total_rooms=2,
            max_occupancy=4
        )
        
        # Set check-in/out dates
        self.today = timezone.now().date()
        self.check_in = self.today + timedelta(days=1)
        self.check_out = self.check_in + timedelta(days=3)
    
    def test_inventory_calculation_basic(self):
        """Test 1: Basic inventory calculation"""
        print("\n✓ TEST 1: Basic Inventory Calculation")
        
        # Before any bookings
        available = self.room_double.get_available_rooms(self.check_in, self.check_out)
        self.assertEqual(available, 5, f"Should have 5 available rooms, got {available}")
        print(f"  ✓ Initial available rooms: {available}")
        
        # Book 2 rooms
        booking = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        # After booking
        available = self.room_double.get_available_rooms(self.check_in, self.check_out)
        self.assertEqual(available, 3, f"Should have 3 available rooms, got {available}")
        print(f"  ✓ After booking 2 rooms: {available} available")
    
    def test_inventory_multiple_bookings(self):
        """Test 2: Multiple overlapping bookings"""
        print("\n✓ TEST 2: Multiple Overlapping Bookings")
        
        initial = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  Initial: {initial} rooms")
        
        # Create 3 bookings
        bookings = []
        for i in range(3):
            booking = Booking.objects.create(
                user=self.user,
                hotel=self.hotel,
                room_type=self.room_double,
                rooms_booked=1,
                check_in=self.check_in,
                check_out=self.check_out,
                total_price=Decimal('100.00'),
                status='PENDING'
            )
            bookings.append(booking)
            available = self.room_double.get_available_rooms(self.check_in, self.check_out)
            print(f"  After booking {i+1}: {available} rooms available")
            self.assertEqual(available, initial - (i + 1))

    def test_admin_snapshot_availability_updates_for_upcoming_booking(self):
        """Admin snapshot availability should decrement immediately for upcoming bookings."""
        print("\n✓ TEST: Admin Snapshot Availability")

        before = self.room_double.available_rooms
        self.assertEqual(before, 5, f"Expected initial snapshot availability 5, got {before}")

        Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=1,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('100.00'),
            status='PENDING'
        )

        after = self.room_double.available_rooms
        print(f"  Snapshot availability: {before} -> {after}")
        self.assertEqual(after, 4, f"Expected snapshot availability 4 after booking, got {after}")
    
    def test_inventory_cancellation_restoration(self):
        """Test 3: Inventory restoration on cancellation"""
        print("\n✓ TEST 3: Inventory Restoration on Cancellation")
        
        before = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  Before booking: {before} available")
        
        # Create booking
        booking = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        during = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  During booking: {during} available (2 booked)")
        self.assertEqual(during, before - 2)
        
        # Cancel booking
        booking.status = 'CANCELLED'
        booking.save()
        
        after = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  After cancellation: {after} available (restored)")
        self.assertEqual(after, before, "Should restore to original availability")
    
    def test_inventory_non_overlapping_dates(self):
        """Test 4: Non-overlapping date ranges don't affect availability"""
        print("\n✓ TEST 4: Non-Overlapping Dates")
        
        # Book for dates 1-3
        booking1 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=3,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('900.00'),
            status='PENDING'
        )
        
        # Check availability for dates 4-6 (no overlap)
        later_checkin = self.check_out + timedelta(days=1)
        later_checkout = later_checkin + timedelta(days=2)
        
        available = self.room_double.get_available_rooms(later_checkin, later_checkout)
        print(f"  Booking 1: {self.check_in} to {self.check_out}")
        print(f"  Availability check: {later_checkin} to {later_checkout}")
        print(f"  Available rooms (non-overlapping): {available}")
        self.assertEqual(available, 5, "Non-overlapping dates should show full availability")
    
    def test_inventory_partial_overlap(self):
        """Test 5: Partial overlaps are handled correctly"""
        print("\n✓ TEST 5: Partial Date Overlaps")
        
        # Book for dates 1-3
        booking1 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        # Check for dates that partially overlap (2-4)
        overlap_checkin = self.check_in + timedelta(days=1)
        overlap_checkout = self.check_out + timedelta(days=1)
        
        available = self.room_double.get_available_rooms(overlap_checkin, overlap_checkout)
        print(f"  Booking: {self.check_in} to {self.check_out} (2 rooms)")
        print(f"  Check: {overlap_checkin} to {overlap_checkout}")
        print(f"  Available (2-room booking still active): {available}")
        self.assertEqual(available, 3, "Partial overlap should affect availability")
    
    def test_cancelled_bookings_dont_count(self):
        """Test 6: Cancelled bookings are excluded from availability calculation"""
        print("\n✓ TEST 6: Cancelled Bookings Excluded")
        
        # Create 2 bookings
        booking1 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        with_both = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  With 2 bookings (4 rooms): {with_both} available")
        self.assertEqual(with_both, 1)
        
        # Cancel first booking
        booking1.status = 'CANCELLED'
        booking1.save()
        
        with_one = self.room_double.get_available_rooms(self.check_in, self.check_out)
        print(f"  After cancelling 1st booking: {with_one} available")
        self.assertEqual(with_one, 3, "Cancelled booking should be excluded")
    
    def test_inventory_status_report(self):
        """Test 7: Inventory status reporting"""
        print("\n✓ TEST 7: Inventory Status Report")
        
        # Create mixed bookings
        booking1 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=2,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('600.00'),
            status='PENDING'
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            room_type=self.room_double,
            rooms_booked=1,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=Decimal('300.00'),
            status='CONFIRMED'
        )
        
        status = self.room_double.get_inventory_status(self.check_in, self.check_out)
        
        print(f"  Total rooms: {status['total_rooms']}")
        print(f"  Booked rooms: {status['booked_rooms']}")
        print(f"  Available rooms: {status['available_rooms']}")
        print(f"  Active bookings: {status['active_bookings']}")
        print(f"  Sanity check: {'✓ PASS' if status['sanity_check'] else '✗ FAIL'}")
        
        self.assertEqual(status['total_rooms'], 5)
        self.assertEqual(status['booked_rooms'], 3)
        self.assertEqual(status['available_rooms'], 2)
        self.assertEqual(status['active_bookings'], 2)
        self.assertTrue(status['sanity_check'])
    
    def test_inventory_integrity_verification(self):
        """Test 8: Inventory integrity verification"""
        print("\n✓ TEST 8: Inventory Integrity Verification")
        
        # Create valid bookings
        for i in range(3):
            Booking.objects.create(
                user=self.user,
                hotel=self.hotel,
                room_type=self.room_double,
                rooms_booked=1,
                check_in=self.check_in,
                check_out=self.check_out,
                total_price=Decimal('100.00'),
                status='PENDING'
            )
        
        verification = self.room_double.verify_inventory_integrity(self.check_in, self.check_out)
        
        print(f"  Valid: {verification['valid']}")
        print(f"  Total: {verification['total_rooms']}")
        print(f"  Booked: {verification['booked_rooms']}")
        print(f"  Available: {verification['available_rooms']}")
        print(f"  Errors: {verification['errors'] or 'None'}")
        
        self.assertTrue(verification['valid'])
        self.assertEqual(verification['booked_rooms'], 3)
        self.assertEqual(verification['available_rooms'], 2)
        self.assertEqual(len(verification['errors']), 0)
    
    def test_overbooking_detection(self):
        """Test 9: Overbooking detection in integrity check"""
        print("\n✓ TEST 9: Overbooking Detection")
        
        # Try to manually create overbooking (bypassing normal validation)
        # This simulates a potential data corruption scenario
        bookings = []
        for i in range(6):  # Try to book 6 rooms when only 5 exist
            booking = Booking(
                user=self.user,
                hotel=self.hotel,
                room_type=self.room_double,
                rooms_booked=1,
                check_in=self.check_in,
                check_out=self.check_out,
                total_price=Decimal('100.00'),
                status='PENDING'
            )
            bookings.append(booking)
        
        # Bulk create to bypass model validation
        Booking.objects.bulk_create(bookings)
        
        verification = self.room_double.verify_inventory_integrity(self.check_in, self.check_out)
        
        print(f"  Valid: {verification['valid']}")
        print(f"  Total: {verification['total_rooms']}")
        print(f"  Booked: {verification['booked_rooms']}")
        print(f"  Errors: {verification['errors']}")
        
        self.assertFalse(verification['valid'], "Should detect overbooking")
        self.assertTrue(len(verification['errors']) > 0)
        print(f"  ✓ Detected overbooking error: {verification['errors'][0][:50]}...")


class HotelBookingAPITestCase(TestCase):
    """API-level tests for booking creation"""
    
    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.hotel = Hotel.objects.create(
            name='Test Hotel',
            city='Lahore',
            address='123 Main St',
            description='Test hotel',
            rating=4.5
        )
        
        self.room_type = RoomType.objects.create(
            hotel=self.hotel,
            type='double',
            price_per_night=Decimal('100.00'),
            total_rooms=3,
            max_occupancy=2
        )
        
        self.today = timezone.now().date()
        self.check_in = self.today + timedelta(days=1)
        self.check_out = self.check_in + timedelta(days=2)
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_booking_inventory_response(self):
        """Test 10: API returns inventory status in booking response"""
        print("\n✓ TEST 10: API Booking Response Includes Inventory")
        
        payload = {
            'hotel': self.hotel.id,
            'room_type': self.room_type.id,
            'rooms_booked': 1,
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'adults': 1,
            'children': 0,
            'payment_method': 'ARRIVAL',
            'guest_name': 'Test User',
            'guest_email': 'test@example.com',
            'guest_phone': '1234567890'
        }
        
        response = self.client.post('/api/bookings/create/', payload)
        print(f"  Response status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            if 'inventory_status' in data:
                print(f"  ✓ Inventory status in response:")
                print(f"    Before: {data['inventory_status']['before_booking']}")
                print(f"    After: {data['inventory_status']['after_booking']}")
                print(f"    Booked: {data['inventory_status']['rooms_booked']}")


if __name__ == '__main__':
    import django
    django.setup()
    
    # Run tests
    print("\n" + "="*70)
    print(" HOTEL ROOM INVENTORY SYSTEM - TEST SUITE")
    print("="*70)
    
    pytest.main([__file__, '-v', '-s'])

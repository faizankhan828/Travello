#!/usr/bin/env python
"""
Hotel Availability Calculation - Detailed Analysis
Analyzes backend logic WITHOUT running Django
"""

import sys
from datetime import date, timedelta

print("\n" + "="*80)
print(" HOTEL AVAILABILITY LOGIC - DETAILED ANALYSIS")
print("="*80)

# Simulate the availability calculation logic
def simulate_get_available_rooms(total_rooms, bookings, check_in, check_out):
    """
    Simulate RoomType.get_available_rooms()
    
    Args:
        total_rooms: Total rooms in room type
        bookings: List of dicts with {check_in, check_out, rooms_booked, status}
        check_in: Date to check availability from
        check_out: Date to check availability to
    
    Returns:
        Number of available rooms
    """
    booked = 0
    
    for booking in bookings:
        # Check if booking overlaps with requested period
        # Overlap rule: booking.check_in < requested.check_out AND booking.check_out > requested.check_in
        if booking['check_in'] < check_out and booking['check_out'] > check_in:
            # Only count if status is PENDING, PAID, or CONFIRMED
            if booking['status'] in ['PENDING', 'PAID', 'CONFIRMED']:
                booked += booking['rooms_booked']
    
    available = max(0, total_rooms - booked)
    return available, booked


def format_date(date_obj):
    """Format date for display"""
    return date_obj.strftime('%Y-%m-%d')


# Test Case 1: No bookings
print("\n▌ TEST 1: No Bookings")
print("-" * 80)
today = date.today()
check_in = today + timedelta(days=5)
check_out = check_in + timedelta(days=3)

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=[],
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Bookings: None")
print(f"Period: {format_date(check_in)} to {format_date(check_out)}")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 50 available, 0 booked")
print(f"Status: {'✓ PASS' if available == 50 and booked == 0 else '✗ FAIL'}")


# Test Case 2: One overlapping booking
print("\n▌ TEST 2: One Overlapping Booking")
print("-" * 80)
bookings = [{
    'check_in': check_in,
    'check_out': check_out,
    'rooms_booked': 5,
    'status': 'CONFIRMED'
}]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Bookings: 1 (5 rooms, {format_date(check_in)} to {format_date(check_out)}, CONFIRMED)")
print(f"Period: {format_date(check_in)} to {format_date(check_out)}")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 45 available, 5 booked")
print(f"Status: {'✓ PASS' if available == 45 and booked == 5 else '✗ FAIL'}")


# Test Case 3: Partial overlap
print("\n▌ TEST 3: Partial Overlap (Booking ends before checkout)")
print("-" * 80)
middle_date = check_in + timedelta(days=1)
bookings = [{
    'check_in': check_in,
    'check_out': middle_date,  # Ends day 1
    'rooms_booked': 3,
    'status': 'PENDING'
}]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Booking: 3 rooms, {format_date(check_in)} to {format_date(middle_date)} (ends day 1)")
print(f"Check period: {format_date(check_in)} to {format_date(check_out)} (3 days)")
print(f"Overlap: YES - booking overlaps our dates")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 47 available, 3 booked (partial overlap counts)")
print(f"Status: {'✓ PASS' if available == 47 and booked == 3 else '✗ FAIL'}")


# Test Case 4: No overlap - booking after
print("\n▌ TEST 4: No Overlap (Booking after period)")
print("-" * 80)
later_check_in = check_out + timedelta(days=1)
later_check_out = later_check_in + timedelta(days=2)

bookings = [{
    'check_in': check_in,
    'check_out': check_out,
    'rooms_booked': 5,
    'status': 'CONFIRMED'
}]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=later_check_in,
    check_out=later_check_out
)

print(f"Total rooms: 50")
print(f"Booking: {format_date(check_in)} to {format_date(check_out)}")
print(f"Check period: {format_date(later_check_in)} to {format_date(later_check_out)}")
print(f"Overlap: NO - booking ends before our check-in")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 50 available, 0 booked")
print(f"Status: {'✓ PASS' if available == 50 and booked == 0 else '✗ FAIL'}")


# Test Case 5: Multiple overlapping bookings
print("\n▌ TEST 5: Multiple Overlapping Bookings")
print("-" * 80)
bookings = [
    {
        'check_in': check_in,
        'check_out': check_out,
        'rooms_booked': 5,
        'status': 'CONFIRMED'
    },
    {
        'check_in': check_in + timedelta(days=1),
        'check_out': check_out,
        'rooms_booked': 3,
        'status': 'PENDING'
    },
    {
        'check_in': check_in,
        'check_out': check_out,
        'rooms_booked': 2,
        'status': 'PAID'
    }
]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Booking 1: 5 rooms, {format_date(check_in)} to {format_date(check_out)}, CONFIRMED")
print(f"Booking 2: 3 rooms, {format_date(check_in + timedelta(days=1))} to {format_date(check_out)}, PENDING")
print(f"Booking 3: 2 rooms, {format_date(check_in)} to {format_date(check_out)}, PAID")
print(f"Check period: {format_date(check_in)} to {format_date(check_out)}")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 40 available, 10 booked (all overlap)")
print(f"Status: {'✓ PASS' if available == 40 and booked == 10 else '✗ FAIL'}")


# Test Case 6: Cancelled booking should not count
print("\n▌ TEST 6: Cancelled Booking (Should Not Count)")
print("-" * 80)
bookings = [
    {
        'check_in': check_in,
        'check_out': check_out,
        'rooms_booked': 5,
        'status': 'CONFIRMED'
    },
    {
        'check_in': check_in,
        'check_out': check_out,
        'rooms_booked': 10,
        'status': 'CANCELLED'  # Should NOT be counted
    }
]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Booking 1: 5 rooms, CONFIRMED (COUNTS)")
print(f"Booking 2: 10 rooms, CANCELLED (DOES NOT COUNT)")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 45 available, 5 booked (cancelled ignored)")
print(f"Status: {'✓ PASS' if available == 45 and booked == 5 else '✗ FAIL'}")


# Test Case 7: Edge case - booking starts on checkout date
print("\n▌ TEST 7: Edge Case - Booking Starts on Checkout")
print("-" * 80)
bookings = [{
    'check_in': check_out,  # Starts exactly when we checkout
    'check_out': check_out + timedelta(days=2),
    'rooms_booked': 5,
    'status': 'CONFIRMED'
}]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Our period: {format_date(check_in)} to {format_date(check_out)}")
print(f"Booking: starts on {format_date(check_out)}")
print(f"Overlap: NO (booking.check_in == our.check_out, which means no overlap)")
print(f"Booked: {booked}")
print(f"Available: {available}")
print(f"Expected: 50 available, 0 booked")
print(f"Status: {'✓ PASS' if available == 50 and booked == 0 else '✗ FAIL'}")


# Test Case 8: Overbooking scenario
print("\n▌ TEST 8: Overbooking Detection")
print("-" * 80)
bookings = [
    {'check_in': check_in, 'check_out': check_out, 'rooms_booked': 30, 'status': 'CONFIRMED'},
    {'check_in': check_in, 'check_out': check_out, 'rooms_booked': 25, 'status': 'CONFIRMED'},
]

available, booked = simulate_get_available_rooms(
    total_rooms=50,
    bookings=bookings,
    check_in=check_in,
    check_out=check_out
)

print(f"Total rooms: 50")
print(f"Booking 1: 30 rooms")
print(f"Booking 2: 25 rooms")
print(f"Total booked: {booked} (EXCEEDS total_rooms!)")
print(f"Available: {available} (clamped to 0)")
print(f"Status: OVERBOOKING DETECTED ❌")
print(f"Note: Backend should catch this and prevent it!")


print("\n" + "="*80)
print(" OVERLAP LOGIC EXPLANATION")
print("="*80)
print("""
Two date ranges overlap if:
  booking.check_in < requested.check_out
  AND
  booking.check_out > requested.check_in

Examples:
1. Booking: 5-7, Request: 6-8 ✓ OVERLAP
   - 5 < 8 (booking starts before request ends) ✓
   - 7 > 6 (booking ends after request starts) ✓

2. Booking: 5-6, Request: 6-8 ✗ NO OVERLAP
   - 5 < 8 ✓
   - 6 > 6 ✗ (booking ends exactly when request starts)

3. Booking: 8-9, Request: 5-7 ✗ NO OVERLAP
   - 8 < 7 ✗ (booking starts after request ends)
""")

print("="*80)
print(" AVAILABILITY LOGIC SUMMARY")
print("="*80)
print("""
1. Find all bookings that OVERLAP with requested dates
2. Include ONLY statuses: PENDING, PAID, CONFIRMED
3. Exclude: CANCELLED, COMPLETED
4. Sum rooms_booked from all overlapping bookings
5. Available = total_rooms - booked_sum
6. Result is always >= 0 (clamped)
""")

print("\n✓ ANALYSIS COMPLETE\n")

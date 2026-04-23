# Hotel Room Inventory Issue - Root Cause Analysis

**Status:** DIAGNOSTIC PHASE
**Date:** April 15, 2026
**Issue:** Room counts not updating on booking/cancellation

---

## STEP 1: DATA FLOW UNDERSTANDING

### Current Architecture

```
Hotel Model (1)
    ↓
    └─→ [room_types] (many RoomType)
            ├─ total_rooms: IntegerField (static - set by admin)
            ├─ get_available_rooms(check_in, check_out): Method
            │   └─ Calculates: total_rooms - booked_in_period
            ├─ available_rooms: @property (convenience wrapper)
            │   └─ Calls get_available_rooms() with no date args
            └─ bookings (many Booking - related_name='bookings')

Booking Model
    ├─ room_type: FK → RoomType
    ├─ rooms_booked: IntegerField
    ├─ check_in: DateField
    ├─ check_out: DateField
    ├─ status: CharField (PENDING, PAID, CONFIRMED, CANCELLED, COMPLETED)
    └─ created_at, updated_at: timestamps
```

### Key Models

#### Hotel Model
```python
@property
def total_rooms(self):
    """Calculate total rooms across all room types"""
    return sum(room_type.total_rooms for room_type in self.room_types.all())

@property
def available_rooms(self):
    """Calculate available rooms across all room types"""
    return sum(room_type.available_rooms for room_type in self.room_types.all())
```

#### RoomType Model
```python
total_rooms = models.IntegerField(validators=[MinValueValidator(1)])
# Note: NO available_rooms field in database

def get_available_rooms(self, check_in=None, check_out=None):
    """Calculate available rooms for a specific date range"""
    if check_in is None:
        check_in = timezone.now().date()
    if check_out is None:
        check_out = check_in + timezone.timedelta(days=1)
    
    overlapping_bookings = Booking.objects.filter(
        room_type=self,
        status__in=['PENDING', 'PAID', 'CONFIRMED'],  # ← KEY: Excludes CANCELLED
        check_in__lt=check_out,
        check_out__gt=check_in
    )
    
    booked = overlapping_bookings.aggregate(
        total=Sum('rooms_booked')
    )['total'] or 0
    
    total = self.total_rooms or 0
    return max(0, total - booked)

@property
def available_rooms(self):
    """Get currently available rooms (from today onwards)"""
    return self.get_available_rooms()
```

#### Booking Model (relevant fields)
```python
room_type = ForeignKey(RoomType, related_name='bookings')
rooms_booked = IntegerField(default=1)
check_in = DateField()
check_out = DateField()
status = CharField(choices=[PENDING, PAID, CONFIRMED, CANCELLED, COMPLETED])
```

---

## STEP 2: ROOT CAUSE IDENTIFICATION

### Finding 1: Booking Creation Logic (views.py line 120-160)

**Current Implementation:**
```python
@transaction.atomic
def create(self, request, *args, **kwargs):
    """Create a new booking"""
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # ❌ NO AVAILABILITY CHECK HERE
    # ❌ NO INVENTORY DECREMENT HERE
    
    booking = serializer.save(user=request.user)
    
    if payment_method == 'ARRIVAL':
        booking.status = 'PENDING'
        booking.save()
    elif payment_method == 'ONLINE':
        booking.status = 'PENDING'
        booking.lock_room(minutes=15)
        booking.save()
    
    return Response({...})
```

**Problem:**
- ✗ No validation: `available_rooms > rooms_booked`?
- ✗ No check: Is room_type.get_available_rooms() > 0?
- ✗ No locks: What about race conditions (2 users booking simultaneously)?
- ✗ No logging: Can't track why booking succeeded despite low availability

**Result:** Users can book more rooms than available → inventory goes negative (impossible state)

---

### Finding 2: Cancellation Logic (views.py line 174-210)

**Current Implementation:**
```python
@transaction.atomic
def partial_update(self, request, *args, **kwargs):
    """Admin only - Update booking status"""
    booking = self.get_object()
    new_status = request.data.get('status', booking.status)
    
    serializer = self.get_serializer(booking, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    if new_status == 'CANCELLED' and booking.status == 'CANCELLED':
        # Just update metadata
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = request.user
        booking.cancellation_reason = request.data.get(...)
        booking.save(...)
```

**Analysis:**
- ✓ When status changes to CANCELLED, the booking is excluded from future get_available_rooms() queries
- ✓ So theoretically, available_rooms SHOULD increase automatically
- **HOWEVER:** The issue is...

---

### Finding 3: The Real Issue - Response/Display Problem

#### Scenario Analysis:

**Scenario 1: API Response Not Updated**
```
Admin Hotel Dashboard:
  Before Booking: available_rooms = 5
  User Books 2: room_type.get_available_rooms() = 3 (correct!)
  BUT API returns: available_rooms = 5 (stale!)
  
Why? Possible causes:
  a) Response is cached before decrement
  b) Serializer computes available_rooms at wrong time
  c) Database not committed yet (transaction isolation)
  d) Dashboard queries old data (N+1 query problem)
```

**Scenario 2: Frontend Shows Stale Data**
```
User Dashboard displays available_rooms from:
  - Initial API response (cached)
  - Not refreshing after each booking
  - Showing number from page load, not real-time
```

**Scenario 3: Timestamp Misalignment**
```
RoomType.get_available_rooms() uses check_in/check_out:
  - User checks availability for: 2026-04-20 to 2026-04-23
  - API returns: 5 rooms available
  - User books successfully
  - System recalculates: 4 rooms available
  - BUT on-screen still shows 5
```

---

### Finding 4: Serializer Usage Issue

In `views.py` line 50-54:
```python
@action(detail=True, methods=['get'], url_path='rooms')
def get_rooms(self, request, pk=None):
    hotel = self.get_object()
    room_types = hotel.room_types.all()
    serializer = RoomTypeDetailSerializer(room_types, many=True)
    return Response({...})
```

**Question:** What does `RoomTypeDetailSerializer` include?
- Does it call `available_rooms` property at serialization time?
- Or does it have a hardcoded/cached `available_rooms` field?

**Need to Check:** `serializers.py` to see if serializer computes live data

---

### Finding 5: The Logic is Theoretically Correct, But...

The design is actually sound:
```
RoomType.total_rooms = 10 (fixed)
RoomType.get_available_rooms() = 10 - (bookings with status in PENDING/PAID/CONFIRMED for overlapping dates)
```

When booking created: Status = PENDING → included in calculation → available decreases ✓
When booking cancelled: Status = CANCELLED → excluded from calculation → available increases ✓

**But the symptoms suggest:**
1. The calculation is not being called on response
2. OR the calculation is being called but returning wrong results
3. OR the frontend is caching old data

---

## Identified Root Causes

### Root Cause #1: Missing Availability Validation on Booking

**Location:** `views.py` BookingViewSet.create() line ~130

**Issue:**
```python
# Current: Just saves booking, no check
booking = serializer.save(user=request.user)

# Should be:
available = room_type.get_available_rooms(check_in, check_out)
if available < rooms_booked:
    raise ValidationError(
        f"Only {available} room(s) available for selected dates"
    )
```

**Impact:** Allows overbooking → inventory impossible states

---

### Root Cause #2: No Transaction Safety / Race Conditions

**Location:** `views.py` BookingViewSet.create() line ~120

**Issue:**
```python
@transaction.atomic  # Atomic block started
def create(self, request, ...):
    # Timeline:
    # T1: User A checks availability → 5 rooms
    # T2: User B checks availability → 5 rooms
    # T3: User A books 5 rooms → OK (5 - 5 = 0)
    # T4: User B books 5 rooms → OK (5 - 5 = 0) ← DOUBLE BOOKING!
    #
    # Why? Because User B's query at T2 didn't see User A's booking yet
```

**Fix Needed:**
```python
room_type = RoomType.objects.select_for_update().get(id=...)
# This locks the row until transaction ends
```

---

### Root Cause #3: Serializer Not Computing Real-Time Data

**Location:** `serializers.py` RoomTypeDetailSerializer

**Hypothesis:**
- If serializer has a field: `available_rooms = serializers.IntegerField()`
- It might be getting value at serialization time only
- Not dynamic / updated on each request

---

### Root Cause #4: Frontend Caching / Missing Refresh

**Location:** Frontend component (React)

**Hypothesis:**
- After booking succeeds, frontend doesn't refresh room availability
- Still showing number from initial page load
- No real-time update mechanism

---

## Database State Verification Needed

Before implementing fix, run these queries:

### Query 1: Check a specific hotel's rooms

```sql
SELECT 
    rt.id,
    rt.hotel_id,
    rt.type,
    rt.total_rooms,
    COUNT(CASE WHEN b.status IN ('PENDING', 'PAID', 'CONFIRMED') THEN 1 END) as booked_count,
    rt.total_rooms - COUNT(CASE WHEN b.status IN ('PENDING', 'PAID', 'CONFIRMED') THEN 1 END) as calculated_available
FROM hotels_roomtype rt
LEFT JOIN hotels_booking b ON rt.id = b.room_type_id
    AND b.check_in < CURDATE() + 1  -- Tomorrow
    AND b.check_out > CURDATE()      -- Today or later
WHERE rt.hotel_id = 1
GROUP BY rt.id, rt.hotel_id, rt.type, rt.total_rooms;
```

### Query 2: Check bookings for today

```sql
SELECT 
    b.id,
    b.room_type_id,
    b.rooms_booked,
    b.status,
    b.check_in,
    b.check_out,
    rt.total_rooms
FROM hotels_booking b
JOIN hotels_roomtype rt ON b.room_type_id = rt.id
WHERE b.check_in < CURDATE() + 1
  AND b.check_out > CURDATE()
ORDER BY rt.hotel_id, rt.type;
```

### Query 3: Check for negative/impossible states

```sql
SELECT 
    rt.id,
    rt.type,
    rt.total_rooms,
    COUNT(b.id) as total_bookings,
    SUM(CASE WHEN b.status IN ('PENDING', 'PAID', 'CONFIRMED') THEN b.rooms_booked ELSE 0 END) as booked
FROM hotels_roomtype rt
LEFT JOIN hotels_booking b ON rt.id = b.room_type_id
GROUP BY rt.id, rt.type, rt.total_rooms
HAVING booked > total_rooms;  -- ← Should return 0 rows if data is valid
```

---

## Summary: What's Actually Broken

| Component | Current State | Expected State | Gap |
|-----------|---------------|-----------------|-----|
| **DB Model** | Correct calculation logic in get_available_rooms() | ✓ | None |
| **Booking Create** | No availability check, allows overbooking | Should validate | ✗ CRITICAL |
| **Race Condition Safety** | None (no select_for_update) | Should lock row | ✗ CRITICAL |
| **Booking Cancel** | Sets status=CANCELLED | ✓ Automatically excluded from calculations | ✓ OK |
| **Serializer Response** | ??? (need to verify if includes real-time available_rooms) | Should compute at response time | ? UNCLEAR |
| **Frontend Display** | Likely cached from page load | Should refresh after each action | ? UNCLEAR |

---

## Next Steps

### Step 3: Implementation
1. Add availability validation to booking creation
2. Add row-level locking (select_for_update) to prevent race conditions
3. Ensure serializers compute real-time data
4. Add comprehensive logging for debugging
5. Verify frontend refresh mechanism

### Step 4-8: Detailed fixes follow...

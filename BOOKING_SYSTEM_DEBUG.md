# 🔍 HOTEL BOOKING SYSTEM - COMPREHENSIVE DEBUGGING

## UNDERSTANDING THE CURRENT SYSTEM

### Backend Data Flow
1. **Admin creates rooms**: Hotel → RoomType model (sets `total_rooms`)
2. **User books room**: Creates Booking record with:
   - `room_type` (ForeignKey)
   - `rooms_booked` (how many rooms)
   - `check_in`, `check_out` dates
   - `status` (PENDING, PAID, CONFIRMED, CANCELLED)
3. **Availability calculation**: `RoomType.get_available_rooms(check_in, check_out)`

### Current Implementation (from code review)

#### ✅ Models (Working Correctly)
```python
# RoomType.get_available_rooms()
1. Find overlapping bookings:
   - check_in < selected_check_out AND check_out > selected_check_in
   - Status IN ('PENDING', 'PAID', 'CONFIRMED')
2. Sum rooms from all overlapping bookings
3. Return: total_rooms - booked_sum
```

#### ✅ Backend API (Working Correctly)
- Endpoint: `POST /hotels/check-availability/`
- Response includes: `room_types[].available_rooms`

#### ❌ Frontend Display (ISSUES FOUND)

**Issue 1: booked Calculation is WRONG**
```javascript
// Current code (WRONG):
const booked = bookedRooms(room);

// bookedRooms() function does:
available = (liveAvailability ?? room.available_rooms ?? 0)
booked = total_rooms - available
```

**Problem**: `room.available_rooms` is a property that calculates from TODAY onwards, not from selected dates!

**Issue 2: "Checking..." appears then disappears**
- Correctly shows when `availabilityLoading` is true
- But if response takes time or fails silently, user sees "Checking..."

**Issue 3: Dates must trigger automatic check**
- Code has useEffect that calls on date change - ✓ Good
- But first time page loads, dates might be empty

---

## 🧪 TEST CASES TO UNDERSTAND CURRENT STATE

### Test Scenario 1: Basic Availability Calculation

```
Setup:
- Hotel: "Test Hotel"
- Room Type: "Double" with 50 total rooms
- No bookings exist

Expected:
- available_rooms should = 50

What to check:
- Go to /api/hotels/{id}/check-availability/
- Send: { hotel: 1, check_in: 2026-05-01, check_out: 2026-05-05 }
- Verify response has available_rooms: 50
```

### Test Scenario 2: After Booking

```
Setup:
- Same hotel, 50 total rooms
- Create booking: 5 rooms, 2026-05-01 to 2026-05-05, CONFIRMED

Expected:
- For same dates: available_rooms = 45
- For different dates (non-overlapping): available_rooms = 50

What to check:
- Admin: Create booking via API
- Check availability API again
- Verify booked rooms reduced availability
```

### Test Scenario 3: Cancellation

```
Setup:
- Same booking as above
- Cancel the booking (set status to CANCELLED)

Expected:
- available_rooms goes back to 50
```

---

## 🔴 IDENTIFIED PROBLEMS

### Problem 1: Frontend `booked` Calculation

**Location**: `HotelDetailPage.js` line ~97
```javascript
const booked = bookedRooms(room);

function bookedRooms() {
  const available = hasSelectedDates 
    ? liveAvailability 
    : (liveAvailability ?? room.available_rooms ?? 0);  // ❌ WRONG!
  return total_rooms - available;
}
```

**Why it's wrong**:
- `room.available_rooms` returns from TODAY onwards (default)
- But user selected dates in future
- So calculation doesn't match

**Fix**: Use API response for all calculations when dates are selected

### Problem 2: Initial Room Data Shows Zero Available

**Location**: Room card shows "Available: {available}
"
- On page load, `available` property uses today's date
- If no bookings today, shows correct number
- But user hasn't selected dates yet
- Should show total_rooms instead

**Fix**: Show total_rooms when no dates selected, show API result when dates are selected

### Problem 3: "Booked" Always Shows as Null

**Location**: `HotelDetailPage.js` line ~318
```javascript
<p>Booked: {booked == null ? '—' : booked}</p>
```

**Why it shows null**:
- If `availability` (from API) is null, then `liveAvailability` is null
- Then `available` becomes `room.available_rooms` (from today)
- Calculation tries to happen but `liveAvailability` was null
- Returns null

**Fix**: Only show booked if we have selected dates

### Problem 4: Dates Not Auto-Triggering Check

**Location**: Line 143 in useEffect
```javascript
useEffect(() => {
  if (checkIn && checkOut) {
    handleCheckAvailability();
  }
}, [checkIn, checkOut, selectedRoomTypeId, roomsBooked]);
```

**Status**: This looks correct! ✓

### Problem 5: API Response Handling

**Location**: Line 125
```javascript
const response = await hotelAPI.checkAvailability(payload);
setAvailability(response.data?.data || null);  // ✓ Looks correct
```

**Status**: Should work if API returns proper structure

---

## 🛠️ FIXING STRATEGY

### STEP 1: Fix Frontend Booked Calculation
- Don't use `room.available_rooms` property (uses today)
- Always use API response when available
- Show calculated booked rooms correctly

### STEP 2: Fix Initial Display
- Room card: Show total + available when no dates
- When dates selected: Show API data

### STEP 3: Ensure API Response is Correct
- Check what backend is returning
- Make sure `room_types[].available_rooms` exists
- Verify booked rooms calculation

### STEP 4: Test Complete Flow
- Create booking
- Check availability before/after
- Cancel and verify restoration

---

## 📊 CURRENT DATA FLOW

```
Frontend (User selects dates)
  ↓
[checkIn, checkOut changed]
  ↓
useEffect triggers handleCheckAvailability()
  ↓
API POST /hotels/check-availability/
  ↓
Backend AvailabilityCheckSerializer.get_availability()
  ↓
For each room_type:
  - RoomType.get_available_rooms(checkIn, checkOut)
  - Calculate booked = overlapping bookings
  - available = total - booked
  ↓
Response returns array of room_types with:
  - total_rooms
  - available_rooms
  - is_available
  ↓
Frontend receives response
  ↓
Display:
  - Available: X rooms (from API)
  - Booked: Y rooms (calculated)
  - Total: Z rooms
```

---

## ✅ WHAT NEEDS TO BE FIXED

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | Booked calculation uses wrong property | HIGH | Use API data only |
| 2 | No live update when booking created | MEDIUM | Refetch availability on interval |
| 3 | "Checking..." never disappears | HIGH | Debug API response |
| 4 | Initial state shows "0" when should show total | MEDIUM | Fix initial display logic |
| 5 | Cancelled bookings not properly excluded | HIGH | Verify status filter in backend |


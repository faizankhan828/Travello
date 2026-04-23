# Hotel Booking Bug Investigation: Admin-Added Rooms Not Bookable

## Issue Summary
Users cannot book admin-added room types even though the system shows 50 total rooms. The error "Not enough rooms for these dates" appears despite plenty of inventory. The UI shows:
- **Total Rooms**: 50 ✓
- **Available**: ? (question mark - no data)
- **Booked**: — (dash - unknown)

---

## 1. ADMIN ROOM CREATION - How are admin rooms added?

### Location: `hotels/admin.py`
```python
@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'type', 'price_per_night', 'total_rooms', 'get_available_rooms', 'max_occupancy')
    list_filter = ('type', 'hotel__city')
    search_fields = ('hotel__name', 'type', 'description')
    ordering = ('hotel', 'price_per_night')
    readonly_fields = ('created_at', 'updated_at', 'get_available_rooms')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('hotel', 'type', 'price_per_night')
        }),
        ('Capacity', {
            'fields': ('total_rooms', 'max_occupancy', 'get_available_rooms')
        }),
        ...
    )
```

### Location: `hotels/views.py` - API room creation
```python
class HotelViewSet(viewsets.ModelViewSet):
    permission_classes: IsStaffUser (for create/update/delete)
    
    def create(self, request, *args, **kwargs):
        # Creates hotel with room_types_payload
        # Uses _upsert_room_types to create/update room types
```

### Admin Room Creation Flow
1. Admin goes to Django admin or uses API
2. Creates RoomType via `RoomTypeAdmin` or `HotelSerializer`
3. Fields required:
   - `hotel` (ForeignKey) ✓
   - `type` (CharField with choices) ✓
   - `price_per_night` (DecimalField) ✓
   - `total_rooms` (IntegerField with MinValueValidator(1)) ✓
   - `max_occupancy` (default=2) ✓

**⚠️ POTENTIAL ISSUE**: `unique_together = ['hotel', 'type']` means only ONE room type of each type per hotel.

---

## 2. ROOM INVENTORY/STOCK TRACKING

### RoomType Model Fields (`hotels/models.py`)
```python
class RoomType(models.Model):
    hotel = ForeignKey(Hotel)
    type = CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    price_per_night = DecimalField()
    total_rooms = IntegerField(validators=[MinValueValidator(1)])  # ← MASTER INVENTORY
    max_occupancy = IntegerField(default=2)
    description = TextField(blank=True)
    amenities = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Finding**: There is **NO separate inventory table**. All inventory is tracked via:
- `RoomType.total_rooms` - Total inventory (fixed)
- `Booking.rooms_booked + Booking.status IN ['PENDING', 'PAID', 'CONFIRMED']` - Booked count

---

## 3. AVAILABILITY CALCULATION LOGIC

### Core Algorithm: `RoomType.get_available_rooms(check_in, check_out)`

**Location**: `hotels/models.py` lines 113-148

```python
def get_available_rooms(self, check_in=None, check_out=None):
    from django.db.models import Sum
    from django.utils import timezone
    
    if check_in is None:
        check_in = timezone.now().date()
    if check_out is None:
        check_out = check_in + timezone.timedelta(days=1)
    
    # OVERLAP RULE: check_in < selected_check_out AND check_out > selected_check_in
    overlapping_bookings = Booking.objects.filter(
        room_type=self,
        status__in=['PENDING', 'PAID', 'CONFIRMED'],  # ← STATUS FILTER
        check_in__lt=check_out,
        check_out__gt=check_in
    )
    
    # Sum booked rooms
    booked = overlapping_bookings.aggregate(
        total=Sum('rooms_booked')
    )['total'] or 0
    
    # Calculate available
    total = self.total_rooms or 0
    return max(0, total - booked)
```

### Availability Check - API Endpoint
**Location**: `hotels/views.py` lines 1235-1314 (`RoomAvailabilityView`)

```python
class RoomAvailabilityView(APIView):
    def post(self, request):
        # Validates dates and hotel/room_type
        availability = serializer.get_availability()
        # Returns: {
        #   'hotel_id': int,
        #   'hotel_name': str,
        #   'check_in': date,
        #   'check_out': date,
        #   'nights': int,
        #   'room_types': [
        #       {
        #           'id': int,
        #           'type': str,
        #           'total_rooms': int,
        #           'available_rooms': int,  ← CALCULATED HERE
        #           'is_available': bool,
        #           'total_price': float
        #       }
        #   ]
        # }
```

### Availability Serializer
**Location**: `hotels/serializers.py` lines 441-550 (`AvailabilityCheckSerializer`)

```python
def get_availability(self):
    hotel = self.validated_data['hotel_obj']
    check_in = self.validated_data['check_in']
    check_out = self.validated_data['check_out']
    
    # Uses RoomType.check_availability_for_hotel()
    availability_data = RoomType.check_availability_for_hotel(hotel, check_in, check_out)
    
    # For each room type, calls: room_type.get_available_rooms(check_in, check_out)
```

**Availability is calculated correctly** ✓

---

## 4. DIFFERENT CODE PATHS FOR ADMIN-ADDED VS REGULAR ROOMS

### **CRITICAL FINDING: No distinction between admin and regular rooms**

The code treats all rooms identically:
- No `is_admin` field on RoomType
- No `source` field (admin vs scraped)
- No status field (ACTIVE/INACTIVE)
- No special filtering for admin-created rooms

**Both follow the same path**:
1. `GET /api/hotels/{id}/` → Returns all room_types
2. `POST /api/hotels/check-availability/` → Checks all room_types
3. Booking creation uses same logic for all rooms

---

## 5. POTENTIAL ROOT CAUSES

### **ROOT CAUSE #1: total_rooms NOT BEING SET CORRECTLY**

When admin adds a room through the serializer:
```python
# hotels/serializers.py - HotelSerializer._upsert_room_types()
room_type_objs.append(RoomType(
    hotel=hotel,
    type=rt['type'],
    price_per_night=rt['price_per_night'],
    total_rooms=rt['total_rooms'],  # ← Must be in payload
    max_occupancy=rt.get('max_occupancy', 2),
    ...
))
```

**🔴 ISSUE**: If admin doesn't provide `total_rooms` in API payload, or if it's set to 0, or if there's a database issue, `total_rooms` could be:
- 0 or None → available_rooms = 0
- Not saved properly → Database inconsistency

### **ROOT CAUSE #2: Booking Status Filter Issue**

The availability calculation only counts bookings with status IN `['PENDING', 'PAID', 'CONFIRMED']`

```python
overlapping_bookings = Booking.objects.filter(
    room_type=self,
    status__in=['PENDING', 'PAID', 'CONFIRMED'],  # ← Only these statuses
    check_in__lt=check_out,
    check_out__gt=check_in
)
```

**Possible scenario**: If a test booking exists with a different status (e.g., 'COMPLETED', 'CANCELLED'), it won't be counted as booked, but might still be in the database causing confusion.

### **ROOT CAUSE #3: null/0 Handling in Availability Calculation**

```python
booked = overlapping_bookings.aggregate(total=Sum('rooms_booked'))['total'] or 0
total = self.total_rooms or 0  # ← If total_rooms is None, returns 0
return max(0, total - booked)  # ← Always >= 0
```

If `RoomType.total_rooms` is somehow None or 0, available rooms will always be 0.

### **ROOT CAUSE #4: Frontend Display Issue**

**Location**: `frontend/src/components/HotelDetailPage.js` lines 300-305

```javascript
if (hasSelectedDates) {
    if (availabilityLoading && liveAvailability == null) {
        displayedAvailable = 'Checking...';
    } else if (liveAvailability != null) {
        displayedAvailable = liveAvailability;
    } else {
        // ← Shows "?" when API response is null/undefined for this room
        displayedAvailable = '?';
    }
}

// Booked calculation
const booked = bookedRooms(room);  // Returns null if no dates or no API data
// Displays: hasSelectedDates && booked !== null ? booked : '—'
```

**🔴 ISSUE**: When API doesn't return data for a room_type in the availability response, `liveAvailability` is undefined, causing display of "?"

This suggests the **API isn't including admin-added rooms** in the availability response!

---

## 6. API RESPONSE VALIDATION

### Expected API Response:
```json
{
  "success": true,
  "data": {
    "hotel_id": 1,
    "hotel_name": "Hotel Name",
    "room_types": [
      {
        "id": 5,
        "type": "double",
        "type_display": "Double",
        "price_per_night": 75.00,
        "total_rooms": 50,
        "available_rooms": 50,
        "is_available": true,
        "total_price": 15000.00
      }
    ]
  }
}
```

### **Critical Question**: Is the room_type appearing in the response?

If `room_types` array is missing admin-added rooms, the issue is in:
1. `Hotel.room_types.all()` queryset filtering
2. `RoomType.check_availability_for_hotel()` filtering
3. Serialization in `AvailabilityCheckSerializer.get_availability()`

---

## RECOMMENDED DEBUGGING STEPS

### 1. **Check Database**
```python
# In Django shell:
from hotels.models import RoomType, Hotel

hotel = Hotel.objects.get(id=<admin_hotel_id>)
rooms = hotel.room_types.all()
print(f"Total room types: {rooms.count()}")

for room in rooms:
    print(f"  - {room.type}: total_rooms={room.total_rooms}, available={room.get_available_rooms()}")
```

### 2. **Test Availability API**
```bash
curl -X POST http://localhost:8000/api/hotels/check-availability/ \
  -H "Content-Type: application/json" \
  -d '{
    "hotel": <HOTEL_ID>,
    "check_in": "2026-04-20",
    "check_out": "2026-04-25"
  }'
```

**Check**: Does response include the admin-added room type?

### 3. **Check RoomType Serialization**
```python
from hotels.serializers import RoomTypeSerializer
room = RoomType.objects.get(id=<ROOM_ID>)
serializer = RoomTypeSerializer(room)
print(serializer.data)
# Check if 'available_rooms' field returns correct value
```

### 4. **Verify Booking Status**
```python
# Any bookings with non-standard status?
from hotels.models import Booking
bookings = Booking.objects.filter(room_type__id=<ROOM_ID>)
for b in bookings:
    print(f"Booking {b.id}: status={b.status}")
```

---

## SUMMARY TABLE

| Component | Status | Finding |
|-----------|--------|---------|
| Admin Room Creation | ✓ Works | Via Django admin or API |
| RoomType Model | ✓ Correct | No status/admin-specific fields |
| Inventory Tracking | ✓ Correct | Uses `total_rooms` + Booking count |
| Availability Calculation | ✓ Logic OK | Uses proper overlap detection |
| Status Filtering | ✓ Correct | Only counts PENDING/PAID/CONFIRMED |
| API Response | 🔴 **SUSPECT** | May not include admin rooms or returns null |
| Frontend Display | ✓ Correct | Shows "?" when API data missing |

---

## ROOT CAUSE HYPOTHESIS

**Most Likely**: Admin-added rooms have `total_rooms=0` or the API response isn't including them

**Alternative**: Database issue where `total_rooms` field isn't being saved/retrieved correctly

**Test This First**:
1. Create admin room with `total_rooms=50`
2. Call availability API
3. Check if room appears in response with correct `total_rooms` value

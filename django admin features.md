# Django Super Admin Features

## Overview
The Django Admin Panel (Super Admin) provides comprehensive backend management for the Travello system. It allows super admins to manage users, hotels, bookings, payments, reviews, and OTP authentication with advanced filtering, searching, and bulk actions.

---

## Access & Authentication

### Login URL
- **Path:** `/admin/` (Django default)
- **Credentials:** Super admin username and password
- **Session:** Django session-based authentication

### Permissions
- Super user account required (`is_superuser = True`)
- Staff account required (`is_staff = True`)
- Full access to all registered models

---

## Registered Models & Management

### 1. User Management (Authentication Module)

#### Custom User Admin
- **Model:** User (extended Django User model)
- **Access:** `/admin/authentication/user/`

**List View Columns:**
- Email (primary)
- Username
- First Name
- Last Name
- Is Staff (boolean)
- Date Joined (timestamp)

**Filters:**
- Is Staff (Yes/No)
- Is Superuser (Yes/No)
- Is Active (Yes/No)
- Date Joined (date range)

**Search Fields:**
- Email
- Username
- First Name
- Last Name

**Ordering:** By email (ascending)

**Fieldsets (Edit View):**
1. **None** - Email, Password
2. **Personal Info** - Username, First Name, Last Name
3. **Permissions** - Is Active, Is Staff, Is Superuser, Groups, User Permissions
4. **Important Dates** - Last Login, Date Joined

**Add Fieldsets:**
- Email, Username, Password (with confirmation)

---

### 2. OTP Management (Authentication Module)

#### OTP Admin
- **Model:** OTP (One-Time Password)
- **Access:** `/admin/authentication/otp/`

**List View Columns:**
- User (foreign key)
- Purpose (email_verification, password_reset, etc.)
- OTP Code (actual code)
- Created At (timestamp)
- Expires At (timestamp)
- Attempts (integer counter)
- Is Used (boolean)

**Filters:**
- Purpose (dropdown)
- Is Used (Yes/No)
- Created At (date range)

**Search Fields:**
- User Email
- OTP Code

**Read-Only Fields:**
- Created At
- OTP Code (cannot be edited)

**Fieldsets:**
1. **None** - User, OTP Code, Purpose
2. **Expiry & Validation** - Created At, Expires At, Is Used
3. **Security** - Attempts (failed attempts counter)

---

### 3. Hotel Management (Hotels Module)

#### Hotel Admin
- **Model:** Hotel
- **Access:** `/admin/hotels/hotel/`

**List View Columns:**
- Name
- City
- Rating (star rating)
- Get Total Rooms (calculated)
- Get Available Rooms (calculated)
- WiFi Available (boolean)
- Parking Available (boolean)
- Created At (timestamp)

**Filters:**
- WiFi Available (Yes/No)
- Parking Available (Yes/No)
- City
- Rating (range)

**Search Fields:**
- Name
- City
- Address
- Description

**Ordering:** By Created At (newest first)

**Read-Only Fields:**
- Created At
- Updated At
- Get Total Rooms
- Get Available Rooms

**Fieldsets:**
1. **Basic Information** - Name, City, Address, Description
2. **Media & Rating** - Image (upload), Rating
3. **Amenities** - WiFi Available, Parking Available
4. **Statistics** (Collapsible) - Total Rooms, Available Rooms, Created At, Updated At

**Custom Methods:**
- `get_total_rooms()` - Displays total room count
- `get_available_rooms()` - Displays available room count

---

### 4. Room Type Management (Hotels Module)

#### Room Type Admin
- **Model:** RoomType
- **Access:** `/admin/hotels/roomtype/`

**List View Columns:**
- Hotel (foreign key)
- Type (Single/Double/Triple/Quad/Family)
- Price Per Night (currency)
- Total Rooms (count)
- Get Available Rooms (color-coded)
- Max Occupancy (number)

**Filters:**
- Type (dropdown)
- Hotel City

**Search Fields:**
- Hotel Name
- Type
- Description

**Ordering:** By Hotel, then Price Per Night

**Read-Only Fields:**
- Created At
- Updated At
- Get Available Rooms

**Fieldsets:**
1. **Basic Information** - Hotel, Type, Price Per Night
2. **Capacity** - Total Rooms, Max Occupancy, Get Available Rooms
3. **Details** - Description, Amenities (JSON field)
4. **Timestamps** (Collapsible) - Created At, Updated At

**Custom Display:**
- Available rooms color-coded:
  - Green: >5 rooms available
  - Orange: 1-5 rooms available
  - Red: 0 rooms available

**Inline:** Room Type Inline on Hotel detail page

---

### 5. Booking Management (Hotels Module)

#### Booking Admin
- **Model:** Booking
- **Access:** `/admin/hotels/booking/`

**List View Columns (13 columns):**
- Booking Reference (unique identifier)
- Get User Info (formatted as "username <email>")
- Hotel (foreign key)
- Room Type (foreign key)
- Rooms Booked (count)
- Check In (date)
- Check Out (date)
- Get Nights (calculated nights)
- Total Price (currency)
- Payment Method (ONLINE/PAY_AT_ARRIVAL)
- Get Status (color-coded)
- Get Cancellation Date (if cancelled)
- Created At (timestamp)

**Filters:**
- Status (PENDING/PAID/CONFIRMED/CANCELLED/COMPLETED)
- Payment Method
- Refund Status
- Check In Date
- Check Out Date
- Created At (date range)

**Search Fields:**
- Booking Reference
- User Email
- User Username
- Hotel Name
- Guest Name
- Guest Email
- Guest Phone

**Ordering:** By Created At (newest first)

**Date Hierarchy:** Check In (drill down by date)

**Read-Only Fields:**
- Created At
- Updated At
- Get Nights
- Booking Reference
- Invoice Number
- Base Price
- Tax Amount
- Service Charge
- Cancelled At
- Cancelled By
- Get User Detail
- Get Payment Summary

**Fieldsets:**
1. **Booking Information** - Booking Reference, Invoice Number, User, Hotel, Room Type, Rooms Booked
2. **User Details** - Get User Detail (formatted display)
3. **Stay Dates** - Check In, Check Out, Get Nights
4. **Guest Information** - Guest Name, Guest Email, Guest Phone, Special Requests
5. **Price Breakdown** - Base Price, Tax Amount, Service Charge, Total Price
6. **Payment & Status** - Payment Method, Status, Get Payment Summary
7. **Cancellation Details** - Cancelled At, Cancelled By, Cancellation Reason, Refund Amount, Refund Status (with note about auto-population)
8. **Timestamps** (Collapsible) - Created At, Updated At

**Bulk Actions (3):**
1. **Mark as Confirmed** - Changes status to CONFIRMED
2. **Mark as Cancelled** - Changes status to CANCELLED, sets cancelled_at timestamp, records cancelling user
3. **Mark as Completed** - Changes status to COMPLETED

**Inline Models:**
- Payment (StackedInline - read-only, cannot delete, cannot add new)

**Custom Display Methods:**
- `get_nights()` - Displays number_of_nights
- `get_user_info()` - Formats as HTML "username <email>"
- `get_status()` - Color-coded status badge:
  - PENDING: Orange
  - PAID: Blue
  - CONFIRMED: Green
  - CANCELLED: Red
  - COMPLETED: Gray
- `get_cancellation_date()` - Shows red datetime or "-"
- `get_user_detail()` - Formatted HTML with username, email, name
- `get_payment_summary()` - HTML formatted payment details from related Payment record

---

### 6. Payment Management (Hotels Module)

#### Payment Admin
- **Model:** Payment (Stripe integration)
- **Access:** `/admin/hotels/payment/`

**List View Columns:**
- ID (primary key)
- Booking (foreign key)
- Amount (currency amount)
- Currency (code)
- Get Status (formatted)
- Stripe Payment Intent (Stripe transaction ID)
- Payment Method Type (card/etc)
- Created At (timestamp)

**Filters:**
- Status (APPROVED/PENDING/FAILED/REFUNDED)
- Currency (USD/PKR/etc)
- Payment Method Type
- Created At (date range)

**Search Fields:**
- Booking ID
- Booking User Email
- Stripe Payment Intent ID
- Last 4 digits of card

**Ordering:** By Created At (newest first)

**Read-Only Fields:**
- Created At
- Updated At
- Stripe Payment Intent
- Last 4 (card digits)
- Brand (Visa/Mastercard/etc)
- Payment Method Type

**Fieldsets:**
1. **Booking Reference** - Booking
2. **Payment Details** - Amount, Currency, Status
3. **Stripe Information** - Stripe Payment Intent, Stripe Session ID, Payment Method Details
4. **Card Information** - Card Brand, Last 4 Digits
5. **Metadata & Error** - Metadata (JSON), Error Message
6. **Timestamps** - Created At, Updated At

---

### 7. Review Management (Reviews Module)

#### Review Admin
- **Model:** Review
- **Access:** `/admin/reviews/review/`

**List View Columns:**
- User (foreign key)
- Hotel (foreign key)
- Overall Rating (1-5 stars)
- Sentiment (POSITIVE/NEUTRAL/NEGATIVE from NLP)
- Status (draft/published/flagged/removed)
- Helpful Count (integer)
- Created At (timestamp)

**Filters:**
- Status (draft/published/flagged/removed)
- Sentiment (POSITIVE/NEUTRAL/NEGATIVE)
- Overall Rating (1-5)
- Trip Type (business/leisure/etc)
- Created At (date range)

**Search Fields:**
- Title (review headline)
- Content (review text)
- User Email
- Hotel Name

**Read-Only Fields:**
- Sentiment
- Sentiment Score (NLP score)
- Helpful Count
- Report Count
- Created At
- Updated At
- ID

**Date Hierarchy:** Created At (drill down by date)

**Inline Models:**
1. **ReviewPhoto** (TabularInline - extra fields for upload)
2. **ReviewReply** (StackedInline - for admin responses)

**Bulk Actions (5):**
1. **Delete Selected** - Bulk delete reviews
2. **Mark as Published** - Sets status to "published"
3. **Mark as Draft** - Sets status to "draft"
4. **Mark as Flagged** - Sets status to "flagged" (for review)
5. **Mark as Removed** - Sets status to "removed" (hidden from public)

---

### 8. Review Photo Management (Reviews Module)

#### Review Photo Admin
- **Model:** ReviewPhoto
- **Access:** `/admin/reviews/reviewphoto/`

**List View Columns:**
- Review (foreign key)
- Caption (description)
- Uploaded At (timestamp)

**Features:**
- Manage photos attached to reviews
- Delete/edit photo metadata

---

### 9. Review Helpful Management (Reviews Module)

#### Review Helpful Admin
- **Model:** ReviewHelpful
- **Access:** `/admin/reviews/reviewhelpful/`

**List View Columns:**
- User (who marked as helpful)
- Review (the review marked helpful)
- Created At (when marked)

**Features:**
- Track "Helpful" votes on reviews
- Monitor user engagement with review content

---

### 10. Review Reply Management (Reviews Module)

#### Review Reply Admin
- **Model:** ReviewReply
- **Access:** `/admin/reviews/reviewreply/`

**List View Columns:**
- User (who replied)
- Review (which review)
- Created At (timestamp)

**Search Fields:**
- Content (reply text)
- User Email

**Features:**
- Manage admin and user replies to reviews
- Monitor review engagement

---

### 11. Weather Management (Weather Module)

#### Weather Cache Admin
- **Model:** WeatherCache
- **Access:** `/admin/weather/weathercache/`

**List View Columns:**
- City (location)
- Temperature (current temp)
- Condition (sunny/cloudy/rainy/etc)
- Humidity (percentage)
- Wind Speed (km/h)
- Updated At (last refresh timestamp)

**Filters:**
- Updated At (date range)
- Condition (weather type)

**Search Fields:**
- City

**Read-Only Fields:**
- Last Updated
- Updated At

**Fieldsets:**
1. **City** - City name
2. **Weather Data** - Temperature, Condition, Humidity, Wind Speed, Icon Code
3. **Timestamps** - Last Updated, Updated At

**Ordering:** By Updated At (newest first)

**Features:**
- Cache management for weather API responses
- Monitor data freshness
- Manual update capability

---

## Advanced Django Admin Features

### Search Capabilities
- **Smart Search:** Across multiple fields (email, username, hotel name, etc)
- **Field Lookups:** Support for email contains, name contains, etc

### Filtering
- **Filter Sidebar:** Multi-select filters for categorical data
- **Date Filters:** Date range filtering on timestamp fields
- **Boolean Filters:** Yes/No filters for boolean fields
- **Foreign Key Filters:** Filter by related object properties (e.g., hotel city)

### Custom Actions (Bulk Operations)
- Status change actions
- Delete/bulk delete with confirmation
- Mass updates with user feedback

### Read-Only Fields
- System-generated fields cannot be edited
- Timestamps auto-managed
- Calculated fields displayed as read-only

### Fieldsets & Organization
- Logical grouping of related fields
- Collapsible sections for advanced/rarely-used fields
- Organized form layout for better UX

### Date Hierarchies
- Navigate bookings by check-in date
- Navigate reviews by creation date
- Filter by time periods (month/day)

### Inline Editing (Nested Models)
- Edit related records inline
- TabularInline for many items (Room Types)
- StackedInline for detailed editing (Payments, Replies)

### Custom Display Methods
- Color-coded status badges
- Formatted currency values
- HTML-formatted display fields
- Calculated fields (available rooms, nights)

### Ordering & Sorting
- Click column headers to sort
- Multiple sort levels supported
- Default sorting by most recent

---

## Common Admin Tasks

### Manage Users
- Create new admin users with staff privileges
- Reset user passwords
- Activate/deactivate accounts
- Assign permissions and groups

### Manage Hotels
- Add new hotels with amenities
- Update room types and pricing
- Monitor room availability
- Edit hotel ratings and descriptions

### Manage Bookings
- View all booking details
- Mark bookings as confirmed/cancelled/completed
- View payment details inline
- Check guest information and special requests
- Track cancellations and refunds
- Bulk status updates

### Manage Payments
- Monitor payment status
- View Stripe integration details
- Track failed/refunded payments
- Verify payment amounts and currency

### Manage Reviews
- Publish/draft/flag reviews from moderation queue
- View sentiment analysis results
- Delete inappropriate reviews
- Respond to reviews with replies
- View and manage review photos

### Manage OTP
- Monitor OTP delivery
- Check expiration status
- Track failed attempts
- Verify OTP purposes (email, password reset)

### Monitor Weather Cache
- Check cached weather data freshness
- Clear old cached data
- View weather by location

---

## User Interface Features

### Responsive Design
- Desktop optimized interface
- Works on tablets and mobile (limited)
- Full functionality maintained

### Customizable Columns
- Show/hide columns in list view
- Reorder columns
- Adjust column width

### Search & Filter Persistence
- Filters persist in session
- Search history
- Save filter combinations

### Actions & Confirmations
- Confirmation dialogs for destructive actions
- Error messages for validation failures
- Success messages for completed actions

### Change Log & History
- Track who made changes and when
- View object edit history
- Revert to previous versions (if enabled)

---

## Security Features

### Permission-Based Access
- Only super admins can access
- Field-level permissions can be customized
- Add/change/delete permissions per model

### Audit Trail
- Django admin logs all changes
- User attribution on edits
- Timestamp on every modification

### Readonly Fields
- Prevent accidental modification
- Password never shown (hash stored)
- System fields protected

---

## Performance Considerations

### List Display Optimization
- Efficient database queries
- Select-related for foreign keys
- Prefetch-related for reverse relationships

### Pagination
- Large lists paginated (typically 100-200 per page)
- Navigate between pages
- Show total count

### Raw ID Fields
- Can be used for large relation lookups
- Faster than dropdown for thousands of records

---

## API Integration

### Stripe Payment Integration
- View Stripe payment intent IDs
- Monitor transaction status
- Track payment method types
- See error messages from Stripe

### Weather API Integration
- Cache management from OpenWeatherMap
- Monitor data freshness
- Manual refresh capability

---

## Best Practices for Super Admins

✅ **Regular Monitoring** - Check dashboard data consistency
✅ **User Management** - Create staff accounts with appropriate permissions
✅ **Booking Review** - Monitor for suspicious patterns or high cancellations
✅ **Payment Tracking** - Verify all payments processed correctly
✅ **Content Moderation** - Review flagged content regularly
✅ **Data Backup** - Regular database backups
✅ **Permission Review** - Audit user permissions quarterly
✅ **Cache Management** - Clear old weather cache data
✅ **OTP Monitoring** - Monitor OTP failures and expiration issues

---

## Technical Stack

**Framework:** Django 3.2+
**Authentication:** Django Session Auth
**Admin Interface:** Django Admin (django.contrib.admin)
**Database:** SQLite/PostgreSQL
**Custom Features:** Custom admin classes, inline models, actions, display methods

---

## Default Django Admin Features

- User management (groups, permissions)
- Site management
- Admin action logging
- Change history viewing
- Filter by date/hierarchy
- Search across fields
- Bulk editing capability
- Export functionality (via third-party packages)

---

**Super Admin Panel URL:** `{BASE_URL}/admin/`
**Default Port:** 8000 (Django development server)

---

**Last Updated:** March 2026

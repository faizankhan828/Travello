# Admin Dashboard Features

## Overview
The Admin Dashboard provides comprehensive analytics, monitoring, and management tools for administrators. It offers real-time insights into hotel operations, booking patterns, AI recommendation performance, and critical operational metrics.

---

## Main Interface Sections

### Header Navigation
- **Admin Dashboard Title** - Main dashboard label with "Analytics & Management" subtitle
- **Refresh Button** - Real-time data refresh with loading spinner animation
- **Sign Out Button** - Secure logout functionality
- **Dark/Light Mode Support** - Full theme compatibility

---

## Dashboard Tabs

### Tab 1: Analytics Overview
Comprehensive analytics view with 15+ data visualizations and operational metrics.

### Tab 2: Quick Actions Management
Management shortcuts with quick action buttons for hotel and booking management.

---

## Filter & Control Panel

### Period Filter (5 Options)
- **7 Days** - Last week analytics
- **30 Days** - Monthly view (default)
- **90 Days** - Quarterly insights
- **1 Year** - Annual performance
- **All Time** - Complete historical data

### Hotel Filter
- **Dropdown selector** with "All Hotels" option
- **Dynamic options** - Lists all available hotels from database
- Filter all analytics by specific hotel

### Top Hotels Window (4 Options)
- **Top 5 Hotels** - Small sample
- **Top 10 Hotels** - Default view
- **Top 15 Hotels** - Extended view
- **Top 20 Hotels** - Comprehensive view
- Adjusts top performing hotels chart display

### Occupancy Target (5 Options)
- **70% Target**
- **75% Target**
- **80% Target** (default)
- **85% Target**
- **90% Target**
- Benchmark for occupancy rate alerts and KPI comparison

### Export Options
- **Export CSV** - Download complete analytics as CSV file with all metrics and tables
- **Export PDF** - Generate executive report PDF with formatted tables, KPIs, and alerts

---

## KPI Cards Row

### 1. **Total Revenue**
- **Icon:** Money Bill Waves (Green)
- **Display:** PKR format (Pakistani Rupees)
- **Metric:** Sum of all booking revenue
- **Growth Indicator:** % change from previous period (up/down arrow)

### 2. **Total Bookings**
- **Icon:** Book (Indigo)
- **Display:** Total count
- **Metric:** Number of all bookings
- **Growth Indicator:** % change from previous period

### 3. **Conversion Rate**
- **Icon:** Percentage (Amber)
- **Display:** Percentage value
- **Metric:** Booking conversion efficiency
- **Formula:** Booked / Recommended × 100

### 4. **Recommendation CTR**
- **Icon:** Brain (Cyan)
- **Display:** Percentage value
- **Metric:** Click-through rate of AI recommendations
- **Data Source:** Latest CTR trend value

---

## Data Visualizations (15 Charts)

### Row 1: Revenue & Status Analysis

#### 1. **Revenue Trend Chart**
- **Type:** Line Chart
- **X-Axis:** Date (formatted as "Mar 15")
- **Y-Axis:** Revenue amount (auto-scaled with short format: 10K, 1M)
- **Data:** Daily revenue trajectory
- **Color:** Sky blue (#0ea5e9)
- **Purpose:** Track revenue over time to identify trends and seasonal patterns

#### 2. **Booking Status Pie Chart**
- **Type:** Donut/Pie Chart
- **Segments:** 5 status categories
  - **Paid** - Green (#22c55e)
  - **Confirmed** - Blue (#3b82f6)
  - **Completed** - Indigo (#6366f1)
  - **Pending** - Amber (#f59e0b)
  - **Cancelled** - Red (#ef4444)
- **Mini Cards Below:** Numerical breakdown (Confirmed, Cancelled, Pending)
- **Purpose:** Visualize booking status distribution and health

#### 3. **Active Bookings Today**
- **Type:** Large metric card
- **Display:** Large number with label
- **Data:** Real-time active bookings count
- **Purpose:** Show current operational volume at a glance

---

### Row 2: Operational Core

#### 4. **Bookings Trend Bar Chart**
- **Type:** Stacked Bar Chart
- **X-Axis:** Date
- **Y-Axis:** Booking count
- **Stacks:** 3 colored bars per date
  - Confirmed (Green)
  - Cancelled (Red)
  - Pending (Amber)
- **Purpose:** Show booking flow and cancellation rates over time

#### 5. **Alerts Panel**
- **Type:** Alert notification panel
- **Alert Levels:** High, Medium, OK
- **Color Coding:**
  - High (Red) - Critical issues requiring immediate attention
  - Medium (Amber) - Warning, needs monitoring
  - OK (Green) - System stable
- **Alert Types:**
  - High cancellation rate (≥25%)
  - Low occupancy risk (below target)
  - Recommendation CTR drop (>2% decrease)
  - Model F1 score below threshold (<0.6)
  - System stability message (when all OK)

---

### Row 3: Hotel & Inventory Breakdown

#### 6. **Top Performing Hotels Bar Chart**
- **Type:** Horizontal Bar Chart
- **Layout:** Vertical names, horizontal metrics
- **Metric Selector:** 3 options
  - Revenue (default)
  - Bookings
  - Conversion Rate
- **Display:** Top 8 hotels (sorted by selected metric)
- **Color:** Sky blue (#0284c7)
- **Purpose:** Identify best-performing properties

#### 7. **Room Type Distribution Bar Chart**
- **Type:** Horizontal Bar Chart
- **Categories:** Single, Double, Triple, Quad, Family
- **X-Axis:** Booking count
- **Color:** Sky blue (#0ea5e9)
- **Purpose:** Show demand patterns by room type

#### 8. **Payment Method Distribution Pie Chart**
- **Type:** Donut/Pie Chart
- **Segments:** 2 payment methods
  - Online Payment (Indigo #6366f1)
  - Pay on Arrival (Amber #f59e0b)
- **Color:** Colors match payment type
- **Purpose:** Track payment channel mix

---

### Row 4: AI Recommendation & CTR Analytics

#### 9. **Recommendation Conversion Funnel**
- **Type:** Funnel Chart
- **Stages:** 3 levels
  - Recommended (Dark slate)
  - Viewed (Cyan #0ea5e9)
  - Booked (Green #22c55e)
- **Labels:** Stage names and numerical values inside
- **Purpose:** Show AI recommendation conversion pipeline

#### 10. **Recommendation CTR Trend Line Chart**
- **Type:** Line Chart
- **X-Axis:** Date
- **Y-Axis:** CTR percentage (0-100%)
- **Color:** Teal (#14b8a6)
- **Purpose:** Track AI recommendation click-through effectiveness over time

#### 11. **Booking Source Distribution Pie Chart**
- **Type:** Donut/Pie Chart
- **Segments:** 4 traffic sources
  - Web (Sky blue #0ea5e9)
  - Mobile (Orange #f97316)
  - AI Recommendation (Teal #14b8a6)
  - Manual Search (Purple #8b5cf6)
- **Legend:** Shows source names and percentages
- **Purpose:** Understand booking origin distribution

---

### Row 5: Revenue Growth & Risk Analysis

#### 12. **Cumulative Revenue Area Chart**
- **Type:** Area Chart (gradient fill)
- **Format:** Smooth curve with gradient background
- **X-Axis:** Date
- **Y-Axis:** Cumulative revenue amount
- **Color Gradient:** Blue (#0284c7) with fade
- **Purpose:** Show long-term earnings growth trajectory

#### 13. **Refund & Cancellation Trend Line Chart**
- **Type:** Dual Line Chart
- **Lines:** 2 metrics
  - Cancelled (Red #ef4444)
  - Refunded (Orange #f97316)
- **X-Axis:** Date
- **Y-Axis:** Count
- **Purpose:** Monitor operational and policy risk signals

#### 14. **Hotel Occupancy Rate Gauge**
- **Type:** Radial Bar Chart (circular gauge)
- **Display:** Large percentage in center (e.g., "75.3%")
- **Gauge Color:** Sky blue (#0284c7)
- **Range:** 0-100% with comparison to occupancy target
- **Purpose:** Show inventory utilization KPI at a glance

---

### Row 6: ML Model Health Monitoring

#### 15. **Model Quality Metrics Line Chart**
- **Type:** Triple Line Chart
- **Lines:** 3 metrics
  - Precision (Blue #2563eb)
  - Recall (Teal #14b8a6)
  - F1 Score (Purple #a855f7)
- **X-Axis:** Date
- **Y-Axis:** Score (0-1 scale)
- **Purpose:** Monitor AI recommendation model drift and performance degradation

#### 16. **Customer Location Heatmap Grid**
- **Type:** Grid of colored cards
- **Display:** Top 10 geographic locations
- **Card Info:** Location name, booking count
- **Color Intensity:** Based on booking concentration
- **Purpose:** Show demand concentration by region/city

---

## Data Table

### Recent Bookings Table
- **Display:** Latest booking entries from selected period
- **Columns:**
  - Hotel (name, truncated)
  - Guest (guest name or "—" if unavailable)
  - Check-in (date formatted as "Mar 15")
  - Amount (PKR currency formatted)
  - Status (color-coded badge)
- **Status Colors:**
  - Green - Paid/Completed
  - Blue - Confirmed
  - Red - Cancelled
  - Amber - Pending
- **Interaction:** Hover highlighting
- **Purpose:** Quick reference of recent booking activity

---

## Quick Actions Tab Features

### Quick Stats Row (4 Cards)
1. **Total Hotels** - Count of all hotels in system
2. **Total Bookings** - Complete booking count
3. **Total Revenue** - Sum of all revenue (PKR)
4. **Cancelled Bookings** - Count of cancelled bookings

### Action Buttons (3 Quick Links)

#### 1. **Manage Hotels**
- Icon: Hotel (Sky blue gradient)
- Link: Admin hotels management page
- Description: "Add, edit, or remove hotels"

#### 2. **Manage Bookings**
- Icon: Book (Purple-Pink gradient)
- Link: Admin bookings management page
- Description: "View, filter, and update all bookings"

#### 3. **Django Admin**
- Icon: Users (Gray gradient)
- Link: Django admin panel
- Description: "Users, payments, raw data"
- Note: Opens in new window

---

## Widget Integrations

### Weather Widget
- Real-time weather display
- Weather forecast for trip planning
- Location-aware updates
- Show/hide details toggle

---

## Additional Features

### Authentication & Security
- Admin role verification on load
- Auth token management (access & refresh)
- Secure logout with token clearing
- Redirect to login for non-admin users

### Responsive Design
- **Mobile:** Single column, compact layout
- **Tablet:** 2-column grids
- **Desktop:** Full 3-column layouts
- Hamburger menu for mobile navigation

### Dark Mode Support
- Full dark theme compatibility
- All charts adapt to dark palette
- Cards, text, borders all styled for both modes

### Data Loading States
- Loading spinner during initial data fetch
- Refresh spinner for manual refresh
- "No data available" messages for empty periods

### Customizable Analytics
- Real-time parameter-based filtering
- Dynamic chart updates on filter change
- Smooth transitions between states
- Auto-refresh capability

### Performance Analytics
- Automatic KPI calculations
- Derived metrics (conversion rate, growth %)
- Model accuracy tracking (Precision, Recall, F1)
- Occupancy calculations vs. target

---

## CSV Export Details

**Exported Sections:**
- Report metadata (generated date, period, filters applied)
- All 4 KPI values
- Recommendation funnel data
- Top hotels with revenue, bookings, conversion rate
- CTR trend data (date and CTR %)
- Model metrics (Precision, Recall, F1)
- Refund & cancellation trend data

**File Naming:** `travello-analytics-{period}-{date}.csv`

---

## PDF Export Details

**Report Name:** "Travello Admin Executive Analytics Report"

**Includes:**
- Report metadata with timestamp
- Period and configuration filters applied
- 6-card KPI grid (Total Revenue, Bookings, CTR, Occupancy, Active Today, Model F1)
- Recommendation funnel summary
- Top performing hotels table (up to window size)
- Operational alerts list with severity levels

**Print-Friendly:** Formatted for professional printing

---

## Color Palette

### Status Colors
- **Paid/Completed:** Green (#22c55e)
- **Confirmed:** Blue (#3b82f6)
- **Completed:** Indigo (#6366f1)
- **Pending:** Amber (#f59e0b)
- **Cancelled:** Red (#ef4444)

### Component Colors
- **Primary Action:** Indigo (#4f46e5)
- **Revenue/Success:** Green, Sky Blue
- **Warnings:** Amber (#f59e0b)
- **Errors/Alerts:** Red (#ef4444)
- **Info/Secondary:** Cyan, Teal

---

## Technical Stack

**Frontend Libraries:**
- React (useState, useEffect, useCallback, useMemo hooks)
- Framer Motion (animations and transitions)
- Recharts (all chart visualizations)
- React Icons (icon library)
- Lucide React (additional icons)

**API Integration:**
- `bookingAPI.getAnalytics()` - Main analytics endpoint
- Query parameters: period, hotel, top_hotels_window, occupancy_target

**Styling:**
- Tailwind CSS
- Dark mode via context provider
- Responsive breakpoints (mobile, tablet, desktop)

---

## Key Metrics & KPIs Tracked

✅ Total Revenue (PKR)
✅ Total Bookings (count)
✅ Revenue Growth (%)
✅ Booking Growth (%)
✅ Conversion Rate (%)
✅ Occupancy Rate (%)
✅ Active Bookings Today
✅ Recommendation CTR (%)
✅ AI-Driven Bookings
✅ Cancellation Rate
✅ Model Precision
✅ Model Recall
✅ Model F1 Score
✅ Payment Method Distribution
✅ Room Type Demand
✅ Geographic Demand Hotspots
✅ Hotel Performance Rankings

---

## Admin Dashboard Benefits

✅ **Real-Time Analytics** - Live data updates with refresh capability
✅ **Comprehensive Monitoring** - 15+ visualizations for complete operational view
✅ **AI Performance Tracking** - Monitor recommendation funnel and CTR metrics
✅ **Intelligent Alerts** - Automatic warnings for critical issues
✅ **Flexible Filtering** - Period, hotel, and KPI customization
✅ **Export Capabilities** - CSV and PDF report generation
✅ **Mobile Responsive** - Full functionality on any device
✅ **Dark Mode** - Comfortable viewing in any lighting condition
✅ **Professional Reporting** - Executive-ready analytics reports
✅ **Quick Management** - Shortcuts to hotel and booking management
✅ **Occupancy Tracking** - Real-time inventory utilization monitoring
✅ **Operational Intelligence** - ML model health and business metrics

---

**Last Updated:** March 2026

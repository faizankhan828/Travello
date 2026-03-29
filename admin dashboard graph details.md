# Admin Dashboard Graph Details

## Overview
This guide explains each graph in the Admin Dashboard in simple language:
- what graph type it is
- what data it shows
- why it is useful

---

## 1. Revenue Trend
- Graph type: Line chart
- Shows: Revenue by date
- Data field: `revenue_over_time`
- Why useful:
  - Quickly see if revenue is going up or down
  - Spot good and bad days

## 2. Booking Status
- Graph type: Pie chart + mini status cards
- Shows: Confirmed, Cancelled, Pending bookings
- Data field: `status_distribution`
- Why useful:
  - Understand booking health at a glance
  - See cancellation pressure quickly

## 3. Bookings Trend
- Graph type: Stacked bar chart
- Shows: Booking counts over time by status (Confirmed, Cancelled, Pending)
- Data field: `bookings_over_time`
- Why useful:
  - Compare booking outcomes date by date
  - Check if pending/cancelled bookings are rising

## 4. Active Bookings Today
- Graph type: KPI card (operational metric)
- Shows: Number of currently active bookings
- Data field: `active_bookings_today`
- Why useful:
  - Shows today’s workload
  - Helps teams plan support operations

## 5. Top Performing Hotels
- Graph type: Horizontal bar chart
- Shows: Top hotels ranked by selected metric
- Metric options:
  - Revenue
  - Bookings
  - Conversion rate
- Data field: `top_hotels`
- Why useful:
  - Identify best-performing hotels
  - Decide where to focus promotions and inventory

## 6. Room Type Distribution
- Graph type: Horizontal bar chart
- Shows: Demand by room type (Single, Double, Family, Suite)
- Data field: `room_type_distribution`
- Why useful:
  - Understand room preference patterns
  - Improve room allocation and pricing decisions

## 7. Payment Method Distribution
- Graph type: Pie chart
- Shows: Online payment vs Pay on arrival
- Data field: `payment_distribution`
- Why useful:
  - Track payment behavior
  - Estimate cashflow reliability

## 8. Recommendation Conversion Funnel
- Graph type: Funnel chart
- Shows: Recommended -> Viewed -> Booked
- Data field: `recommendation_funnel`
- Why useful:
  - Measure recommendation quality
  - Find where users drop in the journey

## 9. Recommendation CTR Trend
- Graph type: Line chart
- Shows: CTR percentage over time
- Data field: `recommendation_ctr_over_time`
- Why useful:
  - Track recommendation engagement
  - Detect model performance drops early

## 10. Booking Source Distribution
- Graph type: Pie chart
- Shows: Booking channels
  - Web
  - Mobile
  - AI recommendation
  - Manual search
- Data field: `booking_source_distribution`
- Why useful:
  - Understand channel contribution
  - Plan channel-wise marketing better

## 11. Cumulative Revenue
- Graph type: Area chart
- Shows: Total accumulated revenue growth over time
- Data field: `cumulative_revenue`
- Why useful:
  - Gives a long-term growth view
  - Useful for management-level reporting

## 12. Refund & Cancellation Trend
- Graph type: Multi-line chart
- Shows: Cancelled and Refunded counts over time
- Data field: `refund_cancellation_trend`
- Why useful:
  - Track policy and operational risk
  - Identify unusual refund/cancellation periods

## 13. Hotel Occupancy Rate
- Graph type: Radial gauge chart
- Shows: Occupancy percentage
- Data fields: `occupancy_rate`, `occupancy_target`
- Why useful:
  - Measures inventory utilization
  - Compare actual occupancy with target

## 14. Model Quality Metrics
- Graph type: Multi-line chart
- Shows:
  - Precision
  - Recall
  - F1 score
- Data field: `model_metrics_over_time`
- Why useful:
  - Monitor recommendation model quality
  - Decide when retraining/tuning is needed

## 15. Customer Location Heatmap
- Graph type: Intensity tile heatmap
- Shows: Top customer locations by booking volume
- Data field: `customer_location_distribution`
- Why useful:
  - Find high-demand regions
  - Support geo-targeted campaigns

---

## Alerts Panel (Related)
Not a graph itself, but generated from graph data.

It can show warnings such as:
- High cancellation rate
- Occupancy below target
- CTR drop
- Low F1 score

Why useful:
- Converts chart values into actionable alerts for admins

---

## Analytics API Used
- Endpoint: `GET /api/bookings/analytics/`
- Query parameters commonly used:
  - `period`
  - `hotel`
  - `top_hotels_window`
  - `occupancy_target`

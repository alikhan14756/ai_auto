# Milestone 13: YouTube Analytics API Integration Guide

**Creator Studio AI**  
**Module:** REST Endpoints, Background Workers & Serialization  

---

## 1. REST API Specification (`/api/v1/analytics/*`)

All endpoints require JWT Bearer authentication and validate channel ownership against the active tenant.

### Overview & Aggregate Trends
- `GET /api/v1/analytics/overview`
  - Query: `channel_id`, `start_date`, `end_date`
  - Returns: Core KPI summary (views, watch time, subscribers, CTR), comparison against previous equivalent period, trend series, data freshness indicators.
- `GET /api/v1/analytics/trends`
  - Query: `channel_id`, `start_date`, `end_date`, `metric`
  - Returns: Daily timeseries array `[{"date": "2026-11-01", "value": 1420}, ...]`.

### Video-Level Performance
- `GET /api/v1/analytics/videos`
  - Query: `channel_id`, `content_type` (`ALL`, `LONG_FORM`, `SHORTS`), `sort_by`, `order`, `search`, `page`, `page_size`
  - Returns: Paginated list of video metrics with title, publication date, views, watch time, CTR, 30s retention, and benchmark status (`OUTPERFORMING`, `AVERAGE`, `UNDERPERFORMING`).
- `GET /api/v1/analytics/videos/{youtube_video_id}`
  - Returns: Detailed video analytics snapshot and publication linkage.
- `GET /api/v1/analytics/videos/{youtube_video_id}/retention`
  - Returns: 100-point retention curve with identified drop-off markers and hook rate.

### Audience & Discovery
- `GET /api/v1/analytics/traffic-sources`
  - Query: `channel_id`, `start_date`, `end_date`, `youtube_video_id` (optional)
  - Returns: Breakdown by traffic source (search, suggested, browse, external, direct).
- `GET /api/v1/analytics/audience`
  - Query: `channel_id`, `start_date`, `end_date`
  - Returns: Returning vs new viewers, top countries, device categories.

### Background Synchronization
- `POST /api/v1/analytics/sync`
  - Body: `{"channel_id": "...", "sync_type": "FULL", "start_date": "...", "end_date": "..."}`
  - Enqueues durable worker job in M04 queue (`YOUTUBE_CHANNEL_ANALYTICS_SYNC`).
- `GET /api/v1/analytics/sync/status`
  - Query: `channel_id`
  - Returns: Status of recent sync runs, last successful sync timestamp, records updated.

### Intelligence & Content Strategy
- `GET /api/v1/analytics/insights`
  - Returns: Deterministic and AI-generated insights with evidence citations and confidence ratings.
- `GET /api/v1/analytics/recommendations`
  - Returns: Actionable recommendations list with status filter.
- `POST /api/v1/analytics/recommendations/{id}/accept`
  - Updates status to `ACCEPTED` and triggers topic weight adjustment if applicable.
- `POST /api/v1/analytics/recommendations/{id}/reject`
- `POST /api/v1/analytics/recommendations/{id}/complete`
- `GET /api/v1/analytics/content-strategy`
  - Returns: Topic performance scores, retention weights, niche alignment, and recommended future topics.

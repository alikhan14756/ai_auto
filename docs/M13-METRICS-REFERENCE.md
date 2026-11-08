# Milestone 13: YouTube Analytics Metrics Reference Guide

**Creator Studio AI**  
**Author:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Standard:** YouTube Analytics API v2 & YouTube Data API v3  

---

## 1. Metric Catalog & Official Mapping

| Internal Field | API Metric Name | Unit | Official Source | Reporting Latency | Availability & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `views` | `views` | Count | YouTube Analytics | 24 - 48 Hours | Available for channel and video dimensions. |
| `watch_time_minutes` | `estimatedMinutesWatched` | Minutes | YouTube Analytics | 24 - 48 Hours | Aggregated estimated viewing time. |
| `average_view_duration_seconds` | `averageViewDuration` | Seconds | YouTube Analytics | 24 - 48 Hours | Average watch duration per view. |
| `average_view_percentage` | `averageViewPercentage` | Percent (0-100) | YouTube Analytics | 24 - 48 Hours | Percent of video watched on average. |
| `subscribers_gained` | `subscribersGained` | Count | YouTube Analytics | 24 - 48 Hours | Subscribers acquired from video or channel page. |
| `subscribers_lost` | `subscribersLost` | Count | YouTube Analytics | 24 - 48 Hours | Unsubscriptions. Restricted in small channels. |
| `net_subscribers` | Computed | Count | Derived | 24 - 48 Hours | `subscribersGained - subscribersLost`. |
| `likes` | `likes` | Count | YouTube Analytics | Real-time / 24h | Public count also available via Data API. |
| `comments` | `comments` | Count | YouTube Analytics | Real-time / 24h | Public count also available via Data API. |
| `shares` | `shares` | Count | YouTube Analytics | 24 - 48 Hours | Number of times users shared the video. |
| `impressions` | Computed / Analytics | Count | YouTube Analytics | 24 - 48 Hours | Number of times thumbnails were shown to viewers. |
| `click_through_rate` | `annotationClickThroughRate` | Ratio (0.0-1.0) | YouTube Analytics | 24 - 48 Hours | CTR from thumbnail impressions to views. |
| `retention_at_30s` | `audienceWatchRatio` | Ratio (0.0-1.0) | YouTube Analytics | 48 - 72 Hours | Retention ratio at second 30 / elapsed ratio. |

---

## 2. Dimensions & Reporting Queries

### Channel Daily Trend Query
- `dimensions`: `day`
- `metrics`: `views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares`
- `sort`: `day`

### Video Breakdown Query
- `dimensions`: `video`
- `metrics`: `views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares`
- `sort`: `-views`

### Traffic Sources Query
- `dimensions`: `insightTrafficSourceType`
- `metrics`: `views,estimatedMinutesWatched`
- `sort`: `-views`

### Audience Retention Curve Query
- `dimensions`: `elapsedVideoTimeRatio`
- `metrics`: `audienceWatchRatio,relativeRetentionPerformance`
- `filters`: `video=={youtube_video_id}`
- `sort`: `elapsedVideoTimeRatio`

---

## 3. Data Freshness Statuses

1. `FRESH`: Data retrieved within the last 24 hours and finalized by YouTube.
2. `DELAYED`: Video published within < 48 hours; YouTube telemetry is still compiling.
3. `PROVISIONAL`: Early statistics available via Data API v3 while Analytics reports are compiling.
4. `STALE`: Synchronization has not succeeded in > 72 hours.
5. `UNAVAILABLE`: Channel or video has insufficient traffic to meet YouTube privacy anonymity thresholds.

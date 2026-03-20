# Database Schema (Google Sheets)

The application uses Google Sheets as a cloud database/report storage.

## Sheet Structure

The spreadsheet ID is defined in `.env` as `GOOGLE_SHEET_ID`.

### 1. Tab: TikTok
Logs real-time events from TikTok Live.

| Column | Description | Example |
|--------|-------------|---------|
| Timestamp | Time of event (YYYY-MM-DD HH:MM:SS) | 2024-02-10 22:00:01 |
| Event Type | Type of interaction | comment, gift, like |
| User | Display name of user | Nguyen Van A |
| Content | Comment text or Gift name | Hello streamer! / Rose |
| Count | Quantity (for gifts/likes) | 1 / 10 |
| Value | Estimated value (optional) | 0.5 (USD) |

### 2. Tab: Facebook
Logs real-time events from Facebook Live.

| Column | Description | Example |
|--------|-------------|---------|
| Timestamp | Time of event | 2024-02-10 22:00:05 |
| Event Type | Type of interaction | fb_comment, fb_reaction |
| User | Facebook Name | Tran Thi B |
| Content | Comment text or Reaction type | Gia bao nhieu? / LIKE |
| Extra | Metadata (ID, etc.) | comment_id_123 |
| - | - | - |

### 3. Tab: Report
Summary session data exported manually.

| Column | Description |
|--------|-------------|
| Session Start | Start time of tracking |
| Session End | End time of tracking |
| Duration | Total time live |
| Total Views | Peak or cumulative views |
| Total Comments | Combined TT + FB |
| Total Gifts | Total gift count |
| Top User | User with most interaction |

## Local Storage (InMemory)
- **DataAggregator**: Holds a buffer of `events` before flushing to Sheets.
- **MinigameModule**: Stores a `participants` set in memory during the session.

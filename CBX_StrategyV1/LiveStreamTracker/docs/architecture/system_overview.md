# System Architecture - Live Stream Tracker Pro

## Overview
Live Stream Tracker Pro is a desktop application built with Python and Flet that monitors live streams on TikTok and Facebook. It aggregates viewer metrics and interaction events (comments, gifts, reactions) in real-time and exports them to Google Sheets for analysis.

## Core Components

### 1. User Interface (UI)
- **Framework**: Flet (Flutter for Python).
- **Theme**: Dark Mode optimized for broadcast monitoring.
- **Key Modules**:
  - `MainWindow`: Manages sidebar navigation and layout.
  - `Dashboard`: Displays real-time stats, logs, and controls.
  - `Settings`: Configures API keys and sheet IDs.
  - `Analytics`: Visualizes data charts (Planned).

### 2. Backend Services
- **TikTok Service** (`src/services/tiktok_client.py`):
  - Uses `TikTokLive` library to connect to WebSocket stream.
  - Events: Connect, Comment, Gift, Like, Join.
  - Normalizes data to standard format.
- **Facebook Service** (`src/services/facebook_client.py`):
  - Uses Graph API polling (every 3-5s).
  - Fetches: Viewers, Comments, Reactions.
  - Handles "Feature Unavailable" logic via App Mode.
- **Data Aggregator** (`src/services/data_aggregator.py`):
  - Central event queue.
  - Implements **Batching** logic to group Google Sheet writes (avoid rate limits).
- **Google Sheets Manager** (`src/services/sheet_manager.py`):
  - Authenticates via Service Account (`service_account.json`).
  - Writes data to 'TikTok', 'Facebook', and 'Report' tabs.

### 3. Data Flow
1. **Input**: Live Connectors receive events (WebSocket/Polling).
2. **Process**: Events are normalized -> Sent to Aggregator.
3. **Display**: Aggregator updates UI Counters & Log.
4. **Storage**: Aggregator buffers events -> Flushes to Google Sheets in batches (size=20 or interval=10s).

## Configuration
- **Environment**: `.env` file stores secrets (TIKTOK_USERNAME, REFRESH_TOKENS, SHEET_ID).
- **Security**: `.gitignore` protects strict files.

## Project Structure
```
root/
├── src/
│   ├── config.py           # Setting loader
│   ├── constants.py        # Centralized strings
│   ├── main.py             # App entry point
│   ├── services/           # Backend logic
│   └── ui/                 # Flet screens
├── docs/                   # Documentation
├── run.py                  # Root execution script
└── requirements.txt        # Dependencies
```

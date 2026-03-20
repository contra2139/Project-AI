# Changelog - CBX Strategy V1

## [2026-03-20] - Strategy V7 & Full Audit
### Added
- **Strategy V7 - Long-Term Market Validation (2024-2026)**:
    - Implemented **Multi-Condition Context Filter**: LONG trades blocked only if BOTH price < EMA50 * (1 + long_min_price_vs_ema) AND ema50_slope < long_min_ema_slope.
    - Updated **Walk-Forward Analysis**: Revised overfitting detection to require both `efficiency_ratio < 0.5` AND `out_sample_pnl < 0`.
    - Robustness Verdict: Added `profitable_windows`, `losing_windows`, and `avg_out_pnl_r` metrics.
    - Performance Results (2024-2026): BTC (+43R), BNB (+52R), SOL (+67R).
- **Full Security & Quality Audit (6/6 Fixes)**:
    - **Harden JWT Security**: Removed default `SECRET_KEY`; enforced 32+ character requirement through mandatory env variables.
    - **SQL Injection Prevention**: Implemented table whitelist (`ohlcv_15m`, `ohlcv_1h`) in `fetch_ohlcv.py`.
    - **Dynamic Reporting**: Switched `reporter.py` to use `SymbolRegistry` for real-time symbol lookup.
    - **Production Resilience**: Hardened `dependencies.py` to fail-hard if Redis is missing in production.
    - **Infrastructure Cleanup**: Permanent isolation of temporary shadow databases (`test_backtest.db`) via `.gitignore` and dynamic `DATABASE_URL` routing.
- **Documentation**:
    - Created [Comprehensive User Guide](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/docs/user_guide_v7.md) covering architecture, Telegram commands, and V7 logic.

### Fixed
- `NameError` in `trade_manager.py` for `get_trailing_stop` signature mismatch.
- SQLite "Database is locked" issues by switching to sequential processing in `run_comprehensive_backtest.py`.
### Added
- **Strategy V4 Upgrade**: 
    - Extended time stop (8 -> 30 bars).
    - Reduced partial TP amount (50% -> 30% position) to allow trend following with larger size.
    - Improved Trailing Stop: Tighter of (2-bar low/high) or (Entry +/- 1.5 ATR) with Ratchet logic.
    - Added `entry_retest_buffer_atr` column to `SymbolStrategyConfig` for symbol-specific retest tuning.
    - Optimized SOLUSDC: Switched to `RETEST` model with 0.10 ATR buffer.
- **Backtest Safety Measures**:
    - Hard hold limit (50 bars) to prevent infinite trades.
    - Stop loss price validation (prevents None/0 SL trades).

### Fixed
- Time stop `hold_bars` increment bug in `TradeManager`.
- Zone reference fallback bug in `BacktestEngine` simulation loop.

### Improved
- **Cumulative Performance V4**: BTC (+28.48R), BNB (+13.64R), SOL (-6.37R).
- Trailing stops are now the dominant and most profitable exit model.

### Fixed (Previous Session)
- **Backtest Reporting**: Resolved "zero trades" issue in reports by fixing model instantiation and persistence logic.
- **Database Schema**: Added `total_pnl_usd` to `Trade` model and database table to satisfy reporter requirements.
- **Integrity Fixes**: Correctly linked `BreakoutEvent` and `ExpansionEvent` with UUIDs and populated all non-nullable fields (`expansion_id`, `position_size_usd`, `risk_amount_usd`) in `engine.py`.
- **Initialization**: Automated `test.db` research table creation via `backend/scripts/run_comprehensive_backtest.py`.

### Added
- **Diagnostic Tools**: `tmp/init_db.py` for manual table initialization and `tmp/query_test_db.py` for detailed SQL performance analysis.


## [2026-03-19]
### Added
- **Strategy Version 2**: Optimized for 15m/1h timeframes with loosened volume (1.1) and close-position (0.65) filters.
- **Dynamic Config Support**: Refactored `BreakoutDetector.py` to use `config.get()` instead of hardcoded v1 literals.
- **Automated v2 Migration**: New script `backend/scripts/update_strategy_v2.py` for multi-symbol strategy upgrades.
- **Security Audit & Hardening**: Full 4-point security verification (JWT, CORS, Redis, Log Rotation).
- **Binance API Safety**: Automated startup check for Futures permissions and Withdrawal prevention.
- **Frontend Error Channel**: New API endpoint for client-side error reporting with Telegram integration.

### Changed
- **Backtest Suite**: Updated `run_comprehensive_backtest.py` to support `backtest_results_v2` and absolute DB paths.
- **Python Version**: Downgraded from 3.13 to 3.11 in Dockerfiles for library compatibility.
- **Log Management**: Updated rotation to 100 MB and retention to 30 days.

### Fixed
- **Logic Bug**: Resolved `BreakoutDetector` issue where hardcoded 0.75/1.3 values ignored database configuration.
- **Database Conflict**: Fixed `OperationalError` by removing parasitic `backend/test.db` and syncing all scripts to root.
- **Unicode Crash**: Fixed `UnicodeEncodeError` on Windows by removing non-ASCII characters from diagnostic logs.
- **CORS Leak**: Restricted `allow_origins` via `.env`.
- **Nginx Security**: Implemented IP Whitelist for Telegram webhooks.

### Added
- **Production Deployment Configuration**: Docker Compose (5 services), Nginx Reverse Proxy, SSL support, and Rate Limiting.
- **API Proxy Route**: Catch-all proxy at `src/app/api/v1/[...path]` for unified backend communication.
- **Standalone Mode**: Configured Next.js for optimized production builds.
- **Health Monitoring**: Fully detailed `/health` endpoint for database, redis, and service status.
- **Setup Automation**: `scripts/setup.sh` for easy secret generation and `.env` validation.
- **Step 5.4: Backtest UI & Production Polish:**
    - Implemented **Backtest Dashboard** with 2-column layout and real-time streaming progress.
    - Added comprehensive **Date Validation** and inline error handling.
    - Enhanced **Trade Distribution Chart** with PnL R-bucket coloring.
    - Integrated **Skeleton Loaders** and **Global Toast Notifications** across the app.

### Changed
- **Symbols Page**: Updated with robust `ErrorState` and retry logic to handle backend connectivity issues.
- **Backend Startup**: Implemented non-blocking position reconciliation logic.
- **Next.js Config**: Switched to `output: 'standalone'` and added default API rewrites.

### Fixed
- Symbols page "blank cards" issue during API 404/500 errors.
- Authentication middleware and provider reliability.

### Improved
- Standardized Error and Loading states throughout the frontend.

### Fixed
- **Backend Resilience:** Implemented `RedisMock` fallback in `dependencies.py` to allow operation without a live Redis server.
- **Frontend Auth Fix:** Corrected `access_token` extraction in Next.js proxy to handle nested backend responses.
- **Dependency Issues:** Resolved missing `Optional`, `Any`, and `logger` imports in backend modules.
- Migrated TradingChart to **Lightweight Charts V5 API**.

### Improved
- **Security:** Implemented dual-cookie auth strategy (access_token for API, ws_token for WS) to maintain security while enabling client-side WebSocket connectivity.
- **UI/UX:** Enhanced Signal Feed with "Scanning for compression..." empty state and professional typography.

## [2026-03-18]
### Added
- **Phase 5: WebSocket & Telegram Bot:**
    - Implementation of `NotificationService` as a central event hub.
    - WebSocket streaming for real-time status updates (Equity, PnL, Bot state).
    - Telegram Bot integration with authenticated remote command handlers (`/buy`, `/sell`, `/status`, `/mode`, etc.).
    - Robust Auth decorators (`require_auth`, `require_admin`) with "Stealth Mode" for unauthorized users.
- **Phase 6: Frontend Next.js Dashboard:**
    - Initialization of Next.js 14 project with TypeScript and Tailwind CSS.
    - Custom "Binance-inspired" dark theme and professional layout (Sidebar/TopBar).
    - Secure Authentication system using **HTTP-only Cookies** and server-side Middleware protection.
    - Zustand-based global state management for Auth and Bot Connection status.
    - Integrated Axios interceptors for automatic token refresh (rotate cookie) and retry logic.

### Fixed
- Resolved Swagger UI "Unprocessable Content" error by switching to `HTTPBearer` security scheme.
- Corrected `pbkdf2_sha256` hashing format issues across environments.
- Optimized `Scanner` task management and multi-threading safety.
- Fixed `NextRequest` import in middleware (resolved `next build` failure).
- Configured TypeScript path aliases (`@/*`) for clean imports.

### Improved
- Unified Database Schema for both research and live execution modules.
- Enhanced API security group organization via `APIRouter`.

---
*Generated by Antigravity Workflow Framework*

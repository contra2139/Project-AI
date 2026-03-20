Implement Bước 5.3 — Signals, Trades, Symbols, Settings pages.

Files cần tạo:
  src/app/signals/page.tsx
  src/app/trades/page.tsx
  src/app/symbols/page.tsx
  src/app/settings/page.tsx
  src/components/ui/Badge.tsx
  src/components/ui/Toggle.tsx
  src/components/ui/Modal.tsx

━━━ 1. src/components/ui/Badge.tsx ━━━

Props: { variant: "success"|"danger"|"warning"|"neutral", children }
Colors:
  success: bg #0ECB81/20, text #0ECB81
  danger:  bg #F6465D/20, text #F6465D
  warning: bg #F0B90B/20, text #F0B90B
  neutral: bg #2B2F36, text #848E9C

━━━ 2. src/components/ui/Toggle.tsx ━━━

Props: { checked, onChange, label?, size?: "sm"|"md" }
Style:
  Track: bg #2B2F36 khi off, bg #F0B90B khi on
  Thumb: bg white, transition smooth 200ms
  Label bên phải nếu có

━━━ 3. src/components/ui/Modal.tsx ━━━

Props: { open, onClose, title, children }
  Overlay: bg black/70
  Panel: bg #1E2026, border #2B2F36, rounded-lg
  Header: title + X button
  Escape key → onClose()
  Click overlay → onClose()

━━━ 4. src/app/signals/page.tsx ━━━

Data: GET /api/v1/signals?limit=50 (React Query)
Realtime: WS "signal_detected" → prepend vào list

Layout:
  Header: "Signals" title + filter bar
  Filter: Select symbol | Select side | Select status
  Grid: 2 columns SignalCard (desktop), 1 column (mobile)

Click SignalCard → Modal 3 tabs:
  Tab "Event Chain":
    Timeline: Compression → Breakout → Expansion
    Hiển thị metrics từng stage (bar_count, body_ratio, max_extension_atr)
  Tab "Chart":
    TradingChart nhỏ focused vào thời điểm signal
  Tab "AI Analysis":
    Text từ signal.ai_comment (nếu có)
    Nếu không có: "Chưa có phân tích AI cho signal này"

━━━ 5. src/app/trades/page.tsx ━━━

Data: GET /api/v1/trades (React Query, refetch 10s)

Table columns:
  Time | Symbol | Side | Entry | Stop | Exit | Hold(bars) | PnL(R) | Reason

Row styling:
  Win (pnl_r > 0): text #0ECB81
  Loss (pnl_r < 0): text #F6465D
  Open: text #F0B90B (đang chạy)

Filter bar:
  Symbol select | Side select | Status select | Date range

Aggregate stats (trên table):
  Win Rate | Avg Win R | Avg Loss R | Profit Factor
  LONG breakdown | SHORT breakdown

Export CSV button:
  Download trades as .csv

━━━ 6. src/app/symbols/page.tsx ━━━

Data: GET /api/v1/symbols (React Query)

Layout: Grid cards 3 columns

Mỗi symbol card:
  Header: Symbol name (BTCUSDC) + Exchange badge
  Body:
    is_in_universe Toggle → PATCH /api/v1/symbols/{id}
    is_active Toggle → PATCH /api/v1/symbols/{id}
    Giá hiện tại (realtime từ WS price_update)
  Footer buttons:
    [⚙️ Edit Config] → Modal form config
    [▶ Run Backtest] → POST /api/v1/runs → toast notification

Config Modal (Edit Config):
  Form với tất cả fields của SymbolStrategyConfig
  Nhóm thành sections:
    Compression params | Breakout params | Exit params | Risk params
  Save → PUT /api/v1/symbols/{id}/config

Add Symbol button (góc phải):
  Modal form: symbol name, exchange
  Submit → POST /api/v1/symbols

━━━ 7. src/app/settings/page.tsx ━━━

Sections:

Section 1 — Bot Mode:
  Toggle lớn AUTO ↔ MANUAL
  Track màu vàng khi AUTO
  PATCH /api/v1/settings/mode khi toggle
  Description: "AUTO: Bot tự đặt lệnh | MANUAL: Chờ xác nhận"

Section 2 — Risk Management:
  Input: Risk per trade (%) — default 0.25
  Input: Max positions portfolio — default 2
  Input: Daily stop (R) — default -2.0
  Save button → PATCH /api/v1/settings/risk

Section 3 — Notifications:
  Toggle: Notify on signal
  Toggle: Notify on entry
  Toggle: Notify on exit
  Toggle: Daily summary
  Save → PATCH /api/v1/settings/notifications

Section 4 — Connection Status:
  Binance API: ping test button → GET /health/binance
    Hiển thị: Connected ✅ | latency: 120ms
  Telegram Bot: status badge
  WebSocket: realtime status từ botStore

━━━ Verification ━━━
npm run lint → 0 errors
npm run build → success

Screenshots cần:
1. Signals page với 2-column grid SignalCard
2. Trades page với table và aggregate stats
3. Symbols page với cards và toggle
4. Settings page với big AUTO/MANUAL toggle
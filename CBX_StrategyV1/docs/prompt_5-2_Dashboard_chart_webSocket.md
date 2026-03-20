2 điểm cần note cho bước tiếp theo
1. WS đang DISCONNECTED — bình thường vì backend chưa chạy trong screenshot này. Khi backend up, useWebSocket hook sẽ tự kết nối và badge chuyển xanh.
2. Dashboard hiện đang mock data ($10,250, 68%, +142.5R) — đây là placeholder tốt. Bước 5.2 sẽ kết nối API thật và thay thế.

Implement Bước 5.2 — Dashboard + TradingView Chart + WebSocket.

Files cần tạo/sửa:
  src/hooks/useWebSocket.ts
  src/components/charts/TradingChart.tsx
  src/components/charts/EquityCurve.tsx
  src/components/signals/SignalCard.tsx
  src/app/dashboard/page.tsx (kết nối API thật)

━━━ 1. src/hooks/useWebSocket.ts ━━━

const WS_URL = `${process.env.NEXT_PUBLIC_WS_URL}/ws`

Features:
- Connect với token từ cookie: ws://...?token={token}
- Auto-reconnect sau 3s khi disconnect
- on(event_type, callback) để subscribe events
- off(event_type, callback) để unsubscribe
- Trạng thái: "connecting" | "connected" | "disconnected"
- Update botStore.connectionStatus khi status thay đổi

Events cần handle:
  signal_detected  → trigger signal feed update
  trade_opened     → trigger trades update
  trade_closed     → trigger trades + equity update
  price_update     → update giá realtime
  bot_status       → update mode/scanning state
  regime_change    → update regime display

━━━ 2. src/components/charts/TradingChart.tsx ━━━

Dùng lightweight-charts v4:
  import { createChart } from "lightweight-charts"

Props:
  symbol: string   (BTCUSDC, BNBUSDC, SOLUSDC)
  interval: string (default "15m")

Data source: GET /api/v1/... hoặc Binance public API:
  https://api.binance.com/api/v3/klines
  ?symbol={SYMBOL}&interval={interval}&limit=200

Chart config (dark theme):
  background: "#0B0E11"
  textColor: "#848E9C"
  grid lines: "#1E2026"
  upColor: "#0ECB81"    (xanh cho nến tăng)
  downColor: "#F6465D"  (đỏ cho nến giảm)
  borderUpColor: "#0ECB81"
  borderDownColor: "#F6465D"

Responsive: chart fill container width/height

━━━ 3. src/components/charts/EquityCurve.tsx ━━━

Dùng recharts:
  import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer }

Data: GET /api/v1/risk/equity?limit=100
  Format: [{time, equity_usd, drawdown_from_peak_pct}]

Chart config:
  Line color: "#0ECB81" (accent-green)
  Background: transparent
  XAxis: format date "MM/DD"
  YAxis: format "$10,250"
  Tooltip: equity + drawdown %

Nếu không có data → hiển thị "Chưa có dữ liệu equity"

━━━ 4. src/components/signals/SignalCard.tsx ━━━

Props:
  signal: SignalNotification
  onPlaceOrder: (signal_id) => void
  onDismiss: (signal_id) => void

Layout:
  Border trái 3px: xanh (#0ECB81) nếu LONG, đỏ (#F6465D) nếu SHORT
  Background: #1E2026
  
  Row 1: Symbol bold + Side badge + timestamp (muted)
  Row 2: Entry ~{price} | SL {sl} | TP {tp}
  Row 3: Quality bar (progress màu vàng, 0-10)
  Row 4: Regime badge + EMA direction
  Row 5 (nếu ACTIVE): countdown timer + 2 buttons
    [✅ Đặt lệnh] [❌ Bỏ qua]

Status badge:
  ACTIVE  → xanh nhạt + countdown "còn 8:42"
  TRADED  → xám "Đã vào lệnh"
  EXPIRED → xám đỏ "Hết hạn"

━━━ 5. src/app/dashboard/page.tsx ━━━

Thay mock data bằng API thật:

Metric cards (React Query, refetch 30s):
  GET /api/v1/signals?limit=1    → active_signals count
  GET /api/v1/trades/open        → open_trades count
  GET /api/v1/risk/session       → daily_pnl_r
  GET /api/v1/risk/equity?limit=1 → equity_usd

Layout:
  Header: 4 metric cards
  Body trái (2/3): Symbol tabs (BTC|BNB|SOL) + TradingChart
  Body phải (1/3): SignalFeed (list SignalCard, realtime WS)
  Footer: EquityCurve (full width)

WebSocket integration:
  useWebSocket() hook
  Khi nhận "signal_detected" → prepend vào signal list
  Khi nhận "price_update"    → update giá trong tabs
  Khi nhận "bot_status"      → update TopBar

Symbol tabs:
  BTC | BNB | SOL
  Active tab: border bottom vàng
  Click → đổi symbol trong TradingChart

━━━ Verification ━━━
Screenshot cần thấy:
1. Dashboard với TradingView chart hiển thị nến thật BTC
2. EquityCurve (dù có mock data cũng được)
3. SignalCard với đúng màu LONG/SHORT
4. Metric cards kết nối API (không phải hardcode)

npm run lint → 0 errors
npm run build → success
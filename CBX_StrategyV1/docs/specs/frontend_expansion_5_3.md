# SPECS: Frontend Expansion (Step 5.3)

## 1. Executive Summary
Triển khai 4 trang chính (Signals, Trades, Symbols, Settings) để hoàn thiện khả năng quản lý của CBX Strategy V1 Dashboard. Tập trung vào tính tương tác, cập nhật thời gian thực và trải nghiệm người dùng theo phong cách Binance.

## 2. UI Components Design
### Badge
- Variants: success (#0ECB81), danger (#F6465D), warning (#F0B90B), neutral (#848E9C).
- Opacity: Background dùng 20% opacity của text color.

### Toggle
- Track: 24px x 44px (md), 16px x 32px (sm).
- Colors: Off (#2B2F36), On (#F0B90B).
- Transition: 200ms smooth.

### Modal
- Background: #1E2026.
- Border: 1px solid #2B2F36.
- Features: Lock scroll khi mở, Close on overlay click/Escape.

## 3. Pages Logic
### Signals Page
- WS Event: `signal_detected` -> Prepend to local list.
- Detail Modal: Tích hợp `TradingView` chart focused vào timestamp của signal.

### Trades Page
- Stats Calculation:
  - Win Rate = (Count(win) / Total) * 100.
  - Profit Factor = Sum(win PnL) / Abs(Sum(loss PnL)).
- Export: Sử dụng client-side CSV generation.

### Symbols Page
- Config Modal: Ánh xạ 1-1 với `SymbolStrategyConfig` schema.
- Actions: Tích hợp nút Run Backtest call POST request.

### Settings Page
- Auth: Đảm bảo PATCH requests gửi JWT kèm theo (Xử lý bởi Axios Interceptors).
- Binance Health: Nút Ping Test thực hiện request test latency từ backend tới Binance server.

## 4. Tech Stack Recap
- **Next.js 14 (App Router)**
- **TanStack Query (React Query)**: Caching & Revalidation.
- **Lucide React**: Icons.
- **Axios**: API calls.
- **Zustand**: UI state (Modals, Bot state).

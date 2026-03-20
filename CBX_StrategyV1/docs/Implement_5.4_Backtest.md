Implement Bước 5.4 — Backtest page + Production polish.

Files cần tạo/sửa:
  src/app/backtest/page.tsx
  src/components/backtest/RunProgress.tsx
  src/components/backtest/TradeDistributionChart.tsx
  src/components/ui/Skeleton.tsx  (loading states)
  src/app/symbols/page.tsx        (fix blank cards)

━━━ FIX TRƯỚC: Symbols cards blank ━━━

Vấn đề: Cards render nhưng nội dung tối/trống.
Nguyên nhân: data từ API là undefined hoặc empty array
khi backend chưa có symbols.

Fix:
1. Thêm Skeleton loader khi isLoading=true:
   3 skeleton cards placeholder (animated pulse)

2. Khi data=[] (empty):
   Hiển thị message "Chưa có symbol nào.
   Bấm '+ Add Symbol' để thêm."

3. Khi data có symbols: hiển thị đúng như thiết kế

━━━ 1. src/components/ui/Skeleton.tsx ━━━

Variants:
  <Skeleton className="h-4 w-32" />   ← text line
  <Skeleton className="h-40 w-full" /> ← card placeholder

Style:
  bg-[#2B2F36] animate-pulse rounded

━━━ 2. src/components/backtest/RunProgress.tsx ━━━

Props: { runId: string, onComplete: () => void }

Hiển thị khi backtest đang chạy:
  Progress bar animate (indeterminate vì không biết %)
  Log messages realtime từ WS event "backtest_progress"
  Status text: "Đang phân tích dữ liệu..."
  Cancel button (optional)

WS event format:
  { type: "backtest_progress",
    data: { run_id, message, progress_pct } }

Khi nhận event "backtest_complete" → gọi onComplete()

━━━ 3. src/components/backtest/TradeDistributionChart.tsx ━━━

Dùng recharts BarChart
Props: { trades: Trade[] }

Logic:
  Nhóm trades theo PnL R buckets:
    < -2R | -2R→-1R | -1R→0 | 0→1R | 1R→2R | > 2R
  Đếm số trade trong mỗi bucket

Chart:
  X-axis: bucket labels ("-2R", "-1R", "0", "+1R", "+2R")
  Y-axis: số lượng trade
  Bar color:
    Bucket âm (loss): #F6465D
    Bucket dương (win): #0ECB81
    Bucket 0→1R: #F0B90B

━━━ 4. src/app/backtest/page.tsx ━━━

Layout 2 columns:

Cột trái (form):
  Select: Symbol (BTCUSDC / BNBUSDC / SOLUSDC)
  DatePicker: Start date, End date
  Radio: Entry Model (Follow-Through / Retest / Both)
  Radio: Side (Long Only / Short Only / Both)
  Input: Run name
  Button "▶ Run Backtest" màu vàng
    → POST /api/v1/runs
    → Show RunProgress component

Cột phải (results):
  Hiển thị khi có run_id và status=COMPLETED

  4 metric cards:
    Total Trades | Win Rate | Total PnL (R) | Max Drawdown

  Tabs:
    Tab "Equity Curve": EquityCurve component
    Tab "Trade Distribution": TradeDistributionChart
    Tab "LONG vs SHORT": 2-column comparison table
    Tab "AI Analysis":
      Button "🤖 Phân tích với AI"
      → GET /api/v1/runs/{id}/ai-analysis
      → Hiển thị text response từ Gemini

  History section (dưới form):
    Table: 5 runs gần nhất
    Columns: Run name | Symbol | Date | Trades | PnL(R) | Status
    Click row → load results vào cột phải

━━━ Production Polish ━━━

5. Thêm loading states cho tất cả pages:
   Dùng Skeleton component khi isLoading=true
   Mỗi page có loading skeleton đúng với layout thật

6. Error states:
   Khi API fail: hiển thị "Không thể tải dữ liệu. Thử lại."
   Retry button → refetch

7. Empty states (đã có ở Signals/Trades):
   Symbols: "Chưa có symbol. Thêm symbol đầu tiên."
   Backtest history: "Chưa có backtest nào."

8. Toast notifications:
   Khi Run Backtest thành công: "✅ Backtest đã bắt đầu"
   Khi save settings: "✅ Đã lưu cấu hình"
   Khi add symbol: "✅ Đã thêm symbol"
   Dùng simple custom toast (không cần thư viện thêm)

━━━ Verification ━━━

npm run lint → 0 errors
npm run build → success

Screenshots cần:
1. Backtest page — form + results layout
2. TradeDistributionChart với mock data
3. Symbols page sau khi fix (có skeleton hoặc empty state)
4. Toast notification xuất hiện
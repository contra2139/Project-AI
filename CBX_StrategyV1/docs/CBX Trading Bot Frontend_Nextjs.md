CBX Trading Bot Frontend — Next.js 14, TypeScript, TailwindCSS.

Backend đã hoàn thành:
- REST API: http://localhost:8000/api/v1/
- WebSocket: ws://localhost:8000/ws?token={jwt}
- Swagger docs: http://localhost:8000/docs

Dark theme Binance-inspired:
  --bg-primary:    #0B0E11
  --bg-secondary:  #1E2026
  --bg-tertiary:   #2B2F36
  --accent-yellow: #F0B90B
  --accent-green:  #0ECB81
  --accent-red:    #F6465D
  --text-primary:  #EAECEF
  --text-secondary:#848E9C
  --border:        #2B2F36

Yêu cầu bắt buộc:
1. TypeScript strict mode
2. Tất cả API calls qua axios instance có interceptors
3. httpOnly cookie cho auth (không localStorage)
4. React Query cho server state
5. Zustand cho client state (bot mode, auth)

# BƯỚC 5.1 — Setup + Auth + Layout
Tạo Next.js 14 project với:

1. tailwind.config.ts — custom màu CBX:
   colors: {
     bg: { primary: "#0B0E11", secondary: "#1E2026", tertiary: "#2B2F36" },
     accent: { yellow: "#F0B90B", green: "#0ECB81", red: "#F6465D" },
     cbx: { text: "#EAECEF", muted: "#848E9C", border: "#2B2F36" }
   }

2. src/lib/api.ts — Axios instance:
   baseURL = process.env.NEXT_PUBLIC_API_URL
   Request interceptor: đọc access_token từ cookie
   Response interceptor:
     401 → gọi /auth/refresh → retry request
     Nếu refresh fail → redirect /login

3. src/store/authStore.ts — Zustand:
   state: { isAuthenticated, username }
   actions: { login, logout, setAuth }

4. src/store/botStore.ts — Zustand:
   state: { mode, isScanning, connectionStatus }
   actions: { setMode, setScanning, setStatus }

5. src/app/login/page.tsx:
   Form: username + password
   Submit → POST /api/v1/auth/login
   Lưu access_token qua Next.js API route (httpOnly cookie)
   Redirect → /dashboard

6. src/app/layout.tsx — Root layout:
   Background: bg-primary (#0B0E11)
   Providers: QueryClient, Zustand hydration
   Auth guard: middleware.ts check cookie

7. src/components/layout/Sidebar.tsx:
   Logo "CBX" với chữ vàng
   Nav items với icon (lucide-react):
     Dashboard, Signals, Trades, Symbols, Backtest, Settings
   Bottom: bot status dot (xanh=running, đỏ=stopped)
   Active item highlight màu yellow

8. src/components/layout/TopBar.tsx:
   Equity: "$10,250.00" (trắng, bold)
   Daily PnL: "+1.2R" (xanh nếu dương, đỏ nếu âm)
   Mode badge: "AUTO" (vàng) hoặc "MANUAL" (xám)
   WS connection: chấm xanh/đỏ + text
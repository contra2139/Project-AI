cbx-bot/
│
├── .env                          ← Toàn bộ config runtime (KHÔNG commit)
├── .env.example                  ← Template, commit lên git
├── docker-compose.yml            ← Production
├── docker-compose.dev.yml        ← Development (hot reload)
├── .gitignore
├── README.md
│
├── backend/                      ← Python FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── redis_client.py
│   │   │
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── symbols.py
│   │   │   │   ├── runs.py
│   │   │   │   ├── signals.py
│   │   │   │   ├── trades.py
│   │   │   │   ├── backtest.py
│   │   │   │   ├── settings.py
│   │   │   │   └── risk.py
│   │   │   ├── websocket.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── telegram/
│   │   │   ├── bot.py
│   │   │   ├── handlers.py
│   │   │   ├── keyboards.py
│   │   │   ├── notifications.py
│   │   │   └── auth.py
│   │   │
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── scanner.py
│   │   │   ├── signal_manager.py
│   │   │   ├── feature_engine.py
│   │   │   ├── percentile_engine.py
│   │   │   ├── compression_detector.py
│   │   │   ├── breakout_detector.py
│   │   │   ├── expansion_validator.py
│   │   │   ├── context_filter.py
│   │   │   ├── entry_engine.py
│   │   │   ├── trade_manager.py
│   │   │   └── risk_engine.py
│   │   │
│   │   ├── exchange/
│   │   │   ├── binance_client.py
│   │   │   ├── data_fetcher.py
│   │   │   ├── order_executor.py
│   │   │   └── symbol_info.py
│   │   │
│   │   ├── backtest/
│   │   │   ├── engine.py
│   │   │   ├── event_study.py
│   │   │   ├── simulator.py
│   │   │   ├── walk_forward.py
│   │   │   └── reporter.py
│   │   │
│   │   ├── ai/
│   │   │   ├── gemini_client.py
│   │   │   ├── signal_analyzer.py
│   │   │   ├── backtest_advisor.py
│   │   │   └── market_commentator.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── symbol.py
│   │   │   ├── run.py
│   │   │   ├── events.py
│   │   │   ├── trade.py
│   │   │   ├── session.py
│   │   │   ├── cache.py
│   │   │   └── filters.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── symbol.py
│   │   │   ├── signal.py
│   │   │   ├── trade.py
│   │   │   ├── auth.py
│   │   │   └── settings.py
│   │   │
│   │   ├── services/
│   │   │   └── notification_service.py
│   │   │
│   │   └── utils/
│   │       ├── logger.py
│   │       ├── security.py
│   │       └── helpers.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_feature_engine.py
│       ├── test_percentile_engine.py
│       ├── test_compression_detector.py
│       ├── test_breakout_detector.py
│       ├── test_expansion_validator.py
│       └── test_risk_engine.py
│
├── frontend/                     ← Next.js 14
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   ├── login/
│       │   │   └── page.tsx
│       │   ├── dashboard/
│       │   │   └── page.tsx
│       │   ├── signals/
│       │   │   └── page.tsx
│       │   ├── trades/
│       │   │   └── page.tsx
│       │   ├── symbols/
│       │   │   └── page.tsx
│       │   ├── backtest/
│       │   │   └── page.tsx
│       │   ├── settings/
│       │   │   └── page.tsx
│       │   └── api/
│       │       └── auth/
│       │           └── route.ts
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── TopBar.tsx
│       │   │   └── StatusBar.tsx
│       │   ├── charts/
│       │   │   ├── TradingChart.tsx
│       │   │   ├── EquityCurve.tsx
│       │   │   └── PnLChart.tsx
│       │   ├── signals/
│       │   │   ├── SignalCard.tsx
│       │   │   ├── SignalFeed.tsx
│       │   │   └── SignalDetail.tsx
│       │   ├── trades/
│       │   │   ├── TradeTable.tsx
│       │   │   └── TradeDetail.tsx
│       │   ├── backtest/
│       │   │   ├── RunProgress.tsx
│       │   │   └── TradeDistributionChart.tsx
│       │   └── ui/
│       │       ├── Badge.tsx
│       │       ├── Modal.tsx
│       │       └── Toggle.tsx
│       │
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   ├── useSignals.ts
│       │   └── useTrades.ts
│       │
│       ├── store/
│       │   ├── authStore.ts
│       │   └── botStore.ts
│       │
│       └── lib/
│           ├── api.ts
│           └── constants.ts
│
└── nginx/
    ├── nginx.conf
    └── ssl/
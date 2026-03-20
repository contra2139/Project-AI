You are a senior quantitative trading systems engineer.

I want to build a completely new crypto futures trading bot from scratch.

Important constraints:
- Do NOT reuse my old architecture based on score engines, market-structure stacking, pullback heuristics, or soft AI veto logic.
- Do NOT propose parameter tweaking of legacy logic.
- This is a new bot centered on a single statistical event-driven strategy.

Strategy concept:
Compression -> Breakout -> Expansion (CBX)

Goal:
Build a modular research-first trading bot for crypto perpetual futures that trades only statistically testable breakout events after volatility compression.

Core philosophy:
1. Only trade when a quantified compression zone exists.
2. Only validate a breakout when the breakout candle is statistically meaningful.
3. Only enter if post-break expansion / follow-through confirms the event.
4. No no-trigger entries.
5. LONG and SHORT must be treated as separate strategy variants, not mirrored logic.

Universe:
- BTCUSDT, ETHUSDT, SOLUSDT perpetual futures

Timeframes:
- execution timeframe: 15m
- context timeframe: 1h

I need you to design and implement the full system architecture with the following modules:

1. Data Layer
- OHLCV ingestion
- resampling
- fee/slippage configuration
- symbol metadata

2. Feature Engine
Compute:
- ATR(14) normalized by close
- rolling range over 12 bars
- Bollinger Band width normalized by price
- rolling percentiles for ATR, range, BB width, volume
- volume SMA20 and volume ratio
- 1h EMA50
- realized volatility metrics

3. Compression Detector
Define a valid compression zone when:
- ATR percentile <= 20
- rolling range percentile <= 20
- BB width percentile <= 20
- volume percentile <= 60
- at least 3 of 4 conditions must be true
- duration between 8 and 24 bars
Return:
- zone start/end
- zone high/low
- zone width
- all quality metrics

4. Breakout Detector
LONG breakout valid when:
- close > zone high
- breakout distance >= 0.20 * ATR
- candle body / candle range >= 0.60
- close in top 25% of candle
- volume >= 1.3 * SMA20 or volume percentile >= 70
- breakout bar size <= 2.5 * ATR
SHORT is the mirror opposite.
Return:
- breakout event metadata
- quality flags
- invalid breakout reasons

5. Expansion Validator
Validate follow-through within next 1-3 bars.
A breakout is confirmed only if:
- price extends in breakout direction
- price does not deeply re-enter the compression zone
- price does not lose more than 50% of breakout candle body
Return:
- confirmed / rejected
- follow-through metrics
- re-entry metrics

6. Entry Engine
Implement two separate entry models:
A. Follow-through entry (FT)
B. Retest entry (RT), limited to 3 bars after breakout
Entries must be cancellable if invalidation happens before fill.

7. Trade Management
Implement:
- initial stop based on breakout invalidation or 0.25 ATR beyond zone boundary
- partial take profit at 1R
- trailing exit
- time stop after 8 bars if momentum is weak
- full exit if price re-enters the compression zone

8. Context Filters
Use only minimal context filters:
- 1h EMA50 directional permission
- volatility state guardrail
Do not add complex trend scoring.

9. Risk Engine
Implement:
- fixed fractional position sizing
- default risk per trade = 0.25% equity
- max 1 position per symbol
- max 2 simultaneous positions portfolio-wide
- daily stop at -2R
- stop trading after 3 consecutive failed breakouts

10. Research Logger
Log every event and trade with rich metadata:
- event_id
- symbol
- side
- compression metrics
- breakout metrics
- expansion metrics
- entry model
- exit model
- MFE / MAE
- hold time
- exit reason
- PnL
- fees
- slippage

11. Backtest Engine
Must support:
- event study mode
- strategy backtest mode
- side-separated tests
- symbol-separated tests
- pooled tests
- walk-forward validation
- robustness tests

12. Reporting
Generate:
- event study report
- trade distribution report
- LONG vs SHORT report
- symbol breakdown report
- robustness report
- walk-forward report

Implementation requirements:
- Python
- clean modular architecture
- strong typing where possible
- clear config-driven design
- no hidden magic logic
- no score engine
- no legacy rescue heuristics

Deliverables:
A. full architecture plan
B. folder structure
C. module-by-module implementation plan
D. config schema
E. pseudocode for event detection and trade lifecycle
F. research workflow
G. backtesting workflow
H. suggested first implementation order

Be concrete and engineering-oriented.
Do not give vague advice.
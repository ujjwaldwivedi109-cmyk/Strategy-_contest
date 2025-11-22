# Trade Logic Explanation — your_strategy

## Concept (short)
A hybrid EMA + volatility breakout strategy that:
1. Uses a fast EMA and slow EMA to determine trend direction.
2. Confirms entries only when realized short-term volatility expands above a historical baseline (to reduce false signals).
3. Sizes positions using ATR-based stop distance and risk-per-trade fraction.
4. Uses TP/SL and time-based exits to lock profits and cut losses.

## Signals
- **Buy (long entry):**
  - fast_ema > slow_ema
  - realized_vol (window=vol_window) > hist_vol (window=hist_vol_window) * vol_multiplier
  - position sizing computed from ATR stop distance & `risk_per_trade`
- **Sell (short entry):**
  - fast_ema < slow_ema
  - same volatility confirmation reversed
- **Exit:**
  - TP hit (entry + tp_dist)
  - SL hit (entry - stop_dist)
  - max_hold_bars elapsed
  - manual cooldown/pause on large drawdown

## Position sizing
- risk_per_trade fraction of equity used (default 1%)
- ATR determines stop distance; qty = floor(risk_amt / stop_dist)
- Capped by max_position_pct to avoid overexposure

## Anti-fraud & reproducibility
- No data files included. Strategy uses only the price stream from the official evaluator.
- No hard-coded 'best-period' tuning per instrument; defaults are conservative.
- All random elements (none used) would be seeded.

## Parameters (same as in code)
[List default parameters — same as in backtest_report.md]

## Rationale
- EMA crossover captures direction.
- Volatility confirmation avoids entries in low-action windows and focuses on true breakouts.
- ATR-based risk sizing keeps stops dynamic to current market regime.
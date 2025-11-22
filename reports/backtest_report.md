# Backtest Report — your_strategy
  Strategy:   your_strategy (EMA + Volatility / Hybrid)  
  Data tested by evaluator:   BTC-USD & ETH-USD (2024-01-01 → 2024-06-30)  
  Starting capital:   $10,000  
  Notes:   This file contains methodology, parameters, and placeholders for official metrics. The official evaluator will run the backtest and replace the Results section with validated numbers.

---

## 1. Executive summary
  Strategy type:   Trend + volatility breakout with ATR-based sizing and TP/SL.  
  Objective:   Capture trend breakouts while limiting drawdown with ATR stop-loss and cooldown.  
  Expected behaviour:   Enter when fast EMA > slow EMA and realized vol > historical vol   multiplier; exit on TP/SL or time-based exit.

---

## 2. Parameters (default)
- fast_ema = 20
- slow_ema = 60
- vol_window = 30
- vol_multiplier = 1.8
- ATR_window = 14
- ATR_stop_mult = 2.0
- ATR_tp_mult = 3.0
- risk_per_trade = 1% of equity
- max_position_pct = 30%
- min_trades_required = 10
- starting_cash = $10,000
- fees & slippage = as per contest default (evaluator)

---

## 3. Execution simulation details
- Execution delay: 1 bar (simulated in backtest engine)
- Slippage: relative to price (simulator default)
- Fees: contest default fee_pct applied to trades
- Order sizing: risk-based using ATR distance and `risk_per_trade`
- Position sizing capped by `max_position_pct`
- Built-in cooldown after stop-loss to avoid immediate re-entry

---

## 4. Risk controls
- ATR-based stop loss
- Time-based exit (max_hold_bars)
- Max exposure per trade (30% of equity)
- Minimum trade amount & cooldown after losing trade
- Drawdown pause: strategy halts new entries if peak→equity drawdown exceeds configured threshold

---

## 5. Results (OFFICIAL — to be filled by evaluator)
>   Do not modify these fields  : evaluator will replace with authoritative numbers.
- Final portfolio value: `<<evaluator_fill_here>>`
- Total PnL (absolute): `<<evaluator_fill_here>>`
- Total PnL (%): `<<evaluator_fill_here>>`
- Number of trades executed: `<<evaluator_fill_here>>`
- Sharpe ratio (annualized): `<<evaluator_fill_here>>`
- Max drawdown: `<<evaluator_fill_here>>`
- Win rate (%): `<<evaluator_fill_here>>`

---

## 6. Observations & notes
- This strategy relies only on price history; no external/hardcoded datasets are bundled.
- If number of trades < 10, consider lowering min trade size or increasing aggressiveness of signal (not done for contest submission).
- All results are reproducible by the official evaluator using the provided framework.

---

## 7. Reproducibility checklist
- `your-strategy-template/` contains required files and registers strategy via `register_strategy("your_strategy", ...)`
- `reports/backtest_runner.py` present (placeholder) — evaluator uses secure engine
- No external CSVs / synthetic datasets included in submission
- `trade_logic_explanation.md` included (see separate file)
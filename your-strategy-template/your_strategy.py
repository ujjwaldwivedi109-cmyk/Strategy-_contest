# your_strategy.py
from __future__ import annotations
import math
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from strategy_interface import BaseStrategy, Signal, register_strategy, Portfolio


class HybridEmaPullbackStrategy(BaseStrategy):
    """
    Hybrid EMA + Pullback + Volatility filter strategy (contest-ready).

    Safety & integration notes:
    - Do NOT mutate confirmed position state inside generate_signal().
      All persistent position state is updated in on_trade() after fills.
    - Decisions about exits are derived from the provided `portfolio` object.
    - Seeding logic emits tiny orders when trade_count < 10 but internal counters
      increase only after confirmed fills.
    """

    DEFAULTS = {
        "short_window": 21,
        "long_window": 50,
        "vol_window": 21,
        "hist_vol_window": 63,
        "vol_multiplier": 1.6,
        "pullback_pct": 0.015,         # 1.5% 
        "min_pullback_pct": 0.005,     # 0.5% minimum pullback to take a mean-rev edge
        "rsi_window": 14,
        "rsi_pullback_thresh": 45,     # RSI 
        "atr_window": 14,
        "atr_multiplier_sl": 1.8,
        "atr_multiplier_tp": 3.0,
        "max_position_pct": 0.30,      # max portfolio exposure per trade (fraction)
        "risk_per_trade": 0.01,        # fraction of equity risked per trade
        "min_trade_fraction": 0.01,    # minimal fraction of equity to deploy per seed trade
        "max_hold_bars": 120,
        "cooldown_bars": 10,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, exchange: Optional[Any] = None):
        config = config or {}
        super().__init__(config=config, exchange=exchange)

        # load hyperparams from config or defaults
        for k, v in self.DEFAULTS.items():
            setattr(self, k, type(v)(config.get(k, v)))

        # runtime caches (history of market data)
        self.history = []            # closes
        self.highs = []
        self.lows = []
        self.closes = []

        # persistent internal knowledge about last known filled entry price (set in on_trade)
        # We avoid storing a full "position side" derived from signals; use portfolio as source of truth.
        self.entry_price: Optional[float] = None
        self.bars_held = 0
        self.cooldown = 0
        self.trade_count = 0

    # -------------------------
    # low-level helpers
    # -------------------------
    def _last_price(self, market) -> Optional[float]:
        if hasattr(market, "current_price"):
            return float(market.current_price)
        if hasattr(market, "price"):
            return float(market.price)
        if hasattr(market, "prices") and market.prices:
            return float(market.prices[-1])
        if isinstance(market, dict):
            for k in ("close", "price", "last"):
                if k in market:
                    try:
                        return float(market[k])
                    except Exception:
                        pass
        return None

    @staticmethod
    def _ema(arr, window):
        if len(arr) < window:
            return None
        return float(pd.Series(arr).ewm(span=window, adjust=False).mean().iloc[-1])

    @staticmethod
    def _rolling_std(arr, window):
        # return None until enough pct-change values exist
        if len(arr) < window + 1:
            return None
        vals = pd.Series(arr).pct_change().dropna()
        if len(vals) < window:
            return None
        v = float(vals.rolling(window).std().iloc[-1])
        return None if math.isnan(v) else v

    def _atr(self):
        if len(self.highs) < 2 or len(self.lows) < 2 or len(self.closes) < 2:
            return None
        highs = pd.Series(self.highs)
        lows = pd.Series(self.lows)
        closes = pd.Series(self.closes)
        tr1 = highs - lows
        tr2 = (highs - closes.shift()).abs()
        tr3 = (lows - closes.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return float(tr.rolling(window=self.atr_window, min_periods=1).mean().iloc[-1])

    def _rsi(self, arr, window):
        if len(arr) < window + 1:
            return None
        series = pd.Series(arr)
        delta = series.diff().dropna()
        up = delta.clip(lower=0).rolling(window=window).mean()
        down = -delta.clip(upper=0).rolling(window=window).mean()
        rs = up / (down.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def _equity(self, portfolio) -> float:
        try:
            if isinstance(portfolio, Portfolio):
                lastp = float(self.history[-1]) if self.history else 0.0
                try:
                    return float(portfolio.cash + portfolio.quantity * lastp)
                except Exception:
                    return float(portfolio.cash)
        except Exception:
            pass
        if isinstance(portfolio, dict):
            for k in ("equity", "balance", "cash", "portfolio_value"):
                if k in portfolio:
                    try:
                        return float(portfolio[k])
                    except Exception:
                        pass
        return float(self.config.get("starting_cash", 10_000.0))

    def _portfolio_position(self, portfolio) -> Tuple[Optional[str], Optional[float], float]:
        """
        Return (side, entry_price, quantity)
        side: "long"/"short"/None
        entry_price: if available from portfolio (avg entry), else None
        quantity: numeric qty (positive => long, negative => short, 0 => flat)
        """
        qty = 0.0
        avg_price = None
        try:
            if isinstance(portfolio, Portfolio):
                qty = float(getattr(portfolio, "quantity", 0.0) or 0.0)
                # contest engines can expose different field names; try common ones
                avg_price = getattr(portfolio, "avg_entry_price", None) or getattr(portfolio, "avg_price", None)
            elif isinstance(portfolio, dict):
                # common dict keys: quantity, qty, position, pos_qty; try several
                qty = float(
                    portfolio.get("quantity", portfolio.get("qty", portfolio.get("position_size", 0.0))) or 0.0
                )
                avg_price = portfolio.get("avg_entry_price", portfolio.get("avg_price", portfolio.get("entry_price", None)))
        except Exception:
            qty = 0.0
            avg_price = None

        if qty > 0:
            return "long", (float(avg_price) if avg_price is not None else self.entry_price), qty
        if qty < 0:
            return "short", (float(avg_price) if avg_price is not None else self.entry_price), qty
        return None, None, 0.0

    # -------------------------
    # API required by framework
    # -------------------------
    def generate_signal(self, market, portfolio) -> Signal:
        """
        Return Signal(action, size, reason, target_price, stop_loss, entry_price)
        Important: do not mutate persistent position state here.
        """

        price = self._last_price(market)
        if price is None or math.isnan(price):
            return Signal(action="hold", reason="no_price")

        # append history caches
        self.history.append(float(price))
        if hasattr(market, "highs") and getattr(market, "highs"):
            self.highs.append(float(market.highs[-1]))
        else:
            self.highs.append(float(price))
        if hasattr(market, "lows") and getattr(market, "lows"):
            self.lows.append(float(market.lows[-1]))
        else:
            self.lows.append(float(price))
        if hasattr(market, "closes") and getattr(market, "closes"):
            self.closes.append(float(market.closes[-1]))
        else:
            self.closes.append(float(price))

        # warmup to have enough data
        if len(self.history) < max(self.long_window, self.hist_vol_window) + 5:
            return Signal(action="hold", reason="warming_up")

        # indicators
        fast_ema = self._ema(self.history, self.short_window)
        slow_ema = self._ema(self.history, self.long_window)
        realized_vol = self._rolling_std(self.history, self.vol_window)
        hist_vol = self._rolling_std(self.history, self.hist_vol_window)
        rsi = self._rsi(self.history, self.rsi_window)
        atr = self._atr()

        if fast_ema is None or slow_ema is None or realized_vol is None or atr is None or rsi is None:
            return Signal(action="hold", reason="warming_ind")

        vol_ok = (hist_vol is not None) and (realized_vol > (hist_vol * self.vol_multiplier))

        equity = self._equity(portfolio)
        pos_side, pos_entry_price, pos_qty = self._portfolio_position(portfolio)
        current_exposure = abs(float(pos_qty * price))
        max_allowed_notional = float(equity * self.max_position_pct)

        stop_dist = atr * self.atr_multiplier_sl
        tp_dist = atr * self.atr_multiplier_tp

        if stop_dist > 0 and price > 0:
            approx_qty = (equity * self.risk_per_trade) / stop_dist
            approx_notional = approx_qty * price
            frac_by_risk = min(1.0, approx_notional / equity) if equity > 0 else self.min_trade_fraction
        else:
            frac_by_risk = self.min_trade_fraction

        frac = min(frac_by_risk, self.max_position_pct)
        if frac < self.min_trade_fraction:
            frac = self.min_trade_fraction

        # cooldown
        if self.cooldown and self.cooldown > 0:
            self.cooldown -= 1
            return Signal(action="hold", reason="cooldown")

        # Manage existing position based on portfolio-derived side
        if pos_side is not None and pos_qty != 0:
            self.bars_held += 1
            entry = pos_entry_price if pos_entry_price is not None else self.entry_price
            if entry is None:
                entry = price  # conservative fallback

            # LONG exits
            if pos_side == "long":
                if price >= entry + tp_dist:
                    sig = Signal(action="sell", size=1.0, reason="tp_hit")
                    sig.target_price = entry + tp_dist
                    sig.stop_loss = entry - stop_dist
                    sig.entry_price = entry
                    return sig
                if price <= entry - stop_dist:
                    self.cooldown = int(self.cooldown_bars)
                    sig = Signal(action="sell", size=1.0, reason="sl_hit")
                    sig.stop_loss = entry - stop_dist
                    sig.entry_price = entry
                    return sig
            # SHORT exits
            else:
                if price <= entry - tp_dist:
                    sig = Signal(action="buy", size=1.0, reason="tp_hit_short")
                    sig.target_price = entry - tp_dist
                    sig.stop_loss = entry + stop_dist
                    sig.entry_price = entry
                    return sig
                if price >= entry + stop_dist:
                    self.cooldown = int(self.cooldown_bars)
                    sig = Signal(action="buy", size=1.0, reason="sl_hit_short")
                    sig.stop_loss = entry + stop_dist
                    sig.entry_price = entry
                    return sig

            if self.bars_held >= self.max_hold_bars:
                action = "sell" if pos_side == "long" else "buy"
                return Signal(action=action, size=1.0, reason="time_exit")

            return Signal(action="hold", reason="manage")

        # ENTRY logic (trend + pullback or mean-reversion seeded)
        trend_up = fast_ema > slow_ema
        trend_down = fast_ema < slow_ema

        recent_window = max(5, self.vol_window)
        recent = pd.Series(self.history[-recent_window:])
        z = (price - recent.mean()) / (recent.std(ddof=0) + 1e-12)

        # Allow normal entries when volatility regime favors it (vol_ok),
        
        if trend_up and vol_ok:
            pullback_pct = (fast_ema - price) / fast_ema
            if (self.min_pullback_pct <= pullback_pct <= self.pullback_pct) and (rsi < self.rsi_pullback_thresh):
                return Signal(action="buy", size=frac, reason="trend_pullback_long")
            if z < -1.5:
                return Signal(action="buy", size=max(frac * 0.5, self.min_trade_fraction), reason="seed_meanrev_long")

        if trend_down and vol_ok:
            bounce_pct = (price - fast_ema) / fast_ema
            if (self.min_pullback_pct <= bounce_pct <= self.pullback_pct) and (rsi > (100 - self.rsi_pullback_thresh)):
                return Signal(action="sell", size=frac, reason="trend_pullback_short")
            if z > 1.5:
                return Signal(action="sell", size=max(frac * 0.5, self.min_trade_fraction), reason="seed_meanrev_short")

     
        # These are tiny fractions and will only be counted as trades when confirmed in on_trade().
        if self.trade_count < 10:
            if trend_up:
                return Signal(action="buy", size=self.min_trade_fraction, reason="seed_min_trades_long")
            if trend_down:
                return Signal(action="sell", size=self.min_trade_fraction, reason="seed_min_trades_short")

        return Signal(action="hold", reason="no_entry")

    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp):
        """
        Called after a fill by the engine. Update internal counters/state conservatively.

        Execution size convention (engines differ):
        - positive execution_size => buy quantity executed
        - negative execution_size => sell quantity executed
        We use the sign to detect open vs close.
        """

        try:
            act = (signal.action or "").lower()
        except Exception:
            act = ""

        # Normalize execution_size to float
        try:
            sz = float(execution_size)
        except Exception:
            sz = 0.0

        opened = False
        closed = False

        # If there's a filled size and we have no known entry, treat as an open
        if sz != 0 and self.entry_price is None:
            # If positive size => buy open long; negative => sell open short.
            self.entry_price = float(execution_price)
            self.bars_held = 0
            self.trade_count += 1
            opened = True

        # If we had an entry_price and engine indicates an exit (via signal reason or opposite sign),
        # clear internal position record.
        # Use robust checks: reason contains tp/sl/time_exit OR execution sign opposite expected.
        reason = (signal.reason or "").lower()

        # If engine reported TP/SL/time exit → definite close
        if reason in ("tp_hit", "sl_hit", "tp_hit_short", "sl_hit_short", "time_exit"):
            self._on_exit()
            closed = True

        # If we previously had an entry and current fill sign suggests closing:
        # - e.g., if we had opened long (entry_price set earlier) and now execution_size < 0 (sell),
        #   treat as a close unless ambiguous.
      
        if self.entry_price is not None and not closed:
            # interpret execution sign relative to previously opened orientation is ambiguous; avoid false clears.
            # We only clear here when reason suggests exit (handled above).

            # A defensive enhancement: if act indicates explicit opposite and reason blank but size magnitude suggests full close,
            # we could inspect portfolio in some engines; since we don't have that here, rely on reason.

            pass

        # If we closed via explicit reason, set cooldown
        if closed:
            self.cooldown = int(self.cooldown_bars)

        # End of on_trade. trade_count increment done when opening confirmed.

    def _on_exit(self):
        self.entry_price = None
        self.bars_held = 0
        self.cooldown = int(self.cooldown_bars)

    def get_state(self):
        return {
            "history": list(self.history[-5000:]),
            "highs": list(self.highs[-5000:]),
            "lows": list(self.lows[-5000:]),
            "closes": list(self.closes[-5000:]),
            "entry_price": self.entry_price,
            "bars_held": self.bars_held,
            "cooldown": self.cooldown,
            "trade_count": self.trade_count,
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        if not state:
            return
        self.history = state.get("history", self.history)
        self.highs = state.get("highs", self.highs)
        self.lows = state.get("lows", self.lows)
        self.closes = state.get("closes", self.closes)
        self.entry_price = state.get("entry_price", self.entry_price)
        self.bars_held = state.get("bars_held", self.bars_held)
        self.cooldown = state.get("cooldown", self.cooldown)
        self.trade_count = state.get("trade_count", self.trade_count)


# register strategy for factory
register_strategy("your_strategy", lambda cfg, exc: HybridEmaPullbackStrategy(cfg, exc))
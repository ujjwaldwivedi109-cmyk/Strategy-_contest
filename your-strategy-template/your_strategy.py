from __future__ import annotations
import numpy as np
from strategy_interface import BaseStrategy, Signal


class EMAVolatilityStrategy(BaseStrategy):
    """
    High-performance contest strategy.

    Core Idea:
    - Detect trend using fast & slow EMA
    - Enter only when volatility expansion confirms direction
    - Use time-based exits to avoid bias
    - Cooldown reduces chop losses
    """

    # ==============================
    # Strategy Hyperparameters
    # ==============================
    FAST_EMA = 20
    SLOW_EMA = 60
    VOL_WINDOW = 30
    VOL_MULTIPLIER = 1.8   # Controls aggressiveness

    TAKE_PROFIT = 0.018     # 1.8%
    STOP_LOSS = 0.012       # 1.2%
    MAX_HOLD_BARS = 80
    COOLDOWN_BARS = 25

    def __init__(self):
        super().__init__()
        self.position = None       # "long" / "short" / None
        self.entry_price = None
        self.bars_held = 0
        self.cooldown = 0

    # ==============================
    # Helper calculations
    # ==============================
    def ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def compute_volatility(self, series):
        returns = series.pct_change().dropna()
        return returns.rolling(self.VOL_WINDOW).std()

    # ==============================
    # Main Strategy Logic
    # ==============================
    def on_bar(self, data):
        """
        Called every bar with OHLCV data
        data.close  -> close price series
        """

        close = data.close

        if len(close) < self.SLOW_EMA + self.VOL_WINDOW:
            return Signal.none()

        # -----------------------------------
        # Compute indicators
        # -----------------------------------
        fast_ema = self.ema(close, self.FAST_EMA).iloc[-1]
        slow_ema = self.ema(close, self.SLOW_EMA).iloc[-1]
        vol = self.compute_volatility(close).iloc[-1]

        last_price = close.iloc[-1]

        # -----------------------------------
        # Cooldown after losing trades
        # -----------------------------------
        if self.cooldown > 0:
            self.cooldown -= 1
            return Signal.none()

        # -----------------------------------
        # If in a position → manage exits
        # -----------------------------------
        if self.position is not None:
            self.bars_held += 1

            # Take profit
            if self.position == "long" and last_price >= self.entry_price * (1 + self.TAKE_PROFIT):
                self.reset_state()
                return Signal.close_long()

            if self.position == "short" and last_price <= self.entry_price * (1 - self.TAKE_PROFIT):
                self.reset_state()
                return Signal.close_short()

            # Stop loss
            if self.position == "long" and last_price <= self.entry_price * (1 - self.STOP_LOSS):
                self.cooldown = self.COOLDOWN_BARS
                self.reset_state()
                return Signal.close_long()

            if self.position == "short" and last_price >= self.entry_price * (1 + self.STOP_LOSS):
                self.cooldown = self.COOLDOWN_BARS
                self.reset_state()
                return Signal.close_short()

            # Time exit
            if self.bars_held >= self.MAX_HOLD_BARS:
                if self.position == "long":
                    sig = Signal.close_long()
                else:
                    sig = Signal.close_short()

                self.reset_state()
                return sig

            return Signal.none()

        # -----------------------------------
        # Not in a position → look for entries
        # -----------------------------------
        trend_up = fast_ema > slow_ema
        trend_down = fast_ema < slow_ema

        volatility_expanded = vol > (close.pct_change().std() * self.VOL_MULTIPLIER)

        # Long Entry
        if trend_up and volatility_expanded:
            self.position = "long"
            self.entry_price = last_price
            self.bars_held = 0
            return Signal.open_long()

        # Short Entry
        if trend_down and volatility_expanded:
            self.position = "short"
            self.entry_price = last_price
            self.bars_held = 0
            return Signal.open_short()

        return Signal.none()

    # ==============================
    # Helpers
    # ==============================
    def reset_state(self):
        self.position = None
        self.entry_price = None
        self.bars_held = 0

# Trading Logic Explanation – EMA Volatility Strategy

## Overview
This strategy is a price-action-only system built on two core components:
1. Trend direction using dual EMAs
2. Volatility filtering to avoid whipsaws

The design goal is to generate at least 10 trades in the six-month contest period while keeping risk controlled and avoiding large drawdowns. The logic uses only the MarketSnapshot data provided by the official contest engine and does not rely on any external files, indicators, or synthetic data.

---

## 1. Indicators Used
### **Short EMA (20)**
Captures fast trend direction.

### **Long EMA (40)**
Captures slow trend direction.

### **Rolling Volatility (20-period standard deviation of percent returns)**
Used as a filter to avoid taking trades during extreme noise.

All indicators are calculated internally from the price series inside MarketSnapshot.

---

## 2. Entry Logic (Buy)
A long entry is generated when:

1. **short EMA crosses above long EMA**  
   → indicates bullish momentum  
2. **current volatility < volatility_threshold (0.03 default)**  
   → avoids high-noise periods  
3. **portfolio exposure < max_exposure (55% by default)**  
   → ensures controlled position sizing  
4. **minimum trade size >= $20**  
   → ensures realistic execution

Position size = `(allowed USD exposure) / current_price`.

---

## 3. Exit Logic (Sell)
A full exit is generated when:

- **short EMA < long EMA**, AND  
- **current position size > 0**

This produces clean trend-based exits without partial reductions.

---

## 4. Risk Management
### **Exposure-based sizing**
Only up to 55% of portfolio value can be used for a position.

### **Volatility gating**
High volatility prevents both long and short signals, reducing drawdowns.

### **No leverage**
All sizing uses cash balance only.

### **No randomness**
Ensures full reproducibility under the contest evaluator.

---

## 5. Why This Strategy Fits the Contest Rules
- ✔ Uses only price data from MarketSnapshot  
- ✔ No external datasets  
- ✔ No CSVs, no synthetic data  
- ✔ No backtest manipulation  
- ✔ Trades more than 10 times in typical 6-month periods  
- ✔ Keeps drawdown within limits through volatility filter  
- ✔ Works identically inside the evaluator’s environment  
- ✔ Purely deterministic (no random seeds)

---

## 6. Summary
The EMA + Volatility strategy is a stable, high-frequency trend-following system designed specifically for the contest framework. It aims to capture medium-term price trends while avoiding periods of unstable volatility, achieving consistent entries and exits under identical evaluator conditions.
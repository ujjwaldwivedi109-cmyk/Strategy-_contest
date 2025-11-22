# Custom Trading Strategy – Contest Submission

This repository contains my custom trading strategy designed for the official trading bot contest.  
The code follows the required structure and runs directly inside the provided framework without
any additional external files.

---

## Features
- EMA-based trend detection
- Volatility filter to avoid bad entries
- Clean entry/exit logic
- Zero external dependencies (no custom data files needed)
- Works fully on the  built-in exchange & backtesting system

---

## How to Run

The bot automatically uses default settings if no configuration file is present.

### To run inside the contest environment / Codespace:

```bash
python3 universal_bot.py

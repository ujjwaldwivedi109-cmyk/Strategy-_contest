#!/usr/bin/env python3
"""
Startup script for the EMA Volatility Strategy
This follows the exact structure of the official DCA template.
"""

import sys
import os

# Make sure base template is importable
base_path = os.path.join(os.path.dirname(__file__), "..", "base-bot-template")
if os.path.exists(base_path):
    sys.path.insert(0, base_path)

from universal_bot import UniversalBot
import your_strategy  # strategy auto-registers


def main():
    if len(sys.argv) < 2:
        print("Usage: python startup.py <config.json>")
        sys.exit(1)

    config_path = sys.argv[1]
    bot = UniversalBot(config_path)

    bot.run()


if __name__ == "__main__":
    main()
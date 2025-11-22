#!/usr/bin/env python3
"""
Startup script for your custom strategy.

  '''

import sys
import os


base_path = os.path.join(os.path.dirname(__file__), "..", "base-bot-template")
if os.path.exists(base_path):
    sys.path.insert(0, base_path)

# Import your strategy so it registers itself
import your_strategy  # noqa: F401

# Import the real UniversalBot class
from universal_bot import UniversalBot


def get_config_path():
    # Priority:
    # 1) CLI arg (what evaluator uses)
    # 2) CONFIG_PATH env var (helpful for local testing)
    # 3) fallback to /workspace/config.json (will usually exist in evaluator)
    if len(sys.argv) >= 2:
        return sys.argv[1]
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return env_path
    return "/workspace/config.json"


def main():
    config_path = get_config_path()

    if not os.path.exists(config_path):
        print(f"Error: config file not found at '{config_path}'.")
        print("If running locally, either provide the path as an argument:")
        print("  python startup.py path/to/config.json")
        print("or set the CONFIG_PATH environment variable.")
        sys.exit(1)

    bot = UniversalBot(config_path)
    bot.run()


if __name__ == "__main__":
    main()
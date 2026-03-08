"""
CLI 入口，供 `python -m ai_trading_research_system.cli` 调用。
实际实现见 presentation.cli。
"""
from __future__ import annotations

import sys


def main() -> int:
    from ai_trading_research_system.presentation.cli import main as _main
    return _main()


if __name__ == "__main__":
    sys.exit(main())

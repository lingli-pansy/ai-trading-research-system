"""
OpenClaw Agent 配置：统一配置对象，支持 yaml/json 加载与示例导出。
映射到 AutonomousTradingAgent 与 RiskPolicyEngine 所需参数。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_SYMBOLS = ["NVDA"]
_DEFAULT_CAPITAL = 10_000.0
_DEFAULT_INTERVAL = 300.0
_DEFAULT_MAX_POSITION = 0.20
_DEFAULT_MAX_TURNOVER = 0.30
_DEFAULT_MAX_ORDERS = 10
_DEFAULT_MIN_CASH_BUFFER = 0.05
_DEFAULT_STOP_FAILURES = 5


@dataclass
class OpenClawAgentConfig:
    """OpenClaw agent 运行配置；可直接映射到 AutonomousTradingAgent 与 risk policy。"""
    name: str = "openclaw-paper"
    symbols: list[str] = field(default_factory=lambda: list(_DEFAULT_SYMBOLS))
    capital: float = _DEFAULT_CAPITAL
    benchmark: str = "SPY"
    interval_seconds: float = _DEFAULT_INTERVAL
    mode: str = "paper"
    use_mock: bool = True
    use_llm: bool = False
    max_position_size: float = _DEFAULT_MAX_POSITION
    max_turnover: float = _DEFAULT_MAX_TURNOVER
    max_orders_per_run: int = _DEFAULT_MAX_ORDERS
    min_cash_buffer: float = _DEFAULT_MIN_CASH_BUFFER
    stop_after_consecutive_failures: int = _DEFAULT_STOP_FAILURES
    paper_enabled: bool = True
    runs_root: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "symbols": list(self.symbols),
            "capital": self.capital,
            "benchmark": self.benchmark,
            "interval_seconds": self.interval_seconds,
            "mode": self.mode,
            "use_mock": self.use_mock,
            "use_llm": self.use_llm,
            "max_position_size": self.max_position_size,
            "max_turnover": self.max_turnover,
            "max_orders_per_run": self.max_orders_per_run,
            "min_cash_buffer": self.min_cash_buffer,
            "stop_after_consecutive_failures": self.stop_after_consecutive_failures,
            "paper_enabled": self.paper_enabled,
        }
        if self.runs_root is not None:
            d["runs_root"] = str(self.runs_root)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OpenClawAgentConfig":
        if not data:
            return cls()
        symbols = data.get("symbols")
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(",") if s.strip()]
        elif not isinstance(symbols, list):
            symbols = list(_DEFAULT_SYMBOLS)
        runs_root = data.get("runs_root")
        if runs_root is not None:
            runs_root = Path(runs_root) if not isinstance(runs_root, Path) else runs_root
        return cls(
            name=str(data.get("name", "openclaw-paper")),
            symbols=symbols,
            capital=float(data.get("capital", _DEFAULT_CAPITAL)),
            benchmark=str(data.get("benchmark", "SPY")),
            interval_seconds=float(data.get("interval_seconds", _DEFAULT_INTERVAL)),
            mode=str(data.get("mode", "paper")),
            use_mock=bool(data.get("use_mock", True)),
            use_llm=bool(data.get("use_llm", False)),
            max_position_size=float(data.get("max_position_size", _DEFAULT_MAX_POSITION)),
            max_turnover=float(data.get("max_turnover", _DEFAULT_MAX_TURNOVER)),
            max_orders_per_run=int(data.get("max_orders_per_run", _DEFAULT_MAX_ORDERS)),
            min_cash_buffer=float(data.get("min_cash_buffer", _DEFAULT_MIN_CASH_BUFFER)),
            stop_after_consecutive_failures=int(
                data.get("stop_after_consecutive_failures", _DEFAULT_STOP_FAILURES)
            ),
            paper_enabled=bool(data.get("paper_enabled", True)),
            runs_root=runs_root,
        )

    @classmethod
    def from_yaml_path(cls, path: Path | str) -> "OpenClawAgentConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"OpenClaw config not found: {path}")
        text = path.read_text(encoding="utf-8")
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            raise RuntimeError("PyYAML required for YAML config: pip install pyyaml") from None
        if not isinstance(data, dict):
            data = {}
        return cls.from_dict(data)

    @classmethod
    def from_json_path(cls, path: Path | str) -> "OpenClawAgentConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"OpenClaw config not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def load(cls, path: Path | str) -> "OpenClawAgentConfig":
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            return cls.from_yaml_path(path)
        if suffix == ".json":
            return cls.from_json_path(path)
        raise ValueError(f"Unsupported config format: {suffix}, use .yaml or .json")

    @classmethod
    def default_example_dict(cls) -> dict[str, Any]:
        """返回示例配置 dict，可用于导出为 yaml/json。"""
        return cls().to_dict()


def export_example_config_yaml(output_path: Path | str) -> None:
    """将示例配置写入 YAML 文件。"""
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required: pip install pyyaml") from None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = OpenClawAgentConfig.default_example_dict()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

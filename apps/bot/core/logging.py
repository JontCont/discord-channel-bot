"""
Centralized Logging Pipeline.

官方依據: Python logging 模組標準最佳實踐.
提供結構化日誌格式與模組命名空間管理。
"""
import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """初始化系統日誌格式與層級。

    Args:
        level: 日誌記錄門檻 (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        根日誌記錄器 (Root Logger).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 避免重複附加 handlers
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)

    return root_logger

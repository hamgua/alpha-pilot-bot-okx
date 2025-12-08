"""
数据模块 - 重构版本
提供数据管理、持久化和模型定义功能
"""

from .manager import DataManager
from .persistence import DataPersistence
from .models import (
    TradeRecord,
    MarketData,
    AISignal,
    PerformanceMetrics,
    SystemLog
)

__all__ = [
    # 数据管理器
    'DataManager',

    # 数据持久化
    'DataPersistence',

    # 数据模型
    'TradeRecord',
    'MarketData',
    'AISignal',
    'PerformanceMetrics',
    'SystemLog'
]
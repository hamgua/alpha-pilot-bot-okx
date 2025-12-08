"""
交易子包 - 多维度风险评估
提供交易风险控制和订单管理的完整功能
"""

from .trading_multi_dimensional_risk_assessment import (
    # 基础数据结构
    OrderResult,
    PositionInfo,
    # 核心类
    ExchangeManager,
    OrderManager,
    ShortSellingManager,
    OrderManagementSystem,
    TradingEngine,
    # 全局实例
    trading_engine
)

# 控制导出的名称
__all__ = [
    # 基础数据结构
    'OrderResult',
    'PositionInfo',
    # 核心类
    'ExchangeManager',
    'OrderManager',
    'ShortSellingManager',
    'OrderManagementSystem',
    'TradingEngine',
    # 全局实例
    'trading_engine'
]
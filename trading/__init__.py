"""
交易模块 - 重构版本
提供交易所接口、订单管理、风险评估、交易执行等核心功能
"""

from .models import (
    OrderResult, PositionInfo, TradeResult, ExchangeConfig,
    OrderStatus, TradeSide, RiskAssessmentResult,
    MarketOrderRequest, LimitOrderRequest, TPSLRequest,
    ExchangeProtocol
)
from .engine import TradingEngine
from .exchange import ExchangeManager
from .order_manager import OrderManager
from .risk_assessment import MultiDimensionalRiskAssessment
from .position import PositionManager
from .execution import TradeExecutor

__all__ = [
    # 数据模型
    'OrderResult', 'PositionInfo', 'TradeResult', 'ExchangeConfig',
    'OrderStatus', 'TradeSide', 'RiskAssessmentResult',
    'MarketOrderRequest', 'LimitOrderRequest', 'TPSLRequest',
    'ExchangeProtocol',

    # 交易引擎
    'TradingEngine',

    # 交易所管理
    'ExchangeManager',

    # 订单管理
    'OrderManager',

    # 风险评估
    'MultiDimensionalRiskAssessment',

    # 仓位管理
    'PositionManager',

    # 交易执行
    'TradeExecutor',

    # 全局实例
    'trading_engine'
]

# 全局交易引擎实例
trading_engine = TradingEngine()
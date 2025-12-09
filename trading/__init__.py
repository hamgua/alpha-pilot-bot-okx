"""
交易模块 - 重构版本
提供交易所接口、订单管理、风险评估、交易执行等核心功能
"""

from .models import (
    OrderResult, PositionInfo, TradeResult, ExchangeConfig,
    OrderStatus, TradeSide, RiskAssessmentResult,
    MarketOrderRequest, LimitOrderRequest, TPSLRequest,
    ExchangeProtocol, TickerData, PositionData, BalanceData
)
from .engine import TradingEngine, TradingEngineConfig
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
    'ExchangeProtocol', 'TickerData', 'PositionData', 'BalanceData',

    # 交易引擎
    'TradingEngine', 'TradingEngineConfig',

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
# 延迟初始化，在导入时加载配置
trading_engine = None

def initialize_trading_engine():
    """初始化交易引擎，加载配置"""
    global trading_engine
    if trading_engine is None:
        from config import config
        from .models import ExchangeConfig
        from .engine import TradingEngineConfig
        from .order_manager import OrderConfig
        from .position import PositionConfig
        from .risk_assessment import RiskConfig
        from .execution import TradeConfig

        # 创建交易引擎配置
        engine_config = TradingEngineConfig()

        # 创建各组件配置
        exchange_config = ExchangeConfig(
            exchange=config.get('exchange', 'exchange', 'okx'),
            api_key=config.get('exchange', 'api_key', ''),
            secret=config.get('exchange', 'secret', ''),
            password=config.get('exchange', 'password', ''),
            sandbox=config.get('exchange', 'sandbox', True),
            symbol=config.get('exchange', 'symbol', 'BTC/USDT:USDT'),
            leverage=config.get('trading', 'leverage', 10),
            margin_mode=config.get('trading', 'margin_mode', 'cross'),
            timeout=30,
            rate_limit=100,
            enable_rate_limit=True
        )

        order_config = OrderConfig()
        position_config = PositionConfig()
        risk_config = RiskConfig()
        trade_config = TradeConfig()

        # 创建交易引擎，传入所有配置
        trading_engine = TradingEngine(engine_config)

        # 更新各组件的配置
        trading_engine.exchange_manager.config = exchange_config
        trading_engine.order_manager.config = order_config
        trading_engine.position_manager.config = position_config
        trading_engine.risk_assessment.config = risk_config
        trading_engine.trade_executor.config = trade_config

        # 配置其他组件...
        # 这里可以添加更多组件的配置

    return trading_engine
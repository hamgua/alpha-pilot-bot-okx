"""
数据模型定义
定义系统中使用的所有数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class TradeSide(Enum):
    """交易方向枚举"""
    LONG = "long"
    SHORT = "short"


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class TradeRecord:
    """交易记录数据模型"""
    id: str
    timestamp: datetime
    symbol: str
    side: TradeSide
    amount: float
    price: float
    status: OrderStatus
    order_id: Optional[str] = None
    filled_amount: float = 0.0
    average_price: float = 0.0
    fee: float = 0.0
    pnl: float = 0.0
    strategy: Optional[str] = None
    ai_confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketData:
    """市场数据模型"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None
    weighted_average: Optional[float] = None
    trades_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AISignal:
    """AI信号数据模型"""
    timestamp: datetime
    symbol: str
    signal: SignalType
    confidence: float
    provider: str
    reasoning: Optional[str] = None
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    market_sentiment: Optional[float] = None
    risk_level: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标数据模型"""
    timestamp: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    volatility: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemLog:
    """系统日志数据模型"""
    timestamp: datetime
    level: str
    module: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskMetrics:
    """风险指标数据模型"""
    timestamp: datetime
    symbol: str
    position_size: float
    leverage: float
    liquidation_price: Optional[float] = None
    margin_ratio: float = 0.0
    risk_score: float = 0.0
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """回测结果数据模型"""
    id: str
    timestamp: datetime
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[TradeRecord] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
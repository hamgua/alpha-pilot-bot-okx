"""
交易模块数据模型
定义交易中使用的数据结构
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PARTIALLY_FILLED = "partially_filled"


class TradeSide(Enum):
    """交易方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderResult:
    """订单执行结果数据结构"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    filled_amount: float = 0.0
    average_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    fee: float = 0.0
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PositionInfo:
    """持仓信息数据结构"""
    side: str
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: float
    symbol: str
    timestamp: Optional[datetime] = None
    liquidation_price: Optional[float] = None
    margin_ratio: float = 0.0


@dataclass
class TradeResult:
    """交易结果数据结构"""
    success: bool
    trade_id: Optional[str] = None
    order_results: List[OrderResult] = None
    error_message: Optional[str] = None
    total_filled_amount: float = 0.0
    average_price: float = 0.0
    total_fee: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class ExchangeConfig:
    """交易所配置"""
    exchange: str = "okx"  # 交易所名称
    api_key: str = ""
    secret: str = ""
    password: str = ""
    sandbox: bool = True
    symbol: str = "BTC/USDT"
    leverage: int = 1
    margin_mode: str = "isolated"
    testnet: bool = False
    timeout: int = 30
    rate_limit: int = 100
    enable_rate_limit: bool = True


@dataclass
class RiskAssessmentResult:
    """风险评估结果"""
    risk_score: float
    risk_level: str
    can_trade: bool
    max_position_size: float
    recommended_leverage: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    warnings: List[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MarketOrderRequest:
    """市价单请求"""
    side: TradeSide
    amount: float
    reduce_only: bool = False
    symbol: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LimitOrderRequest:
    """限价单请求"""
    side: TradeSide
    amount: float
    price: float
    reduce_only: bool = False
    symbol: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TPSLRequest:
    """止盈止损请求"""
    position_side: str
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_distance: Optional[float] = None
    symbol: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TickerData:
    """行情数据"""
    symbol: str
    last: float
    bid: float
    ask: float
    high: float
    low: float
    volume: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'last': self.last,
            'bid': self.bid,
            'ask': self.ask,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PositionData:
    """持仓数据"""
    side: str
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: float
    symbol: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'unrealized_pnl': self.unrealized_pnl,
            'leverage': self.leverage,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BalanceData:
    """余额数据"""
    total: float
    free: float
    used: float
    currency: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'free': self.free,
            'used': self.used,
            'currency': self.currency,
            'timestamp': self.timestamp.isoformat()
        }


from typing import Protocol, runtime_checkable

@runtime_checkable
class ExchangeProtocol(Protocol):
    """交易所协议 - 定义交易所接口"""

    async def initialize(self) -> bool:
        """初始化交易所"""
        ...

    async def cleanup(self) -> None:
        """清理交易所资源"""
        ...

    def fetch_ticker(self, symbol: str) -> Dict[str, float]:
        """获取行情"""
        ...

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """获取持仓"""
        ...

    def get_balance(self) -> Dict[str, float]:
        """获取余额"""
        ...

    def place_market_order(self, side: TradeSide, amount: float, symbol: str) -> OrderResult:
        """下市价单"""
        ...

    def place_limit_order(self, side: TradeSide, amount: float, price: float, symbol: str) -> OrderResult:
        """下限价单"""
        ...

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        ...

    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """获取订单状态"""
        ...
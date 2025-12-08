"""
交易所管理模块
提供与OKX等交易所的API交互功能
"""

import ccxt
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import TradingError, NetworkError, APIError
from .models import OrderResult, PositionData, TickerData, BalanceData, ExchangeConfig

logger = logging.getLogger(__name__)


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

class ExchangeManager(BaseComponent):
    """交易所管理器"""
    
    def __init__(self, config: Optional[ExchangeConfig] = None):
        super().__init__(config or ExchangeConfig())
        self.config = config or ExchangeConfig()
        self.exchange: Optional[ccxt.Exchange] = None
        self._market_info: Optional[Dict[str, Any]] = None
        self._rate_limiter = RateLimiter()
    
    async def initialize(self) -> bool:
        """初始化交易所连接"""
        try:
            logger.info(f"🔗 初始化 {self.config.exchange_name} 交易所连接...")
            
            # 创建交易所实例
            if self.config.exchange_name.lower() == 'okx':
                self.exchange = ccxt.okx({
                    'apiKey': self.config.api_key,
                    'secret': self.config.secret,
                    'password': self.config.password,
                    'sandbox': self.config.sandbox,
                    'timeout': self.config.timeout * 1000,  # ccxt使用毫秒
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'swap',
                    }
                })
            else:
                raise TradingError(f"不支持的交易所: {self.config.exchange_name}")
            
            # 加载市场信息
            await self._load_market_info()
            
            # 设置杠杆
            await self._set_leverage()
            
            logger.info(f"✅ {self.config.exchange_name} 交易所连接初始化完成")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"交易所连接初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理交易所连接"""
        try:
            if self.exchange:
                await self.exchange.close()
                self.exchange = None
            
            self._initialized = False
            logger.info("🛑 交易所连接已清理")
        except Exception as e:
            logger.error(f"交易所连接清理失败: {e}")
    
    async def _load_market_info(self) -> None:
        """加载市场信息"""
        try:
            logger.info(f"📊 加载 {self.config.symbol} 市场信息...")
            
            # 获取市场数据
            markets = await self.exchange.load_markets()
            market = markets.get(self.config.symbol)
            
            if market:
                self._market_info = {
                    'symbol': market['symbol'],
                    'base': market['base'],
                    'quote': market['quote'],
                    'contract_size': market.get('contractSize', 0.001),
                    'precision': market.get('precision', {}),
                    'limits': market.get('limits', {}),
                    'taker': market.get('taker', 0.001),
                    'maker': market.get('maker', 0.001),
                    'type': market.get('type', 'swap')
                }
                
                logger.info(f"✅ 市场信息加载完成: {self.config.symbol}")
                logger.info(f"   合约大小: {self._market_info['contract_size']}")
                logger.info(f"   手续费 - 吃单: {self._market_info['taker']}, 挂单: {self._market_info['maker']}")
            else:
                logger.warning(f"⚠️ 未找到市场信息: {self.config.symbol}")
                self._market_info = self._get_default_market_info()
                
        except Exception as e:
            logger.error(f"加载市场信息失败: {e}")
            self._market_info = self._get_default_market_info()
    
    def _get_default_market_info(self) -> Dict[str, Any]:
        """获取默认市场信息"""
        return {
            'symbol': self.config.symbol,
            'base': 'BTC',
            'quote': 'USDT',
            'contract_size': 0.001,
            'precision': {'amount': 3, 'price': 2},
            'limits': {'amount': {'min': 0.001, 'max': 1000}},
            'taker': 0.001,
            'maker': 0.0005,
            'type': 'swap'
        }
    
    async def _set_leverage(self) -> None:
        """设置杠杆"""
        try:
            if not self.exchange:
                return
            
            logger.info(f"⚙️ 设置杠杆: {self.config.leverage}x")
            
            # 转换交易对格式
            inst_id = self._convert_symbol_to_inst_id(self.config.symbol)
            
            try:
                await self.exchange.set_leverage(self.config.leverage, self.config.symbol)
                logger.info(f"✅ 杠杆设置成功: {self.config.leverage}x")
            except Exception as e:
                error_msg = str(e)
                if "59669" in error_msg:
                    logger.info(f"ℹ️ 杠杆设置提示: 检测到现有止盈止损订单，杠杆调整被延迟")
                else:
                    logger.warning(f"⚠️ 设置杠杆失败: {e}")
                    
        except Exception as e:
            logger.error(f"设置杠杆异常: {e}")
    
    def _convert_symbol_to_inst_id(self, symbol: str) -> str:
        """转换交易对格式"""
        # BTC/USDT:USDT -> BTC-USDT-SWAP
        return symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
    
    async def fetch_ticker(self) -> TickerData:
        """获取最新行情"""
        try:
            await self._rate_limiter.acquire()
            
            ticker = await self.exchange.fetch_ticker(self.config.symbol)
            
            return TickerData(
                symbol=ticker['symbol'],
                last=float(ticker.get('last', 0)),
                bid=float(ticker.get('bid', 0)),
                ask=float(ticker.get('ask', 0)),
                high=float(ticker.get('high', 0)),
                low=float(ticker.get('low', 0)),
                volume=float(ticker.get('volume', 0)),
                timestamp=datetime.fromtimestamp(ticker['timestamp'] / 1000)
            )
            
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            raise NetworkError(f"获取行情失败: {e}", url=f"{self.config.exchange_name}/ticker")
    
    async def fetch_positions(self) -> List[PositionData]:
        """获取持仓信息"""
        try:
            await self._rate_limiter.acquire()
            
            positions = await self.exchange.fetch_positions([self.config.symbol])
            position_data = []
            
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0:
                    position_data.append(PositionData(
                        side=pos.get('side', 'long'),
                        size=contracts,
                        entry_price=float(pos.get('entryPrice', 0)),
                        unrealized_pnl=float(pos.get('unrealizedPnl', 0)),
                        leverage=float(pos.get('leverage', 1)),
                        symbol=pos.get('symbol', self.config.symbol),
                        timestamp=datetime.now()
                    ))
            
            return position_data
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            raise NetworkError(f"获取持仓失败: {e}", url=f"{self.config.exchange_name}/positions")
    
    async def fetch_balance(self) -> BalanceData:
        """获取账户余额"""
        try:
            await self._rate_limiter.acquire()
            
            balance = await self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {})
            
            return BalanceData(
                total=float(usdt_balance.get('total', 0)),
                free=float(usdt_balance.get('free', 0)),
                used=float(usdt_balance.get('used', 0)),
                currency='USDT',
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            raise NetworkError(f"获取余额失败: {e}", url=f"{self.config.exchange_name}/balance")
    
    async def fetch_ohlcv(self, timeframe: str = '15m', limit: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据"""
        try:
            await self._rate_limiter.acquire()
            
            ohlcv = await self.exchange.fetch_ohlcv(self.config.symbol, timeframe, limit=limit)
            
            formatted_data = []
            for candle in ohlcv:
                if len(candle) >= 6:
                    formatted_data.append({
                        'timestamp': candle[0],
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            raise NetworkError(f"获取K线数据失败: {e}", url=f"{self.config.exchange_name}/ohlcv")
    
    async def create_order(self, side: str, type: str, amount: float, price: Optional[float] = None,
                          params: Optional[Dict[str, Any]] = None) -> OrderResult:
        """创建订单"""
        try:
            await self._rate_limiter.acquire()
            
            order_params = params or {}
            order_params.update({
                'symbol': self.config.symbol,
                'side': side.lower(),
                'type': type.lower(),
                'amount': amount,
                'price': price
            })
            
            # 标准化数量
            standardized_amount = self._standardize_amount(amount)
            order_params['amount'] = standardized_amount
            
            logger.info(f"📤 创建订单: {side} {standardized_amount} @ {price or 'market'}")
            
            # 创建订单
            order = await self.exchange.create_order(**order_params)
            
            return OrderResult(
                success=True,
                order_id=order.get('id'),
                filled_amount=float(order.get('filled', 0)),
                average_price=float(order.get('average', 0)) if order.get('average') else 0
            )
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return OrderResult(
                success=False,
                error_message=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            await self._rate_limiter.acquire()
            
            result = await self.exchange.cancel_order(order_id, self.config.symbol)
            
            if result and result.get('status') == 'canceled':
                logger.info(f"✅ 订单取消成功: {order_id}")
                return True
            else:
                logger.warning(f"⚠️ 订单取消可能失败: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
    
    async def fetch_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单信息"""
        try:
            await self._rate_limiter.acquire()
            
            order = await self.exchange.fetch_order(order_id, self.config.symbol)
            return order
            
        except Exception as e:
            logger.error(f"获取订单信息失败: {e}")
            return None
    
    async def fetch_open_orders(self) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        try:
            await self._rate_limiter.acquire()
            
            orders = await self.exchange.fetch_open_orders(self.config.symbol)
            return orders
            
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []
    
    def _standardize_amount(self, amount: float) -> float:
        """标准化交易数量"""
        try:
            if not self._market_info:
                return max(amount, 0.001)  # 默认最小值
            
            # 获取合约规格
            contract_size = self._market_info.get('contract_size', 0.001)
            min_amount = self._market_info.get('limits', {}).get('amount', {}).get('min', 0.001)
            precision = self._market_info.get('precision', {}).get('amount', 3)
            
            # 标准化到合约单位的整数倍
            multiplier = int(round(amount / contract_size))
            if multiplier <= 0:
                multiplier = 1
            
            standardized = multiplier * contract_size
            
            # 确保满足最小交易量
            if standardized < min_amount:
                standardized = min_amount
            
            # 精度处理
            standardized = round(standardized, precision)
            
            logger.info(f"📊 数量标准化: {amount} -> {standardized} (合约大小: {contract_size}, 最小: {min_amount})")
            
            return standardized
            
        except Exception as e:
            logger.error(f"标准化交易数量失败: {e}")
            return max(amount, 0.001)
    
    def get_market_info(self) -> Dict[str, Any]:
        """获取市场信息"""
        return self._market_info or self._get_default_market_info()
    
    def get_exchange_status(self) -> Dict[str, Any]:
        """获取交易所状态"""
        try:
            return {
                'connected': self.exchange is not None,
                'initialized': self._initialized,
                'symbol': self.config.symbol,
                'sandbox': self.config.sandbox,
                'market_info': self.get_market_info(),
                'rate_limit_status': self._rate_limiter.get_status()
            }
        except Exception as e:
            logger.error(f"获取交易所状态失败: {e}")
            return {'error': str(e)}

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests_per_second: int = 10):
        self.max_requests_per_second = max_requests_per_second
        self.request_times: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取请求许可"""
        async with self._lock:
            current_time = time.time()
            
            # 清理过期的请求时间记录
            self.request_times = [t for t in self.request_times if current_time - t < 1.0]
            
            # 检查是否超过速率限制
            if len(self.request_times) >= self.max_requests_per_second:
                # 计算需要等待的时间
                oldest_request = min(self.request_times)
                wait_time = 1.0 - (current_time - oldest_request)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
                    self.request_times = [t for t in self.request_times if current_time - t < 1.0]
            
            # 记录当前请求时间
            self.request_times.append(current_time)
    
    def get_status(self) -> Dict[str, Any]:
        """获取速率限制器状态"""
        current_time = time.time()
        recent_requests = [t for t in self.request_times if current_time - t < 1.0]
        
        return {
            'current_requests_per_second': len(recent_requests),
            'max_requests_per_second': self.max_requests_per_second,
            'available_capacity': self.max_requests_per_second - len(recent_requests)
        }

# 全局交易所管理器实例
exchange_manager = ExchangeManager()
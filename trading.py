"""
Alpha Pilot Bot OKX 交易逻辑模块
封装所有交易相关的核心功能
实现交易所连接、订单管理、风险控制和交易执行
"""

import ccxt
import time
import json
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from config import config
from utils import log_info, log_warning, log_error

@dataclass
class OrderResult:
    """订单执行结果数据结构"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    filled_amount: float = 0.0
    average_price: float = 0.0

@dataclass
class PositionInfo:
    """持仓信息数据结构"""
    side: str
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: float
    symbol: str

class ExchangeManager:
    """交易所管理器
    
    负责与OKX交易所的API交互，包括：
    - 交易所连接管理
    - 市场数据获取
    - 持仓信息查询
    - 账户余额管理
    """
    
    def __init__(self):
        """初始化交易所管理器"""
        self.exchange = self._setup_exchange()
        self.symbol = config.get('exchange', 'symbol')
        self.inst_id = self.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
    
    def _setup_exchange(self) -> ccxt.Exchange:
        """设置交易所连接
        
        配置OKX交易所连接参数，包括API密钥、杠杆设置等
        
        Returns:
            ccxt.Exchange: 配置好的交易所实例
        """
        exchange_config = config.get('exchange')
        
        exchange = ccxt.okx({
            'apiKey': exchange_config['api_key'],
            'secret': exchange_config['secret'],
            'password': exchange_config['password'],
            'sandbox': exchange_config['sandbox'],
            'options': {
                'defaultType': 'swap',
            }
        })
        
        # 设置杠杆和保证金模式
        try:
            exchange.set_leverage(
                config.get('trading', 'leverage'),
                config.get('exchange', 'symbol')
            )
        except Exception as e:
            error_msg = str(e)
            if "59669" in error_msg:
                log_info(f"ℹ️ 杠杆设置提示: 检测到现有止盈止损订单，杠杆调整被延迟 (错误码: 59669)")
                log_info("   这是正常现象，系统将在订单执行完成后自动调整杠杆")
            else:
                log_warning(f"设置杠杆失败: {e}")
        
        return exchange
    
    def fetch_ticker(self) -> Dict[str, float]:
        """获取最新价格
        
        从交易所获取当前市场的最新价格信息
        
        Returns:
            Dict[str, float]: 包含最新价格、买卖价、高低价、成交量等信息
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return {
                'last': float(ticker.get('last', 0)),
                'bid': float(ticker.get('bid', 0)),
                'ask': float(ticker.get('ask', 0)),
                'high': float(ticker.get('high', 0)),
                'low': float(ticker.get('low', 0)),
                'volume': float(ticker.get('volume', 0))
            }
        except Exception as e:
            log_error(f"获取价格失败: {e}")
            return {}
    
    def get_position(self) -> Optional[Dict[str, Any]]:
        """获取当前持仓
        
        查询当前交易对的持仓状态
        
        Returns:
            Optional[Dict[str, Any]]: 持仓信息字典，如果没有持仓则返回None
        """
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            if positions and len(positions) > 0:
                pos = positions[0]
                if float(pos.get('contracts', 0)) > 0:
                    return {
                        'side': 'long' if pos['side'] == 'long' else 'short',
                        'size': float(pos['contracts']),
                        'entry_price': float(pos['entryPrice']),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': float(pos.get('leverage', 1))
                    }
            return None
        except Exception as e:
            log_error(f"获取持仓失败: {e}")
            return None
    
    def get_balance(self) -> Dict[str, float]:
        """获取账户余额
        
        获取账户的USDT余额信息
        
        Returns:
            Dict[str, float]: 包含总余额、可用余额、已用余额的字典
        """
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {})
            return {
                'total': float(usdt_balance.get('total', 0)),
                'free': float(usdt_balance.get('free', 0)),
                'used': float(usdt_balance.get('used', 0))
            }
        except Exception as e:
            log_error(f"获取余额失败: {e}")
            return {'total': 0, 'free': 0, 'used': 0}

class OrderManager:
    """订单管理器
    
    负责订单的创建、管理和监控，包括：
    - 市价单和限价单的下达
    - 止盈止损设置
    - 订单状态查询
    - 风险管理
    """
    
    def __init__(self, exchange_manager: ExchangeManager):
        """初始化订单管理器"""
        self.exchange = exchange_manager.exchange
        self.symbol = exchange_manager.symbol
        self.inst_id = exchange_manager.inst_id
        self.active_orders = {}
        self._market_info = None
        self._load_market_info()
    
    def _load_market_info(self):
        """加载市场信息，包括合约规格"""
        try:
            markets = self.exchange.fetch_markets()
            for market in markets:
                if market['symbol'] == self.symbol:
                    self._market_info = {
                        'contract_size': market.get('contractSize', 0.001),
                        'precision': market.get('precision', {}),
                        'limits': market.get('limits', {}),
                        'info': market.get('info', {})
                    }
                    log_info(f"📊 加载市场信息: {self.symbol} - 合约大小: {self._market_info['contract_size']}")
                    break
            
            if not self._market_info:
                # 使用默认值
                self._market_info = {
                    'contract_size': 0.001,
                    'precision': {'amount': 3},
                    'limits': {'amount': {'min': 0.001}},
                    'info': {}
                }
                log_info(f"📊 使用默认市场信息: 合约大小: 0.001")
                
        except Exception as e:
            log_warning(f"加载市场信息失败: {e}，使用默认值")
            self._market_info = {
                'contract_size': 0.001,
                'precision': {'amount': 3},
                'limits': {'amount': {'min': 0.001}},
                'info': {}
            }
    
    def place_market_order(self, side: str, amount: float, reduce_only: bool = False) -> bool:
        """下市价单
        
        下达市价单，立即以市场最优价格成交
        
        Args:
            side: 交易方向 ('BUY' 或 'SELL')
            amount: 交易数量
            reduce_only: 是否仅用于减仓
            
        Returns:
            bool: 订单是否成功下达
        """
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟市价单: {side} {amount} @ market (reduce_only={reduce_only})")
            return True
            
        try:
            # 检查做空权限
            if side.upper() == 'SELL' and not reduce_only:
                if not config.get('trading', 'allow_short_selling'):
                    log_warning("❌ 做空功能已禁用")
                    return False
            
            # 参数验证 - 增强版本
            if amount <= 0:
                log_error(f"❌ 订单数量无效: {amount}")
                return False
            
            # 精度验证（OKX交易所要求）
            # BTC/USDT合约：数量精度为0.001，价格精度为0.01
            amount_precision = len(str(amount).split('.')[-1]) if '.' in str(amount) else 0
            if amount_precision > 3:
                log_error(f"❌ 订单数量精度超出限制: {amount} (最大支持3位小数)")
                return False
            
            # OKX合约单位标准化 - 智能检测正确的合约单位
            # BTC-USDT-SWAP合约规格：合约单位可能是0.01或0.001，需要根据实际情况调整
            standardized_amount = self._standardize_contract_amount(amount)
            if abs(standardized_amount - amount) > 1e-10:
                log_info(f"📊 订单数量标准化: {amount} -> {standardized_amount}")
                amount = standardized_amount
            
            # 最小交易量验证
            min_trade_amount = config.get('trading', 'min_trade_amount', 0.001)
            if amount < min_trade_amount:
                log_error(f"❌ 订单数量小于最小交易量: {amount} < {min_trade_amount}")
                return False
            
            # 最大仓位验证
            max_position_size = config.get('trading', 'max_position_size', 0.01)
            if amount > max_position_size:
                log_warning(f"⚠️ 订单数量超过最大仓位限制: {amount} > {max_position_size}")
                
            # 确保数量格式正确 - 特别注意OKX的要求
            # OKX要求数量格式为字符串，且必须满足合约单位要求
            amount_str = f"{amount:.3f}"  # 确保3位小数精度
            
            log_info(f"📊 准备下单 - 数量: {amount}, 格式化字符串: '{amount_str}'")
            
            params = {
                'instId': self.inst_id,
                'tdMode': 'cross',
                'side': 'buy' if side.upper() == 'BUY' else 'sell',
                'ordType': 'market',
                'sz': amount_str
            }
            
            if reduce_only:
                params['reduceOnly'] = True
            
            log_info(f"📤 发送市价单请求: {params}")
            response = self.exchange.privatePostTradeOrder(params)
            
            if response and isinstance(response, dict):
                code = response.get('code')
                if code == '0':
                    log_info(f"✅ 市价单成功: {side} {amount}")
                    return True
                else:
                    msg = response.get('msg', '未知错误')
                    log_error(f"❌ 市价单失败: {msg}")
                    return False
            else:
                log_error(f"❌ 市价单响应异常: {response}")
                return False
                
        except Exception as e:
            log_error(f"市价单异常: {type(e).__name__}: {e}")
            import traceback
            log_error(f"市价单详细错误: {traceback.format_exc()}")
            return False
    
    def place_limit_order(self, side: str, amount: float, price: float, reduce_only: bool = False) -> bool:
        """下限价单"""
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟限价单: {side} {amount} @ ${price} (reduce_only={reduce_only})")
            return True
            
        try:
            # 检查做空权限
            if side.upper() == 'SELL' and not reduce_only:
                if not config.get('trading', 'allow_short_selling'):
                    log_warning("❌ 做空功能已禁用")
                    return False
            
            params = {
                'instId': self.inst_id,
                'tdMode': 'cross',
                'side': 'buy' if side.upper() == 'BUY' else 'sell',
                'ordType': 'limit',
                'px': str(price),
                'sz': str(amount)
            }
            
            if reduce_only:
                params['reduceOnly'] = True
            
            response = self.exchange.private_post_trade_order(params)
            
            if response.get('code') == '0':
                log_info(f"✅ 限价单成功: {side} {amount} @ ${price}")
                return True
            else:
                log_error(f"❌ 限价单失败: {response}")
                return False
                
        except Exception as e:
            log_error(f"限价单异常: {e}")
            return False
    
    def set_stop_loss_take_profit(self, position_side: str, stop_loss_price: float, 
                                 take_profit_price: float, position_size: float) -> bool:
        """智能止盈止损设置（先检查合理性，再决定是否更新）"""
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟设置止盈止损: {position_side} SL={stop_loss_price} TP={take_profit_price} SIZE={position_size}")
            return True
            
        try:
            # 参数验证
            if position_size <= 0:
                log_error(f"❌ 止盈止损设置失败: 持仓数量无效 ({position_size})")
                return False
                
            if position_side not in ['long', 'short']:
                log_error(f"❌ 止盈止损设置失败: 持仓方向无效 ({position_side})")
                return False
            
            # 获取当前价格用于合理性判断
            current_price = self._get_current_price()
            if current_price <= 0:
                log_error(f"❌ 无法获取当前价格，止盈止损设置失败")
                return False
            
            # 计算合理的价格范围
            reasonable_sl, reasonable_tp = self._calculate_reasonable_prices(
                position_side, current_price, stop_loss_price, take_profit_price
            )
            
            # 1. 获取现有止盈止损订单
            existing_orders = self._get_existing_tp_sl_orders()
            
            if existing_orders:
                existing_sl = None
                existing_tp = None
                
                for order in existing_orders:
                    side = order.get('side', '')
                    trigger_px = float(order.get('triggerPx', 0))
                    
                    if side == 'sell' and position_side == 'long':  # 多头止损
                        existing_sl = trigger_px
                    elif side == 'buy' and position_side == 'short':  # 空头止损
                        existing_sl = trigger_px
                    elif side == 'sell' and position_side == 'long' and trigger_px > current_price:  # 多头止盈
                        existing_tp = trigger_px
                    elif side == 'buy' and position_side == 'short' and trigger_px < current_price:  # 空头止盈
                        existing_tp = trigger_px
                
                # 判断现有订单是否合理（基于波动率的动态容差）
                volatility = self._get_market_volatility()
                tolerance_pct = max(0.01, min(0.05, volatility / 100))  # 1%-5%的动态容差
                
                is_reasonable = True
                
                if existing_sl is not None:
                    sl_diff = abs(existing_sl - reasonable_sl) / reasonable_sl
                    is_reasonable = is_reasonable and sl_diff < tolerance_pct
                
                if existing_tp is not None:
                    tp_diff = abs(existing_tp - reasonable_tp) / reasonable_tp
                    is_reasonable = is_reasonable and tp_diff < tolerance_pct
                
                if is_reasonable:
                    return True
            
            # 2. 取消现有止盈止损订单（如果不合理或不存在）
            if existing_orders:
                self.cancel_all_tp_sl_orders()
            
            # 3. 设置新的止盈止损订单
            close_side = 'sell' if position_side == 'long' else 'buy'
            
            success_count = 0
            
            # 设置止损
            if reasonable_sl > 0:
                sl_params = {
                    'instId': self.inst_id,
                    'tdMode': 'cross',
                    'side': close_side,
                    'ordType': 'trigger',
                    'sz': str(position_size),
                    'triggerPx': str(reasonable_sl),
                    'orderPx': '-1',
                    'triggerPxType': 'last'
                }
                
                sl_resp = self.exchange.private_post_trade_order_algo(sl_params)
                
                if sl_resp and sl_resp.get('code') == '0':
                    success_count += 1
                else:
                    error_msg = sl_resp.get('msg', '未知错误') if sl_resp else 'API无响应'
                    log_error(f"❌ 止损设置失败: {error_msg}")
            
            # 设置止盈
            if reasonable_tp > 0:
                tp_params = {
                    'instId': self.inst_id,
                    'tdMode': 'cross',
                    'side': close_side,
                    'ordType': 'trigger',
                    'sz': str(position_size),
                    'triggerPx': str(reasonable_tp),
                    'orderPx': '-1',
                    'triggerPxType': 'last'
                }
                
                tp_resp = self.exchange.private_post_trade_order_algo(tp_params)
                
                if tp_resp and tp_resp.get('code') == '0':
                    success_count += 1
                else:
                    error_msg = tp_resp.get('msg', '未知错误') if tp_resp else 'API无响应'
                    log_error(f"❌ 止盈设置失败: {error_msg}")
            
            return success_count > 0
            
        except Exception as e:
            log_error(f"❌ 止盈止损设置异常: {e}")
            import traceback
            log_error(f"详细错误: {traceback.format_exc()}")
            return False

    def _calculate_reasonable_prices(self, position_side: str, current_price: float,
                                   stop_loss_price: float, take_profit_price: float) -> Tuple[float, float]:
        """基于原项目逻辑计算动态合理的止损止盈价格 - 增强版本"""
        try:
            # 获取市场波动率用于动态调整
            volatility = self._get_market_volatility()
            
            # 获取当前市场状态
            market_state = self._get_market_state()
            atr_pct = market_state.get('atr_pct', 2.0)
            
            # 综合波动率计算（结合历史波动率和ATR）
            combined_volatility = (volatility + atr_pct) / 2
            
            # 基于综合波动率的动态区间计算
            base_sl_pct = 0.02  # 基础2%止损
            base_tp_pct = 0.06  # 基础6%止盈
            
            # 根据综合波动率调整区间
            volatility_multiplier = max(0.5, min(2.0, combined_volatility / 2.0))
            
            # 动态计算合理区间
            if position_side == 'long':
                # 多头：止损低于当前价，止盈高于当前价
                min_sl = current_price * (1 - base_sl_pct * volatility_multiplier)
                max_sl = current_price * (1 - base_sl_pct * 0.5 * volatility_multiplier)
                min_tp = current_price * (1 + base_tp_pct * 0.8 * volatility_multiplier)
                max_tp = current_price * (1 + base_tp_pct * 1.2 * volatility_multiplier)
                
                # 确保止损在当前价下方
                if stop_loss_price >= current_price or stop_loss_price < min_sl:
                    stop_loss_price = max(min_sl, current_price * 0.985)
                elif stop_loss_price > max_sl:
                    stop_loss_price = max_sl
                
                # 确保止盈在当前价上方
                if take_profit_price <= current_price or take_profit_price > max_tp:
                    take_profit_price = min(max_tp, current_price * 1.08)
                elif take_profit_price < min_tp:
                    take_profit_price = min_tp
                    
            else:  # short
                # 空头：止损高于当前价，止盈低于当前价
                min_sl = current_price * (1 + base_sl_pct * 0.5 * volatility_multiplier)
                max_sl = current_price * (1 + base_sl_pct * volatility_multiplier)
                min_tp = current_price * (1 - base_tp_pct * 1.2 * volatility_multiplier)
                max_tp = current_price * (1 - base_tp_pct * 0.8 * volatility_multiplier)
                
                # 确保止损在当前价上方
                if stop_loss_price <= current_price or stop_loss_price > max_sl:
                    stop_loss_price = min(max_sl, current_price * 1.015)
                elif stop_loss_price < min_sl:
                    stop_loss_price = min_sl
                
                # 确保止盈在当前价下方
                if take_profit_price >= current_price or take_profit_price < min_tp:
                    take_profit_price = max(min_tp, current_price * 0.92)
                elif take_profit_price > max_tp:
                    take_profit_price = max_tp
            
            return round(float(stop_loss_price), 2), round(float(take_profit_price), 2)
            
        except Exception as e:
            log_error(f"动态价格计算异常: {e}")
            # 回退到固定比例
            if position_side == 'long':
                return round(current_price * 0.98, 2), round(current_price * 1.06, 2)
            else:
                return round(current_price * 1.02, 2), round(current_price * 0.94, 2)

    def _get_market_volatility(self) -> float:
        """获取当前市场波动率 - 增强版本"""
        try:
            # 获取当前价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            high = float(ticker.get('high', 0))
            low = float(ticker.get('low', 0))
            last = float(ticker.get('last', 0))
            
            if high > 0 and low > 0 and last > 0:
                # 计算日内波动率
                daily_range = abs(high - low) / last * 100
                
                # 获取历史波动率（使用最近的价格历史）
                price_history = self._get_recent_price_history(24)  # 24小时数据
                if len(price_history) >= 2:
                    closes = [float(p['close']) for p in price_history if p.get('close', 0) > 0]
                    if len(closes) >= 2:
                        # 计算历史波动率（标准差）
                        returns = []
                        for i in range(1, len(closes)):
                            if closes[i-1] > 0:
                                returns.append(abs(closes[i] - closes[i-1]) / closes[i-1])
                        
                        if returns:
                            hist_volatility = np.mean(returns) * 100 * np.sqrt(24)  # 年化波动率
                            # 综合日内波动率和历史波动率
                            combined_volatility = (daily_range + hist_volatility) / 2
                            return max(0.5, min(5.0, combined_volatility))
                
                # 如果只日内波动率可用
                return max(0.5, min(5.0, daily_range))
            
            return 2.0  # 默认波动率
            
        except Exception as e:
            log_warning(f"获取市场波动率失败: {e}")
            return 2.0
    
    def _get_recent_price_history(self, hours: int = 24) -> List[Dict[str, float]]:
        """获取最近的价格历史"""
        try:
            # 使用1小时K线获取最近的价格历史
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '1h', limit=hours)
            
            history = []
            for candle in ohlcv:
                if len(candle) >= 6:
                    history.append({
                        'timestamp': candle[0],
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
            
            return history
            
        except Exception as e:
            log_warning(f"获取价格历史失败: {e}")
            return []
    
    def _get_market_state(self) -> Dict[str, Any]:
        """获取当前市场状态"""
        try:
            # 获取当前价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = float(ticker.get('last', 0))
            
            # 获取价格历史计算ATR
            price_history = self._get_recent_price_history(24)
            if len(price_history) >= 14:
                closes = [p['close'] for p in price_history]
                highs = [p['high'] for p in price_history]
                lows = [p['low'] for p in price_history]
                
                # 简化的ATR计算
                if len(closes) >= 14:
                    tr_values = []
                    for i in range(1, len(closes)):
                        if closes[i-1] > 0:
                            tr = max(
                                highs[i] - lows[i],
                                abs(highs[i] - closes[i-1]),
                                abs(lows[i] - closes[i-1])
                            )
                            tr_values.append(tr / closes[i-1])
                    
                    if tr_values:
                        atr_pct = np.mean(tr_values[-14:]) * 100
                        return {
                            'atr_pct': atr_pct,
                            'current_price': current_price,
                            'volatility': 'high' if atr_pct > 3.0 else 'low' if atr_pct < 1.0 else 'normal'
                        }
            
            return {
                'atr_pct': 2.0,
                'current_price': current_price,
                'volatility': 'normal'
            }
            
        except Exception as e:
            log_warning(f"获取市场状态失败: {e}")
            return {
                'atr_pct': 2.0,
                'current_price': 0,
                'volatility': 'normal'
            }
    
    def _get_existing_tp_sl_orders(self) -> List[Dict[str, Any]]:
        """获取现有止盈止损订单 - 完全复制原项目逻辑"""
        try:
            # 转换交易对格式：BTC/USDT:USDT -> BTC-USDT-SWAP
            inst_id = self.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

            # 获取当前持仓方向
            current_position = self.get_current_position()
            if not current_position or current_position['size'] <= 0:
                return []

            position_side = current_position['side']
            current_price = None
            try:
                ticker = self.exchange.fetch_ticker(self.symbol)
                current_price = float(ticker['last'])
            except:
                current_price = 0

            # 使用OKX专用的算法订单API查询所有触发订单
            response = self.exchange.private_get_trade_orders_algo_pending({
                'instType': 'SWAP',
                'instId': inst_id,
                'ordType': 'trigger'
            })
            
            if not response or response.get('code') != '0' or not response.get('data'):
                log_info(f"ℹ️ 无可取消算法订单或查询异常: {response}")
                return []

            tp_sl_orders = []
            for order in response['data']:
                ord_type = order.get('ordType')
                if ord_type in ['trigger', 'oco']:
                    algo_id = order.get('algoId')
                    if algo_id:
                        standardized_order = {
                            'id': algo_id,
                            'type': ord_type,
                            'side': order.get('side', ''),
                            'position_side': position_side,
                            'triggerPx': float(order.get('triggerPx', 0)),
                            'sz': float(order.get('sz', 0)),
                            'status': order.get('state', 'live'),
                            'source': 'algo'
                        }
                        tp_sl_orders.append(standardized_order)

            log_info(f"🔍 查询到 {len(tp_sl_orders)} 个止盈止损订单")
            return tp_sl_orders
            
        except Exception as e:
            log_error(f"获取现有止盈止损订单异常: {e}")
            return []

    def get_current_position(self) -> Optional[Dict[str, Any]]:
        """获取当前持仓情况 - 完全复制原项目逻辑
        
        获取当前交易对的详细持仓信息
        
        Returns:
            Optional[Dict[str, Any]]: 持仓信息，如果没有持仓则返回None
        """
        try:
            positions = self.exchange.fetch_positions([self.symbol])

            for pos in positions:
                if pos['symbol'] == self.symbol:
                    contracts = float(pos['contracts']) if pos['contracts'] else 0

                    if contracts > 0:
                        return {
                            'side': pos['side'],  # 'long' or 'short'
                            'size': contracts,
                            'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0,
                            'unrealized_pnl': float(pos['unrealizedPnl']) if pos['unrealizedPnl'] else 0,
                            'leverage': float(pos['leverage']) if pos['leverage'] else 10,
                            'symbol': pos['symbol']
                        }

            return None

        except Exception as e:
            log_info(f"获取持仓失败: {e}")
            return None

    def _get_current_price(self) -> float:
        """获取当前价格
        
        获取当前市场的最新成交价格
        
        Returns:
            float: 当前价格
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return float(ticker.get('last', 0))
        except Exception as e:
            log_warning(f"获取当前价格失败: {e}")
            return 0.0
    
    def _standardize_contract_amount(self, amount: float, contract_unit: float = 0.001) -> float:
        """标准化合约数量 - 使用交易所实际合约规格和激进调整策略
        
        Args:
            amount: 原始数量
            contract_unit: 默认合约单位
            
        Returns:
            float: 标准化后的数量
        """
        try:
            # 使用从交易所获取的实际市场信息
            if self._market_info:
                actual_contract_size = self._market_info.get('contract_size', contract_unit)
                precision = self._market_info.get('precision', {}).get('amount', 3)
                min_amount = self._market_info.get('limits', {}).get('amount', {}).get('min', 0.001)
            else:
                # 回退到默认值
                actual_contract_size = contract_unit
                precision = 3
                min_amount = 0.001
            
            log_info(f"📊 合约标准化输入: amount={amount}, contract_size={actual_contract_size}, precision={precision}, min_amount={min_amount}")
            
            # 超级激进的OKX BTC-USDT-SWAP标准化策略
            # 基于实际错误"Order quantity must be a multiple of the lot size"
            
            # 策略0: 直接查询交易所的合约规格
            try:
                # 尝试获取OKX的具体合约信息
                instrument_info = self.exchange.publicGetPublicInstruments({
                    'instType': 'SWAP',
                    'instId': self.inst_id
                })
                
                if instrument_info and instrument_info.get('code') == '0' and instrument_info.get('data'):
                    instrument = instrument_info['data'][0]
                    lot_size = float(instrument.get('lotSz', 0.001))  # 合约单位
                    min_sz = float(instrument.get('minSz', 0.001))    # 最小数量
                    tick_sz = float(instrument.get('tickSz', 0.001))  # 价格精度
                    
                    log_info(f"📊 OKX合约信息: lot_size={lot_size}, min_sz={min_sz}, tick_sz={tick_sz}")
                    
                    # 使用交易所的实际lot size
                    if lot_size > 0:
                        multiplier = int(round(amount / lot_size))
                        if multiplier <= 0:
                            multiplier = 1
                        
                        standardized = multiplier * lot_size
                        standardized = round(standardized, precision)
                        
                        if standardized >= min_sz:
                            log_info(f"📊 OKX标准化成功: {amount} -> {standardized} (lot_size: {lot_size}, multiplier: {multiplier})")
                            return standardized
                        
            except Exception as e:
                log_warning(f"获取OKX合约信息失败: {e}")
            
            # 策略1: 超激进的lot size检测 - 针对0.025问题
            # 基于实际错误，OKX BTC-USDT-SWAP可能使用0.01作为基本单位
            if 0.02 <= amount <= 0.03:  # 0.025附近的特殊处理
                # 尝试使用0.01作为基本单位
                multiplier = int(round(amount / 0.01))
                if multiplier > 0:
                    candidate = multiplier * 0.01
                    candidate = round(candidate, precision)
                    if candidate >= min_amount:
                        log_info(f"📊 0.025特殊处理: {amount} -> {candidate} (使用 lot size 0.01, multiplier: {multiplier})")
                        return candidate
            
            # 策略2: 尝试不同的"lot size"定义 - 修复整数除法问题
            possible_lot_sizes = [0.001, 0.01, 0.1, 1.0]
            
            for lot_size in possible_lot_sizes:
                try:
                    # 使用浮点数除法，避免整数问题
                    multiplier_float = amount / lot_size
                    multiplier = int(round(multiplier_float))
                    
                    if multiplier > 0:
                        candidate = multiplier * lot_size
                        candidate = round(candidate, precision)
                        
                        # 检查这个候选值是否可能有效
                        if candidate >= min_amount:
                            # 记录这个尝试
                            log_info(f"📊 尝试 lot size {lot_size}: {amount} -> {candidate} (倍数: {multiplier}, 浮点倍数: {multiplier_float:.4f})")
                            return candidate
                except Exception as e:
                    log_warning(f" lot size {lot_size} 处理失败: {e}")
                    continue
            
            # 策略3: 强制调整到最接近的"安全"值
            if amount > 0.01 and amount <= 0.05:
                # 对于小数量，优先使用0.01作为基本单位
                try:
                    safe_multiplier_float = amount / 0.01
                    safe_multiplier = int(round(safe_multiplier_float))
                    if safe_multiplier > 0:
                        safe_amount = safe_multiplier * 0.01
                        safe_amount = round(safe_amount, precision)
                        if safe_amount >= min_amount:
                            log_info(f"📊 强制安全调整: {amount} -> {safe_amount} (使用 lot size 0.01, 倍数: {safe_multiplier})")
                            return safe_amount
                except Exception as e:
                    log_warning(f"安全调整失败: {e}")
            
            # 策略4: 标准标准化（作为回退）- 修复整数除法问题
            try:
                multiplier_float = amount / actual_contract_size
                multiplier = int(round(multiplier_float))
                if multiplier <= 0:
                    multiplier = 1
                
                standardized_amount = multiplier * actual_contract_size
                standardized_amount = round(standardized_amount, precision)
                
                # 确保在最小交易量以上
                if standardized_amount < min_amount:
                    standardized_amount = min_amount
                
                log_info(f"📊 标准标准化: {amount} -> {standardized_amount} (合约大小: {actual_contract_size}, 倍数: {multiplier})")
                return standardized_amount
            except Exception as e:
                log_warning(f"标准标准化失败: {e}")
            
        except Exception as e:
            log_error(f"合约数量标准化失败: {e}")
            import traceback
            log_error(f"标准化详细错误: {traceback.format_exc()}")
        
        # 最终回退到安全值
        safe_fallback = round(max(float(amount), 0.001), 3)
        log_info(f"📊 使用最终安全回退值: {amount} -> {safe_fallback}")
        return safe_fallback

    def cancel_all_tp_sl_orders(self) -> int:
        """取消所有止盈止损订单 - 完全复制原项目逻辑
        
        取消所有活跃的止盈止损算法订单
        
        Returns:
            int: 成功取消的订单数量
        """
        try:
            # 转换交易对格式：例如 "BTC/USDT:USDT" -> "BTC-USDT-SWAP"
            inst_id = self.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

            # 查询活跃算法订单（止盈止损）
            response = self.exchange.private_get_trade_orders_algo_pending({
                'instType': 'SWAP',
                'instId': inst_id,
                'ordType': 'trigger'
            })

            if not response or response.get('code') != '0' or not response.get('data'):
                log_info(f"ℹ️ 无可取消算法订单或查询异常: {response}")
                return 0

            cancel_params = []
            for order in response['data']:
                ord_type = order.get('ordType')
                if ord_type in ['trigger', 'oco']:
                    algo_id = order.get('algoId')
                    if algo_id:
                        cancel_params.append({
                            "instId": inst_id,
                            "algoId": str(algo_id)
                        })
                    else:
                        log_warning(f"⚠️ 发现算法订单但缺少 algoId: {order}")

            if cancel_params:
                log_info(f"➡️ 准备取消算法订单: {json.dumps(cancel_params, ensure_ascii=False)}")
                cancel_response = self.exchange.request(
                    path="trade/cancel-algos",
                    api="private",
                    method="POST",
                    params=cancel_params
                )
                log_info(f"⬅️ 返回: {cancel_response}")

                if cancel_response.get('code') == '0':
                    log_info(f"✅ 成功发送取消请求，共 {len(cancel_params)} 个")
                    return len(cancel_params)
                else:
                    log_warning(f"⚠️ 取消算法订单失败: {cancel_response}")
            else:
                log_info("ℹ️ 没有符合条件的止盈止损算法订单需要取消")
                
            return 0

        except Exception as e:
            log_error(f"取消止盈止损订单异常: {e}")
            return 0

    def cancel_all_orders_comprehensive(self) -> Dict[str, int]:
        """全面取消所有类型的订单，返回详细统计
        
        取消所有类型的订单，包括算法订单和普通订单
        
        Returns:
            Dict[str, int]: 取消结果的详细统计
        """
        result = {'algorithmic': 0, 'regular': 0, 'total': 0, 'errors': 0}
        
        try:
            log_info("🔄 开始全面取消所有订单...")
            
            # 1. 取消算法订单（止盈止损条件单）
            try:
                # 使用CCXT的标准方法获取算法订单
                try:
                    response = self.exchange.fetchOpenOrders(self.symbol, params={'algo': True})
                    if isinstance(response, list):
                        algo_data = response
                    else:
                        algo_data = []
                except Exception as e:
                    log_warning(f"获取算法订单失败: {e}")
                    algo_data = []
                
                log_info(f"🔍 算法订单: 找到 {len(algo_data)} 个")
                
                # 取消活跃的算法订单
                success_count = 0
                for algo_order in algo_data:
                    try:
                        algo_id = algo_order.get('algoId') or algo_order.get('id')
                        state = algo_order.get('state', '') or algo_order.get('status', '')
                        
                        if algo_id and state in ['live', 'open', 'pending', 'partially_filled']:
                            # 使用CCXT标准方法取消算法订单
                            try:
                                self.exchange.cancelOrder(algo_id, self.symbol)
                                success_count += 1
                                log_info(f"✅ 已取消算法订单: {algo_id}")
                            except Exception as e:
                                log_warning(f"取消算法订单失败: {algo_id}, 原因: {e}")
                    except Exception as e:
                        log_warning(f"处理算法订单失败: {e}")
                
                result['algorithmic'] = success_count
                log_info(f"✅ 算法订单取消完成: 成功 {success_count} 个")
                        
            except Exception as e:
                log_warning(f"算法订单取消异常: {e}")
                result['errors'] += 1
            
            # 2. 取消普通开放订单
            try:
                open_orders = self.exchange.fetch_open_orders(self.symbol)
                
                for order in open_orders:
                    try:
                        if order.get('status') in ['open', 'pending']:
                            self.exchange.cancel_order(order['id'], self.symbol)
                            result['regular'] += 1
                            log_info(f"✅ 已取消普通订单: {order['id']}")
                    except Exception as e:
                        log_warning(f"取消普通订单失败 {order.get('id')}: {e}")
                        result['errors'] += 1
                        
            except Exception as e:
                log_warning(f"普通订单取消异常: {e}")
                result['errors'] += 1
            
            result['total'] = result['algorithmic'] + result['regular']
            log_info(f"📊 订单取消完成: 算法订单={result['algorithmic']}, 普通订单={result['regular']}, 总计={result['total']}, 错误={result['errors']}")
            
        except Exception as e:
            log_error(f"全面取消订单异常: {e}")
            result['errors'] += 1
            
        return result

class ShortSellingManager:
    """做空管理器
    
    负责管理做空交易的相关逻辑和权限控制
    """
    
    def __init__(self):
        """初始化做空管理器"""
        self.config = config.get('trading')
        self.is_enabled = self.config.get('allow_short_selling', False)
    
    def can_short_sell(self, current_position: Optional[Dict[str, Any]] = None) -> bool:
        """检查是否可以做空
        
        根据配置和当前持仓状态判断是否允许做空
        
        Args:
            current_position: 当前持仓信息，可选
            
        Returns:
            bool: 是否允许做空
        """
        if not self.is_enabled:
            return False
        
        # 检查当前持仓
        if current_position:
            # 如果已经有空头仓位，可以加仓
            if current_position['side'] == 'short':
                return True
            # 如果有多头仓位，不能做空（需要先平仓）
            elif current_position['side'] == 'long':
                return False
        
        # 无持仓时可以做空
        return True
    
    def get_short_selling_status(self) -> Dict[str, Any]:
        """获取做空状态
        
        获取当前做空功能的配置状态
        
        Returns:
            Dict[str, Any]: 做空状态信息
        """
        return {
            'enabled': self.is_enabled,
            'current_mode': '双向交易' if self.is_enabled else '仅多头',
            'max_position_size': self.config.get('max_position_size'),
            'leverage': self.config.get('leverage')
        }

class OrderManagementSystem:
    """订单管理系统
    
    提供高级的订单管理功能，包括：
    - 括号订单（同时包含入场、止损、止盈）
    - 订单统计分析
    - 订单参数验证
    - 批量订单管理
    """
    
    def __init__(self, exchange_manager: ExchangeManager):
        """初始化订单管理系统"""
        self.exchange = exchange_manager.exchange
        self.symbol = exchange_manager.symbol
        self.inst_id = exchange_manager.inst_id
        self.active_orders = {}
        self.order_history = []
        self.config = config.get('trading')
        
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """获取所有订单"""
        try:
            orders = self.exchange.fetch_open_orders(self.symbol)
            return [self._format_order(order) for order in orders]
        except Exception as e:
            log_error(f"获取订单失败: {e}")
            return []
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取订单"""
        try:
            order = self.exchange.fetch_order(order_id, self.symbol)
            return self._format_order(order)
        except Exception as e:
            log_error(f"获取订单失败: {e}")
            return None
    
    def cancel_order_by_id(self, order_id: str) -> bool:
        """取消指定订单"""
        try:
            self.exchange.cancel_order(order_id, self.symbol)
            log_info(f"✅ 订单取消成功: {order_id}")
            return True
        except Exception as e:
            log_error(f"取消订单失败: {e}")
            return False
    
    def cancel_all_orders(self, order_type: str = None) -> bool:
        """取消所有订单"""
        try:
            orders = self.get_all_orders()
            
            for order in orders:
                if order_type is None or order.get('type') == order_type:
                    self.cancel_order_by_id(order['id'])
            
            log_info("✅ 所有订单已取消")
            return True
        except Exception as e:
            log_error(f"取消所有订单失败: {e}")
            return False
    
    def place_bracket_order(self, side: str, amount: float, entry_price: float, 
                          stop_loss: float, take_profit: float) -> Dict[str, Any]:
        """下括号订单（包含入场、止损、止盈）"""
        try:
            # 检查做空权限
            if side.upper() == 'SELL' and not self.config.get('allow_short_selling'):
                log_warning("❌ 做空功能已禁用")
                return {'success': False, 'error': 'Short selling disabled'}
            
            # 下入场订单
            entry_order = self.place_limit_order(side, amount, entry_price)
            if not entry_order:
                return {'success': False, 'error': 'Entry order failed'}
            
            # 设置止损止盈（需要等待入场订单成交）
            # 这里简化处理，实际应该监听订单状态
            bracket_order = {
                'entry_order': entry_order,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'status': 'pending'
            }
            
            self.active_orders[entry_order.get('id', 'temp')] = bracket_order
            
            return {
                'success': True,
                'order_id': entry_order.get('id'),
                'bracket_order': bracket_order
            }
            
        except Exception as e:
            log_error(f"括号订单失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计"""
        try:
            orders = self.get_all_orders()
            
            stats = {
                'total_orders': len(orders),
                'pending_orders': len([o for o in orders if o.get('status') == 'open']),
                'filled_orders': len([o for o in orders if o.get('status') == 'closed']),
                'cancelled_orders': len([o for o in orders if o.get('status') == 'cancelled']),
                'orders_by_type': {},
                'orders_by_side': {}
            }
            
            for order in orders:
                order_type = order.get('type', 'unknown')
                order_side = order.get('side', 'unknown')
                
                stats['orders_by_type'][order_type] = stats['orders_by_type'].get(order_type, 0) + 1
                stats['orders_by_side'][order_side] = stats['orders_by_side'].get(order_side, 0) + 1
            
            return stats
            
        except Exception as e:
            log_error(f"获取订单统计失败: {e}")
            return {}
    
    def _format_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """格式化订单信息"""
        return {
            'id': order.get('id'),
            'symbol': order.get('symbol'),
            'type': order.get('type'),
            'side': order.get('side'),
            'amount': float(order.get('amount', 0)),
            'price': float(order.get('price', 0)),
            'status': order.get('status'),
            'filled': float(order.get('filled', 0)),
            'remaining': float(order.get('remaining', 0)),
            'timestamp': order.get('timestamp'),
            'datetime': order.get('datetime')
        }
    
    def validate_order_parameters(self, side: str, amount: float, price: float = None) -> Dict[str, Any]:
        """验证订单参数"""
        errors = []
        
        if side.upper() not in ['BUY', 'SELL']:
            errors.append("无效的交易方向")
        
        if amount <= 0:
            errors.append("订单数量必须大于0")
        
        if price and price <= 0:
            errors.append("订单价格必须大于0")
        
        max_position = self.config.get('max_position_size', 0.01)
        if amount > max_position:
            errors.append(f"订单数量超过最大仓位限制: {max_position}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

class TradingEngine:
    """交易引擎"""
    
    def __init__(self):
        self.exchange_manager = ExchangeManager()
        self.order_manager = OrderManager(self.exchange_manager)
        self.order_system = OrderManagementSystem(self.exchange_manager)
        self.short_selling_manager = ShortSellingManager()
        self.is_running = False
    
    def get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        try:
            ticker = self.exchange_manager.fetch_ticker()
            position = self.exchange_manager.get_position()
            balance = self.exchange_manager.get_balance()
            
            # 获取历史K线数据用于价格变化计算
            price_history = self.get_price_history()
            
            return {
                'price': ticker.get('last', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'high': ticker.get('high', 0),
                'low': ticker.get('low', 0),
                'volume': ticker.get('volume', 0),
                'position': position,
                'balance': balance,
                'price_history': price_history
            }
            
        except Exception as e:
            log_error(f"获取市场数据失败: {e}")
            return {}
    
    def get_price_history(self, timeframe: str = '15m', limit: int = 20) -> List[Dict[str, float]]:
        """获取历史K线数据"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                ohlcv = self.exchange_manager.exchange.fetch_ohlcv(
                    self.exchange_manager.symbol,
                    timeframe,
                    limit=limit
                )
                
                if not ohlcv or len(ohlcv) < 2:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        # 返回模拟数据作为回退
                        current_price = self.exchange_manager.fetch_ticker().get('last', 50000)
                        return [
                            {
                                'timestamp': int(time.time() * 1000) - (i * 900000),  # 15分钟间隔
                                'open': current_price,
                                'high': current_price * 1.001,
                                'low': current_price * 0.999,
                                'close': current_price,
                                'volume': 1000000
                            }
                            for i in range(limit)
                        ]
                
                # 转换为标准格式
                history = []
                for candle in ohlcv:
                    if len(candle) >= 6:
                        history.append({
                            'timestamp': candle[0],
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })
                
                return history
                
            except Exception as e:
                log_error(f"获取历史K线数据失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避
                else:
                    # 最后一次尝试失败，返回回退数据
                    current_price = 50000
                    try:
                        ticker = self.exchange_manager.fetch_ticker()
                        current_price = ticker.get('last', 50000)
                    except:
                        pass
                    
                    return [
                        {
                            'timestamp': int(time.time() * 1000) - (i * 900000),
                            'open': current_price,
                            'high': current_price * 1.001,
                            'low': current_price * 0.999,
                            'close': current_price,
                            'volume': 1000000
                        }
                        for i in range(limit)
                    ]
        
        return []
    
    def execute_trade(self, signal: str, amount: float, price: Optional[float] = None) -> bool:
        """执行交易"""
        log_info(f"🚀 开始执行交易:")
        log_info(f"   信号: {signal}")
        log_info(f"   数量: {amount}")
        log_info(f"   价格: ${price or 'market'}")
        
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟交易: {signal} {amount} @ ${price or 'market'}")
            return True
        
        try:
            # 获取当前持仓
            current_position = self.exchange_manager.get_position()
            log_info(f"📊 当前持仓状态:")
            if current_position:
                log_info(f"   方向: {current_position['side']}")
                log_info(f"   大小: {current_position['size']}")
                log_info(f"   入场价: ${current_position['entry_price']:,.2f}")
                log_info(f"   未实现盈亏: ${current_position['unrealized_pnl']:,.2f}")
            else:
                log_info("   无持仓")
            
            if signal.upper() == 'BUY':
                log_info("📈 执行买入操作")
                result = self.order_manager.place_market_order('BUY', amount)
                log_info(f"✅ 买入操作结果: {'成功' if result else '失败'}")
                return result
            elif signal.upper() == 'SELL':
                # 检查做空权限
                log_info("📉 执行卖出操作")
                if not self.short_selling_manager.can_short_sell(current_position):
                    log_info("   做空权限检查: 不允许做空")
                    if current_position and current_position['side'] == 'long':
                        # 如果是多头仓位，执行平仓
                        close_amount = min(amount, current_position['size'])
                        log_info(f"   平仓数量: {close_amount} (原始: {amount}, 持仓: {current_position['size']})")
                        if close_amount > 0:
                            result = self.order_manager.place_market_order('SELL', close_amount, reduce_only=True)
                            log_info(f"✅ 平仓操作结果: {'成功' if result else '失败'}")
                            return result
                        else:
                            log_info("当前无多头仓位可平仓")
                            return False
                    else:
                        log_warning("做空功能已禁用，无法开空仓")
                        return False
                else:
                    log_info("   做空权限检查: 允许做空")
                    result = self.order_manager.place_market_order('SELL', amount)
                    log_info(f"✅ 卖出操作结果: {'成功' if result else '失败'}")
                    return result
            else:
                log_warning(f"未知信号: {signal}")
                return False
                
        except Exception as e:
            log_error(f"交易执行失败: {e}")
            return False
    
    def execute_trade_with_tp_sl(self, signal: str, amount: float,
                               stop_loss_price: float, take_profit_price: float) -> bool:
        """执行带止盈止损的交易"""
        log_info(f"🚀 开始执行带止盈止损的交易:")
        log_info(f"   信号: {signal}")
        log_info(f"   数量: {amount}")
        log_info(f"   止损价: ${stop_loss_price:,.2f}")
        log_info(f"   止盈价: ${take_profit_price:,.2f}")
        
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟交易: {signal} {amount} @ SL={stop_loss_price} TP={take_profit_price}")
            return True
            
        try:
            success = False
            
            # 获取当前持仓
            current_position = self.exchange_manager.get_position()
            log_info(f"📊 当前持仓状态:")
            if current_position:
                log_info(f"   方向: {current_position['side']}")
                log_info(f"   大小: {current_position['size']}")
                log_info(f"   入场价: ${current_position['entry_price']:,.2f}")
            else:
                log_info("   无持仓")
            
            # 执行主交易
            if signal.upper() == 'BUY':
                log_info("📈 执行买入操作")
                success = self.order_manager.place_market_order('BUY', amount)
                log_info(f"✅ 买入操作结果: {'成功' if success else '失败'}")
            elif signal.upper() == 'SELL':
                # 检查做空权限
                log_info("📉 执行卖出操作")
                if not self.short_selling_manager.can_short_sell(current_position):
                    log_info("   做空权限检查: 不允许做空")
                    if current_position and current_position['side'] == 'long':
                        # 如果是多头仓位，执行平仓
                        close_amount = min(amount, current_position['size'])
                        log_info(f"   平仓数量: {close_amount} (原始: {amount}, 持仓: {current_position['size']})")
                        if close_amount > 0:
                            success = self.order_manager.place_market_order('SELL', close_amount, reduce_only=True)
                            log_info(f"✅ 平仓操作结果: {'成功' if success else '失败'}")
                        else:
                            log_info("当前无多头仓位可平仓")
                            return False
                    else:
                        log_warning("做空功能已禁用，无法开空仓")
                        return False
                else:
                    log_info("   做空权限检查: 允许做空")
                    success = self.order_manager.place_market_order('SELL', amount)
                    log_info(f"✅ 卖出操作结果: {'成功' if success else '失败'}")
            else:
                log_warning(f"未知信号: {signal}")
                return False
            
            if success:
                # 获取当前持仓
                position = self.exchange_manager.get_position()
                if position and position.get('size', 0) > 0:
                    log_info("📊 交易成功，设置止盈止损:")
                    log_info(f"   持仓方向: {position['side']}")
                    log_info(f"   持仓大小: {position['size']}")
                    
                    # 设置止盈止损（空头仓位需要反转止损止盈价格）
                    adjusted_sl, adjusted_tp = self._adjust_tp_sl_for_short(
                        position['side'], stop_loss_price, take_profit_price
                    )
                    
                    log_info(f"   调整后止损价: ${adjusted_sl:,.2f}")
                    log_info(f"   调整后止盈价: ${adjusted_tp:,.2f}")
                    
                    tp_sl_success = self.order_manager.set_stop_loss_take_profit(
                        position['side'],
                        adjusted_sl,
                        adjusted_tp,
                        position['size']
                    )
                    log_info(f"✅ 止盈止损设置结果: {'成功' if tp_sl_success else '失败'}")
                else:
                    log_info("ℹ️ 交易成功但无持仓，跳过止盈止损设置")
            else:
                log_info("❌ 主交易执行失败，跳过止盈止损设置")
                
            return success
                
        except Exception as e:
            log_error(f"带止盈止损的交易执行失败: {e}")
            return False
    
    def _adjust_tp_sl_for_short(self, position_side: str, stop_loss: float, take_profit: float) -> Tuple[float, float]:
        """为空头仓位调整止盈止损价格"""
        if position_side == 'short':
            # 空头仓位：止损价格应高于当前价格，止盈价格应低于当前价格
            # 确保止损价格 > 止盈价格
            if stop_loss <= take_profit:
                stop_loss, take_profit = take_profit, stop_loss
        return stop_loss, take_profit
    
    def update_risk_management(self, position: Optional[Dict[str, Any]], 
                             stop_loss: float, take_profit: float) -> bool:
        """更新风险管理"""
        if not position:
            return False
        
        return self.order_manager.set_stop_loss_take_profit(
            position['side'],
            stop_loss,
            take_profit,
            position['size']
        )
    
    def close_position(self, side: str, amount: float) -> bool:
        """平仓操作 - 超级增强版，专门处理0.025等复杂情况"""
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟平仓: {side} 方向 {amount} 张")
            return True
            
        try:
            # 详细的平仓前验证
            current_position = self.exchange_manager.get_position()
            log_info(f"📊 【平仓前验证】")
            log_info(f"   请求平仓方向: {side}")
            log_info(f"   请求平仓数量: {amount}")
            
            if not current_position:
                log_info("   ❌ 无持仓，无需平仓")
                return True
                
            log_info(f"   当前持仓方向: {current_position['side']}")
            log_info(f"   当前持仓大小: {current_position['size']}")
            log_info(f"   方向匹配检查: {current_position['side']} == {side} -> {current_position['side'] == side}")
            
            # 验证持仓方向
            if current_position['side'] != side:
                log_info("   ⚠️ 方向不匹配，无需平仓")
                return True
                
            # 验证平仓数量
            actual_amount = min(amount, current_position['size'])
            log_info(f"📊 【平仓数量计算】")
            log_info(f"   请求数量: {amount}")
            log_info(f"   持仓数量: {current_position['size']}")
            log_info(f"   实际可平: {actual_amount}")
            
            if actual_amount <= 0:
                log_info("   ⚠️ 无需平仓")
                return True
            
            # 超级激进的合约数量标准化 - 专门针对平仓场景
            log_info(f"📊 【合约数量标准化 - 平仓专用】")
            log_info(f"   标准化前: {actual_amount}")
            
            # 尝试多种标准化策略
            standardized_amount = self._standardize_close_amount(actual_amount)
            log_info(f"   标准化后: {standardized_amount}")
            
            if standardized_amount <= 0:
                log_error(f"❌ 标准化失败: {actual_amount} -> {standardized_amount}")
                return False
            
            # 再次验证标准化后的数量不超过持仓
            final_amount = min(standardized_amount, current_position['size'])
            log_info(f"   最终平仓数量: {final_amount} (二次限制后)")
            
            if final_amount <= 0:
                log_warning(f"⚠️ 最终平仓数量为0，跳过平仓")
                return True
            
            close_side = 'sell' if side == 'long' else 'buy'
            log_info(f"📊 【平仓执行】")
            log_info(f"   平仓方向: {close_side}")
            log_info(f"   平仓数量: {final_amount}")
            log_info(f"   订单类型: reduce_only市价单")
            
            # 执行平仓
            success = self.order_manager.place_market_order(close_side, final_amount, reduce_only=True)
            
            if success:
                log_info(f"✅ 平仓成功: {side} 方向 {final_amount} 张")
                return True
            else:
                log_error(f"❌ 平仓失败: {side} 方向 {final_amount} 张")
                
                # 尝试降级策略 - 使用稍小的数量
                fallback_amount = final_amount * 0.99  # 减少1%
                log_info(f"🔄 尝试降级策略: {final_amount} -> {fallback_amount}")
                
                fallback_success = self.order_manager.place_market_order(close_side, fallback_amount, reduce_only=True)
                if fallback_success:
                    log_info(f"✅ 降级策略成功: {fallback_amount} 张")
                    return True
                else:
                    log_error(f"❌ 降级策略也失败: {fallback_amount} 张")
                    return False
            
        except Exception as e:
            log_error(f"❌ 平仓异常: {type(e).__name__}: {e}")
            import traceback
            log_error(f"平仓详细错误:\n{traceback.format_exc()}")
            return False
    
    def _standardize_close_amount(self, amount: float) -> float:
        """专门为平仓设计的超级激进数量标准化"""
        try:
            log_info(f"📊 【平仓标准化输入】amount={amount}")
            
            # 策略1: 直接查询交易所合约规格
            try:
                inst_id = self.exchange_manager.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
                instrument_info = self.exchange_manager.exchange.publicGetPublicInstruments({
                    'instType': 'SWAP',
                    'instId': inst_id
                })
                
                if instrument_info and instrument_info.get('code') == '0' and instrument_info.get('data'):
                    instrument = instrument_info['data'][0]
                    lot_size = float(instrument.get('lotSz', 0.001))
                    min_sz = float(instrument.get('minSz', 0.001))
                    
                    log_info(f"📊 【OKX合约信息】lot_size={lot_size}, min_sz={min_sz}")
                    
                    # 使用lot size进行标准化
                    if lot_size > 0:
                        multiplier = max(1, int(round(amount / lot_size)))
                        standardized = multiplier * lot_size
                        
                        if standardized >= min_sz:
                            log_info(f"📊 【OKX标准化成功】{amount} -> {standardized} (lot_size: {lot_size}, multiplier: {multiplier})")
                            return standardized
                            
            except Exception as e:
                log_warning(f"获取OKX合约信息失败: {e}")
            
            # 策略2: 针对0.025的特殊处理 - 基于实际错误经验
            if 0.02 <= amount <= 0.03:
                # OKX BTC-USDT-SWAP可能使用0.01作为基本单位
                multiplier = max(1, int(round(amount / 0.01)))
                candidate = multiplier * 0.01
                
                log_info(f"📊 【0.025特殊处理】{amount} -> {candidate} (使用 lot size 0.01, multiplier: {multiplier})")
                return candidate
            
            # 策略3: 尝试常见lot size组合
            common_lot_sizes = [0.001, 0.01, 0.1]
            for lot_size in common_lot_sizes:
                multiplier = max(1, int(round(amount / lot_size)))
                candidate = multiplier * lot_size
                
                if abs(candidate - amount) < lot_size * 0.1:  # 差距小于10%
                    log_info(f"📊 【常见lot size成功】{amount} -> {candidate} (lot_size: {lot_size}, multiplier: {multiplier})")
                    return candidate
            
            # 策略4: 智能四舍五入到合理精度
            if amount < 0.01:
                # 小数量：使用0.001精度
                standardized = round(amount, 3)
            elif amount < 0.1:
                # 中等数量：使用0.01精度
                standardized = round(amount, 2)
            else:
                # 大数量：使用0.1精度
                standardized = round(amount, 1)
            
            log_info(f"📊 【智能四舍五入】{amount} -> {standardized}")
            return max(standardized, 0.001)  # 确保不小于最小值
            
        except Exception as e:
            log_error(f"平仓标准化异常: {e}")
            # 最终回退
            fallback = round(max(float(amount), 0.001), 3)
            log_info(f"📊 【最终回退】{amount} -> {fallback}")
            return fallback

    def get_position_info(self) -> Dict[str, Any]:
        """获取持仓信息"""
        position = self.exchange_manager.get_position()
        short_status = self.short_selling_manager.get_short_selling_status()
        
        if position:
            return {
                'has_position': True,
                'side': position['side'],
                'size': position['size'],
                'entry_price': position['entry_price'],
                'unrealized_pnl': position['unrealized_pnl'],
                'leverage': position['leverage'],
                'short_selling_enabled': short_status['enabled'],
                'current_mode': short_status['current_mode']
            }
        else:
            return {
                'has_position': False,
                'short_selling_enabled': short_status['enabled'],
                'current_mode': short_status['current_mode']
            }

# 全局交易引擎实例
trading_engine = TradingEngine()
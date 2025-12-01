"""
Alpha Arena OKX 交易逻辑模块
封装所有交易相关的核心功能
"""

import ccxt
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from config import config
from logger_config import log_info, log_warning, log_error
from trade_logger import trade_logger

class ExchangeManager:
    """交易所管理器"""
    
    def __init__(self):
        self.exchange = self._setup_exchange()
        self.symbol = config.get('exchange', 'symbol')
        self.inst_id = self.symbol.replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
    
    def _setup_exchange(self) -> ccxt.Exchange:
        """设置交易所连接"""
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
            log_warning(f"设置杠杆失败: {e}")
        
        return exchange
    
    def fetch_ticker(self) -> Dict[str, float]:
        """获取最新价格"""
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
        """获取当前持仓"""
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
        """获取账户余额"""
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
    """订单管理器"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange = exchange_manager.exchange
        self.symbol = exchange_manager.symbol
        self.inst_id = exchange_manager.inst_id
        self.active_orders = {}
    
    def place_market_order(self, side: str, amount: float, reduce_only: bool = False) -> bool:
        """下市价单"""
        try:
            # 检查做空权限
            if side.upper() == 'SELL' and not reduce_only:
                if not config.get('trading', 'allow_short_selling'):
                    log_warning("❌ 做空功能已禁用")
                    return False
            
            params = {
                'tdMode': 'cross',
                'side': 'buy' if side.upper() == 'BUY' else 'sell',
                'ordType': 'market',
                'sz': str(amount),
                'tag': 'alpha_arena'
            }
            
            if reduce_only:
                params['reduceOnly'] = True
            
            response = self.exchange.private_post_trade_order({
                'instId': self.inst_id,
                **params
            })
            
            if response.get('code') == '0':
                log_info(f"✅ 市价单成功: {side} {amount}")
                return True
            else:
                log_error(f"❌ 市价单失败: {response}")
                return False
                
        except Exception as e:
            log_error(f"市价单异常: {e}")
            return False
    
    def place_limit_order(self, side: str, amount: float, price: float, reduce_only: bool = False) -> bool:
        """下限价单"""
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
                'sz': str(amount),
                'tag': 'alpha_arena_limit'
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
        """设置止盈止损"""
        try:
            # 取消现有订单
            self.cancel_all_tp_sl_orders()
            
            close_side = 'sell' if position_side == 'long' else 'buy'
            
            # 设置止损
            if stop_loss_price:
                sl_params = {
                    'instId': self.inst_id,
                    'tdMode': 'cross',
                    'side': close_side,
                    'ordType': 'trigger',
                    'sz': str(position_size),
                    'triggerPx': str(stop_loss_price),
                    'orderPx': '-1',
                    'triggerPxType': 'last',
                    'tag': 'alpha_sl'
                }
                
                sl_resp = self.exchange.private_post_trade_order_algo(sl_params)
                if sl_resp.get('code') == '0':
                    log_info(f"✅ 止损设置成功: ${stop_loss_price}")
                else:
                    log_error(f"❌ 止损设置失败: {sl_resp}")
            
            # 设置止盈
            if take_profit_price:
                tp_params = {
                    'instId': self.inst_id,
                    'tdMode': 'cross',
                    'side': close_side,
                    'ordType': 'trigger',
                    'sz': str(position_size),
                    'triggerPx': str(take_profit_price),
                    'orderPx': '-1',
                    'triggerPxType': 'last',
                    'tag': 'alpha_tp'
                }
                
                tp_resp = self.exchange.private_post_trade_order_algo(tp_params)
                if tp_resp.get('code') == '0':
                    log_info(f"✅ 止盈设置成功: ${take_profit_price}")
                else:
                    log_error(f"❌ 止盈设置失败: {tp_resp}")
            
            return True
            
        except Exception as e:
            log_error(f"止盈止损设置异常: {e}")
            return False
    
    def cancel_all_tp_sl_orders(self) -> bool:
        """取消所有止盈止损订单"""
        try:
            # 获取待处理订单
            pending_orders = self.exchange.fetch_open_orders(self.symbol)
            
            for order in pending_orders:
                if any(tag in str(order.get('tag', '')) for tag in ['alpha_sl', 'alpha_tp']):
                    self.exchange.cancel_order(order['id'], self.symbol)
                    
        except Exception as e:
            log_error(f"取消止盈止损订单失败: {e}")

class ShortSellingManager:
    """做空管理器"""
    
    def __init__(self):
        self.config = config.get('trading')
        self.is_enabled = self.config.get('allow_short_selling', False)
    
    def can_short_sell(self, current_position: Optional[Dict[str, Any]] = None) -> bool:
        """检查是否可以做空"""
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
        """获取做空状态"""
        return {
            'enabled': self.is_enabled,
            'current_mode': '双向交易' if self.is_enabled else '仅多头',
            'max_position_size': self.config.get('max_position_size'),
            'leverage': self.config.get('leverage')
        }

class OrderManagementSystem:
    """订单管理系统"""
    
    def __init__(self, exchange_manager: ExchangeManager):
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
            
            return {
                'price': ticker.get('last', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'high': ticker.get('high', 0),
                'low': ticker.get('low', 0),
                'volume': ticker.get('volume', 0),
                'position': position,
                'balance': balance
            }
            
        except Exception as e:
            log_error(f"获取市场数据失败: {e}")
            return {}
    
    def execute_trade(self, signal: str, amount: float, price: Optional[float] = None) -> bool:
        """执行交易"""
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟交易: {signal} {amount} @ ${price or 'market'}")
            return True
        
        try:
            # 获取当前持仓
            current_position = self.exchange_manager.get_position()
            
            if signal.upper() == 'BUY':
                return self.order_manager.place_market_order('BUY', amount)
            elif signal.upper() == 'SELL':
                # 检查做空权限
                if not self.short_selling_manager.can_short_sell(current_position):
                    if current_position and current_position['side'] == 'long':
                        # 如果是多头仓位，执行平仓
                        close_amount = min(amount, current_position['size'])
                        if close_amount > 0:
                            return self.order_manager.place_market_order('SELL', close_amount, reduce_only=True)
                        else:
                            log_info("当前无多头仓位可平仓")
                            return False
                    else:
                        log_warning("做空功能已禁用，无法开空仓")
                        return False
                
                return self.order_manager.place_market_order('SELL', amount)
            else:
                log_warning(f"未知信号: {signal}")
                return False
                
        except Exception as e:
            log_error(f"交易执行失败: {e}")
            return False
    
    def execute_trade_with_tp_sl(self, signal: str, amount: float, 
                               stop_loss_price: float, take_profit_price: float) -> bool:
        """执行带止盈止损的交易"""
        try:
            success = False
            
            # 获取当前持仓
            current_position = self.exchange_manager.get_position()
            
            # 执行主交易
            if signal.upper() == 'BUY':
                success = self.order_manager.place_market_order('BUY', amount)
            elif signal.upper() == 'SELL':
                # 检查做空权限
                if not self.short_selling_manager.can_short_sell(current_position):
                    if current_position and current_position['side'] == 'long':
                        # 如果是多头仓位，执行平仓
                        close_amount = min(amount, current_position['size'])
                        if close_amount > 0:
                            success = self.order_manager.place_market_order('SELL', close_amount, reduce_only=True)
                        else:
                            log_info("当前无多头仓位可平仓")
                            return False
                    else:
                        log_warning("做空功能已禁用，无法开空仓")
                        return False
                else:
                    success = self.order_manager.place_market_order('SELL', amount)
            else:
                log_warning(f"未知信号: {signal}")
                return False
            
            if success:
                # 获取当前持仓
                position = self.exchange_manager.get_position()
                if position and position.get('size', 0) > 0:
                    # 设置止盈止损（空头仓位需要反转止损止盈价格）
                    adjusted_sl, adjusted_tp = self._adjust_tp_sl_for_short(
                        position['side'], stop_loss_price, take_profit_price
                    )
                    
                    self.order_manager.set_stop_loss_take_profit(
                        position['side'], 
                        adjusted_sl, 
                        adjusted_tp, 
                        position['size']
                    )
                    log_info(f"✅ 止盈止损设置完成 - SL: ${adjusted_sl}, TP: ${adjusted_tp}")
                
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
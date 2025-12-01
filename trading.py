"""
Alpha Arena OKX 交易逻辑模块
封装所有交易相关的核心功能
"""

import ccxt
import time
import json
from typing import Dict, Any, Optional, Tuple
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
            # 获取待取消的订单
            pending_orders = self.exchange.fetch_open_orders(self.symbol)
            
            for order in pending_orders:
                order_id = order.get('id')
                if order_id:
                    self.exchange.cancel_order(order_id, self.symbol)
            
            log_info("✅ 已取消所有止盈止损订单")
            return True
            
        except Exception as e:
            log_error(f"取消订单异常: {e}")
            return False

class TradingEngine:
    """交易引擎 - 核心交易逻辑"""
    
    def __init__(self):
        self.exchange_manager = ExchangeManager()
        self.order_manager = OrderManager(self.exchange_manager)
        self.is_running = False
    
    def get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        ticker = self.exchange_manager.fetch_ticker()
        position = self.exchange_manager.get_position()
        balance = self.exchange_manager.get_balance()
        
        return {
            'price': ticker.get('last', 0),
            'bid': ticker.get('bid', 0),
            'ask': ticker.get('ask', 0),
            'position': position,
            'balance': balance,
            'timestamp': datetime.now()
        }
    
    def execute_trade(self, signal: str, amount: float, price: Optional[float] = None) -> bool:
        """执行交易"""
        if config.get('trading', 'test_mode'):
            log_info(f"🧪 模拟交易: {signal} {amount} @ ${price or 'market'}")
            return True
        
        if price and config.get('strategies', 'limit_order', 'enabled'):
            return self.order_manager.place_limit_order(signal, amount, price)
        else:
            return self.order_manager.place_market_order(signal, amount)
    
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
        if position:
            return {
                'has_position': True,
                'side': position['side'],
                'size': position['size'],
                'entry_price': position['entry_price'],
                'unrealized_pnl': position['unrealized_pnl'],
                'leverage': position['leverage']
            }
        else:
            return {'has_position': False}

# 全局交易引擎实例
trading_engine = TradingEngine()
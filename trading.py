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
        """智能止盈止损设置（先检查合理性，再决定是否更新）"""
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
            
            log_info(f"📊 当前价格: ${current_price:.2f}, 持仓方向: {position_side}, 持仓数量: {position_size}")
            
            # 计算合理的价格范围
            reasonable_sl, reasonable_tp = self._calculate_reasonable_prices(
                position_side, current_price, stop_loss_price, take_profit_price
            )
            
            # 1. 获取现有止盈止损订单
            existing_orders = self._get_existing_tp_sl_orders()
            
            if existing_orders:
                log_info("📊 当前止盈止损订单状态:")
                existing_sl = None
                existing_tp = None
                
                for order in existing_orders:
                    side = order.get('side', '')
                    trigger_px = float(order.get('triggerPx', 0))
                    
                    if side == 'sell' and position_side == 'long':  # 多头止损
                        existing_sl = trigger_px
                        log_info(f"   - 止损: ${trigger_px:.2f}")
                    elif side == 'buy' and position_side == 'short':  # 空头止损
                        existing_sl = trigger_px
                        log_info(f"   - 止损: ${trigger_px:.2f}")
                    elif side == 'sell' and position_side == 'long' and trigger_px > current_price:  # 多头止盈
                        existing_tp = trigger_px
                        log_info(f"   - 止盈: ${trigger_px:.2f}")
                    elif side == 'buy' and position_side == 'short' and trigger_px < current_price:  # 空头止盈
                        existing_tp = trigger_px
                        log_info(f"   - 止盈: ${trigger_px:.2f}")
                
                # 判断现有订单是否合理（基于波动率的动态容差）
                volatility = self._get_market_volatility()
                tolerance_pct = max(0.01, min(0.05, volatility / 100))  # 1%-5%的动态容差
                
                is_reasonable = True
                log_info(f"📏 使用动态容差: {tolerance_pct:.1%} (波动率: {volatility:.1f}%)")
                
                if existing_sl is not None:
                    sl_diff = abs(existing_sl - reasonable_sl) / reasonable_sl
                    is_reasonable = is_reasonable and sl_diff < tolerance_pct
                    log_info(f"   📊 止损合理性: ${existing_sl:.2f} vs ${reasonable_sl:.2f} (差异: {sl_diff:.1%})")
                
                if existing_tp is not None:
                    tp_diff = abs(existing_tp - reasonable_tp) / reasonable_tp
                    is_reasonable = is_reasonable and tp_diff < tolerance_pct
                    log_info(f"   📊 止盈合理性: ${existing_tp:.2f} vs ${reasonable_tp:.2f} (差异: {tp_diff:.1%})")
                
                log_info(f"   ✅ 合理性判断: {'合理' if is_reasonable else '不合理'}")
                
                if is_reasonable:
                    log_info("✅ 当前止盈止损设置合理，无需调整")
                    return True
                else:
                    log_info("⚠️ 当前止盈止损设置不合理，将重新设置")
            
            # 2. 取消现有止盈止损订单（如果不合理或不存在）
            if existing_orders:
                cancelled_count = self.cancel_all_tp_sl_orders()
                if cancelled_count > 0:
                    log_info(f"✅ 已取消 {cancelled_count} 个现有止盈止损订单")
            
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
                
                log_info(f"🎯 设置止损参数: {sl_params}")
                sl_resp = self.exchange.private_post_trade_order_algo(sl_params)
                
                if sl_resp and sl_resp.get('code') == '0':
                    algo_id = sl_resp['data'][0]['algoId'] if sl_resp.get('data') and len(sl_resp.get('data', [])) > 0 else 'unknown'
                    log_info(f"✅ 止损设置成功: trigger=${reasonable_sl}, algoId={algo_id}")
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
                
                log_info(f"🎯 设置止盈参数: {tp_params}")
                tp_resp = self.exchange.private_post_trade_order_algo(tp_params)
                
                if tp_resp and tp_resp.get('code') == '0':
                    algo_id = tp_resp['data'][0]['algoId'] if tp_resp.get('data') and len(tp_resp.get('data', [])) > 0 else 'unknown'
                    log_info(f"✅ 止盈设置成功: trigger=${reasonable_tp}, algoId={algo_id}")
                    success_count += 1
                else:
                    error_msg = tp_resp.get('msg', '未知错误') if tp_resp else 'API无响应'
                    log_error(f"❌ 止盈设置失败: {error_msg}")
            
            result = success_count > 0
            log_info(f"📊 止盈止损设置结果: {'成功' if result else '失败'} (成功设置{success_count}个订单)")
            return result
            
        except Exception as e:
            log_error(f"❌ 止盈止损设置异常: {e}")
            import traceback
            log_error(f"详细错误: {traceback.format_exc()}")
            return False

    def _calculate_reasonable_prices(self, position_side: str, current_price: float, 
                                   stop_loss_price: float, take_profit_price: float) -> Tuple[float, float]:
        """基于原项目逻辑计算动态合理的止损止盈价格"""
        try:
            # 获取市场波动率用于动态调整
            volatility = self._get_market_volatility()
            
            # 基于波动率的动态区间计算
            base_sl_pct = 0.02  # 基础2%止损
            base_tp_pct = 0.06  # 基础6%止盈
            
            # 根据波动率调整区间
            volatility_multiplier = max(0.5, min(2.0, volatility / 2.0))
            
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
                    log_info(f"📉 多头动态止损调整: ${stop_loss_price:.2f} (波动率: {volatility:.1f}%)")
                elif stop_loss_price > max_sl:
                    stop_loss_price = max_sl
                    log_info(f"📉 多头止损优化: ${stop_loss_price:.2f}")
                
                # 确保止盈在当前价上方
                if take_profit_price <= current_price or take_profit_price > max_tp:
                    take_profit_price = min(max_tp, current_price * 1.08)
                    log_info(f"📈 多头动态止盈调整: ${take_profit_price:.2f}")
                elif take_profit_price < min_tp:
                    take_profit_price = min_tp
                    log_info(f"📈 多头止盈优化: ${take_profit_price:.2f}")
                    
            else:  # short
                # 空头：止损高于当前价，止盈低于当前价
                min_sl = current_price * (1 + base_sl_pct * 0.5 * volatility_multiplier)
                max_sl = current_price * (1 + base_sl_pct * volatility_multiplier)
                min_tp = current_price * (1 - base_tp_pct * 1.2 * volatility_multiplier)
                max_tp = current_price * (1 - base_tp_pct * 0.8 * volatility_multiplier)
                
                # 确保止损在当前价上方
                if stop_loss_price <= current_price or stop_loss_price > max_sl:
                    stop_loss_price = min(max_sl, current_price * 1.015)
                    log_info(f"📈 空头动态止损调整: ${stop_loss_price:.2f} (波动率: {volatility:.1f}%)")
                elif stop_loss_price < min_sl:
                    stop_loss_price = min_sl
                    log_info(f"📈 空头止损优化: ${stop_loss_price:.2f}")
                
                # 确保止盈在当前价下方
                if take_profit_price >= current_price or take_profit_price < min_tp:
                    take_profit_price = max(min_tp, current_price * 0.92)
                    log_info(f"📉 空头动态止盈调整: ${take_profit_price:.2f}")
                elif take_profit_price > max_tp:
                    take_profit_price = max_tp
                    log_info(f"📉 空头止盈优化: ${take_profit_price:.2f}")
            
            return round(float(stop_loss_price), 2), round(float(take_profit_price), 2)
            
        except Exception as e:
            log_error(f"动态价格计算异常: {e}")
            # 回退到固定比例
            if position_side == 'long':
                return round(current_price * 0.98, 2), round(current_price * 1.06, 2)
            else:
                return round(current_price * 1.02, 2), round(current_price * 0.94, 2)

    def _get_market_volatility(self) -> float:
        """获取当前市场波动率"""
        try:
            # 简化实现 - 使用ATR或价格变化率
            ticker = self.exchange.fetch_ticker(self.symbol)
            high = float(ticker.get('high', 0))
            low = float(ticker.get('low', 0))
            last = float(ticker.get('last', 0))
            
            if high > 0 and low > 0 and last > 0:
                daily_range = abs(high - low) / last * 100
                return max(0.5, min(5.0, daily_range))
            return 2.0  # 默认波动率
        except:
            return 2.0
    
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

    def get_current_position(self):
        """获取当前持仓情况 - 完全复制原项目逻辑"""
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
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return float(ticker.get('last', 0))
        except Exception as e:
            log_warning(f"获取当前价格失败: {e}")
            return 0.0

    def cancel_all_tp_sl_orders(self) -> int:
        """取消所有止盈止损订单 - 完全复制原项目逻辑"""
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
        """全面取消所有类型的订单，返回详细统计"""
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
    
    def get_price_history(self, timeframe: str = '15m', limit: int = 10) -> List[Dict[str, float]]:
        """获取历史K线数据"""
        try:
            ohlcv = self.exchange_manager.exchange.fetch_ohlcv(
                self.exchange_manager.symbol,
                timeframe,
                limit=limit
            )
            
            # 转换为标准格式
            history = []
            for candle in ohlcv:
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
            log_error(f"获取历史K线数据失败: {e}")
            return []
    
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
    
    def close_position(self, side: str, amount: float) -> bool:
        """平仓操作
        
        Args:
            side: 持仓方向 ('long' 或 'short')
            amount: 平仓数量
            
        Returns:
            bool: 平仓是否成功
        """
        try:
            close_side = 'sell' if side == 'long' else 'buy'
            log_info(f"🔄 执行平仓: {side} 方向，数量: {amount:.4f} 张")
            
            # 使用市价单平仓，设置reduce_only=True
            success = self.order_manager.place_market_order(close_side, amount, reduce_only=True)
            
            if success:
                log_info(f"✅ 平仓成功: {side} 方向 {amount:.4f} 张")
            else:
                log_error(f"❌ 平仓失败: {side} 方向 {amount:.4f} 张")
            
            return success
            
        except Exception as e:
            log_error(f"平仓异常: {e}")
            return False

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
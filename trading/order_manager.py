"""
订单管理模块
提供订单创建、管理和监控功能
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import TradingError, ValidationError
from .models import OrderResult, ExchangeProtocol, ExchangeConfig

if TYPE_CHECKING:
    from typing import Protocol
    from .models import ExchangeProtocol as ExchangeManager

logger = logging.getLogger(__name__)

@dataclass
class OrderResult:
    """订单执行结果"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    filled_amount: float = 0.0
    average_price: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'order_id': self.order_id,
            'error_message': self.error_message,
            'filled_amount': self.filled_amount,
            'average_price': self.average_price,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class OrderConfig(BaseConfig):
    """订单配置"""
    def __init__(self, **kwargs):
        super().__init__(name="OrderManager", **kwargs)
        self.max_order_size = kwargs.get('max_order_size', 0.01)
        self.min_order_size = kwargs.get('min_order_size', 0.0005)  # 降低最小订单大小，匹配最小交易量
        self.max_slippage = kwargs.get('max_slippage', 0.005)  # 0.5%
        self.order_timeout = kwargs.get('order_timeout', 30)
        self.retry_attempts = kwargs.get('retry_attempts', 3)
        self.enable_stop_loss = kwargs.get('enable_stop_loss', True)
        self.enable_take_profit = kwargs.get('enable_take_profit', True)

class OrderManager(BaseComponent):
    """订单管理器"""

    def __init__(self, exchange_manager: ExchangeProtocol, config: Optional[OrderConfig] = None):
        super().__init__(config or OrderConfig())
        self.config = config or OrderConfig()
        self.exchange_manager = exchange_manager
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []
        self._order_monitoring = False
    
    async def initialize(self) -> bool:
        """初始化订单管理器"""
        try:
            logger.info("📋 订单管理器初始化...")
            
            # 确保交易所管理器已初始化
            if not self.exchange_manager.is_initialized():
                success = await self.exchange_manager.initialize()
                if not success:
                    raise TradingError("交易所管理器初始化失败")
            
            # 启动订单监控
            self._start_order_monitoring()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"订单管理器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理订单管理器"""
        try:
            self._stop_order_monitoring()
            
            # 取消所有活跃订单
            await self.cancel_all_orders()
            
            self.active_orders.clear()
            self.order_history.clear()
            
            self._initialized = False
            logger.info("🛑 订单管理器已清理")
        except Exception as e:
            logger.error(f"订单管理器清理失败: {e}")
    
    async def place_market_order(self, side: str, amount: float, reduce_only: bool = False) -> OrderResult:
        """下市价单"""
        try:
            logger.info(f"📈 准备下市价单: {side} {amount} (reduce_only={reduce_only})")
            logger.info(f"📊 订单参数 - side: {side}, amount: {amount}, min_order_size: {self.config.min_order_size}, max_order_size: {self.config.max_order_size}")

            # 验证订单参数
            validation_result = self._validate_order_params(side, amount)
            if not validation_result['valid']:
                error_msg = validation_result['errors'][0]
                logger.warning(f"⚠️ 订单验证失败: {error_msg}")
                return OrderResult(
                    success=False,
                    error_message=error_msg
                )
            
            # 标准化数量
            standardized_amount = self.exchange_manager._standardize_amount(amount)
            
            # 构建订单参数
            order_params = {
                'reduceOnly': reduce_only,
                'instId': self.exchange_manager._convert_symbol_to_inst_id(self.exchange_manager.config.symbol)
            }
            
            # 执行订单
            result = await self.exchange_manager.create_order(
                side=side,
                type='market',
                amount=standardized_amount,
                params=order_params
            )
            
            if result.success:
                # 记录订单
                self._record_order('market', side, standardized_amount, result)
                logger.info(f"✅ 市价单成功: {result.order_id}")
            else:
                logger.error(f"❌ 市价单失败: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"下市价单异常: {e}")
            return OrderResult(
                success=False,
                error_message=f"下市价单异常: {e}"
            )
    
    async def place_limit_order(self, side: str, amount: float, price: float, reduce_only: bool = False) -> OrderResult:
        """下限价单"""
        try:
            logger.info(f"📊 准备下限价单: {side} {amount} @ ${price} (reduce_only={reduce_only})")
            
            # 验证订单参数
            validation_result = self._validate_order_params(side, amount, price)
            if not validation_result['valid']:
                return OrderResult(
                    success=False,
                    error_message=validation_result['errors'][0]
                )
            
            # 标准化数量和价格
            standardized_amount = self.exchange_manager._standardize_amount(amount)
            
            # 构建订单参数
            order_params = {
                'reduceOnly': reduce_only,
                'instId': self.exchange_manager._convert_symbol_to_inst_id(self.exchange_manager.config.symbol)
            }
            
            # 执行订单
            result = await self.exchange_manager.create_order(
                side=side,
                type='limit',
                amount=standardized_amount,
                price=price,
                params=order_params
            )
            
            if result.success:
                # 记录订单
                self._record_order('limit', side, standardized_amount, result, price)
                logger.info(f"✅ 限价单成功: {result.order_id}")
            else:
                logger.error(f"❌ 限价单失败: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"下限价单异常: {e}")
            return OrderResult(
                success=False,
                error_message=f"下限价单异常: {e}"
            )
    
    async def place_stop_order(self, side: str, amount: float, stop_price: float, 
                             reduce_only: bool = True) -> OrderResult:
        """下止损单"""
        try:
            logger.info(f"🛑 准备下止损单: {side} {amount} @ 触发价${stop_price} (reduce_only={reduce_only})")
            
            # 验证订单参数
            validation_result = self._validate_order_params(side, amount, stop_price)
            if not validation_result['valid']:
                return OrderResult(
                    success=False,
                    error_message=validation_result['errors'][0]
                )
            
            # 标准化数量
            standardized_amount = self.exchange_manager._standardize_amount(amount)
            
            # 构建止损订单参数
            order_params = {
                'reduceOnly': reduce_only,
                'instId': self.exchange_manager._convert_symbol_to_inst_id(self.exchange_manager.config.symbol),
                'triggerPx': str(stop_price),
                'orderPx': '-1',  # 市价执行
                'triggerPxType': 'last'
            }
            
            # 执行订单 (使用算法订单API)
            result = await self._create_algo_order(side, standardized_amount, order_params)
            
            if result.success:
                logger.info(f"✅ 止损单成功: {result.order_id}")
            else:
                logger.error(f"❌ 止损单失败: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"下止损单异常: {e}")
            return OrderResult(
                success=False,
                error_message=f"下止损单异常: {e}"
            )
    
    async def _create_algo_order(self, side: str, amount: float, params: Dict[str, Any]) -> OrderResult:
        """创建算法订单 (止损/止盈)"""
        try:
            # 使用OKX的算法订单API
            algo_params = {
                'instId': params['instId'],
                'tdMode': 'cross',
                'side': 'buy' if side.upper() == 'BUY' else 'sell',
                'ordType': 'trigger',
                'sz': str(amount),
                **params
            }
            
            # 调用交易所的私有API
            response = await self.exchange_manager.exchange.privatePostTradeOrderAlgo(algo_params)
            
            if response and response.get('code') == '0':
                algo_id = response.get('data', [{}])[0].get('algoId')
                return OrderResult(
                    success=True,
                    order_id=algo_id
                )
            else:
                error_msg = response.get('msg', '未知错误') if response else 'API无响应'
                return OrderResult(
                    success=False,
                    error_message=f"算法订单创建失败: {error_msg}"
                )
                
        except Exception as e:
            logger.error(f"创建算法订单异常: {e}")
            return OrderResult(
                success=False,
                error_message=f"创建算法订单异常: {e}"
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            logger.info(f"🔄 准备取消订单: {order_id}")
            
            result = await self.exchange_manager.cancel_order(order_id)
            
            if result:
                # 从活跃订单中移除
                if order_id in self.active_orders:
                    order_info = self.active_orders.pop(order_id)
                    order_info['status'] = 'canceled'
                    order_info['cancel_time'] = datetime.now()
                    self.order_history.append(order_info)
                    logger.info(f"✅ 订单取消成功: {order_id}")
                return True
            else:
                logger.error(f"❌ 订单取消失败: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消订单异常: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """取消所有订单"""
        try:
            logger.info("🔄 准备取消所有订单...")
            
            # 获取所有未成交订单
            open_orders = await self.exchange_manager.fetch_open_orders()
            
            canceled_count = 0
            for order in open_orders:
                order_id = order.get('id')
                if order_id:
                    success = await self.cancel_order(order_id)
                    if success:
                        canceled_count += 1
            
            logger.info(f"✅ 取消所有订单完成: 共取消 {canceled_count} 个订单")
            return canceled_count
            
        except Exception as e:
            logger.error(f"取消所有订单异常: {e}")
            return 0
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单状态"""
        try:
            order = await self.exchange_manager.fetch_order(order_id)
            return order
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return None
    
    async def get_all_orders(self) -> List[Dict[str, Any]]:
        """获取所有订单"""
        try:
            return await self.exchange_manager.fetch_open_orders()
        except Exception as e:
            logger.error(f"获取所有订单失败: {e}")
            return []
    
    def _validate_order_params(self, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """验证订单参数"""
        errors = []
        
        # 验证交易方向
        if side.upper() not in ['BUY', 'SELL']:
            errors.append("无效的交易方向，必须是 BUY 或 SELL")
        
        # 验证数量
        if amount <= 0:
            errors.append("订单数量必须大于0")
        elif amount < self.config.min_order_size:
            errors.append(f"订单数量小于最小值: {amount} < {self.config.min_order_size}")
        elif amount > self.config.max_order_size:
            errors.append(f"订单数量超过最大值: {amount} > {self.config.max_order_size}")
        
        # 验证价格 (限价单)
        if price is not None:
            if price <= 0:
                errors.append("订单价格必须大于0")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _record_order(self, order_type: str, side: str, amount: float, result: OrderResult, 
                     price: Optional[float] = None) -> None:
        """记录订单"""
        try:
            order_record = {
                'order_id': result.order_id,
                'type': order_type,
                'side': side,
                'amount': amount,
                'price': price,
                'filled_amount': result.filled_amount,
                'average_price': result.average_price,
                'timestamp': result.timestamp,
                'status': 'open'
            }
            
            self.active_orders[result.order_id] = order_record
            
        except Exception as e:
            logger.error(f"记录订单失败: {e}")
    
    def _start_order_monitoring(self) -> None:
        """启动订单监控"""
        if not self._order_monitoring:
            self._order_monitoring = True
            # 这里可以启动后台任务来监控订单状态
            logger.info("🔄 订单监控已启动")
    
    def _stop_order_monitoring(self) -> None:
        """停止订单监控"""
        if self._order_monitoring:
            self._order_monitoring = False
            logger.info("🛑 订单监控已停止")
    
    async def update_order_status(self, order_id: str) -> bool:
        """更新订单状态"""
        try:
            if order_id not in self.active_orders:
                return False
            
            order_info = await self.get_order_status(order_id)
            if order_info:
                # 更新订单信息
                self.active_orders[order_id].update({
                    'status': order_info.get('status', 'unknown'),
                    'filled': order_info.get('filled', 0),
                    'remaining': order_info.get('remaining', 0),
                    'last_update': datetime.now()
                })
                
                # 如果订单已完成，移动到历史记录
                if order_info.get('status') in ['closed', 'canceled', 'expired']:
                    completed_order = self.active_orders.pop(order_id)
                    completed_order['completion_time'] = datetime.now()
                    self.order_history.append(completed_order)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")
            return False
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃订单"""
        return self.active_orders.copy()
    
    def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取订单历史"""
        return self.order_history[-limit:] if limit > 0 else self.order_history.copy()
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计"""
        try:
            total_orders = len(self.order_history) + len(self.active_orders)
            completed_orders = len(self.order_history)
            active_orders = len(self.active_orders)
            
            if self.order_history:
                successful_orders = len([o for o in self.order_history if o.get('status') == 'closed'])
                failed_orders = len([o for o in self.order_history if o.get('status') in ['canceled', 'expired']])
                success_rate = successful_orders / completed_orders if completed_orders > 0 else 0
            else:
                successful_orders = failed_orders = 0
                success_rate = 0
            
            return {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'active_orders': active_orders,
                'successful_orders': successful_orders,
                'failed_orders': failed_orders,
                'success_rate': success_rate,
                'total_filled_amount': sum(o.get('filled_amount', 0) for o in self.order_history),
                'total_commission': 0  # 可以从交易所获取
            }
            
        except Exception as e:
            logger.error(f"获取订单统计失败: {e}")
            return {'error': str(e)}
    
    async def place_bracket_order(self, side: str, amount: float, entry_price: Optional[float],
                                stop_loss: Optional[float], take_profit: Optional[float]) -> Dict[str, Any]:
        """下括号订单（包含入场、止损、止盈）"""
        try:
            logger.info(f"📊 准备下括号订单: {side} {amount}")
            
            results = {
                'entry_order': None,
                'stop_loss_order': None,
                'take_profit_order': None,
                'success': False
            }
            
            # 1. 下入场订单
            if entry_price:
                entry_result = await self.place_limit_order(side, amount, entry_price)
            else:
                entry_result = await self.place_market_order(side, amount)
            
            results['entry_order'] = entry_result
            
            if not entry_result.success:
                logger.error(f"❌ 入场订单失败: {entry_result.error_message}")
                return results
            
            # 2. 设置止损和止盈（需要等待入场订单成交）
            # 这里简化处理，实际应该监听订单状态
            if stop_loss or take_profit:
                logger.info(f"🎯 设置止损止盈: SL={stop_loss}, TP={take_profit}")
                
                # 获取当前持仓
                positions = await self.exchange_manager.fetch_positions()
                if positions:
                    position = positions[0]
                    
                    if stop_loss:
                        stop_result = await self.place_stop_order(
                            'SELL' if side.upper() == 'BUY' else 'BUY',
                            amount,
                            stop_loss,
                            reduce_only=True
                        )
                        results['stop_loss_order'] = stop_result
                    
                    if take_profit:
                        tp_result = await self.place_stop_order(
                            'SELL' if side.upper() == 'BUY' else 'BUY',
                            amount,
                            take_profit,
                            reduce_only=True
                        )
                        results['take_profit_order'] = tp_result
            
            results['success'] = True
            logger.info("✅ 括号订单创建完成")
            return results
            
        except Exception as e:
            logger.error(f"下括号订单异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

class OrderValidator:
    """订单验证器"""
    
    @staticmethod
    def validate_order_size(amount: float, min_size: float, max_size: float) -> bool:
        """验证订单数量"""
        return min_size <= amount <= max_size
    
    @staticmethod
    def validate_price(price: float, current_price: float, max_slippage: float) -> bool:
        """验证价格合理性"""
        price_diff = abs(price - current_price) / current_price
        return price_diff <= max_slippage
    
    @staticmethod
    def validate_side(side: str) -> bool:
        """验证交易方向"""
        return side.upper() in ['BUY', 'SELL']

# 全局订单管理器实例 (需要在初始化时传入交易所管理器)
# order_manager = OrderManager(exchange_manager)
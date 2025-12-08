"""
交易执行引擎模块
提供高级的交易执行和策略实施功能
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig, SignalData
from core.exceptions import TradingError, ValidationError
from .exchange import ExchangeManager
from .order_manager import OrderManager, OrderResult
from .position import PositionManager, PositionInfo
from .risk_assessment import MultiDimensionalRiskAssessment, RiskAssessmentResult

logger = logging.getLogger(__name__)

@dataclass
class TradeResult:
    """交易执行结果"""
    success: bool
    trade_id: Optional[str]
    signal: str
    amount: float
    price: float
    pnl: float
    fees: float
    execution_time: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'trade_id': self.trade_id,
            'signal': self.signal,
            'amount': self.amount,
            'price': self.price,
            'pnl': self.pnl,
            'fees': self.fees,
            'execution_time': self.execution_time,
            'error_message': self.error_message,
            'metadata': self.metadata or {}
        }

@dataclass
class TradeConfig(BaseConfig):
    """交易执行配置"""
    def __init__(self, **kwargs):
        super().__init__(name="TradeExecutor", **kwargs)
        self.enable_risk_management = kwargs.get('enable_risk_management', True)
        self.enable_position_sizing = kwargs.get('enable_position_sizing', True)
        self.max_slippage = kwargs.get('max_slippage', 0.005)  # 0.5%
        self.execution_timeout = kwargs.get('execution_timeout', 30)
        self.enable_batch_execution = kwargs.get('enable_batch_execution', False)
        self.enable_smart_routing = kwargs.get('enable_smart_routing', True)

class TradeExecutor(BaseComponent):
    """交易执行引擎"""
    
    def __init__(self, exchange_manager: ExchangeManager, order_manager: OrderManager, 
                 position_manager: PositionManager, risk_assessment: MultiDimensionalRiskAssessment,
                 config: Optional[TradeConfig] = None):
        super().__init__(config or TradeConfig())
        self.config = config or TradeConfig()
        self.exchange_manager = exchange_manager
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.risk_assessment = risk_assessment
        self.trade_history: List[TradeResult] = []
        self.execution_stats: Dict[str, Any] = {}
        self._execution_semaphore = asyncio.Semaphore(1)  # 串行执行，避免并发问题
    
    async def initialize(self) -> bool:
        """初始化交易执行引擎"""
        try:
            logger.info("🚀 交易执行引擎初始化...")
            
            # 确保所有依赖组件已初始化
            components = [
                (self.exchange_manager, "交易所管理器"),
                (self.order_manager, "订单管理器"),
                (self.position_manager, "仓位管理器"),
                (self.risk_assessment, "风险评估")
            ]
            
            for component, name in components:
                if not component.is_initialized():
                    success = await component.initialize()
                    if not success:
                        raise TradingError(f"{name}初始化失败")
            
            # 初始化执行统计
            self._initialize_execution_stats()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"交易执行引擎初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理交易执行引擎"""
        self.trade_history.clear()
        self.execution_stats.clear()
        self._initialized = False
        logger.info("🛑 交易执行引擎已清理")
    
    def _initialize_execution_stats(self) -> None:
        """初始化执行统计"""
        self.execution_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'total_fees': 0.0,
            'total_pnl': 0.0,
            'average_execution_time': 0.0,
            'best_execution_time': float('inf'),
            'worst_execution_time': 0.0,
            'slippage_stats': {
                'total_slippage': 0.0,
                'average_slippage': 0.0,
                'max_slippage': 0.0
            }
        }
    
    async def execute_trade(self, signal_data: Dict[str, Any], market_data: Dict[str, Any],
                          portfolio_data: Optional[Dict[str, Any]] = None) -> TradeResult:
        """执行交易"""
        try:
            logger.info("🚀 开始执行交易...")
            start_time = datetime.now()
            
            # 获取信号信息
            signal = signal_data.get('signal', 'HOLD')
            confidence = signal_data.get('confidence', 0.5)
            reason = signal_data.get('reason', '')
            
            if signal == 'HOLD':
                logger.info("⏭️ 收到HOLD信号，跳过交易执行")
                return TradeResult(
                    success=True,
                    trade_id=None,
                    signal='HOLD',
                    amount=0.0,
                    price=0.0,
                    pnl=0.0,
                    fees=0.0,
                    execution_time=0.0,
                    metadata={'reason': 'HOLD signal'}
                )
            
            # 1. 风险评估
            if self.config.enable_risk_management:
                risk_result = await self._perform_risk_assessment(portfolio_data, market_data)
                if not risk_result['can_trade']:
                    return TradeResult(
                        success=False,
                        trade_id=None,
                        signal=signal,
                        amount=0.0,
                        price=0.0,
                        pnl=0.0,
                        fees=0.0,
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        error_message=risk_result['reason'],
                        metadata={'risk_blocked': True}
                    )
            
            # 2. 仓位大小计算
            if self.config.enable_position_sizing:
                position_size = await self._calculate_position_size(signal_data, market_data, portfolio_data)
            else:
                position_size = signal_data.get('amount', 0.001)  # 默认大小
            
            # 3. 价格确定
            execution_price = await self._determine_execution_price(signal, market_data)
            
            # 4. 执行交易
            async with self._execution_semaphore:
                trade_result = await self._execute_single_trade(
                    signal, position_size, execution_price, market_data
                )
            
            # 5. 更新统计
            execution_time = (datetime.now() - start_time).total_seconds()
            trade_result.execution_time = execution_time
            
            self._update_execution_stats(trade_result)
            
            # 6. 记录交易历史
            self.trade_history.append(trade_result)
            
            # 保持历史记录在合理范围内
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-500:]
            
            logger.info(f"✅ 交易执行完成: {signal} {position_size} @ ${execution_price:.2f}, "
                       f"用时: {execution_time:.2f}s")
            
            return trade_result
            
        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            return TradeResult(
                success=False,
                trade_id=None,
                signal=signal_data.get('signal', 'UNKNOWN'),
                amount=0.0,
                price=0.0,
                pnl=0.0,
                fees=0.0,
                execution_time=execution_time,
                error_message=f"交易执行失败: {e}"
            )
    
    async def _perform_risk_assessment(self, portfolio_data: Optional[Dict[str, Any]], 
                                     market_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行风险评估"""
        try:
            logger.info("🛡️ 执行交易前风险评估...")
            
            # 获取综合风险评估
            risk_result = await self.risk_assessment.perform_comprehensive_risk_assessment(
                portfolio_data=portfolio_data,
                market_data=market_data
            )
            
            overall_risk = risk_result.overall_risk_score
            risk_level = risk_result.risk_level
            
            logger.info(f"📊 风险评估结果: 评分 {overall_risk:.1f}, 等级 {risk_level}")
            
            # 风险阈值判断
            if overall_risk > 80:  # 极高风险
                return {
                    'can_trade': False,
                    'reason': f"风险过高 (评分: {overall_risk:.1f})，禁止交易"
                }
            elif overall_risk > 60:  # 高风险
                return {
                    'can_trade': True,
                    'reason': f"风险偏高 (评分: {overall_risk:.1f})，谨慎交易",
                    'risk_adjustment': 0.7  # 降低仓位
                }
            elif overall_risk > 40:  # 中等风险
                return {
                    'can_trade': True,
                    'reason': f"风险中等 (评分: {overall_risk:.1f})，正常交易",
                    'risk_adjustment': 0.9  # 轻微调整
                }
            else:  # 低风险
                return {
                    'can_trade': True,
                    'reason': f"风险较低 (评分: {overall_risk:.1f})，可以交易"
                }
                
        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return {
                'can_trade': False,
                'reason': f"风险评估异常: {e}"
            }
    
    async def _calculate_position_size(self, signal_data: Dict[str, Any], 
                                     market_data: Dict[str, Any],
                                     portfolio_data: Optional[Dict[str, Any]]) -> float:
        """计算仓位大小"""
        try:
            logger.info("📊 计算最优仓位大小...")
            
            # 基础信号强度
            base_signal = signal_data.get('signal', 'HOLD')
            confidence = signal_data.get('confidence', 0.5)
            base_amount = signal_data.get('amount', 0.001)
            
            # 获取市场数据
            current_price = market_data.get('price', 50000)
            technical_data = market_data.get('technical_data', {})
            atr_pct = technical_data.get('atr_pct', 2.0)
            
            # 获取账户余额 (简化处理)
            account_balance = portfolio_data.get('balance', 10000) if portfolio_data else 10000
            
            # 1. 基于信号强度的调整
            signal_multiplier = self._get_signal_multiplier(base_signal, confidence)
            
            # 2. 基于市场波动率的调整
            volatility_multiplier = self._get_volatility_multiplier(atr_pct)
            
            # 3. 基于风险评分的调整
            risk_adjustment = await self._get_risk_adjustment(portfolio_data, market_data)
            
            # 4. 综合计算
            adjusted_size = base_amount * signal_multiplier * volatility_multiplier * risk_adjustment
            
            # 5. 应用最终限制
            final_size = self._apply_position_limits(adjusted_size, account_balance, current_price)
            
            logger.info(f"📊 仓位大小计算: 基础{base_amount} × 信号{signal_multiplier:.2f} × "
                       f"波动{volatility_multiplier:.2f} × 风险{risk_adjustment:.2f} = {final_size:.6f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"计算仓位大小失败: {e}")
            return 0.001  # 最小默认仓位
    
    def _get_signal_multiplier(self, signal: str, confidence: float) -> float:
        """获取信号强度乘数"""
        try:
            base_multipliers = {
                'BUY': 1.0,
                'SELL': 1.0,
                'HOLD': 0.0
            }
            
            base_multiplier = base_multipliers.get(signal.upper(), 0.0)
            
            # 根据信心调整
            confidence_adjustment = 0.5 + (confidence * 0.5)  # 0.5 到 1.0
            
            return base_multiplier * confidence_adjustment
            
        except Exception as e:
            logger.error(f"获取信号乘数失败: {e}")
            return 0.5
    
    def _get_volatility_multiplier(self, atr_pct: float) -> float:
        """获取波动率乘数"""
        try:
            # 低波动率：增加仓位
            # 高波动率：减少仓位
            if atr_pct < 1.0:  # 低波动
                return 1.2
            elif atr_pct < 2.0:  # 正常波动
                return 1.0
            elif atr_pct < 3.0:  # 中等波动
                return 0.8
            else:  # 高波动
                return 0.6
                
        except Exception as e:
            logger.error(f"获取波动率乘数失败: {e}")
            return 1.0
    
    async def _get_risk_adjustment(self, portfolio_data: Optional[Dict[str, Any]], 
                                 market_data: Dict[str, Any]) -> float:
        """获取风险调整系数"""
        try:
            # 获取风险评估结果
            risk_result = await self.risk_assessment.perform_comprehensive_risk_assessment(
                portfolio_data=portfolio_data,
                market_data=market_data
            )
            
            risk_score = risk_result.overall_risk_score
            
            # 基于风险评分的调整
            if risk_score > 80:  # 极高风险
                return 0.3
            elif risk_score > 60:  # 高风险
                return 0.5
            elif risk_score > 40:  # 中等风险
                return 0.7
            elif risk_score > 20:  # 低风险
                return 0.9
            else:  # 极低风险
                return 1.0
                
        except Exception as e:
            logger.error(f"获取风险调整失败: {e}")
            return 0.7  # 保守回退
    
    def _apply_position_limits(self, adjusted_size: float, account_balance: float, current_price: float) -> float:
        """应用仓位限制"""
        try:
            # 1. 基于账户余额的限制
            max_risk_amount = account_balance * 0.02  # 每笔交易最大2%风险
            max_size_by_balance = max_risk_amount / (current_price * 0.02)  # 假设2%止损
            
            # 2. 基于配置的最大仓位限制
            max_size_by_config = self.config.max_position_size
            
            # 3. 应用所有限制
            final_size = min(adjusted_size, max_size_by_balance, max_size_by_config)
            
            # 4. 确保最小仓位
            final_size = max(final_size, 0.001)  # 最小0.001
            
            return final_size
            
        except Exception as e:
            logger.error(f"应用仓位限制失败: {e}")
            return min(adjusted_size, 0.001)
    
    async def _determine_execution_price(self, signal: str, market_data: Dict[str, Any]) -> float:
        """确定执行价格"""
        try:
            # 获取当前市场价格
            current_price = market_data.get('price', 0)
            bid_price = market_data.get('bid', current_price)
            ask_price = market_data.get('ask', current_price)
            
            if signal.upper() == 'BUY':
                # 买入时使用卖价，加上轻微滑点
                execution_price = ask_price * (1 + 0.0001)  # 0.01%滑点
            elif signal.upper() == 'SELL':
                # 卖出时使用买价，减去轻微滑点
                execution_price = bid_price * (1 - 0.0001)  # 0.01%滑点
            else:
                execution_price = current_price
            
            logger.info(f"💰 执行价格确定: {signal} @ ${execution_price:.2f} (当前价: ${current_price:.2f})")
            
            return execution_price
            
        except Exception as e:
            logger.error(f"确定执行价格失败: {e}")
            return market_data.get('price', 50000)  # 回退到当前价格
    
    async def _execute_single_trade(self, signal: str, amount: float, price: float, 
                                  market_data: Dict[str, Any]) -> TradeResult:
        """执行单个交易"""
        try:
            logger.info(f"⚡ 执行交易: {signal} {amount} @ ${price:.2f}")
            
            # 1. 下主订单
            order_result = await self.order_manager.place_market_order(signal, amount)
            
            if not order_result.success:
                return TradeResult(
                    success=False,
                    trade_id=None,
                    signal=signal,
                    amount=amount,
                    price=price,
                    pnl=0.0,
                    fees=0.0,
                    execution_time=0.0,
                    error_message=f"订单执行失败: {order_result.error_message}"
                )
            
            # 2. 获取实际成交价格
            actual_price = order_result.average_price if order_result.average_price > 0 else price
            
            # 3. 更新仓位信息
            await self._update_position_after_trade(signal, amount, actual_price, market_data)
            
            # 4. 计算费用和滑点
            fees = self._estimate_fees(amount, actual_price)
            slippage = abs(actual_price - price) / price
            
            # 5. 验证滑点是否在允许范围内
            if slippage > self.config.max_slippage:
                logger.warning(f"⚠️ 滑点超过阈值: {slippage:.4f} > {self.config.max_slippage:.4f}")
            
            # 6. 计算初始盈亏（简化处理）
            initial_pnl = 0.0  # 新开仓的初始盈亏为0
            
            trade_id = f"TRADE_{int(datetime.now().timestamp() * 1000)}"
            
            return TradeResult(
                success=True,
                trade_id=trade_id,
                signal=signal,
                amount=amount,
                price=actual_price,
                pnl=initial_pnl,
                fees=fees,
                execution_time=0.0,  # 将在外层设置
                metadata={
                    'order_id': order_result.order_id,
                    'slippage': slippage,
                    'filled_amount': order_result.filled_amount
                }
            )
            
        except Exception as e:
            logger.error(f"单笔交易执行失败: {e}")
            return TradeResult(
                success=False,
                trade_id=None,
                signal=signal,
                amount=amount,
                price=price,
                pnl=0.0,
                fees=0.0,
                execution_time=0.0,
                error_message=f"单笔交易执行失败: {e}"
            )
    
    async def _update_position_after_trade(self, signal: str, amount: float, price: float, 
                                         market_data: Dict[str, Any]) -> None:
        """交易后更新仓位信息"""
        try:
            # 获取当前持仓
            current_position = self.position_manager.get_current_position()
            
            if signal.upper() == 'BUY':
                if current_position and current_position.side == 'long':
                    # 加仓
                    new_size = current_position.size + amount
                    new_entry_price = (current_position.entry_price * current_position.size + price * amount) / new_size
                else:
                    # 新开多仓
                    new_size = amount
                    new_entry_price = price
                    new_side = 'long'
                
                position_data = {
                    'side': 'long',
                    'size': new_size,
                    'entry_price': new_entry_price if 'new_entry_price' in locals() else price,
                    'current_price': price,
                    'unrealized_pnl': 0.0,  # 新开仓
                    'realized_pnl': 0.0,
                    'leverage': 10,  # 默认杠杆
                    'symbol': 'BTCUSDT',
                    'timestamp': datetime.now(),
                    'metadata': {'action': 'open_long' if not current_position else 'add_to_long'}
                }
                
            elif signal.upper() == 'SELL':
                if current_position and current_position.side == 'short':
                    # 加空仓
                    new_size = current_position.size + amount
                    new_entry_price = (current_position.entry_price * current_position.size + price * amount) / new_size
                else:
                    # 新开空仓
                    new_size = amount
                    new_entry_price = price
                    new_side = 'short'
                
                position_data = {
                    'side': 'short',
                    'size': new_size,
                    'entry_price': new_entry_price if 'new_entry_price' in locals() else price,
                    'current_price': price,
                    'unrealized_pnl': 0.0,  # 新开仓
                    'realized_pnl': 0.0,
                    'leverage': 10,  # 默认杠杆
                    'symbol': 'BTCUSDT',
                    'timestamp': datetime.now(),
                    'metadata': {'action': 'open_short' if not current_position else 'add_to_short'}
                }
            
            # 更新仓位
            self.position_manager.update_position(position_data)
            
            logger.info(f"📊 仓位更新完成: {signal} {amount} @ ${price:.2f}")
            
        except Exception as e:
            logger.error(f"交易后更新仓位失败: {e}")
    
    def _estimate_fees(self, amount: float, price: float) -> float:
        """估算交易费用"""
        try:
            # 获取交易所费用信息
            market_info = self.exchange_manager.get_market_info()
            taker_fee = market_info.get('taker', 0.001)  # 默认0.1%
            
            # 计算费用
            trade_value = amount * price
            fees = trade_value * taker_fee
            
            return fees
            
        except Exception as e:
            logger.error(f"估算费用失败: {e}")
            return amount * price * 0.001  # 默认0.1%
    
    def _update_execution_stats(self, trade_result: TradeResult) -> None:
        """更新执行统计"""
        try:
            self.execution_stats['total_trades'] += 1
            
            if trade_result.success:
                self.execution_stats['successful_trades'] += 1
                self.execution_stats['total_volume'] += trade_result.amount
                self.execution_stats['total_fees'] += trade_result.fees
                self.execution_stats['total_pnl'] += trade_result.pnl
                
                # 更新执行时间统计
                current_time = trade_result.execution_time
                self.execution_stats['average_execution_time'] = (
                    (self.execution_stats['average_execution_time'] * (self.execution_stats['successful_trades'] - 1) + 
                     current_time) / self.execution_stats['successful_trades']
                )
                self.execution_stats['best_execution_time'] = min(
                    self.execution_stats['best_execution_time'], current_time
                )
                self.execution_stats['worst_execution_time'] = max(
                    self.execution_stats['worst_execution_time'], current_time
                )
            else:
                self.execution_stats['failed_trades'] += 1
            
            # 更新成功率
            total = self.execution_stats['successful_trades'] + self.execution_stats['failed_trades']
            if total > 0:
                success_rate = self.execution_stats['successful_trades'] / total
                logger.info(f"📈 交易成功率: {success_rate:.2%}")
                
        except Exception as e:
            logger.error(f"更新执行统计失败: {e}")
    
    async def execute_batch_trades(self, trade_signals: List[Dict[str, Any]], 
                                 market_data: Dict[str, Any]) -> List[TradeResult]:
        """批量执行交易"""
        try:
            logger.info(f"📦 开始批量执行 {len(trade_signals)} 个交易信号")
            
            if not self.config.enable_batch_execution:
                logger.warning("⚠️ 批量执行功能已禁用")
                return []
            
            results = []
            
            # 按优先级排序
            sorted_signals = sorted(trade_signals, key=lambda x: x.get('priority', 0), reverse=True)
            
            # 并发执行 (但受信号量限制)
            tasks = []
            for signal in sorted_signals:
                task = self.execute_trade(signal, market_data)
                tasks.append(task)
            
            # 等待所有交易完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"批量交易 {i} 失败: {result}")
                    error_result = TradeResult(
                        success=False,
                        trade_id=None,
                        signal=sorted_signals[i].get('signal', 'UNKNOWN'),
                        amount=0.0,
                        price=0.0,
                        pnl=0.0,
                        fees=0.0,
                        execution_time=0.0,
                        error_message=f"批量交易异常: {result}"
                    )
                    final_results.append(error_result)
                else:
                    final_results.append(result)
            
            logger.info(f"✅ 批量交易执行完成: 成功 {sum(1 for r in final_results if r.success)}/{len(final_results)}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"批量交易执行失败: {e}")
            return []
    
    async def close_position(self, position: PositionInfo, close_type: str = 'market') -> TradeResult:
        """平仓"""
        try:
            logger.info(f"🔒 开始平仓: {position.side} {position.size} @ 当前价${position.current_price:.2f}")
            
            # 确定平仓方向
            close_side = 'SELL' if position.side == 'long' else 'BUY'
            
            # 执行平仓
            if close_type == 'market':
                result = await self.order_manager.place_market_order(close_side, position.size, reduce_only=True)
            else:
                # 限价平仓
                result = await self.order_manager.place_limit_order(close_side, position.size, position.current_price, reduce_only=True)
            
            if result.success:
                # 计算实际盈亏
                realized_pnl = position.unrealized_pnl  # 简化处理
                
                trade_id = f"CLOSE_{int(datetime.now().timestamp() * 1000)}"
                
                return TradeResult(
                    success=True,
                    trade_id=trade_id,
                    signal=close_side,
                    amount=position.size,
                    price=result.average_price,
                    pnl=realized_pnl,
                    fees=0.0,  # 简化处理
                    execution_time=0.0,
                    metadata={
                        'close_type': close_type,
                        'original_position': position.to_dict()
                    }
                )
            else:
                return TradeResult(
                    success=False,
                    trade_id=None,
                    signal=close_side,
                    amount=position.size,
                    price=position.current_price,
                    pnl=0.0,
                    fees=0.0,
                    execution_time=0.0,
                    error_message=f"平仓失败: {result.error_message}"
                )
                
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return TradeResult(
                success=False,
                trade_id=None,
                signal='CLOSE',
                amount=position.size,
                price=position.current_price,
                pnl=0.0,
                fees=0.0,
                execution_time=0.0,
                error_message=f"平仓异常: {e}"
            )
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        try:
            total_trades = self.execution_stats['total_trades']
            if total_trades == 0:
                return {'message': '暂无交易记录', 'total_trades': 0}
            
            success_rate = (self.execution_stats['successful_trades'] / total_trades) if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'successful_trades': self.execution_stats['successful_trades'],
                'failed_trades': self.execution_stats['failed_trades'],
                'success_rate': success_rate,
                'total_volume': self.execution_stats['total_volume'],
                'total_fees': self.execution_stats['total_fees'],
                'total_pnl': self.execution_stats['total_pnl'],
                'average_execution_time': self.execution_stats['average_execution_time'],
                'best_execution_time': self.execution_stats['best_execution_time'],
                'worst_execution_time': self.execution_stats['worst_execution_time'],
                'efficiency_metrics': self._calculate_efficiency_metrics()
            }
            
        except Exception as e:
            logger.error(f"获取执行摘要失败: {e}")
            return {'error': str(e)}
    
    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """计算效率指标"""
        try:
            total_trades = self.execution_stats['total_trades']
            successful_trades = self.execution_stats['successful_trades']
            
            if successful_trades == 0:
                return {'message': '暂无成功交易'}
            
            avg_time = self.execution_stats['average_execution_time']
            best_time = self.execution_stats['best_execution_time']
            worst_time = self.execution_stats['worst_execution_time']
            
            return {
                'execution_efficiency': min(1.0, 10.0 / avg_time) if avg_time > 0 else 0.0,  # 10秒内为高效
                'time_consistency': 1.0 - (worst_time - best_time) / max(worst_time, 1.0),  # 时间一致性
                'success_consistency': successful_trades / total_trades if total_trades > 0 else 0.0,
                'average_speed_rating': max(0, 10 - avg_time) if avg_time <= 10 else max(0, 5 - (avg_time - 10) / 2)
            }
            
        except Exception as e:
            logger.error(f"计算效率指标失败: {e}")
            return {'error': str(e)}
    
    def get_trade_history(self, limit: int = 100) -> List[TradeResult]:
        """获取交易历史"""
        return self.trade_history[-limit:] if limit > 0 else self.trade_history.copy()
    
    def export_trade_data(self, format: str = 'json') -> str:
        """导出交易数据"""
        try:
            if format == 'json':
                import json
                return json.dumps({
                    'trade_history': [trade.to_dict() for trade in self.trade_history[-1000:]],  # 最近1000条
                    'execution_summary': self.get_execution_summary(),
                    'config': self.config.to_dict()
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出交易数据失败: {e}")
            return f"导出失败: {e}"

# 全局交易执行器实例 (需要在初始化时传入依赖组件)
# trade_executor = TradeExecutor(exchange_manager, order_manager, position_manager, risk_assessment)
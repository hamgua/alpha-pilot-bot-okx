"""
仓位管理模块
提供仓位监控、管理和优化功能
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import TradingError, ValidationError

logger = logging.getLogger(__name__)

@dataclass
class PositionInfo:
    """持仓信息"""
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    leverage: float
    symbol: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'leverage': self.leverage,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }
    
    @property
    def pnl_percentage(self) -> float:
        """盈亏百分比"""
        if self.entry_price > 0:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100 * self.leverage
        return 0.0
    
    @property
    def is_profitable(self) -> bool:
        """是否盈利"""
        return self.unrealized_pnl > 0
    
    @property
    def position_value(self) -> float:
        """仓位价值"""
        return self.size * self.current_price

@dataclass
class PositionConfig(BaseConfig):
    """仓位配置"""
    def __init__(self, **kwargs):
        super().__init__(name="PositionManager", **kwargs)
        self.max_position_size = kwargs.get('max_position_size', 0.01)
        self.max_leverage = kwargs.get('max_leverage', 20)
        self.stop_loss_threshold = kwargs.get('stop_loss_threshold', 0.02)  # 2%
        self.take_profit_threshold = kwargs.get('take_profit_threshold', 0.04)  # 4%
        self.enable_trailing_stop = kwargs.get('enable_trailing_stop', True)
        self.trailing_stop_distance = kwargs.get('trailing_stop_distance', 0.015)  # 1.5%
        self.enable_position_sizing = kwargs.get('enable_position_sizing', True)

class PositionManager(BaseComponent):
    """仓位管理器"""
    
    def __init__(self, config: Optional[PositionConfig] = None):
        super().__init__(config or PositionConfig())
        self.config = config or PositionConfig()
        self.positions: Dict[str, PositionInfo] = {}
        self.position_history: List[PositionInfo] = []
        self.performance_metrics: Dict[str, Any] = {}
        self._stop_loss_levels: Dict[str, float] = {}
        self._take_profit_levels: Dict[str, float] = {}
    
    async def initialize(self) -> bool:
        """初始化仓位管理器"""
        try:
            logger.info("📊 仓位管理器初始化...")
            
            # 初始化性能指标
            self._initialize_performance_metrics()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"仓位管理器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理仓位管理器"""
        self.positions.clear()
        self.position_history.clear()
        self.performance_metrics.clear()
        self._stop_loss_levels.clear()
        self._take_profit_levels.clear()
        
        self._initialized = False
        logger.info("🛑 仓位管理器已清理")
    
    def _initialize_performance_metrics(self) -> None:
        """初始化性能指标"""
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_streak': 0,
            'peak_equity': 0.0,
            'current_equity': 0.0,
            'max_drawdown': 0.0
        }
    
    def update_position(self, position_data: Dict[str, Any]) -> bool:
        """更新仓位信息"""
        try:
            symbol = position_data.get('symbol', 'UNKNOWN')
            
            # 创建仓位信息对象
            position_info = PositionInfo(
                side=position_data.get('side', 'long'),
                size=float(position_data.get('size', 0)),
                entry_price=float(position_data.get('entry_price', 0)),
                current_price=float(position_data.get('current_price', 0)),
                unrealized_pnl=float(position_data.get('unrealized_pnl', 0)),
                realized_pnl=float(position_data.get('realized_pnl', 0)),
                leverage=float(position_data.get('leverage', 1)),
                symbol=symbol,
                timestamp=position_data.get('timestamp', datetime.now()),
                metadata=position_data.get('metadata')
            )
            
            # 验证仓位信息
            if not self._validate_position(position_info):
                raise ValidationError("仓位信息验证失败")
            
            # 更新仓位
            old_position = self.positions.get(symbol)
            self.positions[symbol] = position_info
            
            # 如果是新仓位或重大更新，记录历史
            if not old_position or self._is_significant_update(old_position, position_info):
                self.position_history.append(position_info)
                
                # 保持历史记录在合理范围内
                if len(self.position_history) > 1000:
                    self.position_history = self.position_history[-500:]
            
            # 更新性能指标
            self._update_performance_metrics(position_info)
            
            logger.info(f"✅ 仓位更新成功: {symbol} - 大小: {position_info.size}, 盈亏: ${position_info.unrealized_pnl:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"仓位更新失败: {e}")
            return False
    
    def _validate_position(self, position: PositionInfo) -> bool:
        """验证仓位信息"""
        try:
            # 验证基本参数
            if position.size < 0:
                return False
            if position.leverage <= 0:
                return False
            if position.entry_price < 0:
                return False
            if position.current_price < 0:
                return False
            
            # 验证仓位限制
            if position.size > self.config.max_position_size:
                logger.warning(f"⚠️ 仓位大小超过限制: {position.size} > {self.config.max_position_size}")
                return False
            
            if position.leverage > self.config.max_leverage:
                logger.warning(f"⚠️ 杠杆超过限制: {position.leverage} > {self.config.max_leverage}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"仓位验证失败: {e}")
            return False
    
    def _is_significant_update(self, old_position: PositionInfo, new_position: PositionInfo) -> bool:
        """判断是否为重大更新"""
        try:
            # 大小变化超过10%
            size_change = abs(new_position.size - old_position.size) / max(old_position.size, 0.001)
            if size_change > 0.1:
                return True
            
            # 价格变化超过5%
            price_change = abs(new_position.current_price - old_position.current_price) / max(old_position.current_price, 0.001)
            if price_change > 0.05:
                return True
            
            # 盈亏变化超过$100
            pnl_change = abs(new_position.unrealized_pnl - old_position.unrealized_pnl)
            if pnl_change > 100:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"判断重大更新失败: {e}")
            return True  # 保守处理
    
    def _update_performance_metrics(self, position: PositionInfo) -> None:
        """更新性能指标"""
        try:
            # 更新基本统计
            self.performance_metrics['total_trades'] += 1
            
            if position.is_profitable:
                self.performance_metrics['winning_trades'] += 1
                self.performance_metrics['total_pnl'] += position.unrealized_pnl
                
                # 更新平均盈利
                current_avg_win = self.performance_metrics['average_win']
                win_count = self.performance_metrics['winning_trades']
                self.performance_metrics['average_win'] = (current_avg_win * (win_count - 1) + position.unrealized_pnl) / win_count
                
                # 更新最大盈利
                self.performance_metrics['largest_win'] = max(self.performance_metrics['largest_win'], position.unrealized_pnl)
                
                # 更新连胜记录
                if self.performance_metrics['current_streak'] >= 0:
                    self.performance_metrics['current_streak'] += 1
                else:
                    self.performance_metrics['current_streak'] = 1
                
                self.performance_metrics['max_consecutive_wins'] = max(
                    self.performance_metrics['max_consecutive_wins'],
                    self.performance_metrics['current_streak']
                )
            else:
                self.performance_metrics['losing_trades'] += 1
                self.performance_metrics['total_pnl'] += position.unrealized_pnl
                
                # 更新平均亏损
                current_avg_loss = self.performance_metrics['average_loss']
                loss_count = self.performance_metrics['losing_trades']
                self.performance_metrics['average_loss'] = (current_avg_loss * (loss_count - 1) + abs(position.unrealized_pnl)) / loss_count
                
                # 更新最大亏损
                self.performance_metrics['largest_loss'] = max(self.performance_metrics['largest_loss'], abs(position.unrealized_pnl))
                
                # 更新连败记录
                if self.performance_metrics['current_streak'] <= 0:
                    self.performance_metrics['current_streak'] -= 1
                else:
                    self.performance_metrics['current_streak'] = -1
                
                self.performance_metrics['max_consecutive_losses'] = max(
                    self.performance_metrics['max_consecutive_losses'],
                    abs(self.performance_metrics['current_streak'])
                )
            
            # 更新胜率
            total_trades = self.performance_metrics['winning_trades'] + self.performance_metrics['losing_trades']
            if total_trades > 0:
                self.performance_metrics['win_rate'] = self.performance_metrics['winning_trades'] / total_trades
            
            # 更新盈亏比
            if self.performance_metrics['average_loss'] > 0:
                self.performance_metrics['profit_factor'] = self.performance_metrics['average_win'] / self.performance_metrics['average_loss']
            
            # 更新权益相关指标
            self.performance_metrics['current_equity'] = self.performance_metrics['total_pnl']
            self.performance_metrics['peak_equity'] = max(self.performance_metrics['peak_equity'], self.performance_metrics['current_equity'])
            
            # 计算最大回撤
            drawdown = (self.performance_metrics['peak_equity'] - self.performance_metrics['current_equity']) / max(self.performance_metrics['peak_equity'], 1)
            self.performance_metrics['max_drawdown'] = max(self.performance_metrics['max_drawdown'], drawdown)
            
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")
    
    def get_current_position(self, symbol: str = None) -> Optional[PositionInfo]:
        """获取当前仓位"""
        if symbol:
            return self.positions.get(symbol)
        
        # 返回第一个仓位（假设只有一个交易对）
        if self.positions:
            return next(iter(self.positions.values()))
        
        return None
    
    def get_all_positions(self) -> Dict[str, PositionInfo]:
        """获取所有仓位"""
        return self.positions.copy()
    
    def get_position_summary(self) -> Dict[str, Any]:
        """获取仓位摘要"""
        try:
            if not self.positions:
                return {
                    'has_positions': False,
                    'total_positions': 0,
                    'total_size': 0,
                    'total_pnl': 0,
                    'average_leverage': 0
                }
            
            total_size = sum(pos.size for pos in self.positions.values())
            total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            total_leverage = sum(pos.leverage for pos in self.positions.values())
            avg_leverage = total_leverage / len(self.positions) if self.positions else 0
            
            profitable_positions = sum(1 for pos in self.positions.values() if pos.is_profitable)
            
            return {
                'has_positions': True,
                'total_positions': len(self.positions),
                'total_size': total_size,
                'total_pnl': total_pnl,
                'average_leverage': avg_leverage,
                'profitable_positions': profitable_positions,
                'win_rate': profitable_positions / len(self.positions) if self.positions else 0,
                'positions_by_side': self._get_positions_by_side()
            }
            
        except Exception as e:
            logger.error(f"获取仓位摘要失败: {e}")
            return {'error': str(e)}
    
    def _get_positions_by_side(self) -> Dict[str, int]:
        """按方向统计仓位"""
        try:
            side_counts = {'long': 0, 'short': 0}
            
            for position in self.positions.values():
                if position.side in side_counts:
                    side_counts[position.side] += 1
            
            return side_counts
            
        except Exception as e:
            logger.error(f"按方向统计仓位失败: {e}")
            return {}
    
    def calculate_position_metrics(self, symbol: str) -> Dict[str, Any]:
        """计算仓位指标"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return {'error': '未找到指定仓位'}
            
            # 计算各种指标
            metrics = {
                'pnl_percentage': position.pnl_percentage,
                'position_value': position.position_value,
                'risk_exposure': position.size * position.leverage,
                'leverage_ratio': position.leverage,
                'entry_efficiency': self._calculate_entry_efficiency(position),
                'current_efficiency': self._calculate_current_efficiency(position),
                'time_in_position': (datetime.now() - position.timestamp).total_seconds() / 3600,  # 小时
                'max_adverse_excursion': self._calculate_max_adverse_excursion(position),
                'max_favorable_excursion': self._calculate_max_favorable_excursion(position)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算仓位指标失败: {e}")
            return {'error': str(e)}
    
    def _calculate_entry_efficiency(self, position: PositionInfo) -> float:
        """计算入场效率"""
        try:
            # 入场效率 = (最佳可能价格 - 实际入场价格) / (最佳可能价格 - 最差可能价格)
            # 简化计算：基于当前价格与入场价格的比较
            if position.entry_price > 0:
                price_change = abs(position.current_price - position.entry_price) / position.entry_price
                return max(0, min(1.0, 1.0 - price_change))  # 价格变化越小，效率越高
            return 0.0
            
        except Exception as e:
            logger.error(f"计算入场效率失败: {e}")
            return 0.0
    
    def _calculate_current_efficiency(self, position: PositionInfo) -> float:
        """计算当前效率"""
        try:
            # 当前效率 = 当前盈亏 / 最大可能盈亏
            # 简化计算：基于当前盈亏与仓位大小的比例
            if position.size > 0:
                efficiency = position.unrealized_pnl / (position.size * position.entry_price)
                return max(-1.0, min(1.0, efficiency))  # 限制在[-1, 1]范围内
            return 0.0
            
        except Exception as e:
            logger.error(f"计算当前效率失败: {e}")
            return 0.0
    
    def _calculate_max_adverse_excursion(self, position: PositionInfo) -> float:
        """计算最大不利偏移"""
        try:
            # 简化计算：基于当前亏损程度
            if position.unrealized_pnl < 0:
                return abs(position.unrealized_pnl) / (position.size * position.entry_price)
            return 0.0
            
        except Exception as e:
            logger.error(f"计算最大不利偏移失败: {e}")
            return 0.0
    
    def _calculate_max_favorable_excursion(self, position: PositionInfo) -> float:
        """计算最大有利偏移"""
        try:
            # 简化计算：基于当前盈利程度
            if position.unrealized_pnl > 0:
                return position.unrealized_pnl / (position.size * position.entry_price)
            return 0.0
            
        except Exception as e:
            logger.error(f"计算最大有利偏移失败: {e}")
            return 0.0
    
    def should_close_position(self, position: PositionInfo, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """判断是否应该平仓"""
        try:
            close_signals = []
            reasons = []
            
            # 1. 止损检查
            if self._check_stop_loss(position):
                close_signals.append('stop_loss')
                reasons.append(f"触发止损: 亏损 {position.unrealized_pnl:.2f}")
            
            # 2. 止盈检查
            if self._check_take_profit(position):
                close_signals.append('take_profit')
                reasons.append(f"触发止盈: 盈利 {position.unrealized_pnl:.2f}")
            
            # 3. 移动止盈检查
            if self.config.enable_trailing_stop:
                trailing_stop_result = self._check_trailing_stop(position, market_data)
                if trailing_stop_result['should_close']:
                    close_signals.append('trailing_stop')
                    reasons.append(trailing_stop_result['reason'])
            
            # 4. 时间止损检查
            if self._check_time_stop(position):
                close_signals.append('time_stop')
                reasons.append("持仓时间超过限制")
            
            # 5. 风险水平检查
            risk_check = self._check_risk_level(position, market_data)
            if risk_check['should_close']:
                close_signals.append('risk_limit')
                reasons.append(risk_check['reason'])
            
            return {
                'should_close': len(close_signals) > 0,
                'close_signals': close_signals,
                'reasons': reasons,
                'urgency': self._determine_urgency(close_signals)
            }
            
        except Exception as e:
            logger.error(f"判断是否应该平仓失败: {e}")
            return {
                'should_close': False,
                'close_signals': [],
                'reasons': [f"判断异常: {e}"],
                'urgency': 'low'
            }
    
    def _check_stop_loss(self, position: PositionInfo) -> bool:
        """检查止损"""
        try:
            if position.unrealized_pnl >= 0:
                return False
            
            loss_percentage = abs(position.pnl_percentage)
            return loss_percentage >= (self.config.stop_loss_threshold * 100)
            
        except Exception as e:
            logger.error(f"检查止损失败: {e}")
            return False
    
    def _check_take_profit(self, position: PositionInfo) -> bool:
        """检查止盈"""
        try:
            if position.unrealized_pnl <= 0:
                return False
            
            profit_percentage = position.pnl_percentage
            return profit_percentage >= (self.config.take_profit_threshold * 100)
            
        except Exception as e:
            logger.error(f"检查止盈失败: {e}")
            return False
    
    def _check_trailing_stop(self, position: PositionInfo, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查移动止盈"""
        try:
            if not self.config.enable_trailing_stop:
                return {'should_close': False, 'reason': ''}
            
            if position.unrealized_pnl <= 0:
                return {'should_close': False, 'reason': ''}
            
            # 计算回撤百分比
            max_favorable = self._calculate_max_favorable_excursion(position)
            current_retracement = max_favorable - (position.unrealized_pnl / (position.size * position.entry_price))
            
            if current_retracement >= self.config.trailing_stop_distance:
                return {
                    'should_close': True,
                    'reason': f"移动止盈触发: 回撤 {current_retracement:.3f} >= 阈值 {self.config.trailing_stop_distance:.3f}"
                }
            
            return {'should_close': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"检查移动止盈失败: {e}")
            return {'should_close': False, 'reason': ''}
    
    def _check_time_stop(self, position: PositionInfo) -> bool:
        """检查时间止损"""
        try:
            time_in_position = (datetime.now() - position.timestamp).total_seconds() / 3600  # 小时
            
            # 默认24小时为时间限制
            max_holding_time = 24
            
            return time_in_position >= max_holding_time
            
        except Exception as e:
            logger.error(f"检查时间止损失败: {e}")
            return False
    
    def _check_risk_level(self, position: PositionInfo, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查风险水平"""
        try:
            # 获取市场波动率
            technical_data = market_data.get('technical_data', {})
            atr_pct = technical_data.get('atr_pct', 2.0)
            
            # 高波动环境下的风险控制
            if atr_pct > 5.0 and position.leverage > 10:
                return {
                    'should_close': True,
                    'reason': f"高波动环境风险控制: ATR {atr_pct:.2f}% > 5%, 杠杆 {position.leverage}x"
                }
            
            return {'should_close': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"检查风险水平失败: {e}")
            return {'should_close': False, 'reason': ''}
    
    def _determine_urgency(self, close_signals: List[str]) -> str:
        """确定紧急程度"""
        try:
            urgency_levels = {
                'stop_loss': 'high',
                'risk_limit': 'high',
                'take_profit': 'medium',
                'trailing_stop': 'medium',
                'time_stop': 'low'
            }
            
            if not close_signals:
                return 'low'
            
            # 找到最高紧急程度
            max_urgency = 'low'
            for signal in close_signals:
                if signal in urgency_levels:
                    urgency = urgency_levels[signal]
                    if urgency == 'high' or (urgency == 'medium' and max_urgency == 'low'):
                        max_urgency = urgency
            
            return max_urgency
            
        except Exception as e:
            logger.error(f"确定紧急程度失败: {e}")
            return 'low'
    
    def calculate_optimal_position_size(self, account_balance: float, risk_per_trade: float,
                                      entry_price: float, stop_loss_price: float) -> float:
        """计算最优仓位大小"""
        try:
            # 基于凯利公式的仓位大小计算
            if stop_loss_price <= 0 or entry_price <= 0:
                return self.config.min_order_size
            
            # 计算风险金额
            risk_amount = account_balance * risk_per_trade
            
            # 计算每单位的风险
            risk_per_unit = abs(entry_price - stop_loss_price)
            
            # 计算最优仓位大小
            optimal_size = risk_amount / (risk_per_unit * entry_price)
            
            # 应用限制
            optimal_size = max(self.config.min_order_size, 
                             min(optimal_size, self.config.max_position_size))
            
            logger.info(f"📊 最优仓位计算: 余额${account_balance:.2f}, 风险{risk_per_trade:.2%}, "
                       f"入场价${entry_price:.2f}, 止损价${stop_loss_price:.2f} -> 仓位{optimal_size:.6f}")
            
            return optimal_size
            
        except Exception as e:
            logger.error(f"计算最优仓位大小失败: {e}")
            return self.config.min_order_size
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            total_trades = self.performance_metrics['total_trades']
            if total_trades == 0:
                return {
                    'message': '暂无交易记录',
                    'total_trades': 0
                }
            
            win_rate = self.performance_metrics['win_rate']
            profit_factor = self.performance_metrics['profit_factor']
            total_pnl = self.performance_metrics['total_pnl']
            
            return {
                'total_trades': total_trades,
                'winning_trades': self.performance_metrics['winning_trades'],
                'losing_trades': self.performance_metrics['losing_trades'],
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_pnl': total_pnl,
                'average_win': self.performance_metrics['average_win'],
                'average_loss': self.performance_metrics['average_loss'],
                'largest_win': self.performance_metrics['largest_win'],
                'largest_loss': self.performance_metrics['largest_loss'],
                'max_consecutive_wins': self.performance_metrics['max_consecutive_wins'],
                'max_consecutive_losses': self.performance_metrics['max_consecutive_losses'],
                'current_streak': self.performance_metrics['current_streak'],
                'max_drawdown': self.performance_metrics['max_drawdown'],
                'sharpe_ratio': self._calculate_sharpe_ratio(),
                'performance_grade': self._calculate_performance_grade()
            }
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {'error': str(e)}
    
    def _calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        try:
            # 简化计算：基于总盈亏和交易次数
            if self.performance_metrics['total_trades'] == 0:
                return 0.0
            
            total_return = self.performance_metrics['total_pnl']
            trade_count = self.performance_metrics['total_trades']
            
            # 假设无风险利率为2%
            risk_free_rate = 0.02
            excess_return = total_return - (risk_free_rate * trade_count / 365)
            
            # 计算波动率 (简化)
            if self.performance_metrics['average_loss'] > 0:
                volatility = (self.performance_metrics['average_win'] + self.performance_metrics['average_loss']) / 2
            else:
                volatility = self.performance_metrics['average_win']
            
            if volatility > 0:
                sharpe_ratio = excess_return / volatility
                return sharpe_ratio
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算夏普比率失败: {e}")
            return 0.0
    
    def _calculate_performance_grade(self) -> str:
        """计算性能等级"""
        try:
            win_rate = self.performance_metrics['win_rate']
            profit_factor = self.performance_metrics['profit_factor']
            
            # 综合评分
            score = (win_rate * 0.6 + min(profit_factor / 2.0, 1.0) * 0.4) * 100
            
            if score >= 80:
                return 'A+ (优秀)'
            elif score >= 70:
                return 'A (良好)'
            elif score >= 60:
                return 'B (中等)'
            elif score >= 50:
                return 'C (及格)'
            else:
                return 'D (需要改进)'
                
        except Exception as e:
            logger.error(f"计算性能等级失败: {e}")
            return 'F (评估失败)'
    
    def export_position_data(self, format: str = 'json') -> str:
        """导出仓位数据"""
        try:
            if format == 'json':
                import json
                return json.dumps({
                    'current_positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
                    'position_history': [pos.to_dict() for pos in self.position_history[-100:]],  # 最近100条
                    'performance_summary': self.get_performance_summary(),
                    'config': self.config.to_dict()
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出仓位数据失败: {e}")
            return f"导出失败: {e}"

# 全局仓位管理器实例
position_manager = PositionManager()
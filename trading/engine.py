"""
交易引擎主模块
整合所有交易组件，提供统一的交易接口
"""

import asyncio
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

from core.base import BaseComponent, BaseConfig
from core.exceptions import TradingError
from .exchange import ExchangeManager, ExchangeConfig
from .order_manager import OrderManager, OrderConfig
from .position import PositionManager, PositionConfig
from .risk_assessment import MultiDimensionalRiskAssessment, RiskConfig
from .execution import TradeExecutor, TradeConfig
from .models import TradeResult, PositionInfo

logger = logging.getLogger(__name__)

class TradingEngineConfig(BaseConfig):
    """交易引擎配置"""

    def __init__(self, **kwargs):
        # 提取交易引擎特有的参数
        self.enable_trading = kwargs.pop('enable_trading', True)
        self.test_mode = kwargs.pop('test_mode', False)
        self.max_daily_trades = kwargs.pop('max_daily_trades', 50)
        self.enable_auto_close = kwargs.pop('enable_auto_close', True)
        self.trading_hours_only = kwargs.pop('trading_hours_only', False)

        # 调用父类构造函数，只传递父类支持的参数
        super().__init__(name="TradingEngine", **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - 重写以包含自定义字段"""
        base_dict = super().to_dict()
        base_dict.update({
            'enable_trading': self.enable_trading,
            'test_mode': self.test_mode,
            'max_daily_trades': self.max_daily_trades,
            'enable_auto_close': self.enable_auto_close,
            'trading_hours_only': self.trading_hours_only
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingEngineConfig':
        """从字典创建实例 - 重写以支持自定义字段"""
        return cls(
            enable_trading=data.get('enable_trading', True),
            test_mode=data.get('test_mode', False),
            max_daily_trades=data.get('max_daily_trades', 50),
            enable_auto_close=data.get('enable_auto_close', True),
            trading_hours_only=data.get('trading_hours_only', False),
            # 父类字段
            name=data.get('name', 'TradingEngine'),
            enabled=data.get('enabled', True),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1)
        )

class TradingEngine(BaseComponent):
    """交易引擎主类"""
    
    def __init__(self, config: Optional[TradingEngineConfig] = None):
        super().__init__(config or TradingEngineConfig())
        self.config = config or TradingEngineConfig()
        
        # 初始化子组件
        self.exchange_config = ExchangeConfig()
        self.order_config = OrderConfig()
        self.position_config = PositionConfig()
        self.risk_config = RiskConfig()
        self.trade_config = TradeConfig()
        
        # 创建组件实例
        self.exchange_manager = ExchangeManager(self.exchange_config)
        self.order_manager = OrderManager(self.exchange_manager, self.order_config)
        self.position_manager = PositionManager(self.position_config)
        self.risk_assessment = MultiDimensionalRiskAssessment(self.risk_config)
        self.trade_executor = TradeExecutor(
            self.exchange_manager, 
            self.order_manager, 
            self.position_manager, 
            self.risk_assessment,
            self.trade_config
        )
        
        # 状态管理
        self.is_trading_active = False
        self.daily_trade_count = 0
        self.last_trade_time = None
        self.engine_stats: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """初始化交易引擎"""
        try:
            logger.info("🚀 交易引擎初始化...")
            
            # 初始化所有子组件
            components = [
                (self.exchange_manager, "交易所管理器"),
                (self.order_manager, "订单管理器"),
                (self.position_manager, "仓位管理器"),
                (self.risk_assessment, "风险评估"),
                (self.trade_executor, "交易执行器")
            ]
            
            for component, name in components:
                logger.info(f"🔄 初始化 {name}...")
                success = await component.initialize()
                if not success:
                    raise TradingError(f"{name}初始化失败")
            
            # 初始化统计信息
            self._initialize_stats()
            
            # 设置交易状态
            self.is_trading_active = self.config.enable_trading
            
            logger.info("✅ 交易引擎初始化完成")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"交易引擎初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理交易引擎"""
        try:
            logger.info("🛑 交易引擎清理中...")
            
            # 停止交易
            self.is_trading_active = False
            
            # 清理所有子组件
            components = [
                self.trade_executor,
                self.risk_assessment,
                self.position_manager,
                self.order_manager,
                self.exchange_manager
            ]
            
            for component in components:
                try:
                    await component.cleanup()
                except Exception as e:
                    logger.error(f"组件清理失败: {e}")
            
            # 重置统计
            self._reset_stats()
            
            logger.info("✅ 交易引擎清理完成")
            self._initialized = False
            
        except Exception as e:
            logger.error(f"交易引擎清理失败: {e}")
    
    def _initialize_stats(self) -> None:
        """初始化统计信息"""
        self.engine_stats = {
            'start_time': datetime.now(),
            'total_signals_processed': 0,
            'total_trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'total_pnl': 0.0,
            'average_trade_size': 0.0,
            'largest_trade': 0.0,
            'smallest_trade': float('inf'),
            'best_trade_pnl': 0.0,
            'worst_trade_pnl': 0.0,
            'current_streak': 0,
            'max_winning_streak': 0,
            'max_losing_streak': 0
        }
    
    def _reset_stats(self) -> None:
        """重置统计信息"""
        self.daily_trade_count = 0
        self.last_trade_time = None
        self.engine_stats.clear()
    
    async def process_signal(self, signal_data: Dict[str, Any], market_data: Dict[str, Any],
                           portfolio_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理交易信号"""
        try:
            logger.info(f"📡 收到交易信号: {signal_data.get('signal', 'UNKNOWN')}")
            
            # 更新统计
            self.engine_stats['total_signals_processed'] += 1
            
            # 1. 验证信号
            if not self._validate_signal(signal_data):
                return {
                    'success': False,
                    'error': '信号验证失败',
                    'signal': signal_data
                }
            
            # 2. 检查交易状态
            if not self._can_trade():
                return {
                    'success': False,
                    'error': '当前无法交易',
                    'signal': signal_data
                }
            
            # 3. 检查每日交易限制
            if self.daily_trade_count >= self.config.max_daily_trades:
                logger.warning(f"⚠️ 达到每日交易限制: {self.config.max_daily_trades}")
                return {
                    'success': False,
                    'error': '达到每日交易限制',
                    'signal': signal_data
                }
            
            # 4. 执行交易
            trade_result = await self.trade_executor.execute_trade(
                signal_data, market_data, portfolio_data
            )
            
            # 5. 更新统计和状态
            self._update_after_trade(trade_result)
            
            # 6. 自动平仓检查（如果启用）
            if self.config.enable_auto_close and trade_result.success:
                await self._check_auto_close_conditions(trade_result)
            
            logger.info(f"✅ 信号处理完成: {trade_result.signal} -> {'成功' if trade_result.success else '失败'}")
            
            return {
                'success': trade_result.success,
                'trade_result': trade_result.to_dict(),
                'daily_trade_count': self.daily_trade_count,
                'remaining_trades': self.config.max_daily_trades - self.daily_trade_count
            }
            
        except Exception as e:
            logger.error(f"信号处理失败: {e}")
            return {
                'success': False,
                'error': f"信号处理异常: {e}",
                'signal': signal_data
            }
    
    def _validate_signal(self, signal_data: Dict[str, Any]) -> bool:
        """验证交易信号"""
        try:
            # 检查必需字段
            required_fields = ['signal', 'confidence']
            for field in required_fields:
                if field not in signal_data:
                    logger.error(f"❌ 信号缺少必需字段: {field}")
                    return False
            
            # 验证信号类型
            signal = signal_data['signal']
            if signal not in ['BUY', 'SELL', 'HOLD']:
                logger.error(f"❌ 无效的信号类型: {signal}")
                return False
            
            # 验证信心值
            confidence = signal_data['confidence']
            if not (0 <= confidence <= 1):
                logger.error(f"❌ 无效的信心值: {confidence}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"信号验证失败: {e}")
            return False
    
    def _can_trade(self) -> bool:
        """检查是否可以交易"""
        try:
            # 检查交易引擎状态
            if not self.is_trading_active:
                logger.warning("⚠️ 交易引擎未激活")
                return False
            
            # 检查初始化状态
            if not self._initialized:
                logger.error("❌ 交易引擎未初始化")
                return False
            
            # 检查测试模式
            if self.config.test_mode:
                logger.info("🧪 测试模式：允许交易")
                return True
            
            # 检查交易时间（简化处理）
            if self.config.trading_hours_only:
                current_hour = datetime.now().hour
                if current_hour < 9 or current_hour > 17:  # 假设交易时间 9:00-17:00
                    logger.info("⏰ 非交易时间")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查交易权限失败: {e}")
            return False
    
    def _update_after_trade(self, trade_result: TradeResult) -> None:
        """交易后更新状态"""
        try:
            if trade_result.success:
                # 更新每日交易计数
                self.daily_trade_count += 1
                self.last_trade_time = datetime.now()
                
                # 更新引擎统计
                self.engine_stats['total_trades_executed'] += 1
                self.engine_stats['successful_trades'] += 1
                self.engine_stats['total_volume'] += trade_result.amount
                self.engine_stats['total_fees'] += trade_result.fees
                self.engine_stats['total_pnl'] += trade_result.pnl
                
                # 更新连胜/连败记录
                if trade_result.pnl > 0:
                    if self.engine_stats['current_streak'] >= 0:
                        self.engine_stats['current_streak'] += 1
                    else:
                        self.engine_stats['current_streak'] = 1
                    self.engine_stats['max_winning_streak'] = max(
                        self.engine_stats['max_winning_streak'],
                        self.engine_stats['current_streak']
                    )
                else:
                    if self.engine_stats['current_streak'] <= 0:
                        self.engine_stats['current_streak'] -= 1
                    else:
                        self.engine_stats['current_streak'] = -1
                    self.engine_stats['max_losing_streak'] = max(
                        self.engine_stats['max_losing_streak'],
                        abs(self.engine_stats['current_streak'])
                    )
                
                # 更新交易大小统计
                self.engine_stats['largest_trade'] = max(
                    self.engine_stats['largest_trade'], trade_result.amount
                )
                self.engine_stats['smallest_trade'] = min(
                    self.engine_stats['smallest_trade'], trade_result.amount
                )
                
                # 更新盈亏统计
                self.engine_stats['best_trade_pnl'] = max(
                    self.engine_stats['best_trade_pnl'], trade_result.pnl
                )
                self.engine_stats['worst_trade_pnl'] = min(
                    self.engine_stats['worst_trade_pnl'], trade_result.pnl
                )
                
            else:
                # 失败交易统计
                self.engine_stats['failed_trades'] += 1
                
                # 重置连胜/连败
                self.engine_stats['current_streak'] = 0
            
            # 更新平均交易大小
            if self.engine_stats['total_trades_executed'] > 0:
                self.engine_stats['average_trade_size'] = (
                    self.engine_stats['total_volume'] / self.engine_stats['total_trades_executed']
                )
            
        except Exception as e:
            logger.error(f"交易后状态更新失败: {e}")
    
    async def _check_auto_close_conditions(self, trade_result: TradeResult) -> None:
        """检查自动平仓条件"""
        try:
            # 获取当前持仓
            current_position = self.position_manager.get_current_position()
            if not current_position:
                return
            
            # 检查是否应该平仓
            close_decision = self.position_manager.should_close_position(current_position, {})
            
            if close_decision['should_close']:
                logger.info(f"🔄 自动平仓条件满足: {close_decision['reasons']}")
                
                # 执行平仓
                close_result = await self.close_position(current_position)
                
                if close_result.success:
                    logger.info(f"✅ 自动平仓成功: 盈亏 ${close_result.pnl:.2f}")
                else:
                    logger.error(f"❌ 自动平仓失败: {close_result.error_message}")
                    
        except Exception as e:
            logger.error(f"自动平仓检查失败: {e}")
    
    async def close_position(self, position: PositionInfo, close_type: str = 'market') -> TradeResult:
        """平仓"""
        try:
            return await self.trade_executor.close_position(position, close_type)
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
                error_message=f"平仓失败: {e}"
            )
    
    async def get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        try:
            # 从交易所获取实时数据
            return await self.exchange_manager.get_market_data()
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return {'error': str(e)}
    
    def get_position_info(self) -> Dict[str, Any]:
        """获取持仓信息"""
        try:
            return self.position_manager.get_position_summary()
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            return {'error': str(e)}
    
    def get_risk_status(self) -> Dict[str, Any]:
        """获取风险状态"""
        try:
            # 获取最新风险评估
            if self.risk_assessment.risk_history:
                latest_risk = self.risk_assessment.risk_history[-1]
                return {
                    'current_risk_score': latest_risk.overall_risk_score,
                    'risk_level': latest_risk.risk_level,
                    'confidence': latest_risk.confidence_score,
                    'recommendations': latest_risk.recommendations[:3]  # 前3条建议
                }
            else:
                return {
                    'current_risk_score': 50.0,
                    'risk_level': 'medium',
                    'confidence': 0.5,
                    'recommendations': ['暂无风险评估数据']
                }
        except Exception as e:
            logger.error(f"获取风险状态失败: {e}")
            return {'error': str(e)}
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        try:
            uptime = (datetime.now() - self.engine_stats['start_time']).total_seconds() / 3600  # 小时
            
            return {
                'is_active': self.is_trading_active,
                'is_initialized': self._initialized,
                'uptime_hours': uptime,
                'daily_trade_count': self.daily_trade_count,
                'max_daily_trades': self.config.max_daily_trades,
                'remaining_trades': self.config.max_daily_trades - self.daily_trade_count,
                'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
                'test_mode': self.config.test_mode,
                'components_status': self._get_components_status()
            }
        except Exception as e:
            logger.error(f"获取引擎状态失败: {e}")
            return {'error': str(e)}
    
    def _get_components_status(self) -> Dict[str, Any]:
        """获取组件状态"""
        try:
            components = {
                'exchange_manager': self.exchange_manager.is_initialized(),
                'order_manager': self.order_manager.is_initialized(),
                'position_manager': self.position_manager.is_initialized(),
                'risk_assessment': self.risk_assessment.is_initialized(),
                'trade_executor': self.trade_executor.is_initialized()
            }
            
            all_ready = all(components.values())
            components['all_ready'] = all_ready
            
            return components
        except Exception as e:
            logger.error(f"获取组件状态失败: {e}")
            return {'error': str(e)}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            # 合并引擎统计和交易执行统计
            engine_summary = {
                'total_signals_processed': self.engine_stats['total_signals_processed'],
                'total_trades_executed': self.engine_stats['total_trades_executed'],
                'successful_trades': self.engine_stats['successful_trades'],
                'failed_trades': self.engine_stats['failed_trades'],
                'total_volume': self.engine_stats['total_volume'],
                'total_pnl': self.engine_stats['total_pnl'],
                'win_rate': (self.engine_stats['successful_trades'] / self.engine_stats['total_trades_executed']) if self.engine_stats['total_trades_executed'] > 0 else 0,
                'current_streak': self.engine_stats['current_streak'],
                'max_winning_streak': self.engine_stats['max_winning_streak'],
                'max_losing_streak': self.engine_stats['max_losing_streak'],
                'best_trade_pnl': self.engine_stats['best_trade_pnl'],
                'worst_trade_pnl': self.engine_stats['worst_trade_pnl'],
                'average_trade_size': self.engine_stats['average_trade_size'],
                'largest_trade': self.engine_stats['largest_trade'],
                'smallest_trade': self.engine_stats['smallest_trade']
            }

            # 添加交易执行统计
            execution_summary = self.trade_executor.get_execution_summary()

            return {
                'engine_performance': engine_summary,
                'execution_performance': execution_summary,
                'uptime_hours': (datetime.now() - self.engine_stats['start_time']).total_seconds() / 3600,
                'performance_grade': self._calculate_overall_performance_grade(engine_summary)
            }

        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {'error': str(e)}

    async def get_price_history(self, timeframe: str = '15m', limit: int = 100) -> List[Dict[str, Any]]:
        """获取历史价格数据"""
        try:
            logger.info(f"📊 开始获取历史价格数据: {timeframe}, 限制: {limit}")
            logger.info(f"   交易所管理器初始化状态: {self.exchange_manager._initialized}")
            logger.info(f"   模拟模式状态: {self.exchange_manager._is_mock_mode}")

            # 如果处于模拟模式，直接调用同步版本的方法
            if self.exchange_manager._is_mock_mode:
                logger.info("   模拟模式：直接生成模拟数据")
                import random
                import time

                # 使用与exchange.py中相同的模拟数据生成逻辑
                current_time = int(time.time())
                random.seed(current_time // 3600)
                base_price = random.randint(95000, 105000)

                formatted_data = []
                current_timestamp = int(time.time() * 1000)

                for i in range(limit):
                    time_offset = i * 0.001
                    price_noise = random.randint(-2000, 2000) + int(time_offset * 100)

                    open_price = base_price + price_noise
                    close_price = open_price + random.randint(-1500, 1500)
                    high_price = max(open_price, close_price) + random.randint(100, 800)
                    low_price = min(open_price, close_price) - random.randint(100, 800)
                    volume = random.randint(5000, 15000)

                    formatted_data.append({
                        'timestamp': current_timestamp - i * 60000 * 15,  # 15分钟间隔
                        'open': float(open_price),
                        'high': float(high_price),
                        'low': float(low_price),
                        'close': float(close_price),
                        'volume': float(volume)
                    })

                # 反转顺序，使最新数据在前
                formatted_data.reverse()
                logger.info(f"   模拟数据生成完成: {len(formatted_data)} 条")
                return formatted_data

            # 非模拟模式，直接调用异步方法
            try:
                result = await self.exchange_manager.fetch_ohlcv(timeframe, limit)
                logger.info(f"   成功获取数据: {len(result)} 条")
                return result
            except Exception as e:
                logger.error(f"获取历史价格数据失败: {e}")
                logger.error(f"错误详情 - 时间框架: {timeframe}, 限制: {limit}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                return []
        except Exception as e:
            logger.error(f"获取历史价格数据失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return []

    def _calculate_overall_performance_grade(self, summary: Dict[str, Any]) -> str:
        """计算整体性能等级"""
        try:
            # 综合评分算法
            win_rate = summary.get('win_rate', 0)
            total_pnl = summary.get('total_pnl', 0)
            avg_trade_size = summary.get('average_trade_size', 0)
            
            # 基础评分 (0-100)
            base_score = 50  # 基础分
            
            # 胜率加分 (0-30分)
            win_rate_score = win_rate * 30
            
            # 盈亏加分/减分 (-20到+20分)
            if total_pnl > 0:
                pnl_score = min(20, total_pnl / 100)  # 每100美元盈利加1分，最多20分
            else:
                pnl_score = max(-20, total_pnl / 50)  # 每50美元亏损减1分，最多-20分
            
            # 交易规模加分 (0-10分)
            size_score = min(10, avg_trade_size * 1000)  # 根据交易规模调整
            
            total_score = base_score + win_rate_score + pnl_score + size_score
            
            # 转换为等级
            if total_score >= 90:
                return 'A+ (卓越)'
            elif total_score >= 80:
                return 'A (优秀)'
            elif total_score >= 70:
                return 'B+ (良好)'
            elif total_score >= 60:
                return 'B (中等)'
            elif total_score >= 50:
                return 'C (及格)'
            else:
                return 'D (需要改进)'
                
        except Exception as e:
            logger.error(f"计算整体性能等级失败: {e}")
            return 'F (评估失败)'
    
    def reset_daily_stats(self) -> None:
        """重置每日统计"""
        try:
            self.daily_trade_count = 0
            self.last_trade_time = None
            
            # 重置引擎统计中的日相关数据
            daily_fields = ['total_trades_executed', 'successful_trades', 'failed_trades']
            for field in daily_fields:
                if field in self.engine_stats:
                    self.engine_stats[field] = 0
            
            logger.info("🔄 每日统计已重置")
            
        except Exception as e:
            logger.error(f"重置每日统计失败: {e}")
    
    def export_performance_data(self, format: str = 'json') -> str:
        """导出性能数据"""
        try:
            if format == 'json':
                import json
                return json.dumps({
                    'engine_stats': self.engine_stats,
                    'performance_summary': self.get_performance_summary(),
                    'engine_status': self.get_engine_status(),
                    'config': self.config.to_dict()
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出性能数据失败: {e}")
            return f"导出失败: {e}"

# 全局交易引擎实例
trading_engine = TradingEngine()
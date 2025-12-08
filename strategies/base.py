"""
策略基类模块
提供策略系统的统一接口和基础功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig, SignalData, MarketData
from core.exceptions import StrategyError

logger = logging.getLogger(__name__)

@dataclass
class StrategySignal:
    """策略信号"""
    signal: str  # BUY, SELL, HOLD
    confidence: float
    reason: str
    strategy_name: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal': self.signal,
            'confidence': self.confidence,
            'reason': self.reason,
            'strategy_name': self.strategy_name,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }

@dataclass
class StrategyConfig(BaseConfig):
    """策略配置"""
    strategy_type: str = "base"
    risk_level: str = "medium"  # low, medium, high
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    start_date: datetime
    end_date: datetime
    equity_curve: List[float]
    daily_returns: List[float]
    trade_history: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_trade_duration': self.avg_trade_duration,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'equity_curve': self.equity_curve,
            'daily_returns': self.daily_returns,
            'trade_history': self.trade_history
        }

class BaseStrategy(BaseComponent):
    """策略基类"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.config = config
        self.strategy_type = config.strategy_type
        self.risk_level = config.risk_level
        self.parameters = config.parameters
        self.is_enabled = config.enabled
    
    @abstractmethod
    async def generate_signal(self, market_data: MarketData, **kwargs) -> StrategySignal:
        """生成交易信号"""
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """获取所需的技术指标"""
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """验证策略参数"""
        pass
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': self.config.name,
            'strategy_type': self.strategy_type,
            'risk_level': self.risk_level,
            'enabled': self.is_enabled,
            'parameters': self.parameters,
            'required_indicators': self.get_required_indicators()
        }
    
    def update_parameters(self, parameters: Dict[str, Any]) -> bool:
        """更新策略参数"""
        try:
            self.parameters.update(parameters)
            return self.validate_parameters()
        except Exception as e:
            logger.error(f"更新策略参数失败: {e}")
            return False
    
    def get_risk_adjustment(self) -> float:
        """获取风险调整因子"""
        risk_multipliers = {
            'low': 0.7,
            'medium': 1.0,
            'high': 1.3
        }
        return risk_multipliers.get(self.risk_level, 1.0)

class ConservativeStrategy(BaseStrategy):
    """保守型策略"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        if config is None:
            config = StrategyConfig(
                name="ConservativeStrategy",
                strategy_type="conservative",
                risk_level="low",
                parameters={
                    'rsi_buy_threshold': 30,
                    'rsi_sell_threshold': 70,
                    'ma_period_short': 20,
                    'ma_period_long': 50,
                    'min_confidence': 0.7,
                    'max_position_size': 0.4
                }
            )
        super().__init__(config)
    
    async def generate_signal(self, market_data: MarketData, **kwargs) -> StrategySignal:
        """生成保守型交易信号"""
        try:
            # 获取技术指标
            technical_data = kwargs.get('technical_data', {})
            rsi = technical_data.get('rsi', 50)
            ma_short = technical_data.get('ma_short', market_data.price)
            ma_long = technical_data.get('ma_long', market_data.price)
            
            # 保守的信号生成逻辑
            signal = 'HOLD'
            confidence = 0.5
            reason = ''
            
            # RSI信号
            if rsi < self.parameters['rsi_buy_threshold']:
                signal = 'BUY'
                confidence = 0.8
                reason = f"RSI超卖({rsi:.1f})，保守买入信号"
            elif rsi > self.parameters['rsi_sell_threshold']:
                signal = 'SELL'
                confidence = 0.8
                reason = f"RSI超买({rsi:.1f})，保守卖出信号"
            
            # 均线确认
            if signal == 'BUY' and ma_short > ma_long:
                confidence = min(confidence * 1.1, 0.9)
                reason += "，均线多头排列确认"
            elif signal == 'SELL' and ma_short < ma_long:
                confidence = min(confidence * 1.1, 0.9)
                reason += "，均线空头排列确认"
            
            # 保守策略倾向于HOLD
            if signal != 'HOLD' and confidence < self.parameters['min_confidence']:
                signal = 'HOLD'
                reason = "信号信心不足，保持观望"
            
            return StrategySignal(
                signal=signal,
                confidence=confidence,
                reason=reason,
                strategy_name=self.config.name,
                timestamp=datetime.now(),
                metadata={
                    'rsi': rsi,
                    'ma_short': ma_short,
                    'ma_long': ma_long
                }
            )
            
        except Exception as e:
            logger.error(f"保守策略信号生成失败: {e}")
            raise StrategyError(f"保守策略信号生成失败: {e}", strategy_type=self.strategy_type)
    
    def get_required_indicators(self) -> List[str]:
        return ['rsi', 'ma_short', 'ma_long']
    
    def validate_parameters(self) -> bool:
        """验证保守策略参数"""
        required_params = ['rsi_buy_threshold', 'rsi_sell_threshold', 'ma_period_short', 'ma_period_long']
        for param in required_params:
            if param not in self.parameters:
                return False

        # 验证参数合理性
        if not (0 < self.parameters['rsi_buy_threshold'] < 50):
            return False
        if not (50 < self.parameters['rsi_sell_threshold'] < 100):
            return False
        if self.parameters['ma_period_short'] >= self.parameters['ma_period_long']:
            return False

        return True

    async def initialize(self) -> bool:
        """初始化策略"""
        try:
            self._initialized = True
            logger.info(f"保守策略初始化成功: {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"保守策略初始化失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理策略资源"""
        try:
            self._initialized = False
            logger.info(f"保守策略清理完成: {self.config.name}")
        except Exception as e:
            logger.error(f"保守策略清理失败: {e}")

class ModerateStrategy(BaseStrategy):
    """中等风险策略"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        if config is None:
            config = StrategyConfig(
                name="ModerateStrategy",
                strategy_type="moderate",
                risk_level="medium",
                parameters={
                    'rsi_buy_threshold': 35,
                    'rsi_sell_threshold': 65,
                    'macd_signal_threshold': 0.1,
                    'trend_confirmation': True,
                    'min_confidence': 0.6,
                    'max_position_size': 0.6
                }
            )
        super().__init__(config)
    
    async def generate_signal(self, market_data: MarketData, **kwargs) -> StrategySignal:
        """生成中等风险交易信号"""
        try:
            technical_data = kwargs.get('technical_data', {})
            rsi = technical_data.get('rsi', 50)
            macd = technical_data.get('macd', {})
            trend = kwargs.get('trend', 'neutral')
            
            # 多因子信号生成
            buy_signals = 0
            sell_signals = 0
            confidence_factors = []
            
            # RSI信号
            if rsi < self.parameters['rsi_buy_threshold']:
                buy_signals += 1
                confidence_factors.append(0.7)
            elif rsi > self.parameters['rsi_sell_threshold']:
                sell_signals += 1
                confidence_factors.append(0.7)
            
            # MACD信号
            if macd and isinstance(macd, dict):
                macd_line = macd.get('macd', 0)
                signal_line = macd.get('signal', 0)
                if macd_line > signal_line and abs(macd_line - signal_line) > self.parameters['macd_signal_threshold']:
                    buy_signals += 1
                    confidence_factors.append(0.8)
                elif macd_line < signal_line and abs(macd_line - signal_line) > self.parameters['macd_signal_threshold']:
                    sell_signals += 1
                    confidence_factors.append(0.8)
            
            # 趋势确认
            if self.parameters['trend_confirmation']:
                if 'bullish' in str(trend).lower():
                    buy_signals += 0.5
                elif 'bearish' in str(trend).lower():
                    sell_signals += 0.5
            
            # 确定最终信号
            if buy_signals > sell_signals:
                signal = 'BUY'
                confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.6
                reason = f"多因子买入信号: RSI({rsi:.1f}) + MACD + 趋势"
            elif sell_signals > buy_signals:
                signal = 'SELL'
                confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.6
                reason = f"多因子卖出信号: RSI({rsi:.1f}) + MACD + 趋势"
            else:
                signal = 'HOLD'
                confidence = 0.5
                reason = "多空信号平衡，建议观望"
            
            return StrategySignal(
                signal=signal,
                confidence=confidence,
                reason=reason,
                strategy_name=self.config.name,
                timestamp=datetime.now(),
                metadata={
                    'rsi': rsi,
                    'macd': macd,
                    'trend': trend,
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals
                }
            )
            
        except Exception as e:
            logger.error(f"中等策略信号生成失败: {e}")
            raise StrategyError(f"中等策略信号生成失败: {e}", strategy_type=self.strategy_type)
    
    def get_required_indicators(self) -> List[str]:
        return ['rsi', 'macd', 'trend']
    
    def validate_parameters(self) -> bool:
        """验证中等策略参数"""
        required_params = ['rsi_buy_threshold', 'rsi_sell_threshold', 'macd_signal_threshold']
        for param in required_params:
            if param not in self.parameters:
                return False
        
        if not (0 < self.parameters['rsi_buy_threshold'] < 50):
            return False
        if not (50 < self.parameters['rsi_sell_threshold'] < 100):
            return False
        if self.parameters['macd_signal_threshold'] <= 0:
            return False

        return True

    async def initialize(self) -> bool:
        """初始化策略"""
        try:
            self._initialized = True
            logger.info(f"中等策略初始化成功: {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"中等策略初始化失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理策略资源"""
        try:
            self._initialized = False
            logger.info(f"中等策略清理完成: {self.config.name}")
        except Exception as e:
            logger.error(f"中等策略清理失败: {e}")

class AggressiveStrategy(BaseStrategy):
    """激进型策略"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        if config is None:
            config = StrategyConfig(
                name="AggressiveStrategy",
                strategy_type="aggressive",
                risk_level="high",
                parameters={
                    'rsi_buy_threshold': 40,
                    'rsi_sell_threshold': 60,
                    'momentum_threshold': 0.02,
                    'volatility_filter': 0.015,
                    'quick_exit': True,
                    'min_confidence': 0.5,
                    'max_position_size': 0.8
                }
            )
        super().__init__(config)
    
    async def generate_signal(self, market_data: MarketData, **kwargs) -> StrategySignal:
        """生成激进型交易信号"""
        try:
            technical_data = kwargs.get('technical_data', {})
            rsi = technical_data.get('rsi', 50)
            momentum = technical_data.get('momentum', 0)
            volatility = technical_data.get('volatility', 0)
            
            # 激进策略倾向于频繁交易
            signal = 'HOLD'
            confidence = 0.5
            reason = ''
            
            # 降低交易门槛
            if rsi < self.parameters['rsi_buy_threshold'] and momentum > self.parameters['momentum_threshold']:
                signal = 'BUY'
                confidence = 0.7
                reason = f"激进买入: RSI({rsi:.1f}) + 动量({momentum:.3f})"
            elif rsi > self.parameters['rsi_sell_threshold'] and momentum < -self.parameters['momentum_threshold']:
                signal = 'SELL'
                confidence = 0.7
                reason = f"激进卖出: RSI({rsi:.1f}) + 动量({momentum:.3f})"
            
            # 波动性过滤
            if volatility > self.parameters['volatility_filter']:
                confidence *= 0.9
                reason += " (高波动环境降低仓位)"
            
            # 快速退出机制
            if self.parameters['quick_exit'] and signal != 'HOLD':
                confidence = min(confidence * 1.2, 0.85)
                reason += " + 快速退出机制"
            
            return StrategySignal(
                signal=signal,
                confidence=confidence,
                reason=reason,
                strategy_name=self.config.name,
                timestamp=datetime.now(),
                metadata={
                    'rsi': rsi,
                    'momentum': momentum,
                    'volatility': volatility,
                    'aggressive_multiplier': 1.2
                }
            )
            
        except Exception as e:
            logger.error(f"激进策略信号生成失败: {e}")
            raise StrategyError(f"激进策略信号生成失败: {e}", strategy_type=self.strategy_type)
    
    def get_required_indicators(self) -> List[str]:
        return ['rsi', 'momentum', 'volatility']
    
    def validate_parameters(self) -> bool:
        """验证激进策略参数"""
        required_params = ['rsi_buy_threshold', 'rsi_sell_threshold', 'momentum_threshold', 'volatility_filter']
        for param in required_params:
            if param not in self.parameters:
                return False
        
        if not (0 < self.parameters['rsi_buy_threshold'] < 50):
            return False
        if not (50 < self.parameters['rsi_sell_threshold'] < 100):
            return False
        if self.parameters['momentum_threshold'] <= 0:
            return False
        if self.parameters['volatility_filter'] <= 0:
            return False
        
        return True

    async def initialize(self) -> bool:
        """初始化策略"""
        try:
            self._initialized = True
            logger.info(f"激进策略初始化成功: {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"激进策略初始化失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理策略资源"""
        try:
            self._initialized = False
            logger.info(f"激进策略清理完成: {self.config.name}")
        except Exception as e:
            logger.error(f"激进策略清理失败: {e}")

class StrategyFactory:
    """策略工厂"""
    
    _strategies = {
        'conservative': ConservativeStrategy,
        'moderate': ModerateStrategy,
        'aggressive': AggressiveStrategy
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: str, config: Optional[StrategyConfig] = None) -> BaseStrategy:
        """创建策略实例"""
        if strategy_type not in cls._strategies:
            raise StrategyError(f"不支持的策略类型: {strategy_type}")
        
        strategy_class = cls._strategies[strategy_type]
        return strategy_class(config)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """获取可用的策略类型"""
        return list(cls._strategies.keys())
    
    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: type):
        """注册新的策略类型"""
        cls._strategies[strategy_type] = strategy_class
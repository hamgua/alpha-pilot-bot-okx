"""
策略选择器模块
根据市场条件、风险偏好等选择最优策略
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import StrategyError
from .base import BaseStrategy, StrategyConfig, StrategyFactory, StrategySignal

logger = logging.getLogger(__name__)

class StrategySelectorConfig(BaseConfig):
    """策略选择器配置"""
    def __init__(self, **kwargs):
        super().__init__(name="StrategySelector", **kwargs)
        self.default_strategy = kwargs.get('default_strategy', 'conservative')
        self.auto_switch = kwargs.get('auto_switch', True)
        self.switch_threshold = kwargs.get('switch_threshold', 0.2)

class StrategySelector(BaseComponent):
    """策略选择器"""
    
    def __init__(self, config: Optional[StrategySelectorConfig] = None):
        super().__init__(config or StrategySelectorConfig())
        self.config = config or StrategySelectorConfig()
        self.current_strategy: Optional[BaseStrategy] = None
        self.strategy_history: List[Dict[str, Any]] = []
        self.performance_cache: Dict[str, float] = {}
        self._initialize_default_strategy()
    
    def _initialize_default_strategy(self):
        """初始化默认策略"""
        try:
            # 优先从环境变量读取
            env_strategy = os.getenv('INVESTMENT_TYPE', '').lower()
            if env_strategy in StrategyFactory.get_available_strategies():
                self.current_strategy = StrategyFactory.create_strategy(env_strategy)
                logger.info(f"✅ 使用环境变量策略: {env_strategy}")
            else:
                # 使用配置文件
                self.current_strategy = StrategyFactory.create_strategy(self.config.default_strategy)
                logger.info(f"✅ 使用默认策略: {self.config.default_strategy}")
                
        except Exception as e:
            logger.error(f"初始化默认策略失败: {e}")
            # 回退到保守策略
            self.current_strategy = StrategyFactory.create_strategy('conservative')
    
    async def initialize(self) -> bool:
        """初始化策略选择器"""
        try:
            logger.info("🎯 策略选择器初始化...")
            
            if self.current_strategy:
                await self.current_strategy.initialize()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"策略选择器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.current_strategy:
                await self.current_strategy.cleanup()
            self._initialized = False
            logger.info("🛑 策略选择器已清理")
        except Exception as e:
            logger.error(f"策略选择器清理失败: {e}")
    
    def get_current_strategy(self) -> Optional[BaseStrategy]:
        """获取当前策略"""
        return self.current_strategy
    
    def get_current_strategy_type(self) -> str:
        """获取当前策略类型"""
        if self.current_strategy:
            return self.current_strategy.strategy_type
        return 'unknown'
    
    async def select_optimal_strategy(self, market_data: Dict[str, Any], 
                                    risk_profile: Optional[Dict[str, Any]] = None) -> BaseStrategy:
        """选择最优策略"""
        try:
            logger.info("🎯 开始选择最优策略...")
            
            # 获取可用策略
            available_strategies = StrategyFactory.get_available_strategies()
            
            # 评估每个策略
            strategy_scores = {}
            for strategy_type in available_strategies:
                try:
                    strategy = StrategyFactory.create_strategy(strategy_type)
                    score = await self._evaluate_strategy(strategy, market_data, risk_profile)
                    strategy_scores[strategy_type] = score
                    logger.info(f"📊 {strategy_type} 策略评分: {score:.3f}")
                except Exception as e:
                    logger.warning(f"⚠️ 评估 {strategy_type} 策略失败: {e}")
                    strategy_scores[strategy_type] = 0.0
            
            # 选择评分最高的策略
            if strategy_scores:
                best_strategy_type = max(strategy_scores, key=strategy_scores.get)
                best_score = strategy_scores[best_strategy_type]
                current_score = strategy_scores.get(self.get_current_strategy_type(), 0.0)
                
                # 决定是否切换策略
                should_switch = self._should_switch_strategy(best_strategy_type, best_score, current_score)
                
                if should_switch and best_strategy_type != self.get_current_strategy_type():
                    await self.switch_strategy(best_strategy_type)
                    logger.info(f"🔄 策略切换完成: {self.get_current_strategy_type()} (评分: {best_score:.3f})")
                else:
                    logger.info(f"✅ 保持当前策略: {self.get_current_strategy_type()}")
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"选择最优策略失败: {e}")
            return self.current_strategy
    
    async def _evaluate_strategy(self, strategy: BaseStrategy, market_data: Dict[str, Any], 
                               risk_profile: Optional[Dict[str, Any]]) -> float:
        """评估策略适用性"""
        try:
            score = 0.0
            
            # 1. 市场条件适配度 (40%)
            market_fit_score = await self._evaluate_market_fit(strategy, market_data)
            score += market_fit_score * 0.4
            
            # 2. 风险偏好匹配度 (30%)
            if risk_profile:
                risk_fit_score = self._evaluate_risk_fit(strategy, risk_profile)
                score += risk_fit_score * 0.3
            else:
                score += 0.3  # 默认满分
            
            # 3. 历史表现 (20%)
            performance_score = self._get_historical_performance(strategy.strategy_type)
            score += performance_score * 0.2
            
            # 4. 策略稳定性 (10%)
            stability_score = self._evaluate_strategy_stability(strategy)
            score += stability_score * 0.1
            
            return score
            
        except Exception as e:
            logger.error(f"评估策略 {strategy.strategy_type} 失败: {e}")
            return 0.0
    
    async def _evaluate_market_fit(self, strategy: BaseStrategy, market_data: Dict[str, Any]) -> float:
        """评估市场条件适配度"""
        try:
            # 获取市场指标
            technical_data = market_data.get('technical_data', {})
            volatility = technical_data.get('volatility', 'normal')
            trend = technical_data.get('trend', 'neutral')
            rsi = technical_data.get('rsi', 50)
            
            strategy_type = strategy.strategy_type
            
            # 基于策略类型的适配规则
            if strategy_type == 'conservative':
                # 保守策略适合低波动、震荡市场
                if volatility == 'low' or (30 <= rsi <= 70):
                    return 0.9
                elif volatility == 'high':
                    return 0.4
                else:
                    return 0.7
                    
            elif strategy_type == 'moderate':
                # 中等策略适合趋势明显的市场
                if trend in ['bullish', 'bearish'] and volatility == 'normal':
                    return 0.9
                elif volatility == 'low':
                    return 0.6
                else:
                    return 0.8
                    
            elif strategy_type == 'aggressive':
                # 激进策略适合高波动、强趋势市场
                if volatility == 'high' and trend in ['bullish', 'bearish']:
                    return 0.9
                elif volatility == 'normal' and trend != 'neutral':
                    return 0.8
                else:
                    return 0.6
                    
            return 0.5
            
        except Exception as e:
            logger.error(f"评估市场适配度失败: {e}")
            return 0.5
    
    def _evaluate_risk_fit(self, strategy: BaseStrategy, risk_profile: Dict[str, Any]) -> float:
        """评估风险偏好匹配度"""
        try:
            user_risk_level = risk_profile.get('risk_level', 'medium')
            strategy_risk_level = strategy.risk_level
            
            # 风险等级匹配
            risk_match_score = {
                ('low', 'conservative'): 1.0,
                ('low', 'moderate'): 0.6,
                ('low', 'aggressive'): 0.2,
                ('medium', 'conservative'): 0.7,
                ('medium', 'moderate'): 1.0,
                ('medium', 'aggressive'): 0.7,
                ('high', 'conservative'): 0.2,
                ('high', 'moderate'): 0.6,
                ('high', 'aggressive'): 1.0
            }
            
            score = risk_match_score.get((user_risk_level, strategy_risk_level), 0.5)
            
            # 考虑其他风险因素
            max_drawdown = risk_profile.get('max_drawdown', 0.1)
            if max_drawdown < 0.05 and strategy_risk_level == 'aggressive':
                score *= 0.5
            elif max_drawdown > 0.2 and strategy_risk_level == 'conservative':
                score *= 0.5
            
            return score
            
        except Exception as e:
            logger.error(f"评估风险偏好匹配度失败: {e}")
            return 0.5
    
    def _get_historical_performance(self, strategy_type: str) -> float:
        """获取历史表现评分"""
        try:
            # 从缓存或默认数据获取
            if strategy_type in self.performance_cache:
                return self.performance_cache[strategy_type]
            
            # 默认历史表现数据
            default_performance = {
                'conservative': 0.7,
                'moderate': 0.8,
                'aggressive': 0.6
            }
            
            return default_performance.get(strategy_type, 0.5)
            
        except Exception as e:
            logger.error(f"获取历史表现失败: {e}")
            return 0.5
    
    def _evaluate_strategy_stability(self, strategy: BaseStrategy) -> float:
        """评估策略稳定性"""
        try:
            # 基于策略参数评估稳定性
            if strategy.strategy_type == 'conservative':
                return 0.9  # 保守策略稳定性高
            elif strategy.strategy_type == 'moderate':
                return 0.8  # 中等策略稳定性中等
            elif strategy.strategy_type == 'aggressive':
                return 0.6  # 激进策略稳定性较低
            else:
                return 0.7
                
        except Exception as e:
            logger.error(f"评估策略稳定性失败: {e}")
            return 0.7
    
    def _should_switch_strategy(self, best_strategy: str, best_score: float, current_score: float) -> bool:
        """判断是否应切换策略"""
        try:
            if not self.config.auto_switch:
                return False
            
            # 评分差距超过阈值才切换
            score_improvement = best_score - current_score
            
            if score_improvement > self.config.switch_threshold:
                logger.info(f"🔄 策略切换条件满足: 评分提升 {score_improvement:.3f} > 阈值 {self.config.switch_threshold}")
                return True
            else:
                logger.info(f"⏭️ 策略切换条件不满足: 评分提升 {score_improvement:.3f} <= 阈值 {self.config.switch_threshold}")
                return False
                
        except Exception as e:
            logger.error(f"判断策略切换失败: {e}")
            return False
    
    async def switch_strategy(self, new_strategy_type: str) -> bool:
        """切换策略"""
        try:
            if new_strategy_type not in StrategyFactory.get_available_strategies():
                logger.error(f"❌ 无效的策略类型: {new_strategy_type}")
                return False
            
            old_strategy = self.get_current_strategy_type()
            
            # 清理旧策略
            if self.current_strategy:
                await self.current_strategy.cleanup()
            
            # 创建新策略
            self.current_strategy = StrategyFactory.create_strategy(new_strategy_type)
            await self.current_strategy.initialize()
            
            # 记录切换历史
            self.strategy_history.append({
                'timestamp': datetime.now(),
                'old_strategy': old_strategy,
                'new_strategy': new_strategy_type,
                'reason': 'automatic_switch'
            })
            
            logger.info(f"🔄 策略切换完成: {old_strategy} -> {new_strategy_type}")
            return True
            
        except Exception as e:
            logger.error(f"策略切换失败: {e}")
            # 回退到默认策略
            self.current_strategy = StrategyFactory.create_strategy(self.config.default_strategy)
            return False
    
    def get_strategy_history(self) -> List[Dict[str, Any]]:
        """获取策略切换历史"""
        return self.strategy_history.copy()
    
    def update_performance_cache(self, strategy_type: str, performance: float):
        """更新性能缓存"""
        self.performance_cache[strategy_type] = performance
    
    def get_strategy_recommendations(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取策略推荐列表"""
        try:
            recommendations = []
            
            for strategy_type in StrategyFactory.get_available_strategies():
                try:
                    strategy = StrategyFactory.create_strategy(strategy_type)
                    score = self._evaluate_strategy(strategy, market_data, None)
                    
                    recommendations.append({
                        'strategy_type': strategy_type,
                        'score': score,
                        'risk_level': strategy.risk_level,
                        'description': self._get_strategy_description(strategy_type),
                        'suitability': self._get_suitability_level(score)
                    })
                except Exception as e:
                    logger.warning(f"评估 {strategy_type} 推荐失败: {e}")
                    continue
            
            # 按评分排序
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations
            
        except Exception as e:
            logger.error(f"获取策略推荐失败: {e}")
            return []
    
    def _get_strategy_description(self, strategy_type: str) -> str:
        """获取策略描述"""
        descriptions = {
            'conservative': '稳健型策略，低风险，适合保守投资者',
            'moderate': '中等风险策略，平衡收益与风险',
            'aggressive': '激进型策略，高风险高收益'
        }
        return descriptions.get(strategy_type, '未知策略类型')
    
    def _get_suitability_level(self, score: float) -> str:
        """获取适合度等级"""
        if score >= 0.8:
            return '非常适合'
        elif score >= 0.6:
            return '适合'
        elif score >= 0.4:
            return '一般'
        else:
            return '不适合'

# 全局策略选择器实例
strategy_selector = StrategySelector()
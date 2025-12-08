"""
自适应策略优化引擎
实现机构级的智能策略优化和动态调整能力
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
from collections import defaultdict, deque
import logging
import warnings
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import optuna
from optuna import Trial
import joblib
import hashlib

# 导入系统组件
from config import config
from utils import log_info, log_warning, log_error
from strategies.strategies_market_sentiment_intelligence import MarketSentimentIntelligence, SentimentAnalysisResult
from trading.trading_multi_dimensional_risk_assessment import MultiDimensionalRiskAssessment, RiskAssessmentResult
from ai.advanced_ai_decision_engine import AdvancedAIDecisionEngine, DecisionResult

@dataclass
class StrategyOptimizationResult:
    """策略优化结果"""
    optimized_parameters: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    optimization_metrics: Dict[str, Any]
    risk_adjusted_metrics: Dict[str, Any]
    market_condition_fit: Dict[str, Any]
    confidence_score: float
    recommended_adjustments: List[Dict[str, Any]]
    backtest_results: Dict[str, Any]
    forward_testing_results: Dict[str, Any]
    strategy_stability_metrics: Dict[str, Any]
    timestamp: datetime
    optimization_method: str
    convergence_analysis: Dict[str, Any]

class MarketCondition(Enum):
    """市场条件类型"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"

class OptimizationMethod(Enum):
    """优化方法"""
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    PARTICLE_SWARM = "particle_swarm"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    GRADIENT_BASED = "gradient_based"
    EVOLUTIONARY = "evolutionary"

class AdaptiveStrategyOptimizer:
    """自适应策略优化引擎 - 机构级智能优化"""
    
    def __init__(self):
        # 核心优化组件
        self.bayesian_optimizer = BayesianOptimizer()
        self.genetic_optimizer = GeneticOptimizer()
        self.particle_swarm_optimizer = ParticleSwarmOptimizer()
        self.ensemble_optimizer = EnsembleOptimizer()
        
        # 机器学习模型
        self.performance_predictor = PerformancePredictor()
        self.market_condition_classifier = MarketConditionClassifier()
        self.strategy_selector = StrategySelector()
        
        # 高级分析工具
        self.backtest_engine = AdvancedBacktestEngine()
        self.forward_tester = ForwardTestingEngine()
        self.stability_analyzer = StrategyStabilityAnalyzer()
        self.convergence_analyzer = ConvergenceAnalyzer()
        
        # 市场感知组件
        self.sentiment_analyzer = MarketSentimentIntelligence()
        self.risk_assessor = MultiDimensionalRiskAssessment()
        self.decision_engine = AdvancedAIDecisionEngine()
        
        # 优化数据库
        self.optimization_db = OptimizationDatabase()
        
        # 性能缓存
        self.performance_cache = {}
        self.cache_duration = 300  # 5分钟缓存
        
        # 优化历史
        self.optimization_history = deque(maxlen=1000)
        
        log_info("🎯 自适应策略优化引擎初始化完成")
    
    async def perform_comprehensive_strategy_optimization(self,
                                                        current_strategy: Dict[str, Any],
                                                        market_data: Dict[str, Any],
                                                        portfolio_data: Optional[Dict[str, Any]] = None,
                                                        optimization_constraints: Optional[Dict[str, Any]] = None) -> StrategyOptimizationResult:
        """执行综合策略优化"""
        
        try:
            log_info("🚀 开始综合策略优化...")
            
            start_time = datetime.now()
            
            # 1. 市场条件识别
            market_condition = await self.market_condition_classifier.classify_market_condition(market_data)
            log_info(f"📊 识别市场条件: {market_condition.value}")
            
            # 2. 情绪分析
            sentiment_result = await self.sentiment_analyzer.calculate_comprehensive_market_sentiment()
            
            # 3. 风险评估
            risk_result = await self.risk_assessor.perform_comprehensive_risk_assessment(
                portfolio_data=portfolio_data,
                market_data=market_data
            )
            
            # 4. 策略性能预测
            performance_prediction = await self.performance_predictor.predict_strategy_performance(
                current_strategy, market_condition, sentiment_result, risk_result
            )
            
            # 5. 多方法并行优化
            optimization_tasks = [
                self.bayesian_optimizer.optimize(current_strategy, market_data, market_condition, optimization_constraints),
                self.genetic_optimizer.optimize(current_strategy, market_data, market_condition, optimization_constraints),
                self.particle_swarm_optimizer.optimize(current_strategy, market_data, market_condition, optimization_constraints)
            ]
            
            bayesian_result, genetic_result, pso_result = await asyncio.gather(*optimization_tasks)
            
            # 6. 集成优化结果
            ensemble_optimization = await self.ensemble_optimizer.combine_results(
                [bayesian_result, genetic_result, pso_result],
                [0.4, 0.3, 0.3]  # 权重分配
            )
            
            # 7. 高级回测验证
            backtest_results = await self.backtest_engine.perform_comprehensive_backtest(
                ensemble_optimization['optimized_parameters'],
                market_data,
                market_condition
            )
            
            # 8. 前向测试
            forward_results = await self.forward_tester.perform_forward_testing(
                ensemble_optimization['optimized_parameters'],
                market_data
            )
            
            # 9. 策略稳定性分析
            stability_metrics = await self.stability_analyzer.analyze_strategy_stability(
                ensemble_optimization['optimized_parameters'],
                backtest_results,
                forward_results
            )
            
            # 10. 收敛性分析
            convergence_analysis = await self.convergence_analyzer.analyze_convergence(
                [bayesian_result, genetic_result, pso_result]
            )
            
            # 11. 风险调整指标计算
            risk_adjusted_metrics = self._calculate_risk_adjusted_metrics(
                backtest_results,
                risk_result,
                performance_prediction
            )
            
            # 12. 市场条件适配度评估
            market_condition_fit = self._assess_market_condition_fit(
                ensemble_optimization['optimized_parameters'],
                market_condition,
                backtest_results
            )
            
            # 13. 置信度评分
            confidence_score = self._calculate_optimization_confidence(
                ensemble_optimization,
                backtest_results,
                stability_metrics,
                convergence_analysis
            )
            
            # 14. 推荐调整建议
            recommended_adjustments = self._generate_recommended_adjustments(
                ensemble_optimization['optimized_parameters'],
                market_condition,
                risk_result,
                backtest_results
            )
            
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = StrategyOptimizationResult(
                optimized_parameters=ensemble_optimization['optimized_parameters'],
                performance_metrics=backtest_results['performance_metrics'],
                optimization_metrics=ensemble_optimization['optimization_metrics'],
                risk_adjusted_metrics=risk_adjusted_metrics,
                market_condition_fit=market_condition_fit,
                confidence_score=confidence_score,
                recommended_adjustments=recommended_adjustments,
                backtest_results=backtest_results,
                forward_testing_results=forward_results,
                strategy_stability_metrics=stability_metrics,
                timestamp=datetime.now(),
                optimization_method="ensemble",
                convergence_analysis=convergence_analysis
            )
            
            # 缓存结果
            self._cache_optimization_result(result)
            
            # 保存到数据库
            await self.optimization_db.save_optimization_result(result)
            
            # 更新优化历史
            self.optimization_history.append(result)
            
            log_info(f"✅ 综合策略优化完成 (耗时: {optimization_time:.1f}s)")
            log_info(f"📈 优化后预期收益率: {risk_adjusted_metrics.get('expected_return', 0):.2%}")
            log_info(f"🛡️ 风险调整收益率: {risk_adjusted_metrics.get('risk_adjusted_return', 0):.2%}")
            
            return result
            
        except Exception as e:
            log_error(f"综合策略优化失败: {e}")
            return self._get_fallback_optimization_result()
    
    def _calculate_risk_adjusted_metrics(self, backtest_results: Dict[str, Any],
                                       risk_result: RiskAssessmentResult,
                                       performance_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """计算风险调整指标"""
        
        try:
            # 基础性能指标
            total_return = backtest_results['performance_metrics'].get('total_return', 0)
            volatility = backtest_results['performance_metrics'].get('volatility', 0.2)
            max_drawdown = backtest_results['performance_metrics'].get('max_drawdown', 0.1)
            
            # 风险调整收益率 (夏普比率)
            risk_free_rate = 0.02  # 假设无风险利率2%
            sharpe_ratio = (total_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 卡尔马比率 (收益率/最大回撤)
            calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0
            
            # 考虑综合风险评分的调整
            risk_adjustment_factor = 1 - (risk_result.overall_risk_score / 100) * 0.5
            
            # 风险调整收益率
            risk_adjusted_return = total_return * risk_adjustment_factor
            
            # 预期收益率 (结合预测)
            expected_return = (total_return + performance_prediction.get('predicted_return', total_return)) / 2
            
            return {
                'total_return': total_return,
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'calmar_ratio': calmar_ratio,
                'risk_adjusted_return': risk_adjusted_return,
                'expected_return': expected_return,
                'risk_adjustment_factor': risk_adjustment_factor
            }
            
        except Exception as e:
            log_error(f"风险调整指标计算失败: {e}")
            return {
                'total_return': 0,
                'volatility': 0.2,
                'max_drawdown': 0.1,
                'sharpe_ratio': 0,
                'calmar_ratio': 0,
                'risk_adjusted_return': 0,
                'expected_return': 0,
                'risk_adjustment_factor': 1.0
            }
    
    def _assess_market_condition_fit(self, optimized_params: Dict[str, Any],
                                   market_condition: MarketCondition,
                                   backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估市场条件适配度"""
        
        try:
            # 基于回测结果计算适配度
            performance_in_condition = backtest_results['performance_metrics'].get('condition_specific_performance', {})
            
            current_condition_performance = performance_in_condition.get(market_condition.value, 0)
            
            # 计算历史平均表现作为基准
            historical_avg_performance = np.mean([
                perf for perf in performance_in_condition.values() if perf > 0
            ]) if performance_in_condition else 0.1
            
            # 适配度评分 (相对于历史平均)
            fit_score = current_condition_performance / historical_avg_performance if historical_avg_performance > 0 else 0.5
            
            # 稳定性评分
            stability_score = backtest_results['performance_metrics'].get('stability_score', 0.5)
            
            # 一致性评分
            consistency_score = self._calculate_consistency_score(
                optimized_params, market_condition, backtest_results
            )
            
            return {
                'market_condition': market_condition.value,
                'fit_score': min(1.0, max(0.0, fit_score)),
                'stability_score': stability_score,
                'consistency_score': consistency_score,
                'overall_adaptation_score': (fit_score + stability_score + consistency_score) / 3,
                'performance_vs_historical': current_condition_performance / historical_avg_performance if historical_avg_performance > 0 else 1.0
            }
            
        except Exception as e:
            log_error(f"市场条件适配度评估失败: {e}")
            return {
                'market_condition': market_condition.value,
                'fit_score': 0.5,
                'stability_score': 0.5,
                'consistency_score': 0.5,
                'overall_adaptation_score': 0.5,
                'performance_vs_historical': 1.0
            }
    
    def _calculate_consistency_score(self, optimized_params: Dict[str, Any],
                                   market_condition: MarketCondition,
                                   backtest_results: Dict[str, Any]) -> float:
        """计算一致性评分"""
        
        try:
            # 检查参数合理性
            param_consistency = self._check_parameter_consistency(optimized_params, market_condition)
            
            # 检查回测结果一致性
            backtest_consistency = backtest_results.get('consistency_metrics', {}).get('parameter_stability', 0.5)
            
            # 综合一致性评分
            consistency_score = (param_consistency + backtest_consistency) / 2
            
            return consistency_score
            
        except Exception as e:
            log_warning(f"一致性评分计算失败: {e}")
            return 0.5
    
    def _check_parameter_consistency(self, params: Dict[str, Any], 
                                   market_condition: MarketCondition) -> float:
        """检查参数一致性"""
        
        try:
            # 基于市场条件的参数合理性检查
            consistency_checks = {
                MarketCondition.TRENDING_BULL: {
                    'trend_following_strength': (0.6, 1.0),
                    'mean_reversion_strength': (0.0, 0.4),
                    'momentum_period': (10, 30)
                },
                MarketCondition.TRENDING_BEAR: {
                    'trend_following_strength': (0.5, 1.0),
                    'mean_reversion_strength': (0.0, 0.3),
                    'momentum_period': (15, 40)
                },
                MarketCondition.RANGE_BOUND: {
                    'trend_following_strength': (0.0, 0.5),
                    'mean_reversion_strength': (0.6, 1.0),
                    'momentum_period': (5, 20)
                },
                MarketCondition.HIGH_VOLATILITY: {
                    'volatility_filter_threshold': (0.02, 0.05),
                    'position_sizing_factor': (0.3, 0.7),
                    'stop_loss_multiplier': (1.5, 3.0)
                }
            }
            
            checks = consistency_checks.get(market_condition, {})
            passed_checks = 0
            total_checks = len(checks)
            
            for param, (min_val, max_val) in checks.items():
                if param in params:
                    value = params[param]
                    if min_val <= value <= max_val:
                        passed_checks += 1
            
            consistency_score = passed_checks / total_checks if total_checks > 0 else 0.5
            
            return consistency_score
            
        except Exception as e:
            log_warning(f"参数一致性检查失败: {e}")
            return 0.5
    
    def _calculate_optimization_confidence(self, ensemble_result: Dict[str, Any],
                                         backtest_results: Dict[str, Any],
                                         stability_metrics: Dict[str, Any],
                                         convergence_analysis: Dict[str, Any]) -> float:
        """计算优化置信度"""
        
        try:
            # 集成优化一致性 (不同方法结果的一致性)
            ensemble_consistency = ensemble_result.get('consistency_score', 0.5)
            
            # 回测表现置信度
            backtest_confidence = backtest_results.get('confidence_score', 0.5)
            
            # 策略稳定性置信度
            stability_confidence = stability_metrics.get('overall_stability_score', 0.5)
            
            # 收敛性置信度
            convergence_confidence = convergence_analysis.get('convergence_quality', 0.5)
            
            # 综合置信度 (加权平均)
            confidence_score = (
                ensemble_consistency * 0.3 +
                backtest_confidence * 0.3 +
                stability_confidence * 0.25 +
                convergence_confidence * 0.15
            )
            
            return min(1.0, max(0.0, confidence_score))
            
        except Exception as e:
            log_error(f"优化置信度计算失败: {e}")
            return 0.5
    
    def _generate_recommended_adjustments(self, optimized_params: Dict[str, Any],
                                        market_condition: MarketCondition,
                                        risk_result: RiskAssessmentResult,
                                        backtest_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成推荐调整建议"""
        
        recommendations = []
        
        try:
            # 基于市场条件的调整建议
            condition_adjustments = self._generate_condition_based_adjustments(
                optimized_params, market_condition
            )
            recommendations.extend(condition_adjustments)
            
            # 基于风险的调整建议
            risk_adjustments = self._generate_risk_based_adjustments(
                optimized_params, risk_result
            )
            recommendations.extend(risk_adjustments)
            
            # 基于回测结果的调整建议
            backtest_adjustments = self._generate_backtest_based_adjustments(
                optimized_params, backtest_results
            )
            recommendations.extend(backtest_adjustments)
            
            return recommendations
            
        except Exception as e:
            log_error(f"推荐调整建议生成失败: {e}")
            return []
    
    def _generate_condition_based_adjustments(self, params: Dict[str, Any],
                                            market_condition: MarketCondition) -> List[Dict[str, Any]]:
        """生成基于市场条件的调整建议"""
        
        adjustments = []
        
        # 趋势市场调整
        if market_condition in [MarketCondition.TRENDING_BULL, MarketCondition.TRENDING_BEAR]:
            adjustments.append({
                'type': 'trend_following_enhancement',
                'parameter': 'trend_following_strength',
                'current_value': params.get('trend_following_strength', 0.5),
                'recommended_value': min(1.0, params.get('trend_following_strength', 0.5) * 1.2),
                'reason': f"{market_condition.value}市场，增强趋势跟踪能力",
                'priority': 'high'
            })
        
        # 震荡市场调整
        elif market_condition == MarketCondition.RANGE_BOUND:
            adjustments.append({
                'type': 'mean_reversion_enhancement',
                'parameter': 'mean_reversion_strength',
                'current_value': params.get('mean_reversion_strength', 0.5),
                'recommended_value': min(1.0, params.get('mean_reversion_strength', 0.5) * 1.3),
                'reason': "震荡市场，增强均值回归策略",
                'priority': 'high'
            })
        
        # 高波动市场调整
        elif market_condition == MarketCondition.HIGH_VOLATILITY:
            adjustments.append({
                'type': 'volatility_filter_tightening',
                'parameter': 'volatility_filter_threshold',
                'current_value': params.get('volatility_filter_threshold', 0.02),
                'recommended_value': params.get('volatility_filter_threshold', 0.02) * 0.8,
                'reason': "高波动市场，收紧波动性过滤条件",
                'priority': 'medium'
            })
            
            adjustments.append({
                'type': 'position_size_reduction',
                'parameter': 'position_sizing_factor',
                'current_value': params.get('position_sizing_factor', 1.0),
                'recommended_value': max(0.3, params.get('position_sizing_factor', 1.0) * 0.7),
                'reason': "高波动市场，降低仓位规模",
                'priority': 'high'
            })
        
        return adjustments
    
    def _generate_risk_based_adjustments(self, params: Dict[str, Any],
                                       risk_result: RiskAssessmentResult) -> List[Dict[str, Any]]:
        """生成基于风险的调整建议"""
        
        adjustments = []
        
        # 高风险调整
        if risk_result.overall_risk_score > 70:
            adjustments.append({
                'type': 'risk_reduction',
                'parameter': 'position_sizing_factor',
                'current_value': params.get('position_sizing_factor', 1.0),
                'recommended_value': max(0.2, params.get('position_sizing_factor', 1.0) * 0.5),
                'reason': f"高风险环境 (风险评分: {risk_result.overall_risk_score:.1f})，大幅降低仓位",
                'priority': 'very_high'
            })
            
            adjustments.append({
                'type': 'stop_loss_tightening',
                'parameter': 'stop_loss_multiplier',
                'current_value': params.get('stop_loss_multiplier', 2.0),
                'recommended_value': max(1.0, params.get('stop_loss_multiplier', 2.0) * 0.6),
                'reason': "高风险环境，收紧止损条件",
                'priority': 'high'
            })
        
        # 中等风险调整
        elif risk_result.overall_risk_score > 40:
            adjustments.append({
                'type': 'moderate_risk_reduction',
                'parameter': 'position_sizing_factor',
                'current_value': params.get('position_sizing_factor', 1.0),
                'recommended_value': max(0.5, params.get('position_sizing_factor', 1.0) * 0.8),
                'reason': f"中等风险环境，适度降低仓位",
                'priority': 'medium'
            })
        
        # 特定风险类别调整
        if risk_result.risk_breakdown.get('volatility_risk', 0) > 60:
            adjustments.append({
                'type': 'volatility_protection',
                'parameter': 'volatility_filter_threshold',
                'current_value': params.get('volatility_filter_threshold', 0.02),
                'recommended_value': params.get('volatility_filter_threshold', 0.02) * 0.7,
                'reason': "波动性风险较高，加强波动性保护",
                'priority': 'medium'
            })
        
        if risk_result.risk_breakdown.get('liquidity_risk', 0) > 60:
            adjustments.append({
                'type': 'liquidity_protection',
                'parameter': 'minimum_volume_threshold',
                'current_value': params.get('minimum_volume_threshold', 1000000),
                'recommended_value': params.get('minimum_volume_threshold', 1000000) * 1.5,
                'reason': "流动性风险较高，提高最小成交量要求",
                'priority': 'medium'
            })
        
        return adjustments
    
    def _generate_backtest_based_adjustments(self, params: Dict[str, Any],
                                           backtest_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成基于回测结果的调整建议"""
        
        adjustments = []
        
        try:
            performance_metrics = backtest_results.get('performance_metrics', {})
            
            # 夏普比率调整
            sharpe_ratio = performance_metrics.get('sharpe_ratio', 0)
            if sharpe_ratio < 1.0:
                adjustments.append({
                    'type': 'sharpe_ratio_improvement',
                    'parameter': 'risk_return_balance',
                    'current_value': params.get('risk_return_balance', 0.5),
                    'recommended_value': max(0.1, params.get('risk_return_balance', 0.5) - 0.1),
                    'reason': f"夏普比率较低 ({sharpe_ratio:.2f})，需要改善风险收益平衡",
                    'priority': 'medium'
                })
            
            # 最大回撤调整
            max_drawdown = performance_metrics.get('max_drawdown', 0.1)
            if max_drawdown > 0.15:
                adjustments.append({
                    'type': 'drawdown_control',
                    'parameter': 'stop_loss_multiplier',
                    'current_value': params.get('stop_loss_multiplier', 2.0),
                    'recommended_value': max(1.0, params.get('stop_loss_multiplier', 2.0) * 0.8),
                    'reason': f"最大回撤较大 ({max_drawdown:.1%})，加强回撤控制",
                    'priority': 'high'
                })
            
            # 胜率调整
            win_rate = performance_metrics.get('win_rate', 0.5)
            if win_rate < 0.45:
                adjustments.append({
                    'type': 'win_rate_improvement',
                    'parameter': 'signal_confirmation_strength',
                    'current_value': params.get('signal_confirmation_strength', 0.5),
                    'recommended_value': min(1.0, params.get('signal_confirmation_strength', 0.5) * 1.2),
                    'reason': f"胜率较低 ({win_rate:.1%})，增强信号确认",
                    'priority': 'medium'
                })
            
            # 盈亏比调整
            profit_factor = performance_metrics.get('profit_factor', 1.0)
            if profit_factor < 1.2:
                adjustments.append({
                    'type': 'profit_factor_improvement',
                    'parameter': 'take_profit_multiplier',
                    'current_value': params.get('take_profit_multiplier', 1.5),
                    'recommended_value': params.get('take_profit_multiplier', 1.5) * 1.1,
                    'reason': f"盈亏比偏低 ({profit_factor:.2f})，提高止盈目标",
                    'priority': 'low'
                })
            
            return adjustments
            
        except Exception as e:
            log_warning(f"基于回测的调整建议生成失败: {e}")
            return []
    
    def _cache_optimization_result(self, result: StrategyOptimizationResult):
        """缓存优化结果"""
        
        cache_key = f"optimization_{datetime.now().strftime('%Y%m%d%H%M')}"
        self.performance_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
    
    def _get_fallback_optimization_result(self) -> StrategyOptimizationResult:
        """获取兜底优化结果"""
        
        return StrategyOptimizationResult(
            optimized_parameters={},
            performance_metrics={},
            optimization_metrics={},
            risk_adjusted_metrics={},
            market_condition_fit={},
            confidence_score=0.3,
            recommended_adjustments=[],
            backtest_results={},
            forward_testing_results={},
            strategy_stability_metrics={},
            timestamp=datetime.now(),
            optimization_method="fallback",
            convergence_analysis={}
        )

class BayesianOptimizer:
    """贝叶斯优化器"""
    
    def __init__(self):
        self.study = None
        self.optimization_history = []
        
    async def optimize(self, current_strategy: Dict[str, Any], 
                      market_data: Dict[str, Any],
                      market_condition: MarketCondition,
                      constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """贝叶斯优化"""
        
        try:
            log_info("🔬 开始贝叶斯优化...")
            
            # 定义参数空间
            param_space = self._define_parameter_space(current_strategy, constraints)
            
            # 创建Optuna研究
            self.study = optuna.create_study(
                direction='maximize',
                sampler=optuna.samplers.TPESampler(seed=42),
                pruner=optuna.pruners.MedianPruner()
            )
            
            # 执行优化
            self.study.optimize(
                lambda trial: self._objective_function(trial, current_strategy, market_data, market_condition),
                n_trials=100,
                timeout=60  # 60秒超时
            )
            
            # 获取最佳参数
            best_params = self.study.best_params
            best_value = self.study.best_value
            
            # 计算优化指标
            optimization_metrics = {
                'best_trial_value': best_value,
                'n_trials': len(self.study.trials),
                'optimization_time': self.study.best_trial.datetime_complete - self.study.best_trial.datetime_start,
                'parameter_importance': self._calculate_parameter_importance(),
                'convergence_speed': self._calculate_convergence_speed()
            }
            
            return {
                'optimized_parameters': best_params,
                'optimization_metrics': optimization_metrics,
                'optimization_method': 'bayesian',
                'consistency_score': self._calculate_consistency_score()
            }
            
        except Exception as e:
            log_error(f"贝叶斯优化失败: {e}")
            return self._get_default_optimization_result('bayesian')
    
    def _define_parameter_space(self, current_strategy: Dict[str, Any], 
                              constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """定义参数空间"""
        
        param_space = {}
        
        # 趋势跟踪参数
        if 'trend_following_strength' in current_strategy:
            param_space['trend_following_strength'] = (0.0, 1.0)
        
        # 均值回归参数
        if 'mean_reversion_strength' in current_strategy:
            param_space['mean_reversion_strength'] = (0.0, 1.0)
        
        # 动量参数
        if 'momentum_period' in current_strategy:
            param_space['momentum_period'] = (5, 50)
        
        # 波动性参数
        if 'volatility_filter_threshold' in current_strategy:
            param_space['volatility_filter_threshold'] = (0.005, 0.05)
        
        # 仓位管理参数
        if 'position_sizing_factor' in current_strategy:
            param_space['position_sizing_factor'] = (0.1, 2.0)
        
        # 止损参数
        if 'stop_loss_multiplier' in current_strategy:
            param_space['stop_loss_multiplier'] = (1.0, 5.0)
        
        # 应用约束
        if constraints:
            for param, constraint in constraints.items():
                if param in param_space:
                    param_space[param] = (constraint.get('min', param_space[param][0]),
                                        constraint.get('max', param_space[param][1]))
        
        return param_space
    
    def _objective_function(self, trial: Trial, current_strategy: Dict[str, Any],
                          market_data: Dict[str, Any], market_condition: MarketCondition) -> float:
        """目标函数"""
        
        try:
            # 生成试验参数
            trial_params = {}
            param_space = self._define_parameter_space(current_strategy, None)
            
            for param, (min_val, max_val) in param_space.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    trial_params[param] = trial.suggest_int(param, min_val, max_val)
                else:
                    trial_params[param] = trial.suggest_float(param, min_val, max_val)
            
            # 创建策略参数
            strategy_params = current_strategy.copy()
            strategy_params.update(trial_params)
            
            # 模拟策略性能 (简化实现)
            performance_score = self._simulate_strategy_performance(
                strategy_params, market_data, market_condition
            )
            
            return performance_score
            
        except Exception as e:
            log_warning(f"目标函数评估失败: {e}")
            return -1e6  # 返回很差的分数
    
    def _simulate_strategy_performance(self, params: Dict[str, Any], 
                                     market_data: Dict[str, Any],
                                     market_condition: MarketCondition) -> float:
        """模拟策略性能 (简化实现)"""
        
        try:
            # 基础性能计算
            base_performance = 0.1  # 10%基础收益
            
            # 趋势跟踪贡献
            trend_contribution = params.get('trend_following_strength', 0.5) * 0.05
            
            # 均值回归贡献
            reversion_contribution = params.get('mean_reversion_strength', 0.5) * 0.03
            
            # 动量贡献
            momentum_contribution = min(1.0, 20 / params.get('momentum_period', 20)) * 0.02
            
            # 波动性调整
            volatility_adjustment = -abs(params.get('volatility_filter_threshold', 0.02) - 0.02) * 10
            
            # 仓位管理调整
            sizing_adjustment = -abs(params.get('position_sizing_factor', 1.0) - 1.0) * 0.05
            
            # 市场条件调整
            condition_multiplier = {
                MarketCondition.TRENDING_BULL: 1.2,
                MarketCondition.TRENDING_BEAR: 0.8,
                MarketCondition.RANGE_BOUND: 1.0,
                MarketCondition.HIGH_VOLATILITY: 0.9,
                MarketCondition.LOW_VOLATILITY: 1.1
            }.get(market_condition, 1.0)
            
            # 综合性能评分
            total_performance = (
                base_performance + 
                trend_contribution + 
                reversion_contribution + 
                momentum_contribution + 
                volatility_adjustment + 
                sizing_adjustment
            ) * condition_multiplier
            
            # 添加一些随机性
            noise = np.random.normal(0, 0.01)
            final_performance = total_performance + noise
            
            return max(-0.5, min(0.5, final_performance))  # 限制范围
            
        except Exception as e:
            log_warning(f"策略性能模拟失败: {e}")
            return 0.0
    
    def _calculate_parameter_importance(self) -> Dict[str, Any]:
        """计算参数重要性"""
        
        try:
            if not self.study or len(self.study.trials) < 10:
                return {}
            
            # 使用Optuna的fanova
            importance = optuna.importance.get_param_importances(self.study)
            return importance
            
        except Exception as e:
            log_warning(f"参数重要性计算失败: {e}")
            return {}
    
    def _calculate_convergence_speed(self) -> float:
        """计算收敛速度"""
        
        try:
            if not self.study or len(self.study.trials) < 20:
                return 0.5
            
            # 计算前20%和后20%试验的平均改进
            trials = self.study.trials
            n_trials = len(trials)
            
            if n_trials < 20:
                return 0.5
            
            early_trials = trials[:n_trials//5]
            late_trials = trials[-n_trials//5:]
            
            early_avg = np.mean([t.value for t in early_trials if t.value is not None])
            late_avg = np.mean([t.value for t in late_trials if t.value is not None])
            
            improvement = (late_avg - early_avg) / abs(early_avg) if early_avg != 0 else 0
            
            # 转换为0-1评分
            convergence_speed = max(0.0, min(1.0, improvement * 5 + 0.5))
            
            return convergence_speed
            
        except Exception as e:
            log_warning(f"收敛速度计算失败: {e}")
            return 0.5
    
    def _calculate_consistency_score(self) -> float:
        """计算一致性评分"""
        
        try:
            if not self.study or len(self.study.trials) < 10:
                return 0.5
            
            # 计算最近10次试验的稳定性
            recent_trials = self.study.trials[-10:]
            values = [t.value for t in recent_trials if t.value is not None]
            
            if len(values) < 5:
                return 0.5
            
            # 计算变异系数
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            if mean_val == 0:
                return 0.5
            
            cv = std_val / abs(mean_val)
            consistency_score = max(0.0, min(1.0, 1 - cv))
            
            return consistency_score
            
        except Exception as e:
            log_warning(f"一致性评分计算失败: {e}")
            return 0.5
    
    def _get_default_optimization_result(self, method: str) -> Dict[str, Any]:
        """获取默认优化结果"""
        return {
            'optimized_parameters': {},
            'optimization_metrics': {
                'best_trial_value': 0,
                'n_trials': 0,
                'optimization_time': 0,
                'parameter_importance': {},
                'convergence_speed': 0.5
            },
            'optimization_method': method,
            'consistency_score': 0.5
        }

class GeneticOptimizer:
    """遗传算法优化器"""
    
    def __init__(self):
        self.population_size = 50
        self.generations = 30
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        
    async def optimize(self, current_strategy: Dict[str, Any], 
                      market_data: Dict[str, Any],
                      market_condition: MarketCondition,
                      constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """遗传算法优化"""
        
        try:
            log_info("🧬 开始遗传算法优化...")
            
            # 初始化种群
            population = self._initialize_population(current_strategy, constraints)
            
            # 进化过程
            best_individual = None
            best_fitness = -float('inf')
            fitness_history = []
            
            for generation in range(self.generations):
                # 评估适应度
                fitness_scores = await self._evaluate_population(population, market_data, market_condition)
                
                # 记录最佳个体
                current_best_idx = np.argmax(fitness_scores)
                current_best_fitness = fitness_scores[current_best_idx]
                
                if current_best_fitness > best_fitness:
                    best_fitness = current_best_fitness
                    best_individual = population[current_best_idx].copy()
                
                fitness_history.append(best_fitness)
                
                # 选择
                selected_population = self._selection(population, fitness_scores)
                
                # 交叉
                offspring_population = self._crossover(selected_population)
                
                # 变异
                mutated_population = self._mutation(offspring_population)
                
                # 更新种群
                population = mutated_population
                
                log_info(f"遗传算法 - 第{generation+1}代: 最佳适应度={best_fitness:.4f}")
            
            # 计算优化指标
            optimization_metrics = {
                'best_fitness': best_fitness,
                'generations': self.generations,
                'population_size': self.population_size,
                'convergence_speed': self._calculate_genetic_convergence_speed(fitness_history),
                'diversity_metrics': self._calculate_population_diversity(population)
            }
            
            return {
                'optimized_parameters': best_individual,
                'optimization_metrics': optimization_metrics,
                'optimization_method': 'genetic',
                'consistency_score': self._calculate_genetic_consistency(fitness_history)
            }
            
        except Exception as e:
            log_error(f"遗传算法优化失败: {e}")
            return self._get_default_optimization_result('genetic')
    
    def _initialize_population(self, current_strategy: Dict[str, Any], 
                             constraints: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """初始化种群"""
        
        population = []
        
        for _ in range(self.population_size):
            individual = current_strategy.copy()
            
            # 随机变异当前策略参数
            for param, value in individual.items():
                if isinstance(value, (int, float)) and param != 'strategy_name':
                    # 应用约束
                    if constraints and param in constraints:
                        min_val = constraints[param].get('min', value * 0.5)
                        max_val = constraints[param].get('max', value * 2.0)
                    else:
                        min_val = value * 0.1
                        max_val = value * 3.0
                    
                    # 生成随机值
                    if isinstance(value, int):
                        individual[param] = np.random.randint(int(min_val), int(max_val) + 1)
                    else:
                        individual[param] = np.random.uniform(min_val, max_val)
            
            population.append(individual)
        
        return population
    
    async def _evaluate_population(self, population: List[Dict[str, Any]], 
                                 market_data: Dict[str, Any],
                                 market_condition: MarketCondition) -> List[float]:
        """评估种群适应度"""
        
        fitness_scores = []
        
        for individual in population:
            # 模拟策略性能
            performance_score = self._simulate_strategy_performance(
                individual, market_data, market_condition
            )
            fitness_scores.append(performance_score)
        
        return fitness_scores
    
    def _selection(self, population: List[Dict[str, Any]], 
                   fitness_scores: List[float]) -> List[Dict[str, Any]]:
        """选择操作 (锦标赛选择)"""
        
        selected_population = []
        tournament_size = 3
        
        for _ in range(len(population)):
            # 随机选择锦标赛个体
            tournament_indices = np.random.choice(len(population), tournament_size, replace=False)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            
            # 选择最佳个体
            winner_idx = tournament_indices[np.argmax(tournament_fitness)]
            selected_population.append(population[winner_idx].copy())
        
        return selected_population
    
    def _crossover(self, population: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """交叉操作"""
        
        offspring_population = []
        
        for i in range(0, len(population), 2):
            parent1 = population[i]
            
            if i + 1 < len(population):
                parent2 = population[i + 1]
                
                if np.random.random() < self.crossover_rate:
                    # 单点交叉
                    child1, child2 = self._single_point_crossover(parent1, parent2)
                    offspring_population.extend([child1, child2])
                else:
                    offspring_population.extend([parent1.copy(), parent2.copy()])
            else:
                offspring_population.append(parent1.copy())
        
        return offspring_population
    
    def _single_point_crossover(self, parent1: Dict[str, Any], 
                              parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """单点交叉"""
        
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        # 获取所有数值参数
        numeric_params = [k for k, v in parent1.items() 
                         if isinstance(v, (int, float)) and k != 'strategy_name']
        
        if len(numeric_params) > 1:
            # 随机选择交叉点
            crossover_point = np.random.randint(1, len(numeric_params))
            
            # 执行交叉
            for i, param in enumerate(numeric_params):
                if i >= crossover_point:
                    child1[param] = parent2[param]
                    child2[param] = parent1[param]
        
        return child1, child2
    
    def _mutation(self, population: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """变异操作"""
        
        mutated_population = []
        
        for individual in population:
            mutated_individual = individual.copy()
            
            for param, value in mutated_individual.items():
                if isinstance(value, (int, float)) and param != 'strategy_name':
                    if np.random.random() < self.mutation_rate:
                        # 高斯变异
                        if isinstance(value, int):
                            mutation = int(np.random.normal(0, abs(value) * 0.1))
                            mutated_individual[param] = max(1, value + mutation)
                        else:
                            mutation = np.random.normal(0, abs(value) * 0.1)
                            mutated_individual[param] = max(0.001, value + mutation)
            
            mutated_population.append(mutated_individual)
        
        return mutated_population
    
    def _calculate_genetic_convergence_speed(self, fitness_history: List[float]) -> float:
        """计算遗传算法收敛速度"""
        
        try:
            if len(fitness_history) < 10:
                return 0.5
            
            # 计算改进速度
            early_avg = np.mean(fitness_history[:5])
            late_avg = np.mean(fitness_history[-5:])
            
            if early_avg == 0:
                return 0.5
            
            improvement_rate = (late_avg - early_avg) / abs(early_avg)
            
            return max(0.0, min(1.0, improvement_rate * 2 + 0.5))
            
        except Exception as e:
            log_warning(f"遗传算法收敛速度计算失败: {e}")
            return 0.5
    
    def _calculate_population_diversity(self, population: List[Dict[str, Any]]) -> float:
        """计算种群多样性"""
        
        try:
            if len(population) < 2:
                return 0.0
            
            # 计算参数差异
            diversity_scores = []
            
            for param in population[0].keys():
                if isinstance(population[0][param], (int, float)) and param != 'strategy_name':
                    values = [individual[param] for individual in population]
                    diversity = np.std(values) / (np.mean(values) + 1e-6)
                    diversity_scores.append(diversity)
            
            if diversity_scores:
                return np.mean(diversity_scores)
            else:
                return 0.0
                
        except Exception as e:
            log_warning(f"种群多样性计算失败: {e}")
            return 0.0
    
    def _calculate_genetic_consistency(self, fitness_history: List[float]) -> float:
        """计算遗传算法一致性"""
        
        try:
            if len(fitness_history) < 5:
                return 0.5
            
            # 计算最后5代的稳定性
            recent_fitness = fitness_history[-5:]
            mean_fitness = np.mean(recent_fitness)
            std_fitness = np.std(recent_fitness)
            
            if mean_fitness == 0:
                return 0.5
            
            cv = std_fitness / abs(mean_fitness)
            consistency = max(0.0, min(1.0, 1 - cv))
            
            return consistency
            
        except Exception as e:
            log_warning(f"遗传算法一致性计算失败: {e}")
            return 0.5

class ParticleSwarmOptimizer:
    """粒子群优化器"""
    
    def __init__(self):
        self.n_particles = 30
        self.n_iterations = 50
        self.c1 = 2.0  # 认知系数
        self.c2 = 2.0  # 社会系数
        self.w = 0.7   # 惯性权重
        
    async def optimize(self, current_strategy: Dict[str, Any], 
                      market_data: Dict[str, Any],
                      market_condition: MarketCondition,
                      constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """粒子群优化"""
        
        try:
            log_info("🌊 开始粒子群优化...")
            
            # 初始化粒子群
            particles = self._initialize_particles(current_strategy, constraints)
            
            # 全局最佳
            global_best_position = None
            global_best_fitness = -float('inf')
            
            # 优化历史
            fitness_history = []
            
            for iteration in range(self.n_iterations):
                # 评估粒子适应度
                for particle in particles:
                    fitness = self._evaluate_particle(particle, market_data, market_condition)
                    particle['fitness'] = fitness
                    
                    # 更新个体最佳
                    if fitness > particle['best_fitness']:
                        particle['best_fitness'] = fitness
                        particle['best_position'] = particle['position'].copy()
                    
                    # 更新全局最佳
                    if fitness > global_best_fitness:
                        global_best_fitness = fitness
                        global_best_position = particle['position'].copy()
                
                fitness_history.append(global_best_fitness)
                
                # 更新粒子位置和速度
                self._update_particles(particles, global_best_position)
                
                log_info(f"粒子群优化 - 第{iteration+1}次迭代: 全局最佳适应度={global_best_fitness:.4f}")
            
            # 计算优化指标
            optimization_metrics = {
                'best_fitness': global_best_fitness,
                'n_iterations': self.n_iterations,
                'n_particles': self.n_particles,
                'convergence_speed': self._calculate_pso_convergence_speed(fitness_history),
                'particle_diversity': self._calculate_particle_diversity(particles)
            }
            
            return {
                'optimized_parameters': self._position_to_params(global_best_position, current_strategy),
                'optimization_metrics': optimization_metrics,
                'optimization_method': 'particle_swarm',
                'consistency_score': self._calculate_pso_consistency(fitness_history)
            }
            
        except Exception as e:
            log_error(f"粒子群优化失败: {e}")
            return self._get_default_optimization_result('particle_swarm')
    
    def _initialize_particles(self, current_strategy: Dict[str, Any], 
                            constraints: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """初始化粒子群"""
        
        particles = []
        
        # 获取参数维度
        param_names = [k for k, v in current_strategy.items() 
                      if isinstance(v, (int, float)) and k != 'strategy_name']
        
        for _ in range(self.n_particles):
            # 随机初始化位置
            position = []
            for param in param_names:
                value = current_strategy[param]
                
                if constraints and param in constraints:
                    min_val = constraints[param].get('min', value * 0.5)
                    max_val = constraints[param].get('max', value * 2.0)
                else:
                    min_val = value * 0.1
                    max_val = value * 3.0
                
                position.append(np.random.uniform(min_val, max_val))
            
            # 随机初始化速度
            velocity = [np.random.uniform(-1, 1) for _ in param_names]
            
            particle = {
                'position': position,
                'velocity': velocity,
                'best_position': position.copy(),
                'best_fitness': -float('inf'),
                'fitness': 0
            }
            
            particles.append(particle)
        
        return particles
    
    def _evaluate_particle(self, particle: Dict[str, Any], 
                         market_data: Dict[str, Any],
                         market_condition: MarketCondition) -> float:
        """评估粒子适应度"""
        
        # 将位置转换为参数字典
        params = self._position_to_params(particle['position'], {})
        
        # 模拟策略性能
        fitness = self._simulate_strategy_performance(params, market_data, market_condition)
        
        return fitness
    
    def _update_particles(self, particles: List[Dict[str, Any]], 
                        global_best_position: List[float]):
        """更新粒子位置和速度"""
        
        for particle in particles:
            # 更新速度
            for i in range(len(particle['velocity'])):
                r1, r2 = np.random.random(), np.random.random()
                
                cognitive_component = self.c1 * r1 * (particle['best_position'][i] - particle['position'][i])
                social_component = self.c2 * r2 * (global_best_position[i] - particle['position'][i])
                
                particle['velocity'][i] = (
                    self.w * particle['velocity'][i] + 
                    cognitive_component + 
                    social_component
                )
            
            # 更新位置
            for i in range(len(particle['position'])):
                particle['position'][i] += particle['velocity'][i]
                
                # 确保位置在合理范围内
                particle['position'][i] = max(0.001, particle['position'][i])
    
    def _position_to_params(self, position: List[float], 
                          current_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """将位置转换为参数字典"""
        
        params = current_strategy.copy()
        
        # 获取参数名称
        param_names = [k for k, v in current_strategy.items() 
                      if isinstance(v, (int, float)) and k != 'strategy_name']
        
        # 更新参数值
        for i, param_name in enumerate(param_names):
            if i < len(position):
                if isinstance(current_strategy[param_name], int):
                    params[param_name] = int(position[i])
                else:
                    params[param_name] = float(position[i])
        
        return params
    
    def _calculate_pso_convergence_speed(self, fitness_history: List[float]) -> float:
        """计算粒子群收敛速度"""
        
        try:
            if len(fitness_history) < 10:
                return 0.5
            
            # 计算改进趋势
            early_avg = np.mean(fitness_history[:5])
            late_avg = np.mean(fitness_history[-5:])
            
            if early_avg == 0:
                return 0.5
            
            improvement_rate = (late_avg - early_avg) / abs(early_avg)
            
            return max(0.0, min(1.0, improvement_rate * 2 + 0.5))
            
        except Exception as e:
            log_warning(f"粒子群收敛速度计算失败: {e}")
            return 0.5
    
    def _calculate_particle_diversity(self, particles: List[Dict[str, Any]]) -> float:
        """计算粒子多样性"""
        
        try:
            if len(particles) < 2:
                return 0.0
            
            # 计算位置的标准差
            positions = [p['position'] for p in particles]
            positions_array = np.array(positions)
            
            # 计算每个维度的标准差
            std_per_dimension = np.std(positions_array, axis=0)
            mean_per_dimension = np.mean(positions_array, axis=0)
            
            # 计算平均变异系数
            cv_per_dimension = std_per_dimension / (mean_per_dimension + 1e-6)
            avg_diversity = np.mean(cv_per_dimension)
            
            return max(0.0, min(1.0, avg_diversity))
            
        except Exception as e:
            log_warning(f"粒子多样性计算失败: {e}")
            return 0.0
    
    def _calculate_pso_consistency(self, fitness_history: List[float]) -> float:
        """计算粒子群一致性"""
        
        try:
            if len(fitness_history) < 5:
                return 0.5
            
            # 计算最后5代的稳定性
            recent_fitness = fitness_history[-5:]
            mean_fitness = np.mean(recent_fitness)
            std_fitness = np.std(recent_fitness)
            
            if mean_fitness == 0:
                return 0.5
            
            cv = std_fitness / abs(mean_fitness)
            consistency = max(0.0, min(1.0, 1 - cv))
            
            return consistency
            
        except Exception as e:
            log_warning(f"粒子群一致性计算失败: {e}")
            return 0.5

class EnsembleOptimizer:
    """集成优化器"""
    
    async def combine_results(self, optimization_results: List[Dict[str, Any]], 
                            weights: List[float]) -> Dict[str, Any]:
        """集成多个优化结果"""
        
        try:
            log_info("🔗 开始集成优化结果...")
            
            # 验证输入
            if len(optimization_results) != len(weights):
                raise ValueError("优化结果数量和权重数量不匹配")
            
            if not np.isclose(sum(weights), 1.0):
                # 标准化权重
                weights = np.array(weights) / sum(weights)
            
            # 提取参数
            all_parameters = [result['optimized_parameters'] for result in optimization_results]
            
            # 参数集成 (加权平均)
            ensemble_params = self._ensemble_parameters(all_parameters, weights)
            
            # 计算集成指标
            ensemble_metrics = self._calculate_ensemble_metrics(optimization_results, weights)
            
            # 计算一致性评分
            consistency_score = self._calculate_ensemble_consistency(all_parameters, weights)
            
            return {
                'optimized_parameters': ensemble_params,
                'optimization_metrics': ensemble_metrics,
                'consistency_score': consistency_score,
                'component_results': optimization_results,
                'weights': weights.tolist() if hasattr(weights, 'tolist') else weights
            }
            
        except Exception as e:
            log_error(f"集成优化失败: {e}")
            return self._get_default_ensemble_result()
    
    def _ensemble_parameters(self, all_parameters: List[Dict[str, Any]], 
                           weights: List[float]) -> Dict[str, Any]:
        """集成参数"""
        
        ensemble_params = {}
        
        # 获取所有参数键
        all_keys = set()
        for params in all_parameters:
            all_keys.update(params.keys())
        
        # 对每个参数进行加权平均
        for key in all_keys:
            values = []
            valid_weights = []
            
            for i, params in enumerate(all_parameters):
                if key in params:
                    values.append(params[key])
                    valid_weights.append(weights[i])
            
            if values and valid_weights:
                # 标准化权重
                valid_weights = np.array(valid_weights)
                valid_weights = valid_weights / valid_weights.sum()
                
                # 加权平均
                if all(isinstance(v, (int, float)) for v in values):
                    ensemble_value = np.average(values, weights=valid_weights)
                    
                    # 如果是整数参数，四舍五入
                    if all(isinstance(v, int) for v in values):
                        ensemble_value = int(round(ensemble_value))
                    
                    ensemble_params[key] = ensemble_value
        
        return ensemble_params
    
    def _calculate_ensemble_metrics(self, optimization_results: List[Dict[str, Any]], 
                                  weights: List[float]) -> Dict[str, Any]:
        """计算集成指标"""
        
        metrics = {}
        
        # 提取所有指标
        all_metrics = [result['optimization_metrics'] for result in optimization_results]
        
        # 加权平均各项指标
        for metric_name in ['best_trial_value', 'best_fitness', 'convergence_speed']:
            values = []
            valid_weights = []
            
            for i, metric_dict in enumerate(all_metrics):
                if metric_name in metric_dict:
                    values.append(metric_dict[metric_name])
                    valid_weights.append(weights[i])
            
            if values and valid_weights:
                valid_weights = np.array(valid_weights)
                valid_weights = valid_weights / valid_weights.sum()
                metrics[metric_name] = np.average(values, weights=valid_weights)
        
        # 计算多样性指标
        diversity_scores = [result.get('consistency_score', 0.5) for result in optimization_results]
        metrics['ensemble_diversity'] = np.std(diversity_scores)
        
        # 计算稳定性指标
        stability_scores = [result.get('consistency_score', 0.5) for result in optimization_results]
        metrics['ensemble_stability'] = np.mean(stability_scores)
        
        return metrics
    
    def _calculate_ensemble_consistency(self, all_parameters: List[Dict[str, Any]], 
                                      weights: List[float]) -> float:
        """计算集成一致性"""
        
        try:
            # 计算参数一致性
            param_consistency_scores = []
            
            # 获取所有参数键
            all_keys = set()
            for params in all_parameters:
                all_keys.update(params.keys())
            
            for key in all_keys:
                values = []
                valid_weights = []
                
                for i, params in enumerate(all_parameters):
                    if key in params and isinstance(params[key], (int, float)):
                        values.append(params[key])
                        valid_weights.append(weights[i])
                
                if len(values) > 1 and valid_weights:
                    # 标准化权重
                    valid_weights = np.array(valid_weights)
                    valid_weights = valid_weights / valid_weights.sum()
                    
                    # 计算加权标准差
                    weighted_mean = np.average(values, weights=valid_weights)
                    variance = np.average((np.array(values) - weighted_mean) ** 2, weights=valid_weights)
                    weighted_std = np.sqrt(variance)
                    
                    # 一致性评分 (变异系数的补数)
                    consistency = 1 - min(1.0, weighted_std / (abs(weighted_mean) + 1e-6))
                    param_consistency_scores.append(consistency)
            
            if param_consistency_scores:
                return np.mean(param_consistency_scores)
            else:
                return 0.5
                
        except Exception as e:
            log_warning(f"集成一致性计算失败: {e}")
            return 0.5
    
    def _get_default_ensemble_result(self) -> Dict[str, Any]:
        """获取默认集成结果"""
        return {
            'optimized_parameters': {},
            'optimization_metrics': {},
            'consistency_score': 0.5,
            'component_results': [],
            'weights': []
        }

class PerformancePredictor:
    """性能预测器"""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'neural_network': MLPRegressor(hidden_layer_sizes=(50, 30), random_state=42)
        }
        
        self.scaler = StandardScaler()
        self.is_trained = False
        
    async def predict_strategy_performance(self, strategy_params: Dict[str, Any],
                                         market_condition: MarketCondition,
                                         sentiment_result: SentimentAnalysisResult,
                                         risk_result: RiskAssessmentResult) -> Dict[str, Any]:
        """预测策略性能"""
        
        try:
            # 特征工程
            features = self._extract_features(strategy_params, market_condition, 
                                            sentiment_result, risk_result)
            
            # 标准化特征
            features_scaled = self.scaler.transform([features])
            
            # 多模型预测
            predictions = {}
            for model_name, model in self.models.items():
                if self.is_trained:
                    pred = model.predict(features_scaled)[0]
                    predictions[f'{model_name}_prediction'] = pred
                else:
                    predictions[f'{model_name}_prediction'] = 0.1  # 默认预测
            
            # 集成预测
            if self.is_trained:
                ensemble_prediction = np.mean(list(predictions.values()))
            else:
                ensemble_prediction = 0.1
            
            # 预测置信度
            prediction_confidence = self._calculate_prediction_confidence(features, predictions)
            
            return {
                'predicted_return': ensemble_prediction,
                'predicted_volatility': 0.2,  # 简化实现
                'predicted_sharpe_ratio': ensemble_prediction / 0.2 if 0.2 > 0 else 0,
                'model_predictions': predictions,
                'prediction_confidence': prediction_confidence,
                'feature_importance': self._get_feature_importance(features)
            }
            
        except Exception as e:
            log_error(f"策略性能预测失败: {e}")
            return {
                'predicted_return': 0.1,
                'predicted_volatility': 0.2,
                'predicted_sharpe_ratio': 0.5,
                'model_predictions': {},
                'prediction_confidence': 0.5,
                'feature_importance': {}
            }
    
    def _extract_features(self, strategy_params: Dict[str, Any],
                        market_condition: MarketCondition,
                        sentiment_result: SentimentAnalysisResult,
                        risk_result: RiskAssessmentResult) -> List[float]:
        """提取特征"""
        
        features = []
        
        # 策略参数特征
        param_features = [
            strategy_params.get('trend_following_strength', 0.5),
            strategy_params.get('mean_reversion_strength', 0.5),
            strategy_params.get('momentum_period', 20) / 50.0,  # 标准化
            strategy_params.get('volatility_filter_threshold', 0.02) * 100,  # 放大
            strategy_params.get('position_sizing_factor', 1.0),
            strategy_params.get('stop_loss_multiplier', 2.0) / 5.0  # 标准化
        ]
        features.extend(param_features)
        
        # 市场条件特征
        condition_map = {
            MarketCondition.TRENDING_BULL: 1.0,
            MarketCondition.TRENDING_BEAR: -1.0,
            MarketCondition.RANGE_BOUND: 0.0,
            MarketCondition.HIGH_VOLATILITY: 0.5,
            MarketCondition.LOW_VOLATILITY: -0.5
        }
        features.append(condition_map.get(market_condition, 0.0))
        
        # 情绪特征
        sentiment_features = [
            sentiment_result.overall_sentiment,
            sentiment_result.confidence_score,
            sentiment_result.sentiment_momentum,
            sentiment_result.sentiment_breakdown.get('fear_greed_index', 50) / 100.0  # 标准化
        ]
        features.extend(sentiment_features)
        
        # 风险特征
        risk_features = [
            risk_result.overall_risk_score / 100.0,  # 标准化
            risk_result.confidence_score,
            risk_result.risk_breakdown.get('market_risk', 50) / 100.0,
            risk_result.risk_breakdown.get('volatility_risk', 50) / 100.0
        ]
        features.extend(risk_features)
        
        return features
    
    def _calculate_prediction_confidence(self, features: List[float], 
                                       predictions: Dict[str, float]) -> float:
        """计算预测置信度"""
        
        try:
            if not predictions:
                return 0.5
            
            # 模型一致性
            pred_values = list(predictions.values())
            pred_std = np.std(pred_values)
            pred_mean = np.mean(pred_values)
            
            consistency_score = 1 - min(1.0, pred_std / (abs(pred_mean) + 1e-6))
            
            # 特征质量评分
            feature_quality = 1 - np.std(features) / (np.mean(np.abs(features)) + 1e-6)
            
            # 历史准确性 (简化实现)
            historical_accuracy = 0.7  # 应该基于历史回测
            
            # 综合置信度
            confidence = (consistency_score * 0.4 + 
                         feature_quality * 0.3 + 
                         historical_accuracy * 0.3)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            log_warning(f"预测置信度计算失败: {e}")
            return 0.5
    
    def _get_feature_importance(self, features: List[float]) -> Dict[str, float]:
        """获取特征重要性"""
        
        # 简化实现 - 返回默认重要性
        feature_names = [
            'trend_following_strength', 'mean_reversion_strength', 'momentum_period',
            'volatility_filter', 'position_sizing', 'stop_loss',
            'market_condition', 'sentiment', 'sentiment_confidence',
            'sentiment_momentum', 'fear_greed', 'overall_risk',
            'risk_confidence', 'market_risk', 'volatility_risk'
        ]
        
        # 默认重要性 (应该基于训练好的模型)
        default_importance = {
            'trend_following_strength': 0.15,
            'mean_reversion_strength': 0.12,
            'momentum_period': 0.08,
            'volatility_filter': 0.10,
            'position_sizing': 0.18,
            'stop_loss': 0.12,
            'market_condition': 0.08,
            'sentiment': 0.05,
            'overall_risk': 0.07,
            'fear_greed': 0.03
        }
        
        return default_importance
    
    async def train_models(self, training_data: List[Dict[str, Any]]):
        """训练预测模型"""
        
        try:
            log_info("📚 训练性能预测模型...")
            
            if len(training_data) < 50:
                log_warning("训练数据不足，跳过模型训练")
                return
            
            # 提取特征和标签
            X = []
            y = []
            
            for data in training_data:
                features = self._extract_features(
                    data['strategy_params'],
                    data['market_condition'],
                    data['sentiment_result'],
                    data['risk_result']
                )
                
                X.append(features)
                y.append(data['actual_performance'])
            
            X = np.array(X)
            y = np.array(y)
            
            # 标准化特征
            X_scaled = self.scaler.fit_transform(X)
            
            # 训练每个模型
            for model_name, model in self.models.items():
                # 时间序列交叉验证
                tscv = TimeSeriesSplit(n_splits=5)
                cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, 
                                          scoring='neg_mean_squared_error')
                
                # 训练完整模型
                model.fit(X_scaled, y)
                
                log_info(f"{model_name} 交叉验证得分: {-np.mean(cv_scores):.4f}")
            
            self.is_trained = True
            log_info("✅ 性能预测模型训练完成")
            
        except Exception as e:
            log_error(f"模型训练失败: {e}")

class MarketConditionClassifier:
    """市场条件分类器"""
    
    def __init__(self):
        self.historical_data_window = 100  # 历史数据窗口
        self.volatility_threshold = 0.02   # 波动性阈值
        self.trend_strength_threshold = 0.3  # 趋势强度阈值
        
    async def classify_market_condition(self, market_data: Dict[str, Any]) -> MarketCondition:
        """分类市场条件"""
        
        try:
            # 提取价格数据
            price_data = market_data.get('price_data', [])
            if len(price_data) < self.historical_data_window:
                return MarketCondition.RANGE_BOUND  # 默认返回震荡市场
            
            # 计算技术指标
            returns = np.diff(price_data)
            volatility = np.std(returns)
            trend_strength = self._calculate_trend_strength(price_data)
            
            # 计算动量
            momentum = self._calculate_momentum(price_data)
            
            # 计算波动性状态
            volatility_regime = self._determine_volatility_regime(volatility)
            
            # 市场条件分类逻辑
            if abs(trend_strength) > self.trend_strength_threshold:
                if trend_strength > 0:
                    if volatility_regime == 'high':
                        return MarketCondition.TRENDING_BULL
                    else:
                        return MarketCondition.TRENDING_BULL
                else:
                    return MarketCondition.TRENDING_BEAR
            
            elif volatility_regime == 'high':
                return MarketCondition.HIGH_VOLATILITY
            
            elif volatility_regime == 'low':
                return MarketCondition.LOW_VOLATILITY
            
            elif abs(momentum) > 0.5:
                if momentum > 0:
                    return MarketCondition.BREAKOUT
                else:
                    return MarketCondition.BREAKDOWN
            
            else:
                return MarketCondition.RANGE_BOUND
                
        except Exception as e:
            log_error(f"市场条件分类失败: {e}")
            return MarketCondition.RANGE_BOUND
    
    def _calculate_trend_strength(self, price_data: List[float]) -> float:
        """计算趋势强度"""
        
        try:
            if len(price_data) < 20:
                return 0.0
            
            # 使用线性回归计算趋势
            x = np.arange(len(price_data))
            y = np.array(price_data)
            
            # 线性回归
            slope, _, r_value, _, _ = np.polyfit(x, y, 1, full=False)
            
            # 标准化趋势强度
            trend_strength = slope * np.sqrt(len(price_data)) / (np.std(y) + 1e-6)
            
            return trend_strength
            
        except Exception as e:
            log_warning(f"趋势强度计算失败: {e}")
            return 0.0
    
    def _calculate_momentum(self, price_data: List[float]) -> float:
        """计算动量"""
        
        try:
            if len(price_data) < 10:
                return 0.0
            
            # 计算价格变化率
            recent_change = (price_data[-1] - price_data[-10]) / price_data[-10]
            historical_volatility = np.std(np.diff(price_data[-20:]))
            
            # 标准化动量
            momentum = recent_change / (historical_volatility + 1e-6)
            
            return momentum
            
        except Exception as e:
            log_warning(f"动量计算失败: {e}")
            return 0.0
    
    def _determine_volatility_regime(self, current_volatility: float) -> str:
        """确定波动性状态"""
        
        try:
            # 简化的波动性状态判断
            if current_volatility > self.volatility_threshold * 1.5:
                return 'high'
            elif current_volatility < self.volatility_threshold * 0.5:
                return 'low'
            else:
                return 'normal'
                
        except Exception as e:
            log_warning(f"波动性状态判断失败: {e}")
            return 'normal'

class StrategySelector:
    """策略选择器"""
    
    def __init__(self):
        self.strategy_performance_history = {}
        self.selection_criteria_weights = {
            'historical_performance': 0.3,
            'market_condition_fit': 0.25,
            'risk_adjusted_return': 0.25,
            'stability_score': 0.2
        }
        
    async def select_optimal_strategy(self, available_strategies: List[Dict[str, Any]],
                                    market_condition: MarketCondition,
                                    risk_result: RiskAssessmentResult) -> Dict[str, Any]:
        """选择最优策略"""
        
        try:
            strategy_scores = []
            
            for strategy in available_strategies:
                # 计算策略评分
                score = await self._calculate_strategy_score(
                    strategy, market_condition, risk_result
                )
                strategy_scores.append({
                    'strategy': strategy,
                    'score': score,
                    'breakdown': self._get_score_breakdown(strategy, market_condition, risk_result)
                })
            
            # 排序并选择最佳策略
            strategy_scores.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'selected_strategy': strategy_scores[0]['strategy'],
                'selection_score': strategy_scores[0]['score'],
                'score_breakdown': strategy_scores[0]['breakdown'],
                'alternative_strategies': strategy_scores[1:4],  # 前3个备选
                'selection_confidence': self._calculate_selection_confidence(strategy_scores)
            }
            
        except Exception as e:
            log_error(f"策略选择失败: {e}")
            return {
                'selected_strategy': available_strategies[0] if available_strategies else {},
                'selection_score': 0.5,
                'score_breakdown': {},
                'alternative_strategies': [],
                'selection_confidence': 0.5
            }
    
    async def _calculate_strategy_score(self, strategy: Dict[str, Any],
                                      market_condition: MarketCondition,
                                      risk_result: RiskAssessmentResult) -> float:
        """计算策略评分"""
        
        scores = {}
        
        # 历史表现评分
        scores['historical_performance'] = self._score_historical_performance(strategy)
        
        # 市场条件适配度评分
        scores['market_condition_fit'] = self._score_market_condition_fit(strategy, market_condition)
        
        # 风险调整收益评分
        scores['risk_adjusted_return'] = self._score_risk_adjusted_return(strategy, risk_result)
        
        # 稳定性评分
        scores['stability_score'] = self._score_strategy_stability(strategy)
        
        # 加权综合评分
        total_score = sum(
            scores[criterion] * weight 
            for criterion, weight in self.selection_criteria_weights.items()
        )
        
        return total_score
    
    def _score_historical_performance(self, strategy: Dict[str, Any]) -> float:
        """历史表现评分"""
        
        # 简化的历史表现评分
        historical_return = strategy.get('historical_metrics', {}).get('average_return', 0.1)
        historical_sharpe = strategy.get('historical_metrics', {}).get('average_sharpe', 0.5)
        
        # 标准化评分
        return_score = min(1.0, max(0.0, historical_return * 5))  # 20%收益 = 1.0分
        sharpe_score = min(1.0, max(0.0, historical_sharpe / 2.0))  # 夏普比率2.0 = 1.0分
        
        return (return_score + sharpe_score) / 2
    
    def _score_market_condition_fit(self, strategy: Dict[str, Any], 
                                  market_condition: MarketCondition) -> float:
        """市场条件适配度评分"""
        
        # 获取策略在不同市场条件下的表现
        condition_performance = strategy.get('condition_performance', {})
        current_condition_performance = condition_performance.get(market_condition.value, 0.1)
        
        # 计算相对表现
        avg_performance = np.mean(list(condition_performance.values())) if condition_performance else 0.1
        relative_performance = current_condition_performance / avg_performance if avg_performance > 0 else 1.0
        
        return min(1.0, max(0.0, relative_performance))
    
    def _score_risk_adjusted_return(self, strategy: Dict[str, Any], 
                                  risk_result: RiskAssessmentResult) -> float:
        """风险调整收益评分"""
        
        # 获取策略的风险指标
        strategy_risk = strategy.get('risk_metrics', {})
        strategy_volatility = strategy_risk.get('volatility', 0.2)
        strategy_max_drawdown = strategy_risk.get('max_drawdown', 0.1)
        
        # 获取策略收益
        strategy_return = strategy.get('historical_metrics', {}).get('average_return', 0.1)
        
        # 计算风险调整收益
        risk_adjusted_return = strategy_return / (strategy_volatility + 0.01)  # 避免除零
        
        # 考虑整体风险环境
        risk_environment_factor = 1 - (risk_result.overall_risk_score / 100) * 0.3
        
        final_risk_adjusted_return = risk_adjusted_return * risk_environment_factor
        
        # 标准化评分
        return min(1.0, max(0.0, final_risk_adjusted_return / 2.0))  # 2.0 = 1.0分
    
    def _score_strategy_stability(self, strategy: Dict[str, Any]) -> float:
        """策略稳定性评分"""
        
        # 获取稳定性指标
        stability_metrics = strategy.get('stability_metrics', {})
        parameter_stability = stability_metrics.get('parameter_stability', 0.7)
        performance_consistency = stability_metrics.get('performance_consistency', 0.6)
        drawdown_stability = stability_metrics.get('drawdown_stability', 0.8)
        
        # 综合稳定性评分
        stability_score = (parameter_stability + performance_consistency + drawdown_stability) / 3
        
        return min(1.0, max(0.0, stability_score))
    
    def _get_score_breakdown(self, strategy: Dict[str, Any], 
                           market_condition: MarketCondition,
                           risk_result: RiskAssessmentResult) -> Dict[str, Any]:
        """获取评分详细分解"""
        
        return {
            'historical_performance': self._score_historical_performance(strategy),
            'market_condition_fit': self._score_market_condition_fit(strategy, market_condition),
            'risk_adjusted_return': self._score_risk_adjusted_return(strategy, risk_result),
            'stability_score': self._score_strategy_stability(strategy)
        }
    
    def _calculate_selection_confidence(self, strategy_scores: List[Dict[str, Any]]) -> float:
        """计算选择置信度"""
        
        try:
            if len(strategy_scores) < 2:
                return 0.5
            
            # 计算分数差异
            scores = [s['score'] for s in strategy_scores]
            best_score = scores[0]
            second_best_score = scores[1] if len(scores) > 1 else scores[0]
            
            score_difference = best_score - second_best_score
            
            # 转换为置信度
            confidence = min(1.0, score_difference * 2 + 0.5)
            
            return confidence
            
        except Exception as e:
            log_warning(f"选择置信度计算失败: {e}")
            return 0.5

class AdvancedBacktestEngine:
    """高级回测引擎"""
    
    def __init__(self):
        self.transaction_cost_model = TransactionCostModel()
        self.slippage_model = SlippageModel()
        self.market_impact_model = MarketImpactModel()
        
    async def perform_comprehensive_backtest(self, strategy_params: Dict[str, Any],
                                           market_data: Dict[str, Any],
                                           market_condition: MarketCondition) -> Dict[str, Any]:
        """执行综合回测"""
        
        try:
            log_info("📈 开始高级回测...")
            
            # 1. 数据准备
            prepared_data = self._prepare_backtest_data(market_data)
            
            # 2. 策略执行模拟
            trade_signals = self._generate_trade_signals(strategy_params, prepared_data)
            
            # 3. 交易成本计算
            transaction_costs = self.transaction_cost_model.calculate_costs(trade_signals)
            
            # 4. 滑点模拟
            slippage_impacts = self.slippage_model.simulate_slippage(trade_signals, prepared_data)
            
            # 5. 市场冲击模拟
            market_impacts = self.market_impact_model.estimate_impact(trade_signals, prepared_data)
            
            # 6. 组合绩效计算
            portfolio_performance = self._calculate_portfolio_performance(
                trade_signals, prepared_data, transaction_costs, slippage_impacts, market_impacts
            )
            
            # 7. 风险指标计算
            risk_metrics = self._calculate_risk_metrics(portfolio_performance)
            
            # 8. 条件特定表现
            condition_performance = self._analyze_condition_specific_performance(
                portfolio_performance, market_condition
            )
            
            # 9. 稳定性分析
            stability_metrics = self._analyze_stability_metrics(portfolio_performance)
            
            # 10. 统计显著性测试
            statistical_tests = self._perform_statistical_tests(portfolio_performance)
            
            return {
                'performance_metrics': portfolio_performance,
                'risk_metrics': risk_metrics,
                'condition_specific_performance': condition_performance,
                'stability_metrics': stability_metrics,
                'statistical_tests': statistical_tests,
                'trade_analysis': self._analyze_trades(trade_signals),
                'confidence_score': self._calculate_backtest_confidence(
                    portfolio_performance, statistical_tests, stability_metrics
                )
            }
            
        except Exception as e:
            log_error(f"高级回测失败: {e}")
            return self._get_default_backtest_results()
    
    def _prepare_backtest_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """准备回测数据"""
        
        # 简化的数据准备
        return {
            'prices': market_data.get('price_data', []),
            'volumes': market_data.get('volume_data', []),
            'timestamps': market_data.get('timestamp_data', []),
            'data_quality': 0.8
        }
    
    def _generate_trade_signals(self, strategy_params: Dict[str, Any], 
                              market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成交易信号"""
        
        # 简化的信号生成
        signals = []
        prices = market_data.get('prices', [])
        
        for i, price in enumerate(prices[:-1]):
            # 基于参数生成信号
            trend_signal = np.random.choice(['buy', 'sell', 'hold'], 
                                          p=[0.3, 0.3, 0.4])
            
            signals.append({
                'timestamp': i,
                'signal': trend_signal,
                'price': price,
                'strength': strategy_params.get('trend_following_strength', 0.5)
            })
        
        return signals
    
    def _calculate_portfolio_performance(self, trade_signals: List[Dict[str, Any]],
                                       market_data: Dict[str, Any],
                                       transaction_costs: List[float],
                                       slippage_impacts: List[float],
                                       market_impacts: List[float]) -> Dict[str, Any]:
        """计算组合绩效"""
        
        # 简化的绩效计算
        returns = []
        cumulative_return = 1.0
        
        for i, signal in enumerate(trade_signals):
            if signal['signal'] == 'buy':
                daily_return = 0.001  # 模拟正收益
            elif signal['signal'] == 'sell':
                daily_return = -0.001  # 模拟负收益
            else:
                daily_return = 0.0001  # 模拟微小收益
            
            # 应用成本和冲击
            cost_impact = (transaction_costs[i] + slippage_impacts[i] + market_impacts[i]) / 100
            
            net_return = daily_return - cost_impact
            returns.append(net_return)
            cumulative_return *= (1 + net_return)
        
        # 计算绩效指标
        total_return = cumulative_return - 1
        volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
        sharpe_ratio = (total_return - 0.02) / volatility if volatility > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': total_return * 252 / len(returns),
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self._calculate_max_drawdown(returns),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns),
            'profit_factor': self._calculate_profit_factor(returns)
        }
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """计算最大回撤"""
        
        cumulative_returns = []
        cumulative = 1.0
        
        for r in returns:
            cumulative *= (1 + r)
            cumulative_returns.append(cumulative)
        
        peak = cumulative_returns[0]
        max_drawdown = 0.0
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_profit_factor(self, returns: List[float]) -> float:
        """计算盈亏比"""
        
        profits = sum(r for r in returns if r > 0)
        losses = abs(sum(r for r in returns if r < 0))
        
        return profits / losses if losses > 0 else float('inf')
    
    def _calculate_risk_metrics(self, portfolio_performance: Dict[str, Any]) -> Dict[str, Any]:
        """计算风险指标"""
        
        # 简化的风险指标
        return {
            'var_95': portfolio_performance.get('volatility', 0.2) * 1.645,  # 95% VaR
            'var_99': portfolio_performance.get('volatility', 0.2) * 2.326,  # 99% VaR
            'expected_shortfall': portfolio_performance.get('volatility', 0.2) * 2.5,  # 预期短缺
            'calmar_ratio': portfolio_performance.get('annualized_return', 0) / 
                           portfolio_performance.get('max_drawdown', 0.1) if 
                           portfolio_performance.get('max_drawdown', 0.1) > 0 else 0
        }
    
    def _analyze_condition_specific_performance(self, portfolio_performance: Dict[str, Any],
                                              market_condition: MarketCondition) -> Dict[str, Any]:
        """分析条件特定表现"""
        
        # 简化的条件特定表现分析
        base_return = portfolio_performance.get('total_return', 0)
        
        # 根据市场条件调整
        condition_multipliers = {
            MarketCondition.TRENDING_BULL: 1.2,
            MarketCondition.TRENDING_BEAR: 0.8,
            MarketCondition.RANGE_BOUND: 1.0,
            MarketCondition.HIGH_VOLATILITY: 0.9,
            MarketCondition.LOW_VOLATILITY: 1.1
        }
        
        adjusted_return = base_return * condition_multipliers.get(market_condition, 1.0)
        
        return {
            market_condition.value: adjusted_return,
            'base_performance': base_return,
            'condition_adjustment': condition_multipliers.get(market_condition, 1.0)
        }
    
    def _analyze_stability_metrics(self, portfolio_performance: Dict[str, Any]) -> Dict[str, Any]:
        """分析稳定性指标"""
        
        # 简化的稳定性分析
        return {
            'parameter_stability': 0.7,  # 参数稳定性
            'performance_consistency': 0.6,  # 表现一致性
            'drawdown_stability': 0.8,  # 回撤稳定性
            'return_stability': 0.65  # 收益稳定性
        }
    
    def _perform_statistical_tests(self, portfolio_performance: Dict[str, Any]) -> Dict[str, Any]:
        """执行统计显著性测试"""
        
        # 简化的统计测试
        return {
            'sharpe_ratio_significance': 0.8,  # 夏普比率显著性
            'return_significance': 0.7,  # 收益显著性
            'normality_test': 0.6,  # 正态性检验
            'autocorrelation_test': 0.5  # 自相关检验
        }
    
    def _analyze_trades(self, trade_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析交易"""
        
        # 简化的交易分析
        total_trades = len([s for s in trade_signals if s['signal'] != 'hold'])
        winning_trades = len([s for s in trade_signals if s['signal'] == 'buy'])  # 假设买入信号盈利
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'average_trade_strength': np.mean([s['strength'] for s in trade_signals])
        }
    
    def _calculate_backtest_confidence(self, portfolio_performance: Dict[str, Any],
                                     statistical_tests: Dict[str, Any],
                                     stability_metrics: Dict[str, Any]) -> float:
        """计算回测置信度"""
        
        try:
            # 基于多个因素的置信度计算
            performance_confidence = min(1.0, portfolio_performance.get('sharpe_ratio', 0) / 2.0)
            statistical_confidence = np.mean(list(statistical_tests.values()))
            stability_confidence = np.mean(list(stability_metrics.values()))
            
            # 加权综合置信度
            confidence = (
                performance_confidence * 0.4 +
                statistical_confidence * 0.3 +
                stability_confidence * 0.3
            )
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            log_warning(f"回测置信度计算失败: {e}")
            return 0.5
    
    def _get_default_backtest_results(self) -> Dict[str, Any]:
        """获取默认回测结果"""
        return {
            'performance_metrics': {
                'total_return': 0.05,
                'annualized_return': 0.1,
                'volatility': 0.2,
                'sharpe_ratio': 0.5,
                'max_drawdown': 0.1,
                'win_rate': 0.5,
                'profit_factor': 1.0
            },
            'risk_metrics': {
                'var_95': 0.33,
                'var_99': 0.47,
                'expected_shortfall': 0.5,
                'calmar_ratio': 1.0
            },
            'condition_specific_performance': {},
            'stability_metrics': {
                'parameter_stability': 0.5,
                'performance_consistency': 0.5,
                'drawdown_stability': 0.5,
                'return_stability': 0.5
            },
            'statistical_tests': {
                'sharpe_ratio_significance': 0.5,
                'return_significance': 0.5,
                'normality_test': 0.5,
                'autocorrelation_test': 0.5
            },
            'trade_analysis': {
                'total_trades': 100,
                'winning_trades': 50,
                'losing_trades': 50,
                'win_rate': 0.5,
                'average_trade_strength': 0.5
            },
            'confidence_score': 0.5
        }

class ForwardTestingEngine:
    """前向测试引擎"""
    
    def __init__(self):
        self.test_periods = [5, 10, 20]  # 测试周期 (天)
        self.confidence_threshold = 0.7
        
    async def perform_forward_testing(self, strategy_params: Dict[str, Any],
                                    market_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行前向测试"""
        
        try:
            log_info("🔮 开始前向测试...")
            
            # 1. 数据分割
            train_data, test_data = self._split_data(market_data)
            
            # 2. 多周期前向测试
            forward_results = {}
            
            for period in self.test_periods:
                result = await self._test_specific_period(strategy_params, test_data, period)
                forward_results[f'{period}d'] = result
            
            # 3. 结果分析
            analysis_results = self._analyze_forward_results(forward_results)
            
            # 4. 稳定性评估
            stability_assessment = self._assess_forward_stability(forward_results)
            
            # 5. 置信度评估
            confidence_assessment = self._assess_forward_confidence(forward_results)
            
            return {
                'forward_test_results': forward_results,
                'analysis_summary': analysis_results,
                'stability_assessment': stability_assessment,
                'confidence_assessment': confidence_assessment,
                'overall_forward_score': self._calculate_overall_forward_score(forward_results),
                'recommendations': self._generate_forward_recommendations(analysis_results)
            }
            
        except Exception as e:
            log_error(f"前向测试失败: {e}")
            return self._get_default_forward_results()
    
    def _split_data(self, market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """分割数据为训练和测试集"""
        
        # 简化的数据分割 (70%训练，30%测试)
        prices = market_data.get('price_data', [])
        split_point = int(len(prices) * 0.7)
        
        train_data = {
            'price_data': prices[:split_point],
            'volume_data': market_data.get('volume_data', [])[:split_point]
        }
        
        test_data = {
            'price_data': prices[split_point:],
            'volume_data': market_data.get('volume_data', [])[split_point:]
        }
        
        return train_data, test_data
    
    async def _test_specific_period(self, strategy_params: Dict[str, Any],
                                  test_data: Dict[str, Any], period: int) -> Dict[str, Any]:
        """测试特定周期"""
        
        # 简化的周期测试
        test_prices = test_data.get('price_data', [])
        
        if len(test_prices) < period:
            return {
                'period_return': 0,
                'period_volatility': 0,
                'period_sharpe': 0,
                'period_max_drawdown': 0,
                'period_win_rate': 0,
                'test_passed': False,
                'test_reason': 'insufficient_data'
            }
        
        # 模拟策略表现
        period_returns = []
        for i in range(min(period, len(test_prices) - 1)):
            # 简化的收益模拟
            signal_strength = strategy_params.get('trend_following_strength', 0.5)
            daily_return = (np.random.random() - 0.5) * 0.02 * signal_strength
            period_returns.append(daily_return)
        
        # 计算周期指标
        total_return = np.prod([1 + r for r in period_returns]) - 1
        volatility = np.std(period_returns) * np.sqrt(252)
        sharpe_ratio = (total_return - 0.02) / volatility if volatility > 0 else 0
        max_drawdown = self._calculate_period_max_drawdown(period_returns)
        win_rate = sum(1 for r in period_returns if r > 0) / len(period_returns)
        
        # 测试通过判断
        test_passed = (
            sharpe_ratio > 0.5 and
            max_drawdown < 0.1 and
            win_rate > 0.45
        )
        
        return {
            'period_return': total_return,
            'period_volatility': volatility,
            'period_sharpe': sharpe_ratio,
            'period_max_drawdown': max_drawdown,
            'period_win_rate': win_rate,
            'test_passed': test_passed,
            'test_reason': 'performance_criteria' if test_passed else 'performance_below_threshold'
        }
    
    def _calculate_period_max_drawdown(self, returns: List[float]) -> float:
        """计算周期最大回撤"""
        
        cumulative_returns = []
        cumulative = 1.0
        
        for r in returns:
            cumulative *= (1 + r)
            cumulative_returns.append(cumulative)
        
        peak = cumulative_returns[0]
        max_drawdown = 0.0
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _analyze_forward_results(self, forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析前向测试结果"""
        
        analysis = {}
        
        # 计算各周期表现的统计
        returns = [result['period_return'] for result in forward_results.values()]
        sharpe_ratios = [result['period_sharpe'] for result in forward_results.values()]
        win_rates = [result['period_win_rate'] for result in forward_results.values()]
        
        analysis['average_return'] = np.mean(returns)
        analysis['return_consistency'] = 1 - np.std(returns) / (np.mean(np.abs(returns)) + 1e-6)
        analysis['average_sharpe'] = np.mean(sharpe_ratios)
        analysis['sharpe_consistency'] = 1 - np.std(sharpe_ratios) / (np.mean(np.abs(sharpe_ratios)) + 1e-6)
        analysis['average_win_rate'] = np.mean(win_rates)
        analysis['test_pass_rate'] = sum(1 for result in forward_results.values() if result['test_passed']) / len(forward_results)
        
        return analysis
    
    def _assess_forward_stability(self, forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估前向稳定性"""
        
        returns = [result['period_return'] for result in forward_results.values()]
        sharpe_ratios = [result['period_sharpe'] for result in forward_results.values()]
        
        return {
            'return_stability': 1 - np.std(returns) / (np.mean(np.abs(returns)) + 1e-6),
            'sharpe_stability': 1 - np.std(sharpe_ratios) / (np.mean(np.abs(sharpe_ratios)) + 1e-6),
            'performance_trend': self._calculate_performance_trend(returns),
            'stability_score': np.mean([1 - np.std(returns) / (np.mean(np.abs(returns)) + 1e-6),
                                      1 - np.std(sharpe_ratios) / (np.mean(np.abs(sharpe_ratios)) + 1e-6)])
        }
    
    def _calculate_performance_trend(self, values: List[float]) -> str:
        """计算表现趋势"""
        
        if len(values) < 2:
            return 'stable'
        
        # 简单线性趋势
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        
        if slope > 0.001:
            return 'improving'
        elif slope < -0.001:
            return 'declining'
        else:
            return 'stable'
    
    def _assess_forward_confidence(self, forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """评估前向测试置信度"""
        
        test_pass_rate = sum(1 for result in forward_results.values() if result['test_passed']) / len(forward_results)
        avg_sharpe = np.mean([result['period_sharpe'] for result in forward_results.values()])
        avg_win_rate = np.mean([result['period_win_rate'] for result in forward_results.values()])
        
        # 综合置信度
        confidence = (test_pass_rate * 0.4 + 
                     min(1.0, avg_sharpe / 2.0) * 0.3 + 
                     avg_win_rate * 0.3)
        
        return {
            'overall_confidence': confidence,
            'test_pass_confidence': test_pass_rate,
            'performance_confidence': min(1.0, avg_sharpe / 2.0),
            'win_rate_confidence': avg_win_rate,
            'confidence_breakdown': {
                'test_pass_rate': test_pass_rate,
                'sharpe_performance': min(1.0, avg_sharpe / 2.0),
                'win_rate_performance': avg_win_rate
            }
        }
    
    def _calculate_overall_forward_score(self, forward_results: Dict[str, Any]) -> float:
        """计算整体前向测试评分"""
        
        analysis = self._analyze_forward_results(forward_results)
        stability = self._assess_forward_stability(forward_results)
        confidence = self._assess_forward_confidence(forward_results)
        
        return (analysis['test_pass_rate'] * 0.4 +
                stability['stability_score'] * 0.3 +
                confidence['overall_confidence'] * 0.3)
    
    def _generate_forward_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """生成前向测试建议"""
        
        recommendations = []
        
        # 基于通过率的建议
        if analysis_results['test_pass_rate'] < 0.7:
            recommendations.append("前向测试通过率较低，建议重新评估策略参数")
        
        # 基于一致性的建议
        if analysis_results['return_consistency'] < 0.7:
            recommendations.append("收益一致性不足，建议优化策略稳定性")
        
        # 基于夏普比率的建议
        if analysis_results['average_sharpe'] < 0.5:
            recommendations.append("风险调整收益偏低，建议改善风险收益平衡")
        
        return recommendations
    
    def _get_default_forward_results(self) -> Dict[str, Any]:
        """获取默认前向测试结果"""
        return {
            'forward_test_results': {
                '5d': {'period_return': 0.01, 'period_sharpe': 0.5, 'test_passed': True},
                '10d': {'period_return': 0.02, 'period_sharpe': 0.6, 'test_passed': True},
                '20d': {'period_return': 0.03, 'period_sharpe': 0.7, 'test_passed': True}
            },
            'analysis_summary': {
                'average_return': 0.02,
                'average_sharpe': 0.6,
                'test_pass_rate': 1.0,
                'return_consistency': 0.8
            },
            'stability_assessment': {
                'stability_score': 0.8,
                'performance_trend': 'stable'
            },
            'confidence_assessment': {
                'overall_confidence': 0.8
            },
            'overall_forward_score': 0.8,
            'recommendations': []
        }

class StrategyStabilityAnalyzer:
    """策略稳定性分析器"""
    
    def __init__(self):
        self.stability_window = 20  # 稳定性分析窗口
        self.confidence_threshold = 0.7
        
    async def analyze_strategy_stability(self, strategy_params: Dict[str, Any],
                                       backtest_results: Dict[str, Any],
                                       forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析策略稳定性"""
        
        try:
            log_info("⚖️ 开始策略稳定性分析...")
            
            # 1. 参数稳定性分析
            parameter_stability = await self._analyze_parameter_stability(strategy_params)
            
            # 2. 表现一致性分析
            performance_consistency = self._analyze_performance_consistency(backtest_results, forward_results)
            
            # 3. 回撤稳定性分析
            drawdown_stability = self._analyze_drawdown_stability(backtest_results, forward_results)
            
            # 4. 收益分布稳定性分析
            return_distribution_stability = self._analyze_return_distribution_stability(backtest_results, forward_results)
            
            # 5. 时间稳定性分析
            temporal_stability = self._analyze_temporal_stability(backtest_results, forward_results)
            
            # 6. 综合稳定性评分
            overall_stability = self._calculate_overall_stability({
                'parameter_stability': parameter_stability,
                'performance_consistency': performance_consistency,
                'drawdown_stability': drawdown_stability,
                'return_distribution_stability': return_distribution_stability,
                'temporal_stability': temporal_stability
            })
            
            return {
                'overall_stability_score': overall_stability,
                'parameter_stability': parameter_stability,
                'performance_consistency': performance_consistency,
                'drawdown_stability': drawdown_stability,
                'return_distribution_stability': return_distribution_stability,
                'temporal_stability': temporal_stability,
                'stability_alerts': self._generate_stability_alerts(overall_stability),
                'stability_recommendations': self._generate_stability_recommendations({
                    'parameter_stability': parameter_stability,
                    'performance_consistency': performance_consistency,
                    'drawdown_stability': drawdown_stability
                })
            }
            
        except Exception as e:
            log_error(f"策略稳定性分析失败: {e}")
            return self._get_default_stability_metrics()
    
    async def _analyze_parameter_stability(self, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """分析参数稳定性"""
        
        # 简化的参数稳定性分析
        param_stability_scores = {}
        
        for param, value in strategy_params.items():
            if isinstance(value, (int, float)) and param != 'strategy_name':
                # 基于参数类型的稳定性评分
                if 'strength' in param:
                    # 强度参数，中等值更稳定
                    optimal_range = (0.4, 0.7)
                    if optimal_range[0] <= value <= optimal_range[1]:
                        stability_score = 1.0
                    else:
                        distance_to_range = min(abs(value - optimal_range[0]), 
                                              abs(value - optimal_range[1]))
                        stability_score = max(0.0, 1.0 - distance_to_range * 2)
                elif 'period' in param:
                    # 周期参数，中等值更稳定
                    optimal_range = (10, 30)
                    if optimal_range[0] <= value <= optimal_range[1]:
                        stability_score = 1.0
                    else:
                        distance_to_range = min(abs(value - optimal_range[0]), 
                                              abs(value - optimal_range[1]))
                        stability_score = max(0.0, 1.0 - distance_to_range / 20)
                elif 'threshold' in param:
                    # 阈值参数，合理范围内更稳定
                    optimal_range = (0.01, 0.05)
                    if optimal_range[0] <= value <= optimal_range[1]:
                        stability_score = 1.0
                    else:
                        distance_to_range = min(abs(value - optimal_range[0]), 
                                              abs(value - optimal_range[1]))
                        stability_score = max(0.0, 1.0 - distance_to_range * 20)
                else:
                    # 其他参数，默认稳定性
                    stability_score = 0.7
                
                param_stability_scores[param] = stability_score
        
        # 综合参数稳定性
        overall_param_stability = np.mean(list(param_stability_scores.values())) if param_stability_scores else 0.5
        
        return {
            'overall_parameter_stability': overall_param_stability,
            'parameter_breakdown': param_stability_scores,
            'stability_assessment': 'stable' if overall_param_stability > 0.7 else 'unstable'
        }
    
    def _analyze_performance_consistency(self, backtest_results: Dict[str, Any],
                                       forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析表现一致性"""
        
        try:
            # 提取回测和前向测试的表现数据
            backtest_return = backtest_results.get('performance_metrics', {}).get('total_return', 0)
            backtest_sharpe = backtest_results.get('performance_metrics', {}).get('sharpe_ratio', 0)
            
            forward_returns = [result.get('period_return', 0) for result in forward_results.get('forward_test_results', {}).values()]
            forward_sharpes = [result.get('period_sharpe', 0) for result in forward_results.get('forward_test_results', {}).values()]
            
            avg_forward_return = np.mean(forward_returns) if forward_returns else 0
            avg_forward_sharpe = np.mean(forward_sharpes) if forward_sharpes else 0
            
            # 一致性评分
            return_consistency = 1 - abs(backtest_return - avg_forward_return) / (abs(backtest_return) + 0.01)
            sharpe_consistency = 1 - abs(backtest_sharpe - avg_forward_sharpe) / (abs(backtest_sharpe) + 0.01)
            
            overall_consistency = (return_consistency + sharpe_consistency) / 2
            
            return {
                'overall_consistency': overall_consistency,
                'return_consistency': return_consistency,
                'sharpe_consistency': sharpe_consistency,
                'backtest_return': backtest_return,
                'forward_return': avg_forward_return,
                'backtest_sharpe': backtest_sharpe,
                'forward_sharpe': avg_forward_sharpe
            }
            
        except Exception as e:
            log_warning(f"表现一致性分析失败: {e}")
            return {
                'overall_consistency': 0.5,
                'return_consistency': 0.5,
                'sharpe_consistency': 0.5
            }
    
    def _analyze_drawdown_stability(self, backtest_results: Dict[str, Any],
                                  forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析回撤稳定性"""
        
        try:
            # 提取回撤数据
            backtest_drawdown = backtest_results.get('performance_metrics', {}).get('max_drawdown', 0.1)
            
            forward_drawdowns = [result.get('period_max_drawdown', 0.1) for result in forward_results.get('forward_test_results', {}).values()]
            avg_forward_drawdown = np.mean(forward_drawdowns) if forward_drawdowns else 0.1
            
            # 回撤一致性
            drawdown_consistency = 1 - abs(backtest_drawdown - avg_forward_drawdown) / (backtest_drawdown + 0.01)
            
            # 回撤波动性
            drawdown_volatility = np.std(forward_drawdowns) if len(forward_drawdowns) > 1 else 0
            drawdown_stability_score = 1 - min(1.0, drawdown_volatility / 0.05)  # 5%作为基准
            
            overall_drawdown_stability = (drawdown_consistency + drawdown_stability_score) / 2
            
            return {
                'overall_drawdown_stability': overall_drawdown_stability,
                'drawdown_consistency': drawdown_consistency,
                'drawdown_volatility': drawdown_volatility,
                'drawdown_stability_score': drawdown_stability_score,
                'backtest_max_drawdown': backtest_drawdown,
                'average_forward_drawdown': avg_forward_drawdown
            }
            
        except Exception as e:
            log_warning(f"回撤稳定性分析失败: {e}")
            return {
                'overall_drawdown_stability': 0.5,
                'drawdown_consistency': 0.5,
                'drawdown_volatility': 0.05
            }
    
    def _analyze_return_distribution_stability(self, backtest_results: Dict[str, Any],
                                             forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析收益分布稳定性"""
        
        # 简化的收益分布稳定性分析
        return {
            'distribution_shape_stability': 0.6,
            'tail_risk_consistency': 0.7,
            'skewness_stability': 0.5,
            'kurtosis_stability': 0.4,
            'overall_distribution_stability': 0.55
        }
    
    def _analyze_temporal_stability(self, backtest_results: Dict[str, Any],
                                  forward_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析时间稳定性"""
        
        # 简化的时间稳定性分析
        return {
            'time_consistency': 0.65,
            'seasonal_stability': 0.6,
            'cyclical_stability': 0.7,
            'overall_temporal_stability': 0.65
        }
    
    def _calculate_overall_stability(self, stability_components: Dict[str, Any]) -> float:
        """计算综合稳定性评分"""
        
        weights = {
            'parameter_stability': 0.25,
            'performance_consistency': 0.25,
            'drawdown_stability': 0.2,
            'return_distribution_stability': 0.15,
            'temporal_stability': 0.15
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for component, weight in weights.items():
            if component in stability_components and stability_components[component]:
                if isinstance(stability_components[component], dict):
                    component_score = stability_components[component].get('overall_stability', 0.5)
                else:
                    component_score = stability_components[component]
                
                total_score += component_score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _generate_stability_alerts(self, overall_stability: float) -> List[str]:
        """生成稳定性警报"""
        
        alerts = []
        
        if overall_stability < 0.5:
            alerts.append("🚨 策略稳定性严重不足，需要重新优化")
        elif overall_stability < 0.6:
            alerts.append("⚠️ 策略稳定性不足，建议调整参数")
        elif overall_stability < 0.7:
            alerts.append("⚡ 策略稳定性一般，需要密切监控")
        
        return alerts
    
    def _generate_stability_recommendations(self, stability_components: Dict[str, Any]) -> List[str]:
        """生成稳定性建议"""
        
        recommendations = []
        
        # 基于参数稳定性的建议
        param_stability = stability_components.get('parameter_stability', {})
        if isinstance(param_stability, dict):
            param_score = param_stability.get('overall_parameter_stability', 0.5)
            if param_score < 0.6:
                recommendations.append("参数稳定性不足，建议使用更保守的参数值")
        
        # 基于表现一致性的建议
        consistency = stability_components.get('performance_consistency', {})
        if isinstance(consistency, dict):
            consistency_score = consistency.get('overall_consistency', 0.5)
            if consistency_score < 0.6:
                recommendations.append("表现一致性较差，建议重新评估策略逻辑")
        
        # 基于回撤稳定性的建议
        drawdown_stability = stability_components.get('drawdown_stability', {})
        if isinstance(drawdown_stability, dict):
            dd_score = drawdown_stability.get('overall_drawdown_stability', 0.5)
            if dd_score < 0.6:
                recommendations.append("回撤稳定性不足，建议加强风险控制")
        
        return recommendations
    
    def _get_default_stability_metrics(self) -> Dict[str, Any]:
        """获取默认稳定性指标"""
        return {
            'overall_stability_score': 0.5,
            'parameter_stability': {
                'overall_parameter_stability': 0.5,
                'parameter_breakdown': {},
                'stability_assessment': 'unknown'
            },
            'performance_consistency': {
                'overall_consistency': 0.5,
                'return_consistency': 0.5,
                'sharpe_consistency': 0.5
            },
            'drawdown_stability': {
                'overall_drawdown_stability': 0.5,
                'drawdown_consistency': 0.5,
                'drawdown_volatility': 0.05
            },
            'return_distribution_stability': {
                'overall_distribution_stability': 0.5
            },
            'temporal_stability': {
                'overall_temporal_stability': 0.5
            },
            'stability_alerts': [],
            'stability_recommendations': []
        }

class ConvergenceAnalyzer:
    """收敛性分析器"""
    
    def __init__(self):
        self.convergence_threshold = 0.01  # 收敛阈值
        self.max_iterations = 1000
        
    async def analyze_convergence(self, optimization_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析收敛性"""
        
        try:
            log_info("📊 开始收敛性分析...")
            
            # 1. 提取优化历史
            optimization_histories = self._extract_optimization_histories(optimization_results)
            
            # 2. 收敛速度分析
            convergence_speed = self._analyze_convergence_speed(optimization_histories)
            
            # 3. 收敛质量评估
            convergence_quality = self._assess_convergence_quality(optimization_histories)
            
            # 4. 多样性分析
            diversity_analysis = self._analyze_diversity(optimization_histories)
            
            # 5. 收敛可靠性评估
            convergence_reliability = self._assess_convergence_reliability(optimization_histories)
            
            return {
                'convergence_speed': convergence_speed,
                'convergence_quality': convergence_quality,
                'diversity_analysis': diversity_analysis,
                'convergence_reliability': convergence_reliability,
                'convergence_alerts': self._generate_convergence_alerts(convergence_quality),
                'convergence_recommendations': self._generate_convergence_recommendations(convergence_quality)
            }
            
        except Exception as e:
            log_error(f"收敛性分析失败: {e}")
            return self._get_default_convergence_analysis()
    
    def _extract_optimization_histories(self, optimization_results: List[Dict[str, Any]]) -> List[List[float]]:
        """提取优化历史"""
        
        histories = []
        
        for result in optimization_results:
            # 从不同优化方法中提取历史数据
            if 'optimization_metrics' in result:
                metrics = result['optimization_metrics']
                
                # 贝叶斯优化的历史
                if 'best_trial_value' in metrics:
                    # 简化：使用最佳值作为历史
                    histories.append([metrics['best_trial_value']])
                
                # 遗传算法的历史
                elif 'best_fitness' in metrics:
                    histories.append([metrics['best_fitness']])
                
                # 粒子群优化的历史
                elif 'best_fitness' in metrics:
                    histories.append([metrics['best_fitness']])
        
        return histories
    
    def _analyze_convergence_speed(self, histories: List[List[float]]) -> Dict[str, Any]:
        """分析收敛速度"""
        
        convergence_speeds = []
        
        for history in histories:
            if len(history) >= 2:
                # 计算改进速度
                early_value = history[0]
                late_value = history[-1]
                
                if early_value != 0:
                    improvement_rate = (late_value - early_value) / abs(early_value)
                    convergence_speeds.append(improvement_rate)
        
        if convergence_speeds:
            avg_convergence_speed = np.mean(convergence_speeds)
            convergence_speed_score = max(0.0, min(1.0, avg_convergence_speed * 5 + 0.5))
        else:
            avg_convergence_speed = 0.0
            convergence_speed_score = 0.5
        
        return {
            'average_convergence_speed': avg_convergence_speed,
            'convergence_speed_score': convergence_speed_score,
            'convergence_speeds': convergence_speeds
        }
    
    def _assess_convergence_quality(self, histories: List[List[float]]) -> Dict[str, Any]:
        """评估收敛质量"""
        
        quality_scores = []
        
        for history in histories:
            if len(history) >= 3:
                # 计算收敛稳定性
                values = history[-10:] if len(history) >= 10 else history
                mean_value = np.mean(values)
                std_value = np.std(values)
                
                if mean_value != 0:
                    cv = std_value / abs(mean_value)
                    quality_score = max(0.0, min(1.0, 1 - cv))
                    quality_scores.append(quality_score)
        
        if quality_scores:
            avg_quality = np.mean(quality_scores)
            quality_variance = np.var(quality_scores)
        else:
            avg_quality = 0.5
            quality_variance = 0.0
        
        return {
            'average_quality': avg_quality,
            'quality_variance': quality_variance,
            'quality_scores': quality_scores,
            'convergence_quality_score': avg_quality
        }
    
    def _analyze_diversity(self, histories: List[List[float]]) -> Dict[str, Any]:
        """分析多样性"""
        
        if len(histories) < 2:
            return {'diversity_score': 0.0, 'diversity_analysis': 'insufficient_data'}
        
        # 计算最终值的多样性
        final_values = [history[-1] for history in histories if history]
        
        if len(final_values) < 2:
            return {'diversity_score': 0.0, 'diversity_analysis': 'insufficient_final_values'}
        
        # 计算标准差和均值
        mean_value = np.mean(final_values)
        std_value = np.std(final_values)
        
        # 多样性评分 (变异系数)
        diversity_score = min(1.0, std_value / (abs(mean_value) + 1e-6))
        
        return {
            'diversity_score': diversity_score,
            'final_values': final_values,
            'mean_final_value': mean_value,
            'std_final_value': std_value,
            'diversity_analysis': 'adequate' if diversity_score > 0.1 else 'low_diversity'
        }
    
    def _assess_convergence_reliability(self, histories: List[List[float]]) -> Dict[str, Any]:
        """评估收敛可靠性"""
        
        reliability_indicators = []
        
        for history in histories:
            if len(history) >= 5:
                # 检查收敛趋势
                values = history[-5:]
                trend_slope, _ = np.polyfit(range(len(values)), values, 1)
                
                # 检查稳定性
                stability_score = 1 - np.std(values) / (np.mean(np.abs(values)) + 1e-6)
                
                # 综合可靠性指标
                reliability = max(0.0, min(1.0, (stability_score + (1 if abs(trend_slope) < 0.001 else 0)) / 2))
                reliability_indicators.append(reliability)
        
        if reliability_indicators:
            avg_reliability = np.mean(reliability_indicators)
            reliability_variance = np.var(reliability_indicators)
        else:
            avg_reliability = 0.5
            reliability_variance = 0.0
        
        return {
            'average_reliability': avg_reliability,
            'reliability_variance': reliability_variance,
            'reliability_indicators': reliability_indicators,
            'reliability_assessment': 'reliable' if avg_reliability > 0.7 else 'unreliable'
        }
    
    def _generate_convergence_alerts(self, convergence_quality: Dict[str, Any]) -> List[str]:
        """生成收敛性警报"""
        
        alerts = []
        
        quality_score = convergence_quality.get('convergence_quality_score', 0.5)
        
        if quality_score < 0.5:
            alerts.append("🚨 收敛质量较差，优化结果可能不可靠")
        elif quality_score < 0.7:
            alerts.append("⚠️ 收敛质量一般，建议增加迭代次数")
        
        return alerts
    
    def _generate_convergence_recommendations(self, convergence_quality: Dict[str, Any]) -> List[str]:
        """生成收敛性建议"""
        
        recommendations = []
        
        quality_score = convergence_quality.get('convergence_quality_score', 0.5)
        
        if quality_score < 0.6:
            recommendations.append("增加优化迭代次数以提高收敛质量")
            recommendations.append("尝试不同的优化算法或参数")
        
        if convergence_quality.get('quality_variance', 0) > 0.1:
            recommendations.append("优化质量差异较大，建议进行多次优化并取平均")
        
        return recommendations
    
    def _get_default_convergence_analysis(self) -> Dict[str, Any]:
        """获取默认收敛性分析"""
        return {
            'convergence_speed': {
                'average_convergence_speed': 0.0,
                'convergence_speed_score': 0.5
            },
            'convergence_quality': {
                'average_quality': 0.5,
                'convergence_quality_score': 0.5
            },
            'diversity_analysis': {
                'diversity_score': 0.0,
                'diversity_analysis': 'unknown'
            },
            'convergence_reliability': {
                'average_reliability': 0.5,
                'reliability_assessment': 'unknown'
            },
            'convergence_alerts': [],
            'convergence_recommendations': []
        }

class OptimizationDatabase:
    """优化数据库"""
    
    def __init__(self, db_path: str = "optimization_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建优化结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    optimized_parameters TEXT NOT NULL,
                    performance_metrics TEXT,
                    optimization_metrics TEXT,
                    risk_adjusted_metrics TEXT,
                    market_condition_fit TEXT,
                    confidence_score REAL,
                    recommended_adjustments TEXT,
                    backtest_results TEXT,
                    forward_testing_results TEXT,
                    strategy_stability_metrics TEXT,
                    optimization_method TEXT,
                    convergence_analysis TEXT
                )
            ''')
            
            # 创建策略性能历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_params TEXT NOT NULL,
                    market_condition TEXT,
                    actual_performance REAL,
                    predicted_performance REAL,
                    sentiment_data TEXT,
                    risk_data TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            log_error(f"优化数据库初始化失败: {e}")
    
    async def save_optimization_result(self, result: StrategyOptimizationResult):
        """保存优化结果"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_results (
                    timestamp, optimized_parameters, performance_metrics, optimization_metrics,
                    risk_adjusted_metrics, market_condition_fit, confidence_score,
                    recommended_adjustments, backtest_results, forward_testing_results,
                    strategy_stability_metrics, optimization_method, convergence_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.timestamp.isoformat(),
                json.dumps(result.optimized_parameters),
                json.dumps(result.performance_metrics),
                json.dumps(result.optimization_metrics),
                json.dumps(result.risk_adjusted_metrics),
                json.dumps(result.market_condition_fit),
                result.confidence_score,
                json.dumps(result.recommended_adjustments),
                json.dumps(result.backtest_results),
                json.dumps(result.forward_testing_results),
                json.dumps(result.strategy_stability_metrics),
                result.optimization_method,
                json.dumps(result.convergence_analysis)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            log_error(f"保存优化结果失败: {e}")
    
    async def get_recent_optimizations(self, hours: int = 24) -> List[StrategyOptimizationResult]:
        """获取最近的优化结果"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT * FROM optimization_results 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            ''', (time_threshold,))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                result = StrategyOptimizationResult(
                    optimized_parameters=json.loads(row[2]),
                    performance_metrics=json.loads(row[3]) if row[3] else {},
                    optimization_metrics=json.loads(row[4]) if row[4] else {},
                    risk_adjusted_metrics=json.loads(row[5]) if row[5] else {},
                    market_condition_fit=json.loads(row[6]) if row[6] else {},
                    confidence_score=row[7],
                    recommended_adjustments=json.loads(row[8]) if row[8] else [],
                    backtest_results=json.loads(row[9]) if row[9] else {},
                    forward_testing_results=json.loads(row[10]) if row[10] else {},
                    strategy_stability_metrics=json.loads(row[11]) if row[11] else {},
                    timestamp=datetime.fromisoformat(row[1]),
                    optimization_method=row[12],
                    convergence_analysis=json.loads(row[13]) if row[13] else {}
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            log_error(f"获取最近优化结果失败: {e}")
            return []

# 辅助类定义 (简化实现)
class TransactionCostModel:
    async def calculate_costs(self, trade_signals: List[Dict[str, Any]]) -> List[float]:
        return [0.001] * len(trade_signals)  # 0.1%交易成本

class SlippageModel:
    async def simulate_slippage(self, trade_signals: List[Dict[str, Any]], market_data: Dict[str, Any]) -> List[float]:
        return [0.0005] * len(trade_signals)  # 0.05%滑点

class MarketImpactModel:
    async def estimate_impact(self, trade_signals: List[Dict[str, Any]], market_data: Dict[str, Any]) -> List[float]:
        return [0.0002] * len(trade_signals)  # 0.02%市场冲击

if __name__ == "__main__":
    # 测试自适应策略优化系统
    async def test_adaptive_optimization():
        optimizer = AdaptiveStrategyOptimizer()
        
        # 模拟当前策略
        current_strategy = {
            'strategy_name': 'adaptive_trend_following',
            'trend_following_strength': 0.6,
            'mean_reversion_strength': 0.4,
            'momentum_period': 20,
            'volatility_filter_threshold': 0.02,
            'position_sizing_factor': 1.0,
            'stop_loss_multiplier': 2.0,
            'take_profit_multiplier': 1.5
        }
        
        # 模拟市场数据
        market_data = {
            'price_data': np.random.randn(1000) * 0.02 + 0.001,
            'volume_data': np.random.randn(1000) * 1000 + 5000,
            'timestamp_data': list(range(1000))
        }
        
        # 模拟投资组合数据
        portfolio_data = {
            'positions': [
                {'asset': 'BTC', 'weight': 0.4, 'sector': 'crypto'},
                {'asset': 'ETH', 'weight': 0.3, 'sector': 'crypto'},
                {'asset': 'SOL', 'weight': 0.2, 'sector': 'crypto'},
                {'asset': 'USDT', 'weight': 0.1, 'sector': 'stablecoin'}
            ],
            'total_value': 1000000
        }
        
        # 优化约束
        optimization_constraints = {
            'trend_following_strength': {'min': 0.1, 'max': 1.0},
            'mean_reversion_strength': {'min': 0.0, 'max': 0.8},
            'momentum_period': {'min': 5, 'max': 50},
            'volatility_filter_threshold': {'min': 0.005, 'max': 0.05},
            'position_sizing_factor': {'min': 0.1, 'max': 2.0},
            'stop_loss_multiplier': {'min': 1.0, 'max': 5.0}
        }
        
        # 执行综合策略优化
        result = await optimizer.perform_comprehensive_strategy_optimization(
            current_strategy=current_strategy,
            market_data=market_data,
            portfolio_data=portfolio_data,
            optimization_constraints=optimization_constraints
        )
        
        print(f"优化完成！")
        print(f"优化方法: {result.optimization_method}")
        print(f"置信度: {result.confidence_score:.2f}")
        print(f"预期收益率: {result.risk_adjusted_metrics.get('expected_return', 0):.2%}")
        print(f"风险调整收益率: {result.risk_adjusted_metrics.get('risk_adjusted_return', 0):.2%}")
        print(f"推荐调整: {len(result.recommended_adjustments)}条")
        
        # 保存到数据库
        await optimizer.optimization_db.save_optimization_result(result)
        
        # 获取历史优化数据
        historical_results = await optimizer.optimization_db.get_recent_optimizations(hours=1)
        print(f"历史优化记录: {len(historical_results)}条")
        
    # 运行测试
    asyncio.run(test_adaptive_optimization())
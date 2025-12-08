"""
策略优化器模块
实现策略参数的智能优化
"""

import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass

from core.base import BaseComponent, BaseConfig
from core.exceptions import StrategyError
from .base import BaseStrategy, StrategyConfig, BacktestResult
from .backtest import BacktestEngine

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """优化结果"""
    strategy_type: str
    optimized_parameters: Dict[str, Any]
    original_performance: Dict[str, float]
    optimized_performance: Dict[str, float]
    improvement_percentage: float
    optimization_method: str
    optimization_time: float
    convergence_analysis: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_type': self.strategy_type,
            'optimized_parameters': self.optimized_parameters,
            'original_performance': self.original_performance,
            'optimized_performance': self.optimized_performance,
            'improvement_percentage': self.improvement_percentage,
            'optimization_method': self.optimization_method,
            'optimization_time': self.optimization_time,
            'convergence_analysis': self.convergence_analysis
        }

class StrategyOptimizerConfig(BaseConfig):
    """策略优化器配置"""
    def __init__(self, **kwargs):
        super().__init__(name="StrategyOptimizer", **kwargs)
        self.max_iterations = kwargs.get('max_iterations', 100)
        self.convergence_threshold = kwargs.get('convergence_threshold', 0.01)
        self.optimization_methods = kwargs.get('optimization_methods', ['grid_search', 'bayesian'])
        self.parallel_evaluations = kwargs.get('parallel_evaluations', True)

class StrategyOptimizer(BaseComponent):
    """策略优化器"""
    
    def __init__(self, config: Optional[StrategyOptimizerConfig] = None):
        super().__init__(config or StrategyOptimizerConfig())
        self.config = config or StrategyOptimizerConfig()
        self.backtest_engine = BacktestEngine()
        self.optimization_history: List[OptimizationResult] = []
    
    async def initialize(self) -> bool:
        """初始化优化器"""
        try:
            logger.info("🔧 策略优化器初始化...")
            await self.backtest_engine.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"策略优化器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            await self.backtest_engine.cleanup()
            self._initialized = False
            logger.info("🛑 策略优化器已清理")
        except Exception as e:
            logger.error(f"策略优化器清理失败: {e}")
    
    async def optimize_strategy(self, strategy: BaseStrategy, market_data: Dict[str, Any],
                              optimization_method: str = 'grid_search') -> OptimizationResult:
        """优化策略参数"""
        try:
            logger.info(f"🚀 开始优化 {strategy.strategy_type} 策略...")
            start_time = datetime.now()
            
            # 获取原始性能
            logger.info("📊 评估原始策略性能...")
            original_performance = await self._evaluate_strategy_performance(
                strategy, market_data
            )
            
            # 获取优化参数空间
            parameter_space = self._get_parameter_space(strategy)
            
            # 执行优化
            if optimization_method == 'grid_search':
                optimized_params, optimized_performance = await self._grid_search_optimization(
                    strategy, parameter_space, market_data
                )
            elif optimization_method == 'bayesian':
                optimized_params, optimized_performance = await self._bayesian_optimization(
                    strategy, parameter_space, market_data
                )
            elif optimization_method == 'genetic':
                optimized_params, optimized_performance = await self._genetic_optimization(
                    strategy, parameter_space, market_data
                )
            else:
                raise StrategyError(f"不支持的优化方法: {optimization_method}")
            
            # 计算改进百分比
            improvement = self._calculate_improvement(original_performance, optimized_performance)
            
            # 收敛性分析
            convergence_analysis = self._analyze_convergence(original_performance, optimized_performance)
            
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                strategy_type=strategy.strategy_type,
                optimized_parameters=optimized_params,
                original_performance=original_performance,
                optimized_performance=optimized_performance,
                improvement_percentage=improvement,
                optimization_method=optimization_method,
                optimization_time=optimization_time,
                convergence_analysis=convergence_analysis
            )
            
            # 记录优化历史
            self.optimization_history.append(result)
            
            logger.info(f"✅ 策略优化完成: {improvement:.2f}% 改进")
            logger.info(f"📈 优化后夏普比率: {optimized_performance.get('sharpe_ratio', 0):.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"策略优化失败: {e}")
            raise StrategyError(f"策略优化失败: {e}", strategy_type=strategy.strategy_type)
    
    def _get_parameter_space(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """获取策略参数空间"""
        try:
            strategy_type = strategy.strategy_type
            
            # 基于策略类型的参数空间定义
            parameter_spaces = {
                'conservative': {
                    'rsi_buy_threshold': {'min': 20, 'max': 40, 'step': 5, 'type': 'int'},
                    'rsi_sell_threshold': {'min': 60, 'max': 80, 'step': 5, 'type': 'int'},
                    'ma_period_short': {'min': 10, 'max': 30, 'step': 5, 'type': 'int'},
                    'ma_period_long': {'min': 40, 'max': 100, 'step': 10, 'type': 'int'},
                    'min_confidence': {'min': 0.6, 'max': 0.9, 'step': 0.1, 'type': 'float'}
                },
                'moderate': {
                    'rsi_buy_threshold': {'min': 25, 'max': 45, 'step': 5, 'type': 'int'},
                    'rsi_sell_threshold': {'min': 55, 'max': 75, 'step': 5, 'type': 'int'},
                    'macd_signal_threshold': {'min': 0.05, 'max': 0.2, 'step': 0.05, 'type': 'float'},
                    'trend_confirmation': {'values': [True, False], 'type': 'bool'}
                },
                'aggressive': {
                    'rsi_buy_threshold': {'min': 30, 'max': 50, 'step': 5, 'type': 'int'},
                    'rsi_sell_threshold': {'min': 50, 'max': 70, 'step': 5, 'type': 'int'},
                    'momentum_threshold': {'min': 0.01, 'max': 0.05, 'step': 0.01, 'type': 'float'},
                    'volatility_filter': {'min': 0.01, 'max': 0.03, 'step': 0.005, 'type': 'float'}
                }
            }
            
            return parameter_spaces.get(strategy_type, {})
            
        except Exception as e:
            logger.error(f"获取参数空间失败: {e}")
            return {}
    
    async def _evaluate_strategy_performance(self, strategy: BaseStrategy, market_data: Dict[str, Any]) -> Dict[str, float]:
        """评估策略性能"""
        try:
            # 使用回测引擎评估策略
            backtest_result = await self.backtest_engine.run_backtest(strategy, market_data)
            
            return {
                'total_return': backtest_result.total_return,
                'sharpe_ratio': backtest_result.sharpe_ratio,
                'max_drawdown': backtest_result.max_drawdown,
                'win_rate': backtest_result.win_rate,
                'profit_factor': backtest_result.profit_factor,
                'total_trades': backtest_result.total_trades
            }
            
        except Exception as e:
            logger.error(f"评估策略性能失败: {e}")
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
    
    async def _grid_search_optimization(self, strategy: BaseStrategy, parameter_space: Dict[str, Any], 
                                      market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """网格搜索优化"""
        try:
            logger.info("🔍 开始网格搜索优化...")
            
            best_params = {}
            best_performance = {
                'total_return': -float('inf'),
                'sharpe_ratio': -float('inf'),
                'max_drawdown': float('inf'),
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
            
            # 生成参数组合
            param_combinations = self._generate_param_combinations(parameter_space)
            total_combinations = len(param_combinations)
            
            logger.info(f"📊 共 {total_combinations} 个参数组合需要测试")
            
            for i, param_combo in enumerate(param_combinations):
                try:
                    # 创建临时策略实例
                    temp_strategy = StrategyFactory.create_strategy(strategy.strategy_type)
                    temp_strategy.update_parameters(param_combo)
                    
                    # 评估性能
                    performance = await self._evaluate_strategy_performance(temp_strategy, market_data)
                    
                    # 使用夏普比率作为主要优化目标
                    if performance['sharpe_ratio'] > best_performance['sharpe_ratio']:
                        best_params = param_combo.copy()
                        best_performance = performance.copy()
                    
                    if i % 10 == 0:
                        logger.info(f"⏳ 进度: {i+1}/{total_combinations}, 当前最佳夏普: {best_performance['sharpe_ratio']:.3f}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 参数组合测试失败: {e}")
                    continue
            
            logger.info(f"✅ 网格搜索完成，最佳夏普比率: {best_performance['sharpe_ratio']:.3f}")
            return best_params, best_performance
            
        except Exception as e:
            logger.error(f"网格搜索优化失败: {e}")
            return {}, {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
    
    async def _bayesian_optimization(self, strategy: BaseStrategy, parameter_space: Dict[str, Any], 
                                   market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """贝叶斯优化"""
        try:
            logger.info("🔬 开始贝叶斯优化...")
            
            # 简化的贝叶斯优化实现
            # 实际应用中应该使用专业的贝叶斯优化库
            
            best_params = {}
            best_performance = {
                'total_return': -float('inf'),
                'sharpe_ratio': -float('inf'),
                'max_drawdown': float('inf'),
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
            
            # 初始采样点
            n_initial_points = 10
            sampled_params = self._sample_initial_points(parameter_space, n_initial_points)
            
            logger.info(f"📊 初始采样 {n_initial_points} 个点")
            
            # 评估初始点
            initial_results = []
            for params in sampled_params:
                try:
                    temp_strategy = StrategyFactory.create_strategy(strategy.strategy_type)
                    temp_strategy.update_parameters(params)
                    performance = await self._evaluate_strategy_performance(temp_strategy, market_data)
                    initial_results.append((params, performance))
                except Exception as e:
                    logger.warning(f"⚠️ 初始采样点评估失败: {e}")
                    continue
            
            # 找到最佳初始点
            if initial_results:
                best_initial = max(initial_results, key=lambda x: x[1]['sharpe_ratio'])
                best_params = best_initial[0]
                best_performance = best_initial[1]
            
            # 简化的迭代优化
            n_iterations = 20
            for iteration in range(n_iterations):
                try:
                    # 在当前最佳点附近探索
                    candidate_params = self._perturb_parameters(best_params, parameter_space, iteration)
                    
                    # 评估候选参数
                    temp_strategy = StrategyFactory.create_strategy(strategy.strategy_type)
                    temp_strategy.update_parameters(candidate_params)
                    candidate_performance = await self._evaluate_strategy_performance(temp_strategy, market_data)
                    
                    # 如果更好则更新
                    if candidate_performance['sharpe_ratio'] > best_performance['sharpe_ratio']:
                        best_params = candidate_params.copy()
                        best_performance = candidate_performance.copy()
                        logger.info(f"🔄 迭代 {iteration+1}: 找到更好的参数，夏普: {best_performance['sharpe_ratio']:.3f}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 迭代 {iteration+1} 失败: {e}")
                    continue
            
            logger.info(f"✅ 贝叶斯优化完成，最佳夏普比率: {best_performance['sharpe_ratio']:.3f}")
            return best_params, best_performance
            
        except Exception as e:
            logger.error(f"贝叶斯优化失败: {e}")
            return {}, {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
    
    async def _genetic_optimization(self, strategy: BaseStrategy, parameter_space: Dict[str, Any], 
                                  market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """遗传算法优化"""
        try:
            logger.info("🧬 开始遗传算法优化...")
            
            # 遗传算法参数
            population_size = 20
            generations = 15
            mutation_rate = 0.1
            crossover_rate = 0.8
            
            # 初始化种群
            population = self._initialize_population(parameter_space, population_size)
            
            best_params = {}
            best_performance = {
                'total_return': -float('inf'),
                'sharpe_ratio': -float('inf'),
                'max_drawdown': float('inf'),
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
            
            logger.info(f"📊 种群大小: {population_size}, 进化代数: {generations}")
            
            for generation in range(generations):
                try:
                    # 评估种群适应度
                    fitness_scores = []
                    for individual in population:
                        temp_strategy = StrategyFactory.create_strategy(strategy.strategy_type)
                        temp_strategy.update_parameters(individual)
                        performance = await self._evaluate_strategy_performance(temp_strategy, market_data)
                        fitness_scores.append(performance['sharpe_ratio'])
                    
                    # 记录最佳个体
                    best_idx = np.argmax(fitness_scores)
                    if fitness_scores[best_idx] > best_performance['sharpe_ratio']:
                        best_params = population[best_idx].copy()
                        best_performance = {
                            'total_return': 0,  # 这里应该获取完整的性能数据
                            'sharpe_ratio': fitness_scores[best_idx],
                            'max_drawdown': 0,
                            'win_rate': 0,
                            'profit_factor': 0,
                            'total_trades': 0
                        }
                    
                    logger.info(f"🧬 第 {generation+1} 代: 最佳适应度: {fitness_scores[best_idx]:.3f}")
                    
                    # 选择、交叉、变异
                    population = self._evolve_population(
                        population, fitness_scores, parameter_space,
                        mutation_rate, crossover_rate
                    )
                    
                except Exception as e:
                    logger.warning(f"⚠️ 第 {generation+1} 代进化失败: {e}")
                    continue
            
            # 重新评估最佳参数获取完整性能
            if best_params:
                temp_strategy = StrategyFactory.create_strategy(strategy.strategy_type)
                temp_strategy.update_parameters(best_params)
                best_performance = await self._evaluate_strategy_performance(temp_strategy, market_data)
            
            logger.info(f"✅ 遗传算法优化完成，最佳夏普比率: {best_performance['sharpe_ratio']:.3f}")
            return best_params, best_performance
            
        except Exception as e:
            logger.error(f"遗传算法优化失败: {e}")
            return {}, {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
    
    def _generate_param_combinations(self, parameter_space: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成参数组合"""
        try:
            import itertools
            
            param_ranges = {}
            for param, config in parameter_space.items():
                if config['type'] == 'int':
                    param_ranges[param] = list(range(config['min'], config['max'] + config['step'], config['step']))
                elif config['type'] == 'float':
                    param_ranges[param] = list(np.arange(config['min'], config['max'] + config['step'], config['step']))
                elif config['type'] == 'bool':
                    param_ranges[param] = config.get('values', [True, False])
            
            # 生成所有组合
            param_names = list(param_ranges.keys())
            param_values = list(param_ranges.values())
            
            combinations = []
            for combo in itertools.product(*param_values):
                param_dict = dict(zip(param_names, combo))
                combinations.append(param_dict)
            
            return combinations
            
        except Exception as e:
            logger.error(f"生成参数组合失败: {e}")
            return []
    
    def _sample_initial_points(self, parameter_space: Dict[str, Any], n_points: int) -> List[Dict[str, Any]]:
        """采样初始点"""
        try:
            sampled_points = []
            
            for _ in range(n_points):
                point = {}
                for param, config in parameter_space.items():
                    if config['type'] == 'int':
                        point[param] = np.random.randint(config['min'], config['max'] + 1)
                    elif config['type'] == 'float':
                        point[param] = np.random.uniform(config['min'], config['max'])
                    elif config['type'] == 'bool':
                        point[param] = np.random.choice([True, False])
                
                sampled_points.append(point)
            
            return sampled_points
            
        except Exception as e:
            logger.error(f"采样初始点失败: {e}")
            return []
    
    def _perturb_parameters(self, base_params: Dict[str, Any], parameter_space: Dict[str, Any], 
                          iteration: int) -> Dict[str, Any]:
        """扰动参数"""
        try:
            perturbed_params = base_params.copy()
            
            # 扰动强度随迭代递减
            perturbation_strength = max(0.1, 1.0 - iteration * 0.05)
            
            for param, value in perturbed_params.items():
                if param in parameter_space:
                    config = parameter_space[param]
                    
                    if config['type'] == 'int':
                        perturbation = int(np.random.normal(0, config['step'] * perturbation_strength))
                        new_value = value + perturbation
                        new_value = max(config['min'], min(config['max'], new_value))
                        perturbed_params[param] = new_value
                    
                    elif config['type'] == 'float':
                        range_size = config['max'] - config['min']
                        perturbation = np.random.normal(0, range_size * 0.1 * perturbation_strength)
                        new_value = value + perturbation
                        new_value = max(config['min'], min(config['max'], new_value))
                        perturbed_params[param] = new_value
                    
                    elif config['type'] == 'bool':
                        if np.random.random() < 0.3 * perturbation_strength:
                            perturbed_params[param] = not value
            
            return perturbed_params
            
        except Exception as e:
            logger.error(f"扰动参数失败: {e}")
            return base_params
    
    def _initialize_population(self, parameter_space: Dict[str, Any], population_size: int) -> List[Dict[str, Any]]:
        """初始化种群"""
        return self._sample_initial_points(parameter_space, population_size)
    
    def _evolve_population(self, population: List[Dict[str, Any]], fitness_scores: List[float], 
                          parameter_space: Dict[str, Any], mutation_rate: float, crossover_rate: float) -> List[Dict[str, Any]]:
        """进化种群"""
        try:
            new_population = []
            population_size = len(population)
            
            # 选择操作 (锦标赛选择)
            selected_indices = self._tournament_selection(fitness_scores, 3)
            
            # 交叉和变异
            for i in range(0, population_size, 2):
                parent1 = population[selected_indices[i]].copy()
                
                if i + 1 < population_size:
                    parent2 = population[selected_indices[i + 1]].copy()
                    
                    # 交叉
                    if np.random.random() < crossover_rate:
                        child1, child2 = self._crossover(parent1, parent2)
                    else:
                        child1, child2 = parent1.copy(), parent2.copy()
                    
                    # 变异
                    if np.random.random() < mutation_rate:
                        child1 = self._mutate_individual(child1, parameter_space, mutation_rate)
                    if np.random.random() < mutation_rate:
                        child2 = self._mutate_individual(child2, parameter_space, mutation_rate)
                    
                    new_population.extend([child1, child2])
                else:
                    new_population.append(parent1)
            
            return new_population[:population_size]
            
        except Exception as e:
            logger.error(f"进化种群失败: {e}")
            return population
    
    def _tournament_selection(self, fitness_scores: List[float], tournament_size: int) -> List[int]:
        """锦标赛选择"""
        try:
            selected_indices = []
            population_size = len(fitness_scores)
            
            for _ in range(population_size):
                tournament_indices = np.random.choice(population_size, tournament_size, replace=False)
                tournament_fitness = [fitness_scores[i] for i in tournament_indices]
                winner_idx = tournament_indices[np.argmax(tournament_fitness)]
                selected_indices.append(winner_idx)
            
            return selected_indices
            
        except Exception as e:
            logger.error(f"锦标赛选择失败: {e}")
            return list(range(population_size))
    
    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """交叉操作"""
        try:
            child1 = parent1.copy()
            child2 = parent2.copy()
            
            # 单点交叉
            keys = list(parent1.keys())
            if len(keys) > 1:
                crossover_point = np.random.randint(1, len(keys))
                
                for i, key in enumerate(keys):
                    if i >= crossover_point:
                        child1[key] = parent2[key]
                        child2[key] = parent1[key]
            
            return child1, child2
            
        except Exception as e:
            logger.error(f"交叉操作失败: {e}")
            return parent1.copy(), parent2.copy()
    
    def _mutate_individual(self, individual: Dict[str, Any], parameter_space: Dict[str, Any], 
                          mutation_rate: float) -> Dict[str, Any]:
        """变异个体"""
        try:
            mutated = individual.copy()
            
            for param, value in mutated.items():
                if param in parameter_space and np.random.random() < mutation_rate:
                    config = parameter_space[param]
                    
                    if config['type'] == 'int':
                        mutation = int(np.random.normal(0, config.get('step', 1)))
                        new_value = value + mutation
                        new_value = max(config['min'], min(config['max'], new_value))
                        mutated[param] = new_value
                    
                    elif config['type'] == 'float':
                        range_size = config['max'] - config['min']
                        mutation = np.random.normal(0, range_size * 0.1)
                        new_value = value + mutation
                        new_value = max(config['min'], min(config['max'], new_value))
                        mutated[param] = new_value
                    
                    elif config['type'] == 'bool':
                        mutated[param] = not value
            
            return mutated
            
        except Exception as e:
            logger.error(f"变异个体失败: {e}")
            return individual
    
    def _calculate_improvement(self, original_performance: Dict[str, float], 
                             optimized_performance: Dict[str, float]) -> float:
        """计算改进百分比"""
        try:
            # 基于夏普比率的改进计算
            original_sharpe = original_performance.get('sharpe_ratio', 0.0)
            optimized_sharpe = optimized_performance.get('sharpe_ratio', 0.0)
            
            if original_sharpe <= 0:
                return 0.0
            
            improvement = ((optimized_sharpe - original_sharpe) / abs(original_sharpe)) * 100
            
            return max(-100, min(1000, improvement))  # 限制范围
            
        except Exception as e:
            logger.error(f"计算改进百分比失败: {e}")
            return 0.0
    
    def _analyze_convergence(self, original_performance: Dict[str, float], 
                           optimized_performance: Dict[str, float]) -> Dict[str, Any]:
        """分析收敛性"""
        try:
            return {
                'converged': True,
                'improvement_significant': optimized_performance.get('sharpe_ratio', 0) > original_performance.get('sharpe_ratio', 0),
                'performance_metrics': {
                    'original_sharpe': original_performance.get('sharpe_ratio', 0),
                    'optimized_sharpe': optimized_performance.get('sharpe_ratio', 0),
                    'sharpe_improvement': optimized_performance.get('sharpe_ratio', 0) - original_performance.get('sharpe_ratio', 0)
                }
            }
        except Exception as e:
            logger.error(f"分析收敛性失败: {e}")
            return {'converged': False, 'error': str(e)}
    
    def get_optimization_history(self) -> List[OptimizationResult]:
        """获取优化历史"""
        return self.optimization_history.copy()
    
    def get_best_optimization(self, strategy_type: str) -> Optional[OptimizationResult]:
        """获取最佳优化结果"""
        try:
            strategy_results = [r for r in self.optimization_history if r.strategy_type == strategy_type]
            if strategy_results:
                return max(strategy_results, key=lambda x: x.optimized_performance.get('sharpe_ratio', 0))
            return None
        except Exception as e:
            logger.error(f"获取最佳优化结果失败: {e}")
            return None

# 全局优化器实例
strategy_optimizer = StrategyOptimizer()
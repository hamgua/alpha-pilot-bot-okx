"""
策略子包 - 市场情绪智能和自适应策略优化
提供策略选择、回测、优化、监控等完整功能
"""

from .strategies_market_sentiment_intelligence import (
    # 基础数据结构
    BacktestResult,
    StrategyStatus,
    MarketStatus,
    OptimizationResult,
    # 核心类
    StateManager,
    MarketAnalyzer,
    StrategySelector,
    StrategyBacktestEngine,
    StrategyOptimizer,
    StrategyMonitor,
    # 全局实例
    market_analyzer,
    strategy_selector,
    # 工具函数
    run_strategy_demo,
    quick_strategy_test
)

from .strategies_adaptive_optimizer import (
    # 核心类
    StrategyBehaviorHandler,
    StrategyExecutor,
    # 全局实例
    signal_processor,
    strategy_executor
)

# 控制导出的名称
__all__ = [
    # 基础数据结构
    'BacktestResult',
    'StrategyStatus', 
    'MarketStatus',
    'OptimizationResult',
    # 核心类 - 市场情绪智能
    'StateManager',
    'MarketAnalyzer',
    'StrategySelector',
    'StrategyBacktestEngine',
    'StrategyOptimizer',
    'StrategyMonitor',
    # 核心类 - 自适应策略优化
    'StrategyBehaviorHandler',
    'StrategyExecutor',
    # 全局实例
    'market_analyzer',
    'strategy_selector',
    'signal_processor',
    'strategy_executor',
    # 工具函数
    'run_strategy_demo',
    'quick_strategy_test'
]
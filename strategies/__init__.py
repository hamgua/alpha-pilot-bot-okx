"""
策略模块 - 重构版本
提供策略选择、回测、优化、市场情绪分析等核心功能
"""

from .base import (
    BaseStrategy, 
    StrategyConfig, 
    BacktestResult, 
    StrategySignal,
    ConservativeStrategy,
    ModerateStrategy, 
    AggressiveStrategy,
    StrategyFactory
)
from .selector import StrategySelector, StrategySelectorConfig
from .optimizer import StrategyOptimizer, StrategyOptimizerConfig, OptimizationResult
from .backtest import BacktestEngine, BacktestConfig
from .market_sentiment import MarketSentimentAnalyzer, SentimentAnalysisResult

__all__ = [
    # 基础策略类
    'BaseStrategy',
    'StrategyConfig',
    'BacktestResult',
    'StrategySignal',
    'ConservativeStrategy',
    'ModerateStrategy',
    'AggressiveStrategy',
    'StrategyFactory',
    
    # 策略选择器
    'StrategySelector',
    'StrategySelectorConfig',
    
    # 策略优化器
    'StrategyOptimizer',
    'StrategyOptimizerConfig',
    'OptimizationResult',
    
    # 回测引擎
    'BacktestEngine',
    'BacktestConfig',
    
    # 市场情绪分析
    'MarketSentimentAnalyzer',
    'SentimentAnalysisResult',
    
    # 全局实例
    'strategy_selector',
    'strategy_optimizer',
    'backtest_engine',
    'market_sentiment_analyzer'
]

# 全局实例
strategy_selector = StrategySelector()
strategy_optimizer = StrategyOptimizer()
backtest_engine = BacktestEngine()
market_sentiment_analyzer = MarketSentimentAnalyzer()
"""
策略模块 - 向后兼容文件
用于兼容仍从根目录导入策略的代码
"""

# 从重构后的模块导入所有公开的类和函数
from strategies.base import *
from strategies.selector import *
from strategies.optimizer import *
from strategies.backtest import *
from strategies.market_sentiment import *
from strategies.consolidation import ConsolidationDetector, consolidation_detector

# 创建向后兼容的别名
MarketAnalyzer = MarketSentimentAnalyzer
market_analyzer = market_sentiment_analyzer
StrategyExecutor = StrategySelector
StrategyBehaviorHandler = StrategySelector
StrategyMonitor = StrategySelector
StrategyBacktestEngine = BacktestEngine
RiskManager = MarketSentimentAnalyzer

# 信号处理函数 - 需要实现或从其他模块导入
def crash_protection(*args, **kwargs):
    """崩溃保护 - 向后兼容"""
    return strategy_selector.crash_protection(*args, **kwargs) if hasattr(strategy_selector, 'crash_protection') else False

def generate_enhanced_fallback_signal(*args, **kwargs):
    """增强兜底信号 - 向后兼容"""
    return strategy_selector.generate_enhanced_fallback_signal(*args, **kwargs) if hasattr(strategy_selector, 'generate_enhanced_fallback_signal') else None
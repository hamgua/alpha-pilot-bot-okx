"""
Alpha Pilot Bot OKX - 简化API包
按照PEP 8子包收纳规范重构的模块化交易系统
"""

# 从子包导入主要功能，提供简化的API接口
from ai import ai, AIClient, AISignal
from trading import trading_engine, TradingEngine, ExchangeManager
from strategies import (
    StrategySelector, StrategyExecutor, StrategyBehaviorHandler,
    market_analyzer, signal_processor, consolidation_detector, crash_protection
)
from config import config
from utils import log_info, log_warning, log_error

# 主要类导出
__all__ = [
    # AI模块
    'ai',
    'AIClient', 
    'AISignal',
    
    # 交易模块
    'trading_engine',
    'TradingEngine',
    'ExchangeManager',
    
    # 策略模块
    'StrategySelector',
    'StrategyExecutor', 
    'StrategyBehaviorHandler',
    'market_analyzer',
    'signal_processor',
    'consolidation_detector',
    'crash_protection',
    
    # 配置模块
    'config',
    
    # 工具模块
    'log_info',
    'log_warning',
    'log_error'
]

# 版本信息
__version__ = "2.0.0"
__author__ = "Alpha Pilot Bot Team"
__description__ = "AI驱动的OKX自动交易系统 - 模块化架构重构版"

# 简化API函数
def create_bot():
    """创建交易机器人实例"""
    from main import AlphaArenaBot
    return AlphaArenaBot()

def get_market_data():
    """获取市场数据"""
    return trading_engine.get_market_data()

def get_ai_signal(market_data):
    """获取AI交易信号"""
    return ai.get_signal_from_provider('kimi', market_data)

def execute_trade(signal, amount):
    """执行交易"""
    return trading_engine.execute_trade(signal, amount)

# 快速启动函数
def run_bot():
    """快速启动交易机器人"""
    bot = create_bot()
    bot.run()

# 配置检查函数
def check_config():
    """检查系统配置"""
    validation_result = config.get_validation_status()
    if validation_result.is_valid:
        log_info("✅ 系统配置验证通过")
        return True
    else:
        log_error(f"❌ 配置验证失败: {validation_result.errors}")
        return False

# 系统状态函数
def get_system_status():
    """获取系统状态"""
    from utils import system_monitor
    return system_monitor.get_stats()
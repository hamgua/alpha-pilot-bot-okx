"""
AI决策模块 - 重构版本
提供多AI提供商支持和智能信号融合
"""

from .ai import AIClient
from .signals import AISignal, SignalFusionResult
from .fusion import SignalFusionEngine
from .fallback import FallbackSignalGenerator
from .timeout import TimeoutManager
from .proxy import ProxyManager, create_proxy_session, get_proxy_recommendations
from .rate_limiter import MultiProviderRateLimiter, rate_limit, get_rate_limit_stats

# 创建全局AI客户端实例
ai_client = AIClient()

# 导出常用的函数和属性
providers = ai_client.providers
get_ai_signal = ai_client.get_ai_signal
get_multi_ai_signals = ai_client.get_multi_ai_signals
fuse_signals = ai_client.fuse_signals
generate_enhanced_fallback_signal = ai_client.generate_enhanced_fallback_signal

__all__ = [
    'AIClient',
    'AISignal',
    'SignalFusionResult',
    'SignalFusionEngine',
    'FallbackSignalGenerator',
    'TimeoutManager',
    'ProxyManager',
    'create_proxy_session',
    'get_proxy_recommendations',
    'MultiProviderRateLimiter',
    'rate_limit',
    'get_rate_limit_stats',
    'ai_client',
    'providers',
    'get_ai_signal',
    'get_multi_ai_signals',
    'fuse_signals',
    'generate_enhanced_fallback_signal'
]
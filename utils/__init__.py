"""
工具模块 - 重构版本
提供日志、缓存、监控、错误恢复等核心工具功能
"""

# 日志系统
from .logging import (
    TradingLogger,
    log_info,
    log_warning,
    log_error,
    log_debug,
    log_trade_event,
    log_signal,
    log_risk_event,
    log_error_event,
    log_performance,
    log_decision,
    log_ai_decision,
    log_strategy_signal,
    log_risk_management,
    log_execution_stats,
    set_log_level,
    get_log_level,
    rotate_logs,
    cleanup_old_logs,
    get_log_stats,
    trading_logger
)

# 缓存管理
from .cache import (
    CacheManager,
    MemoryManager,
    cache_manager,
    memory_manager,
    get_cache_stats,
    get_memory_stats,
    clear_all_cache,
    clear_all_history
)

# 系统监控
from .monitoring import (
    SystemMonitor,
    ProcessMonitor,
    HealthChecker,
    system_monitor,
    process_monitor,
    health_checker,
    get_system_status,
    get_performance_summary,
    start_system_monitoring,
    stop_system_monitoring,
    register_default_health_checks
)

# 错误恢复
from .error_recovery import (
    ErrorCategory,
    ErrorRecord,
    ErrorClassifier,
    RecoveryStrategy,
    ErrorRecoveryManager,
    error_recovery,
    handle_error,
    get_recovery_stats
)

# 数据验证工具
from .data_validation import (
    DataValidator,
    JSONHelper,
    data_validator,
    json_helper
)

# 时间工具
from .time_helper import (
    TimeHelper,
    time_helper
)

# JSON工具 (从data_validation模块导入)
from .data_validation import (
    JSONHelper,
    json_helper
)

# 系统工具
from .system_utils import (
    SystemUtils,
    system_utils
)

__all__ = [
    # 日志系统
    'TradingLogger',
    'log_info',
    'log_warning',
    'log_error',
    'log_debug',
    'log_trade_event',
    'log_signal',
    'log_risk_event',
    'log_error_event',
    'log_performance',
    'log_decision',
    'log_ai_decision',
    'log_strategy_signal',
    'log_risk_management',
    'log_execution_stats',
    'set_log_level',
    'get_log_level',
    'rotate_logs',
    'cleanup_old_logs',
    'get_log_stats',
    'trading_logger',
    
    # 缓存管理
    'CacheManager',
    'MemoryManager',
    'cache_manager',
    'memory_manager',
    'get_cache_stats',
    'get_memory_stats',
    'clear_all_cache',
    'clear_all_history',
    
    # 系统监控
    'SystemMonitor',
    'ProcessMonitor',
    'HealthChecker',
    'system_monitor',
    'process_monitor',
    'health_checker',
    'get_system_status',
    'get_performance_summary',
    'start_system_monitoring',
    'stop_system_monitoring',
    'register_default_health_checks',
    
    # 错误恢复
    'ErrorCategory',
    'ErrorRecord',
    'ErrorClassifier',
    'RecoveryStrategy',
    'ErrorRecoveryManager',
    'error_recovery',
    'handle_error',
    'get_recovery_stats',
    
    # 数据验证
    'DataValidator',
    'JSONHelper',
    'data_validator',
    'json_helper',
    
    # 时间工具
    'TimeHelper',
    'time_helper',
    
    # JSON工具
    'JSONHelper',
    'json_helper',

    # 系统工具
    'SystemUtils',
    'system_utils'
]

# 全局实例
from .logging import trading_logger
from .cache import cache_manager, memory_manager
from .monitoring import system_monitor, health_checker
from .error_recovery import error_recovery
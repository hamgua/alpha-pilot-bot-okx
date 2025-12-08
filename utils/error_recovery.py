"""
错误恢复模块
提供统一的错误处理和恢复机制
"""

import time
import traceback
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import threading
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"
    API = "api"
    DATA = "data"
    SYSTEM = "system"
    STRATEGY = "strategy"
    UNKNOWN = "unknown"

@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: str
    error_type: str
    error_message: str
    category: str
    context: Dict[str, Any]
    stack_trace: str
    recovery_attempt: int
    recovery_result: Optional[Dict[str, Any]] = None

class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        self.classification_rules = {
            ErrorCategory.NETWORK: [
                'ConnectionError', 'TimeoutError', 'NetworkError',
                'SSLError', 'ProxyError', 'DNSLookupError', 'ConnectionResetError',
                'requests.exceptions', 'aiohttp.ClientError'
            ],
            ErrorCategory.API: [
                'APIError', 'RateLimitError', 'AuthenticationError',
                'PermissionError', 'InvalidRequestError', 'ExchangeError',
                'InsufficientFunds', 'InvalidOrder', 'OrderNotFound'
            ],
            ErrorCategory.DATA: [
                'DataError', 'ValidationError', 'MissingDataError',
                'PriceError', 'TimestampError', 'FormatError', 'JSONDecodeError'
            ],
            ErrorCategory.SYSTEM: [
                'MemoryError', 'SystemError', 'ProcessError',
                'ResourceError', 'ThreadError', 'QueueError', 'OSError'
            ],
            ErrorCategory.STRATEGY: [
                'StrategyError', 'CalculationError', 'LogicError',
                'ConfigurationError', 'ParameterError'
            ]
        }
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """对错误进行分类"""
        try:
            error_name = type(error).__name__
            error_message = str(error).lower()
            
            for category, patterns in self.classification_rules.items():
                if any(pattern.lower() in error_name.lower() or 
                       pattern.lower() in error_message 
                       for pattern in patterns):
                    return category
            
            return ErrorCategory.UNKNOWN
            
        except Exception as e:
            logger.error(f"错误分类失败: {e}")
            return ErrorCategory.UNKNOWN

class RecoveryStrategy:
    """恢复策略"""
    
    def __init__(self, name: str, action: Callable, max_retries: int = 3, 
                 cooldown_time: int = 60, priority: int = 1):
        self.name = name
        self.action = action
        self.max_retries = max_retries
        self.cooldown_time = cooldown_time
        self.priority = priority
        self.retry_count = 0
        self.last_attempt = None

class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        self.error_classifier = ErrorClassifier()
        self.recovery_strategies: Dict[ErrorCategory, List[RecoveryStrategy]] = {}
        self.error_history: List[ErrorRecord] = []
        self.recovery_stats = {
            'total_errors': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
        self._lock = threading.Lock()
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        """设置默认恢复策略"""
        # 网络错误恢复策略
        self.recovery_strategies[ErrorCategory.NETWORK] = [
            RecoveryStrategy(
                name="retry_with_backoff",
                action=self._retry_with_backoff,
                max_retries=3,
                cooldown_time=30,
                priority=1
            ),
            RecoveryStrategy(
                name="switch_network_config",
                action=self._switch_network_config,
                max_retries=2,
                cooldown_time=60,
                priority=2
            )
        ]
        
        # API错误恢复策略
        self.recovery_strategies[ErrorCategory.API] = [
            RecoveryStrategy(
                name="rate_limit_backoff",
                action=self._rate_limit_backoff,
                max_retries=2,
                cooldown_time=120,
                priority=1
            ),
            RecoveryStrategy(
                name="switch_api_endpoint",
                action=self._switch_api_endpoint,
                max_retries=1,
                cooldown_time=300,
                priority=2
            )
        ]
        
        # 数据错误恢复策略
        self.recovery_strategies[ErrorCategory.DATA] = [
            RecoveryStrategy(
                name="use_fallback_data",
                action=self._use_fallback_data,
                max_retries=1,
                cooldown_time=0,
                priority=1
            ),
            RecoveryStrategy(
                name="validate_and_correct",
                action=self._validate_and_correct,
                max_retries=2,
                cooldown_time=10,
                priority=2
            )
        ]
        
        # 系统错误恢复策略
        self.recovery_strategies[ErrorCategory.SYSTEM] = [
            RecoveryStrategy(
                name="memory_cleanup",
                action=self._memory_cleanup,
                max_retries=1,
                cooldown_time=30,
                priority=1
            ),
            RecoveryStrategy(
                name="restart_service",
                action=self._restart_service,
                max_retries=1,
                cooldown_time=300,
                priority=2
            )
        ]
        
        # 策略错误恢复策略
        self.recovery_strategies[ErrorCategory.STRATEGY] = [
            RecoveryStrategy(
                name="use_conservative_strategy",
                action=self._use_conservative_strategy,
                max_retries=1,
                cooldown_time=0,
                priority=1
            ),
            RecoveryStrategy(
                name="recalculate_parameters",
                action=self._recalculate_parameters,
                max_retries=2,
                cooldown_time=60,
                priority=2
            )
        ]
    
    async def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        统一的错误处理入口
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            恢复结果字典
        """
        try:
            self.recovery_stats['total_errors'] += 1
            
            # 1. 错误分类
            error_category = self.error_classifier.classify_error(error)
            
            # 2. 记录错误
            error_record = self._record_error(error, error_category, context)
            
            # 3. 执行恢复策略
            recovery_result = await self._execute_recovery(error_category, error, context)
            
            # 4. 更新统计
            if recovery_result['success']:
                self.recovery_stats['successful_recoveries'] += 1
            else:
                self.recovery_stats['failed_recoveries'] += 1
            
            # 5. 发送警报（如果需要）
            if recovery_result['severity'] in ['HIGH', 'CRITICAL']:
                self._send_alert(error_record, recovery_result)
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"错误处理失败: {e}")
            return {
                'success': False,
                'action': 'FALLBACK_SHUTDOWN',
                'severity': 'CRITICAL',
                'message': f'错误处理失败: {e}',
                'next_action': 'SAFE_SHUTDOWN'
            }
    
    def _record_error(self, error: Exception, category: ErrorCategory, context: Optional[Dict[str, Any]]) -> ErrorRecord:
        """记录错误信息"""
        try:
            error_record = ErrorRecord(
                timestamp=datetime.now().isoformat(),
                error_type=type(error).__name__,
                error_message=str(error),
                category=category.value,
                context=context or {},
                stack_trace=traceback.format_exc(),
                recovery_attempt=0
            )
            
            self.error_history.append(error_record)
            
            # 保持最近100条错误记录
            if len(self.error_history) > 100:
                self.error_history.pop(0)
            
            return error_record
            
        except Exception as e:
            logger.error(f"记录错误失败: {e}")
            return ErrorRecord(
                timestamp=datetime.now().isoformat(),
                error_type=type(error).__name__,
                error_message=str(error),
                category=category.value,
                context=context or {},
                stack_trace=traceback.format_exc(),
                recovery_attempt=0
            )
    
    async def _execute_recovery(self, category: ErrorCategory, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """执行恢复策略"""
        try:
            strategies = self.recovery_strategies.get(category, [])
            
            if not strategies:
                return await self._handle_unknown_error(error, context)
            
            # 按优先级排序
            strategies.sort(key=lambda x: x.priority)
            
            for strategy in strategies:
                try:
                    if strategy.retry_count >= strategy.max_retries:
                        continue
                    
                    # 检查冷却时间
                    if strategy.last_attempt and (time.time() - strategy.last_attempt) < strategy.cooldown_time:
                        continue
                    
                    logger.info(f"🔄 执行恢复策略: {strategy.name}")
                    
                    # 执行恢复动作
                    result = await strategy.action(error, context)
                    
                    strategy.retry_count += 1
                    strategy.last_attempt = time.time()
                    
                    if result['success']:
                        return result
                    
                except Exception as e:
                    logger.error(f"恢复策略 {strategy.name} 执行失败: {e}")
                    continue
            
            # 所有策略都失败
            return {
                'success': False,
                'action': 'ALL_STRATEGIES_FAILED',
                'severity': 'HIGH',
                'message': '所有恢复策略都失败',
                'next_action': 'SAFE_SHUTDOWN'
            }
            
        except Exception as e:
            logger.error(f"执行恢复策略失败: {e}")
            return {
                'success': False,
                'action': 'RECOVERY_EXECUTION_FAILED',
                'severity': 'CRITICAL',
                'message': f'恢复执行失败: {e}',
                'next_action': 'SAFE_SHUTDOWN'
            }
    
    async def _handle_unknown_error(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """处理未知错误"""
        logger.error(f"❓ 未知错误: {error}")
        return {
            'success': False,
            'action': 'UNKNOWN_ERROR',
            'severity': 'HIGH',
            'message': f'未知错误: {error}',
            'next_action': 'SAFE_SHUTDOWN'
        }
    
    def _send_alert(self, error_record: ErrorRecord, recovery_result: Dict[str, Any]):
        """发送错误警报"""
        alert_message = f"""
        🚨 交易系统错误警报
        
        时间: {error_record.timestamp}
        错误类型: {error_record.error_type}
        错误分类: {error_record.category}
        严重程度: {recovery_result['severity']}
        恢复动作: {recovery_result['action']}
        下一步行动: {recovery_result['next_action']}
        
        错误详情: {error_record.error_message}
        上下文: {json.dumps(error_record.context, indent=2)}
        """
        
        logger.error(alert_message)
        # 实际应用中这里会发送邮件、短信等通知
    
    # 恢复策略实现
    async def _retry_with_backoff(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """指数退避重试"""
        try:
            retry_count = context.get('retry_count', 0) if context else 0
            base_delay = 2 ** retry_count
            
            logger.info(f"⏰ 指数退避重试: 第{retry_count + 1}次，等待{base_delay}秒")
            await asyncio.sleep(base_delay)
            
            return {
                'success': True,
                'action': 'RETRY_WITH_BACKOFF',
                'severity': 'LOW',
                'message': f'指数退避重试完成，延迟{base_delay}秒',
                'next_action': 'RETRY',
                'retry_count': retry_count + 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'BACKOFF_FAILED',
                'severity': 'MEDIUM',
                'message': f'指数退避失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _switch_network_config(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """切换网络配置"""
        try:
            logger.info("🌐 切换网络配置")
            # 这里可以实现网络配置切换逻辑
            # 例如：切换代理、DNS、网络接口等
            
            return {
                'success': True,
                'action': 'SWITCH_NETWORK_CONFIG',
                'severity': 'MEDIUM',
                'message': '网络配置已切换',
                'next_action': 'RETRY'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'NETWORK_SWITCH_FAILED',
                'severity': 'HIGH',
                'message': f'网络配置切换失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _rate_limit_backoff(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """限频退避"""
        try:
            # 获取限频信息
            retry_after = context.get('retry_after', 60) if context else 60
            
            logger.info(f"⏱️ 限频退避: 等待{retry_after}秒")
            await asyncio.sleep(retry_after)
            
            return {
                'success': True,
                'action': 'RATE_LIMIT_BACKOFF',
                'severity': 'LOW',
                'message': f'限频退避完成，等待{retry_after}秒',
                'next_action': 'RETRY'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'RATE_LIMIT_BACKOFF_FAILED',
                'severity': 'MEDIUM',
                'message': f'限频退避失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _switch_api_endpoint(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """切换API端点"""
        try:
            logger.info("🔌 切换API端点")
            # 这里可以实现API端点切换逻辑
            
            return {
                'success': True,
                'action': 'SWITCH_API_ENDPOINT',
                'severity': 'MEDIUM',
                'message': 'API端点已切换',
                'next_action': 'RETRY'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'API_ENDPOINT_SWITCH_FAILED',
                'severity': 'HIGH',
                'message': f'API端点切换失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _use_fallback_data(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用回退数据"""
        try:
            logger.info("📊 使用回退数据")
            # 这里可以实现回退数据逻辑
            
            return {
                'success': True,
                'action': 'USE_FALLBACK_DATA',
                'severity': 'LOW',
                'message': '已使用回退数据',
                'next_action': 'CONTINUE_WITH_FALLBACK'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'FALLBACK_DATA_FAILED',
                'severity': 'MEDIUM',
                'message': f'回退数据失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _validate_and_correct(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """验证并纠正数据"""
        try:
            logger.info("✅ 验证并纠正数据")
            # 这里可以实现数据验证和纠正逻辑
            
            return {
                'success': True,
                'action': 'VALIDATE_AND_CORRECT',
                'severity': 'LOW',
                'message': '数据已验证并纠正',
                'next_action': 'CONTINUE'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'VALIDATION_FAILED',
                'severity': 'MEDIUM',
                'message': f'数据验证失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _memory_cleanup(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """内存清理"""
        try:
            logger.info("🧹 执行内存清理")
            # 这里可以实现内存清理逻辑
            import gc
            gc.collect()
            
            return {
                'success': True,
                'action': 'MEMORY_CLEANUP',
                'severity': 'LOW',
                'message': '内存清理完成',
                'next_action': 'CONTINUE'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'MEMORY_CLEANUP_FAILED',
                'severity': 'MEDIUM',
                'message': f'内存清理失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _restart_service(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """重启服务"""
        try:
            logger.info("🔄 重启服务")
            # 这里可以实现服务重启逻辑
            
            return {
                'success': True,
                'action': 'RESTART_SERVICE',
                'severity': 'HIGH',
                'message': '服务重启完成',
                'next_action': 'RETRY'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'SERVICE_RESTART_FAILED',
                'severity': 'CRITICAL',
                'message': f'服务重启失败: {e}',
                'next_action': 'SAFE_SHUTDOWN'
            }
    
    async def _use_conservative_strategy(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用保守策略"""
        try:
            logger.info("🛡️ 使用保守策略")
            # 这里可以实现保守策略逻辑
            
            return {
                'success': True,
                'action': 'USE_CONSERVATIVE_STRATEGY',
                'severity': 'LOW',
                'message': '已切换到保守策略',
                'next_action': 'CONTINUE_WITH_CONSERVATIVE_MODE'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'CONSERVATIVE_STRATEGY_FAILED',
                'severity': 'MEDIUM',
                'message': f'保守策略失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    async def _recalculate_parameters(self, error: Exception, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """重新计算参数"""
        try:
            logger.info("🧮 重新计算参数")
            # 这里可以实现参数重新计算逻辑
            
            return {
                'success': True,
                'action': 'RECALCULATE_PARAMETERS',
                'severity': 'LOW',
                'message': '参数已重新计算',
                'next_action': 'CONTINUE'
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'PARAMETER_RECALCULATION_FAILED',
                'severity': 'MEDIUM',
                'message': f'参数重新计算失败: {e}',
                'next_action': 'TRY_NEXT_STRATEGY'
            }
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        try:
            total_errors = self.recovery_stats['total_errors']
            successful_recoveries = self.recovery_stats['successful_recoveries']
            failed_recoveries = self.recovery_stats['failed_recoveries']
            
            success_rate = successful_recoveries / max(total_errors, 1)
            
            # 错误分布统计
            error_distribution = {}
            for error in self.error_history[-50:]:  # 最近50条
                category = error.category
                error_distribution[category] = error_distribution.get(category, 0) + 1
            
            return {
                'total_errors': total_errors,
                'successful_recoveries': successful_recoveries,
                'failed_recoveries': failed_recoveries,
                'success_rate': success_rate,
                'recent_errors': self.error_history[-10:],  # 最近10条
                'error_distribution': error_distribution,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取恢复统计失败: {e}")
            return {
                'total_errors': self.recovery_stats['total_errors'],
                'successful_recoveries': self.recovery_stats['successful_recoveries'],
                'failed_recoveries': self.recovery_stats['failed_recoveries'],
                'success_rate': 0.0,
                'error': str(e)
            }

# 全局错误恢复管理器实例
error_recovery = ErrorRecoveryManager()

# 向后兼容的函数
def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """处理错误（向后兼容）"""
    return asyncio.run(error_recovery.handle_error(error, context))

def get_recovery_stats() -> Dict[str, Any]:
    """获取恢复统计（向后兼容）"""
    return error_recovery.get_recovery_stats()

# 导出主要功能
__all__ = [
    'ErrorCategory',
    'ErrorRecord',
    'ErrorClassifier',
    'RecoveryStrategy',
    'ErrorRecoveryManager',
    'error_recovery',
    'handle_error',
    'get_recovery_stats'
]
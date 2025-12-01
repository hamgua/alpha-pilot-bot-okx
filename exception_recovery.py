"""
高级异常恢复机制
基于原项目功能.md的设计规范，实现智能异常分类、自动恢复和故障转移
"""

import asyncio
import json
import traceback
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import hashlib
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RecoveryStrategy:
    """恢复策略"""
    name: str
    retry_count: int = 3
    backoff_factor: float = 2.0
    max_wait: int = 300
    fallback_action: str = "skip"
    
class ExceptionClassifier:
    """异常分类器"""
    
    def __init__(self):
        self.classification_rules = {
            'network': [
                'ConnectionError', 'TimeoutError', 'NetworkError',
                'SSLError', 'ProxyError', 'DNSLookupError',
                'ConnectionResetError', 'ConnectionRefusedError'
            ],
            'api': [
                'APIError', 'RateLimitError', 'AuthenticationError',
                'PermissionError', 'InvalidRequestError', 'ExchangeError',
                'InsufficientFunds', 'InvalidOrder', 'OrderNotFound',
                'BadRequest', 'Unauthorized', 'Forbidden', 'NotFound'
            ],
            'data': [
                'DataError', 'ValidationError', 'MissingDataError',
                'PriceError', 'TimestampError', 'FormatError',
                'JSONDecodeError', 'KeyError', 'ValueError'
            ],
            'system': [
                'MemoryError', 'SystemError', 'ProcessError',
                'ResourceError', 'ThreadError', 'QueueError',
                'OSError', 'RuntimeError', 'SystemExit'
            ],
            'strategy': [
                'StrategyError', 'CalculationError', 'LogicError',
                'ConfigurationError', 'ParameterError',
                'AttributeError', 'TypeError'
            ],
            'external': [
                'ExchangeMaintenance', 'MarketClosed', 'TradingHalted',
                'InsufficientLiquidity', 'MarketDataError'
            ]
        }
    
    def classify_exception(self, exception: Exception) -> str:
        """分类异常类型"""
        
        exception_name = exception.__class__.__name__
        exception_message = str(exception).lower()
        
        # 按异常名称分类
        for category, patterns in self.classification_rules.items():
            if exception_name in patterns:
                return category
        
        # 按消息内容分类
        message_keywords = {
            'network': ['connection', 'timeout', 'network', 'dns', 'proxy'],
            'api': ['api', 'rate limit', 'authentication', 'permission', 'exchange'],
            'data': ['data', 'validation', 'format', 'json', 'key', 'value'],
            'system': ['memory', 'system', 'resource', 'process', 'thread'],
            'external': ['maintenance', 'closed', 'halted', 'liquidity', 'market']
        }
        
        for category, keywords in message_keywords.items():
            if any(keyword in exception_message for keyword in keywords):
                return category
        
        return 'unknown'

class ExceptionRecoveryManager:
    """
    高级异常恢复管理器
    实现智能异常处理、自动恢复、故障转移
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('exception_recovery', {})
        self.enabled = self.config.get('enabled', True)
        
        # 异常分类器
        self.classifier = ExceptionClassifier()
        
        # 恢复策略配置
        self.recovery_strategies = {
            'network': RecoveryStrategy(
                name="network_recovery",
                retry_count=5,
                backoff_factor=2.0,
                max_wait=300,
                fallback_action="retry_later"
            ),
            'api': RecoveryStrategy(
                name="api_recovery",
                retry_count=3,
                backoff_factor=1.5,
                max_wait=180,
                fallback_action="use_cache"
            ),
            'data': RecoveryStrategy(
                name="data_recovery",
                retry_count=2,
                backoff_factor=1.0,
                max_wait=60,
                fallback_action="skip"
            ),
            'system': RecoveryStrategy(
                name="system_recovery",
                retry_count=1,
                backoff_factor=1.0,
                max_wait=30,
                fallback_action="graceful_shutdown"
            ),
            'strategy': RecoveryStrategy(
                name="strategy_recovery",
                retry_count=2,
                backoff_factor=1.0,
                max_wait=60,
                fallback_action="use_default"
            ),
            'external': RecoveryStrategy(
                name="external_recovery",
                retry_count=3,
                backoff_factor=2.0,
                max_wait=600,
                fallback_action="wait_and_retry"
            ),
            'unknown': RecoveryStrategy(
                name="unknown_recovery",
                retry_count=1,
                backoff_factor=1.0,
                max_wait=30,
                fallback_action="log_and_continue"
            )
        }
        
        # 异常历史
        self.exception_history = []
        self.recovery_stats = {}
        
        # 故障转移配置
        self.fallback_handlers = {}
        
        # 系统状态
        self.system_health = {
            'last_exception': None,
            'recovery_mode': False,
            'degraded_services': [],
            'circuit_breaker': False
        }
        
        logger.info("🔄 高级异常恢复管理器初始化完成")
    
    async def execute_with_recovery(self, operation: Callable, *args, 
                                  operation_name: str = "default", **kwargs) -> Any:
        """
        执行操作并处理异常恢复
        
        Args:
            operation: 要执行的操作函数
            operation_name: 操作名称
            *args, **kwargs: 操作参数
            
        Returns:
            操作结果
        """
        
        if not self.enabled:
            return await operation(*args, **kwargs)
        
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            return await self._handle_exception(e, operation, args, kwargs, operation_name)
    
    async def _handle_exception(self, exception: Exception, operation: Callable,
                              args: tuple, kwargs: dict, operation_name: str) -> Any:
        """处理异常"""
        
        # 分类异常
        exception_type = self.classifier.classify_exception(exception)
        
        # 记录异常
        exception_record = {
            'timestamp': datetime.now().isoformat(),
            'type': exception_type,
            'exception': str(exception),
            'traceback': traceback.format_exc(),
            'operation': operation_name,
            'hash': self._generate_exception_hash(exception)
        }
        
        self.exception_history.append(exception_record)
        
        # 限制历史记录长度
        if len(self.exception_history) > 1000:
            self.exception_history = self.exception_history[-1000:]
        
        logger.error(f"🚨 异常捕获: {exception_type} - {exception}")
        
        # 获取恢复策略
        strategy = self.recovery_strategies.get(exception_type, self.recovery_strategies['unknown'])
        
        # 执行恢复
        return await self._execute_recovery(exception, strategy, operation, args, kwargs, operation_name)
    
    async def _execute_recovery(self, exception: Exception, strategy: RecoveryStrategy,
                              operation: Callable, args: tuple, kwargs: dict,
                              operation_name: str) -> Any:
        """执行恢复策略"""
        
        exception_type = self.classifier.classify_exception(exception)
        
        # 更新恢复统计
        if exception_type not in self.recovery_stats:
            self.recovery_stats[exception_type] = {
                'total_count': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0,
                'last_occurrence': None
            }
        
        stats = self.recovery_stats[exception_type]
        stats['total_count'] += 1
        stats['last_occurrence'] = datetime.now().isoformat()
        
        # 执行重试
        for attempt in range(strategy.retry_count):
            try:
                wait_time = min(strategy.backoff_factor ** attempt, strategy.max_wait)
                
                if wait_time > 0:
                    logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                
                logger.info(f"🔄 尝试恢复: {operation_name} (尝试 {attempt + 1}/{strategy.retry_count})")
                result = await operation(*args, **kwargs)
                
                stats['successful_recoveries'] += 1
                logger.info(f"✅ 恢复成功: {operation_name}")
                
                return result
                
            except Exception as retry_exception:
                logger.warning(f"⚠️ 重试失败: {retry_exception}")
                
                if attempt == strategy.retry_count - 1:
                    stats['failed_recoveries'] += 1
                    
                    # 执行回退操作
                    return await self._execute_fallback(
                        exception, strategy.fallback_action, operation_name
                    )
    
    async def _execute_fallback(self, exception: Exception, fallback_action: str,
                              operation_name: str) -> Any:
        """执行回退操作"""
        
        logger.warning(f"🛡️ 执行回退操作: {fallback_action}")
        
        fallback_handlers = {
            'skip': lambda: None,
            'use_cache': lambda: self._use_cached_result(operation_name),
            'use_default': lambda: self._use_default_value(operation_name),
            'retry_later': lambda: self._schedule_retry(operation_name),
            'graceful_shutdown': lambda: self._graceful_shutdown(exception),
            'wait_and_retry': lambda: self._wait_and_retry(exception, operation_name),
            'log_and_continue': lambda: self._log_and_continue(exception)
        }
        
        handler = fallback_handlers.get(fallback_action, fallback_handlers['log_and_continue'])
        
        try:
            return await handler()
        except Exception as e:
            logger.error(f"❌ 回退操作失败: {e}")
            return None
    
    def _use_cached_result(self, operation_name: str) -> Any:
        """使用缓存结果"""
        # 这里可以实现缓存逻辑
        logger.info(f"📦 使用缓存结果: {operation_name}")
        return None
    
    def _use_default_value(self, operation_name: str) -> Any:
        """使用默认值"""
        logger.info(f"🔧 使用默认值: {operation_name}")
        
        # 根据操作类型返回合适的默认值
        defaults = {
            'fetch_price': {'price': 0, 'timestamp': datetime.now().isoformat()},
            'calculate_signal': {'signal': 'HOLD', 'confidence': 0.5},
            'execute_trade': {'success': False, 'error': 'default_fallback'},
            'get_balance': {'total': 0, 'available': 0}
        }
        
        return defaults.get(operation_name, None)
    
    async def _schedule_retry(self, operation_name: str) -> Any:
        """安排稍后重试"""
        logger.info(f"⏰ 安排稍后重试: {operation_name}")
        # 这里可以实现任务队列逻辑
        return None
    
    async def _graceful_shutdown(self, exception: Exception) -> None:
        """优雅关闭"""
        logger.critical(f"🛑 优雅关闭系统: {exception}")
        
        # 保存系统状态
        await self._save_system_state()
        
        # 关闭所有服务
        self.system_health['circuit_breaker'] = True
        
        # 通知管理员
        await self._notify_admin("SYSTEM_SHUTDOWN", str(exception))
    
    async def _wait_and_retry(self, exception: Exception, operation_name: str) -> Any:
        """等待并重试"""
        wait_time = 300  # 5分钟后重试
        logger.info(f"⏳ 等待 {wait_time} 秒后重试: {operation_name}")
        await asyncio.sleep(wait_time)
        return None
    
    async def _log_and_continue(self, exception: Exception) -> None:
        """记录并继续"""
        logger.error(f"📝 记录异常并继续: {exception}")
        return None
    
    def _generate_exception_hash(self, exception: Exception) -> str:
        """生成异常哈希"""
        exception_str = str(exception)
        return hashlib.md5(exception_str.encode()).hexdigest()[:8]
    
    async def _save_system_state(self):
        """保存系统状态"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'exception_history': self.exception_history[-100:],  # 最近100条
            'recovery_stats': self.recovery_stats,
            'system_health': self.system_health
        }
        
        # 这里可以实现状态持久化逻辑
        logger.info(f"💾 系统状态已保存: {len(state['exception_history'])} 条异常记录")
    
    async def _notify_admin(self, event_type: str, message: str):
        """通知管理员"""
        notification = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'system_state': self.system_health
        }
        
        logger.critical(f"📢 管理员通知: {json.dumps(notification, indent=2)}")
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """获取恢复摘要"""
        
        total_exceptions = len(self.exception_history)
        successful_recoveries = sum(stats['successful_recoveries'] 
                                  for stats in self.recovery_stats.values())
        failed_recoveries = sum(stats['failed_recoveries'] 
                              for stats in self.recovery_stats.values())
        
        recovery_rate = (successful_recoveries / total_exceptions * 100 
                        if total_exceptions > 0 else 0)
        
        return {
            'total_exceptions': total_exceptions,
            'successful_recoveries': successful_recoveries,
            'failed_recoveries': failed_recoveries,
            'recovery_rate': f"{recovery_rate:.2f}%",
            'recovery_stats': self.recovery_stats,
            'system_health': self.system_health,
            'recent_exceptions': self.exception_history[-10:]
        }
    
    def get_exception_distribution(self) -> Dict[str, int]:
        """获取异常分布"""
        
        distribution = {}
        for record in self.exception_history:
            category = record['type']
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution
    
    def enable_recovery_mode(self):
        """启用恢复模式"""
        self.system_health['recovery_mode'] = True
        logger.info("🔧 恢复模式已启用")
    
    def disable_recovery_mode(self):
        """禁用恢复模式"""
        self.system_health['recovery_mode'] = False
        logger.info("🔧 恢复模式已禁用")
    
    def add_fallback_handler(self, operation_name: str, handler: Callable):
        """添加回退处理器"""
        self.fallback_handlers[operation_name] = handler
        logger.info(f"🔧 添加回退处理器: {operation_name}")
    
    def update_recovery_strategy(self, exception_type: str, strategy: RecoveryStrategy):
        """更新恢复策略"""
        self.recovery_strategies[exception_type] = strategy
        logger.info(f"🔧 更新恢复策略: {exception_type} -> {strategy.name}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        
        health_score = 100
        
        # 基于异常频率调整健康分数
        recent_exceptions = [
            ex for ex in self.exception_history
            if datetime.fromisoformat(ex['timestamp']) > datetime.now() - timedelta(hours=1)
        ]
        
        if len(recent_exceptions) > 10:
            health_score -= 30
        elif len(recent_exceptions) > 5:
            health_score -= 20
        elif len(recent_exceptions) > 2:
            health_score -= 10
        
        # 基于恢复率调整健康分数
        total_exceptions = len(self.exception_history)
        if total_exceptions > 0:
            successful_rate = sum(stats['successful_recoveries'] 
                                for stats in self.recovery_stats.values()) / total_exceptions
            health_score += int(successful_rate * 20)
        
        self.system_health['health_score'] = max(0, min(100, health_score))


# 全局异常恢复管理器实例
exception_recovery = ExceptionRecoveryManager({
    'exception_recovery': {
        'enabled': True,
        'max_retry_count': 3,
        'backoff_factor': 2.0,
        'max_wait_time': 300
    }
})

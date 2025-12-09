"""
智能重试处理器
提供基于不同错误类型的智能重试策略
"""

import asyncio
import time
import logging
import random
from functools import wraps
from typing import Callable, Any, Optional, Dict, List, Union
from enum import Enum

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """重试策略"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    ADAPTIVE = "adaptive"

class RetryCondition(Enum):
    """重试条件"""
    ALL = "all"
    NETWORK = "network"
    TIMEOUT = "timeout"
    CONNECTION_RESET = "connection_reset"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"

class RetryConfig:
    """重试配置"""

    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
                 conditions: List[RetryCondition] = None,
                 on_retry: Optional[Callable] = None,
                 on_give_up: Optional[Callable] = None):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.conditions = conditions or [RetryCondition.NETWORK, RetryCondition.TIMEOUT]
        self.on_retry = on_retry
        self.on_give_up = on_give_up

class RetryHandler:
    """智能重试处理器"""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.retry_stats: Dict[str, Any] = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'retry_by_provider': defaultdict(int),
            'retry_by_error_type': defaultdict(int)
        }

    def should_retry(self, exception: Exception, condition: RetryCondition) -> bool:
        """判断是否应该重试"""
        error_message = str(exception).lower()

        # 检查错误类型
        if condition == RetryCondition.ALL:
            return True

        if condition == RetryCondition.NETWORK:
            network_errors = [
                'connection', 'connect', 'network', 'timeout',
                'reset', 'refused', 'aborted', 'broken'
            ]
            return any(err in error_message for err in network_errors)

        if condition == RetryCondition.TIMEOUT:
            return 'timeout' in error_message

        if condition == RetryCondition.CONNECTION_RESET:
            return 'connection reset by peer' in error_message

        if condition == RetryCondition.RATE_LIMIT:
            rate_limit_errors = [
                'rate limit', 'too many requests', '429', 'quota exceeded'
            ]
            return any(err in error_message for err in rate_limit_errors)

        if condition == RetryCondition.SERVER_ERROR:
            server_errors = ['500', '502', '503', '504', 'internal server error']
            return any(err in error_message for err in server_errors)

        return False

    def calculate_delay(self, attempt: int, provider: str = "") -> float:
        """计算重试延迟"""
        if self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)

        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # 添加随机抖动避免惊群效应
            base_delay = self.config.base_delay * (2 ** attempt)
            jitter = random.uniform(0.1, 0.5) * base_delay
            delay = base_delay + jitter

        elif self.config.strategy == RetryStrategy.ADAPTIVE:
            # 基于提供商历史表现调整延迟
            base_delay = self.config.base_delay * (2 ** attempt)

            # 获取提供商成功率（简化版）
            # 这里可以接入实际的提供商统计
            success_rate = 0.8  # 假设值

            if success_rate < 0.5:
                delay = base_delay * 1.5
            elif success_rate > 0.9:
                delay = base_delay * 0.8
            else:
                delay = base_delay

        else:
            delay = self.config.base_delay

        # 限制最大延迟
        return min(delay, self.config.max_delay)

    def smart_retry(self, func: Callable) -> Callable:
        """智能重试装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            provider = kwargs.get('provider', '') or args[0] if args else ''

            for attempt in range(self.config.max_attempts):
                try:
                    result = await func(*args, **kwargs)

                    # 如果成功，更新统计
                    if attempt > 0:
                        self.retry_stats['successful_retries'] += 1
                        logger.info(f"✅ 重试成功: {provider} (第{attempt}次重试)")

                    return result

                except Exception as e:
                    # 判断是否应该重试
                    should_retry = False
                    for condition in self.config.conditions:
                        if self.should_retry(e, condition):
                            should_retry = True
                            break

                    if not should_retry or attempt == self.config.max_attempts - 1:
                        # 不重试或达到最大重试次数
                        self.retry_stats['failed_retries'] += 1

                        if self.config.on_give_up:
                            self.config.on_give_up(e, attempt, provider)

                        logger.error(f"❌ 重试失败，放弃: {provider} (第{attempt + 1}次)")
                        raise

                    # 执行重试
                    self.retry_stats['total_retries'] += 1
                    self.retry_stats['retry_by_provider'][provider] += 1

                    # 获取错误类型
                    error_type = type(e).__name__
                    self.retry_stats['retry_by_error_type'][error_type] += 1

                    delay = self.calculate_delay(attempt, provider)

                    if self.config.on_retry:
                        self.config.on_retry(e, attempt, provider, delay)

                    logger.warning(f"🔄 准备重试: {provider} (第{attempt + 1}次，延迟{delay:.1f}s) - {error_type}: {str(e)[:100]}")
                    await asyncio.sleep(delay)

            return None

        return wrapper

    def get_stats(self) -> Dict[str, Any]:
        """获取重试统计"""
        return {
            'total_retries': self.retry_stats['total_retries'],
            'successful_retries': self.retry_stats['successful_retries'],
            'failed_retries': self.retry_stats['failed_retries'],
            'retry_by_provider': dict(self.retry_stats['retry_by_provider']),
            'retry_by_error_type': dict(self.retry_stats['retry_by_error_type']),
            'success_rate': (
                self.retry_stats['successful_retries'] / self.retry_stats['total_retries']
                if self.retry_stats['total_retries'] > 0 else 0
            )
        }

    def reset_stats(self):
        """重置统计"""
        self.retry_stats = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'retry_by_provider': defaultdict(int),
            'retry_by_error_type': defaultdict(int)
        }

# 默认重试配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL_JITTER,
    conditions=[RetryCondition.NETWORK, RetryCondition.TIMEOUT, RetryCondition.CONNECTION_RESET]
)

# 提供商特定的重试配置
PROVIDER_RETRY_CONFIGS = {
    'deepseek': RetryConfig(
        max_attempts=2,
        base_delay=1.5,
        max_delay=20.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        conditions=[RetryCondition.NETWORK, RetryCondition.TIMEOUT]
    ),
    'kimi': RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=25.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        conditions=[RetryCondition.NETWORK, RetryCondition.TIMEOUT, RetryCondition.CONNECTION_RESET]
    ),
    'qwen': RetryConfig(
        max_attempts=2,
        base_delay=1.0,
        max_delay=15.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        conditions=[RetryCondition.NETWORK, RetryCondition.TIMEOUT]
    ),
    'openai': RetryConfig(
        max_attempts=1,
        base_delay=3.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        conditions=[RetryCondition.NETWORK, RetryCondition.RATE_LIMIT]
    )
}

# 全局重试处理器
retry_handler = RetryHandler(DEFAULT_RETRY_CONFIG)

def get_retry_handler(provider: str = "") -> RetryHandler:
    """获取提供商特定的重试处理器"""
    if provider in PROVIDER_RETRY_CONFIGS:
        return RetryHandler(PROVIDER_RETRY_CONFIGS[provider])
    return retry_handler

def smart_retry(provider: str = ""):
    """智能重试装饰器"""
    def decorator(func: Callable):
        handler = get_retry_handler(provider)
        return handler.smart_retry(func)
    return decorator

# 便捷的函数
def get_retry_stats() -> Dict[str, Any]:
    """获取重试统计"""
    return retry_handler.get_stats()

def reset_retry_stats():
    """重置重试统计"""
    retry_handler.reset_stats()
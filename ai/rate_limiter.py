"""
请求限流器模块
提供智能的API请求限流，避免触发服务提供商的限制
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_second: float = 1.0
    requests_per_minute: float = 30.0
    requests_per_hour: float = 500.0
    burst_size: int = 3
    adaptive_enabled: bool = True
    provider_specific: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class RequestRecord:
    """请求记录"""
    timestamp: float
    provider: str
    success: bool
    response_time: float
    endpoint: str = ""

class AdaptiveRateLimiter:
    """自适应限流器"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_history: deque = deque()
        self.provider_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_hits': 0,
            'avg_response_time': 0,
            'current_rate': 0,
            'last_request_time': 0
        })

        # 滑动窗口计数器
        self.second_window: deque = deque()
        self.minute_window: deque = deque()
        self.hour_window: deque = deque()

        # 令牌桶
        self.tokens = config.burst_size
        self.last_refill = time.time()

        # 锁
        self._lock = threading.Lock()

        # 自适应参数
        self.adaptive_multiplier = 1.0
        self.last_error_time = 0

        logger.info(f"✅ 自适应限流器初始化完成")

    def _clean_old_records(self):
        """清理旧的请求记录"""
        current_time = time.time()

        # 清理超过1小时的记录
        cutoff_time = current_time - 3600
        while self.request_history and self.request_history[0].timestamp < cutoff_time:
            self.request_history.popleft()

        # 清理滑动窗口
        while self.second_window and self.second_window[0] < current_time - 1:
            self.second_window.popleft()

        while self.minute_window and self.minute_window[0] < current_time - 60:
            self.minute_window.popleft()

        while self.hour_window and self.hour_window[0] < current_time - 3600:
            self.hour_window.popleft()

    def _get_current_rates(self) -> Dict[str, float]:
        """获取当前请求速率"""
        current_time = time.time()

        # 计算各时间窗口内的请求数
        second_requests = sum(1 for t in self.second_window if current_time - t < 1)
        minute_requests = sum(1 for t in self.minute_window if current_time - t < 60)
        hour_requests = sum(1 for t in self.hour_window if current_time - t < 3600)

        return {
            'per_second': second_requests,
            'per_minute': minute_requests,
            'per_hour': hour_requests
        }

    def _update_provider_stats(self, provider: str, success: bool, response_time: float):
        """更新提供商统计"""
        stats = self.provider_stats[provider]
        stats['total_requests'] += 1
        stats['last_request_time'] = time.time()

        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1

        # 更新平均响应时间
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (stats['avg_response_time'] * 0.9) + (response_time * 0.1)

    def _adaptive_adjustment(self, provider: str) -> float:
        """自适应调整限流参数"""
        if not self.config.adaptive_enabled:
            return 1.0

        stats = self.provider_stats[provider]

        # 基于成功率调整
        if stats['total_requests'] > 10:
            success_rate = stats['successful_requests'] / stats['total_requests']
            if success_rate < 0.8:
                # 成功率低，降低请求频率
                self.adaptive_multiplier = max(0.5, self.adaptive_multiplier * 0.9)
                logger.info(f"📉 {provider} 成功率低({success_rate:.2f})，降低请求频率至 {self.adaptive_multiplier:.2f}x")
            elif success_rate > 0.95 and self.adaptive_multiplier < 1.5:
                # 成功率高，可以适当提高请求频率
                self.adaptive_multiplier = min(1.5, self.adaptive_multiplier * 1.05)
                logger.info(f"📈 {provider} 成功率高({success_rate:.2f})，提高请求频率至 {self.adaptive_multiplier:.2f}x")

        # 基于错误时间调整
        current_time = time.time()
        if current_time - self.last_error_time < 300:  # 5分钟内有错误
            self.adaptive_multiplier = max(0.5, self.adaptive_multiplier * 0.95)

        return self.adaptive_multiplier

    async def acquire_permission(self, provider: str, endpoint: str = "") -> bool:
        """获取请求许可"""
        with self._lock:
            self._clean_old_records()

            current_time = time.time()

            # 获取提供商特定配置
            provider_config = self.config.provider_specific.get(provider, {})

            # 计算自适应调整
            adaptive_multiplier = self._adaptive_adjustment(provider)

            # 应用限流限制
            rps = (provider_config.get('requests_per_second', self.config.requests_per_second) *
                   adaptive_multiplier)
            rpm = (provider_config.get('requests_per_minute', self.config.requests_per_minute) *
                   adaptive_multiplier)
            rph = (provider_config.get('requests_per_hour', self.config.requests_per_hour) *
                   adaptive_multiplier)

            # 获取当前速率
            current_rates = self._get_current_rates()

            # 检查是否超过限制
            if current_rates['per_second'] >= rps:
                wait_time = 1.0 / rps - (current_time - self.second_window[-1])
                logger.debug(f"⏳ {provider} 达到每秒限流，等待 {wait_time:.2f}秒")
                return False

            if current_rates['per_minute'] >= rpm:
                wait_time = 60.0 / rpm - (current_time - self.minute_window[-1])
                logger.debug(f"⏳ {provider} 达到每分钟限流，等待 {wait_time:.2f}秒")
                return False

            if current_rates['per_hour'] >= rph:
                wait_time = 3600.0 / rph - (current_time - self.hour_window[-1])
                logger.debug(f"⏳ {provider} 达到每小时限流，等待 {wait_time:.2f}秒")
                return False

            # 令牌桶算法
            time_passed = current_time - self.last_refill
            tokens_to_add = time_passed * rps
            self.tokens = min(self.config.burst_size, self.tokens + tokens_to_add)
            self.last_refill = current_time

            if self.tokens < 1:
                logger.debug(f"⏳ {provider} 令牌桶为空，等待令牌生成")
                return False

            # 消耗令牌
            self.tokens -= 1

            # 记录请求
            self.second_window.append(current_time)
            self.minute_window.append(current_time)
            self.hour_window.append(current_time)

            logger.debug(f"✅ {provider} 限流检查通过，当前令牌: {self.tokens:.2f}")
            return True

    def record_request(self, provider: str, success: bool, response_time: float, endpoint: str = ""):
        """记录请求结果"""
        with self._lock:
            current_time = time.time()

            # 创建请求记录
            record = RequestRecord(
                timestamp=current_time,
                provider=provider,
                success=success,
                response_time=response_time,
                endpoint=endpoint
            )

            self.request_history.append(record)

            # 更新提供商统计
            self._update_provider_stats(provider, success, response_time)

            # 记录错误
            if not success:
                self.last_error_time = current_time
                stats = self.provider_stats[provider]
                stats['rate_limit_hits'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取限流统计"""
        with self._lock:
            self._clean_old_records()

            total_requests = len(self.request_history)
            successful_requests = sum(1 for r in self.request_history if r.success)

            current_rates = self._get_current_rates()

            provider_stats = {}
            for provider, stats in self.provider_stats.items():
                provider_stats[provider] = {
                    'total_requests': stats['total_requests'],
                    'successful_requests': stats['successful_requests'],
                    'failed_requests': stats['failed_requests'],
                    'rate_limit_hits': stats['rate_limit_hits'],
                    'success_rate': (stats['successful_requests'] / stats['total_requests']
                                   if stats['total_requests'] > 0 else 0),
                    'avg_response_time': stats['avg_response_time'],
                    'current_rate': stats['current_rate']
                }

            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'overall_success_rate': successful_requests / total_requests if total_requests > 0 else 0,
                'current_rates': current_rates,
                'provider_stats': provider_stats,
                'adaptive_multiplier': self.adaptive_multiplier,
                'current_tokens': self.tokens,
                'burst_size': self.config.burst_size
            }

class MultiProviderRateLimiter:
    """多提供商限流管理器"""

    def __init__(self):
        self.limiters: Dict[str, AdaptiveRateLimiter] = {}
        self._initialize_provider_limiters()

    def _initialize_provider_limiters(self):
        """初始化各提供商的限流器"""
        # 默认限流配置
        default_config = RateLimitConfig(
            requests_per_second=1.0,
            requests_per_minute=30.0,
            requests_per_hour=500.0,
            burst_size=3,
            adaptive_enabled=True
        )

        # 提供商特定的限流配置
        provider_configs = {
            'deepseek': RateLimitConfig(
                requests_per_second=0.5,
                requests_per_minute=20.0,
                requests_per_hour=300.0,
                burst_size=2,
                adaptive_enabled=True
            ),
            'kimi': RateLimitConfig(
                requests_per_second=0.8,
                requests_per_minute=25.0,
                requests_per_hour=400.0,
                burst_size=3,
                adaptive_enabled=True
            ),
            'qwen': RateLimitConfig(
                requests_per_second=1.0,
                requests_per_minute=35.0,
                requests_per_hour=600.0,
                burst_size=4,
                adaptive_enabled=True
            ),
            'openai': RateLimitConfig(
                requests_per_second=0.3,
                requests_per_minute=15.0,
                requests_per_hour=200.0,
                burst_size=2,
                adaptive_enabled=True
            )
        }

        # 创建限流器
        for provider, config in provider_configs.items():
            self.limiters[provider] = AdaptiveRateLimiter(config)

    async def wait_for_permission(self, provider: str, endpoint: str = "",
                                timeout: float = 30.0) -> bool:
        """等待获取请求许可"""
        if provider not in self.limiters:
            # 使用默认限流器
            self.limiters[provider] = AdaptiveRateLimiter(RateLimitConfig())

        limiter = self.limiters[provider]
        start_time = time.time()

        while time.time() - start_time < timeout:
            if await limiter.acquire_permission(provider, endpoint):
                return True

            # 等待一小段时间后重试
            await asyncio.sleep(0.1)

        logger.warning(f"⏰ {provider} 等待限流许可超时")
        return False

    def record_request_result(self, provider: str, success: bool,
                            response_time: float, endpoint: str = ""):
        """记录请求结果"""
        if provider in self.limiters:
            self.limiters[provider].record_request(provider, success, response_time, endpoint)

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有限流器的统计"""
        all_stats = {}
        for provider, limiter in self.limiters.items():
            all_stats[provider] = limiter.get_stats()
        return all_stats

    def reset_stats(self, provider: str = None):
        """重置统计"""
        if provider:
            if provider in self.limiters:
                # 重新创建限流器以清空统计
                config = self.limiters[provider].config
                self.limiters[provider] = AdaptiveRateLimiter(config)
        else:
            # 重置所有
            self._initialize_provider_limiters()

# 全局限流器实例
rate_limiter = MultiProviderRateLimiter()

# 便捷的限流装饰器
def rate_limit(provider: str, endpoint: str = "", timeout: float = 30.0):
    """限流装饰器"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # 等待限流许可
            if not await rate_limiter.wait_for_permission(provider, endpoint, timeout):
                raise Exception(f"Rate limit timeout for {provider}")

            start_time = time.time()
            success = False

            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                # 判断是否是限流错误
                if 'rate limit' in str(e).lower() or 'too many requests' in str(e).lower():
                    rate_limiter.limiters[provider].last_error_time = time.time()
                raise
            finally:
                # 记录请求结果
                response_time = time.time() - start_time
                rate_limiter.record_request_result(provider, success, response_time, endpoint)

        return wrapper
    return decorator

# 向后兼容的函数
async def check_rate_limit(provider: str) -> bool:
    """检查是否可以发送请求（向后兼容）"""
    return await rate_limiter.wait_for_permission(provider)

def update_rate_limit_stats(provider: str, success: bool, response_time: float):
    """更新限流统计（向后兼容）"""
    rate_limiter.record_request_result(provider, success, response_time)

def get_rate_limit_stats() -> Dict[str, Any]:
    """获取限流统计（向后兼容）"""
    return rate_limiter.get_all_stats()
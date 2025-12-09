"""
超时管理模块
处理AI请求的超时控制和性能统计
"""

import time
import random
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from core.base import BaseConfig
from core.exceptions import NetworkError, TimeoutError

logger = logging.getLogger(__name__)

@dataclass
class TimeoutStats:
    """超时统计"""
    avg_response_time: float = 0.0
    timeout_rate: float = 0.0
    total_requests: int = 0
    timeout_requests: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'avg_response_time': self.avg_response_time,
            'timeout_rate': self.timeout_rate,
            'total_requests': self.total_requests,
            'timeout_requests': self.timeout_requests,
            'last_update': self.last_update.isoformat()
        }

@dataclass
class ProviderTimeoutStats:
    """提供商超时统计"""
    avg_response_time: float = 0.0
    timeout_count: int = 0
    total_requests: int = 0
    success_rate: float = 1.0
    last_response_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'avg_response_time': self.avg_response_time,
            'timeout_count': self.timeout_count,
            'total_requests': self.total_requests,
            'success_rate': self.success_rate,
            'last_response_time': self.last_response_time
        }

class TimeoutManager:
    """超时管理器"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        self.config = config or BaseConfig(name="TimeoutManager")
        self.timeout_stats = {
            'global': TimeoutStats(),
            'provider': {}  # 各提供商的统计
        }
        self.timeout_config = self._get_default_timeout_config()
        self.retry_cost_config = self._get_default_retry_cost_config()
        
    def _get_default_timeout_config(self) -> Dict[str, Dict[str, float]]:
        """获取默认超时配置 - 针对不稳定网络优化"""
        return {
            'deepseek': {
                'connection_timeout': 15.0,  # 增加连接超时
                'response_timeout': 25.0,    # 增加响应超时
                'total_timeout': 45.0,       # 增加总超时
                'retry_base_delay': 5.0,     # 增加重试延迟
                'max_retries': 2,            # 减少重试次数，避免频繁重试
                'performance_score': 0.75,
                'connection_pool_size': 20,  # 连接池大小
                'keepalive_timeout': 120     # 保持连接时间
            },
            'kimi': {
                'connection_timeout': 12.0,  # 增加连接超时
                'response_timeout': 22.0,    # 增加响应超时
                'total_timeout': 40.0,       # 增加总超时
                'retry_base_delay': 4.0,     # 增加重试延迟
                'max_retries': 2,            # 减少重试次数
                'performance_score': 0.80,
                'connection_pool_size': 20,
                'keepalive_timeout': 120
            },
            'qwen': {
                'connection_timeout': 10.0,  # 增加连接超时
                'response_timeout': 20.0,    # 增加响应超时
                'total_timeout': 35.0,       # 增加总超时
                'retry_base_delay': 3.5,     # 增加重试延迟
                'max_retries': 2,            # 减少重试次数
                'performance_score': 0.85,
                'connection_pool_size': 20,
                'keepalive_timeout': 120
            },
            'openai': {
                'connection_timeout': 18.0,  # 增加连接超时
                'response_timeout': 30.0,    # 增加响应超时
                'total_timeout': 50.0,       # 增加总超时
                'retry_base_delay': 6.0,     # 增加重试延迟
                'max_retries': 1,            # 减少重试次数
                'performance_score': 0.70,
                'connection_pool_size': 20,
                'keepalive_timeout': 120
            }
        }
    
    def _get_default_retry_cost_config(self) -> Dict[str, Any]:
        """获取默认重试成本配置"""
        return {
            'max_daily_cost': 150.0,
            'current_daily_cost': 0.0,
            'cost_weights': {
                'deepseek': 1.2,
                'kimi': 1.3,
                'qwen': 1.0,
                'openai': 1.8
            }
        }
    
    def get_timeout_config(self, provider: str) -> Dict[str, float]:
        """获取提供商的超时配置"""
        return self.timeout_config.get(provider, self.timeout_config['openai'])
    
    def calculate_dynamic_timeout(self, provider: str, base_config: Dict[str, float]) -> Dict[str, float]:
        """计算动态调整的超时时间"""
        try:
            # 获取历史统计
            stats = self.timeout_stats['provider'].get(provider, ProviderTimeoutStats())
            avg_response_time = stats.avg_response_time
            success_rate = stats.success_rate
            timeout_count = stats.timeout_count
            total_requests = stats.total_requests
            
            # 基础超时配置
            adjusted_config = base_config.copy()
            
            # 如果历史数据不足，使用基础配置
            if total_requests < 5:
                return adjusted_config
            
            # 基于成功率调整超时时间
            if success_rate < 0.8:  # 成功率低于80%
                # 增加超时时间
                multiplier = 1.2 if success_rate < 0.6 else 1.1
                adjusted_config['total_timeout'] *= multiplier
                adjusted_config['response_timeout'] *= multiplier
                logger.info(f"⏰ {provider} 成功率低({success_rate:.2f})，超时时间调整: {multiplier:.1f}x")
            
            elif success_rate > 0.95 and avg_response_time > 0:  # 成功率高且响应时间稳定
                # 减少超时时间以提高效率
                multiplier = 0.9
                adjusted_config['total_timeout'] *= multiplier
                adjusted_config['response_timeout'] *= multiplier
                logger.info(f"⏰ {provider} 性能优秀，超时时间优化: {multiplier:.1f}x")
            
            # 基于最近超时情况调整
            recent_timeout_rate = timeout_count / total_requests if total_requests > 0 else 0
            if recent_timeout_rate > 0.2:  # 最近超时率超过20%
                adjusted_config['total_timeout'] *= 1.3
                adjusted_config['retry_base_delay'] *= 1.2
                logger.info(f"⏰ {provider} 最近超时率高({recent_timeout_rate:.2f})，增加超时缓冲")
            
            # 确保最小超时时间
            adjusted_config['total_timeout'] = max(adjusted_config['total_timeout'], 5.0)
            adjusted_config['response_timeout'] = max(adjusted_config['response_timeout'], 3.0)
            adjusted_config['connection_timeout'] = max(adjusted_config['connection_timeout'], 2.0)
            
            return adjusted_config
            
        except Exception as e:
            logger.error(f"动态超时计算失败: {e}")
            return base_config
    
    def update_timeout_stats(self, provider: str, response_time: float, success: bool, timeout_type: str = None):
        """更新超时统计信息"""
        try:
            # 初始化提供商统计
            if provider not in self.timeout_stats['provider']:
                self.timeout_stats['provider'][provider] = ProviderTimeoutStats()
            
            stats = self.timeout_stats['provider'][provider]
            global_stats = self.timeout_stats['global']
            
            # 更新全局统计
            global_stats.total_requests += 1
            if not success:
                global_stats.timeout_requests += 1
            
            # 更新提供商统计
            stats.total_requests += 1
            stats.last_response_time = response_time
            
            if success and response_time > 0:
                # 更新平均响应时间（使用移动平均）
                if stats.avg_response_time == 0:
                    stats.avg_response_time = response_time
                else:
                    stats.avg_response_time = (stats.avg_response_time * 0.8) + (response_time * 0.2)
            elif not success:
                if timeout_type == 'timeout':
                    stats.timeout_count += 1
            
            # 计算成功率
            if stats.total_requests > 0:
                stats.success_rate = (stats.total_requests - stats.timeout_count) / stats.total_requests
                global_stats.timeout_rate = global_stats.timeout_requests / global_stats.total_requests
            
            # 记录统计更新
            logger.info(f"📊 {provider} 超时统计更新: 成功率={stats.success_rate:.2f}, 平均响应={stats.avg_response_time:.1f}s, 总请求={stats.total_requests}")
            
        except Exception as e:
            logger.error(f"超时统计更新失败: {e}")
    
    def calculate_exponential_backoff(self, provider: str, attempt: int, base_delay: float) -> float:
        """计算指数退避延迟时间"""
        try:
            # 基础指数退避公式: base_delay * 2^attempt + jitter
            jitter = random.uniform(0.1, 0.5)  # 添加随机抖动避免惊群效应
            backoff_delay = base_delay * (2 ** attempt) + jitter
            
            # 最大退避时间限制
            max_backoff = 30.0  # 最大30秒
            backoff_delay = min(backoff_delay, max_backoff)
            
            # 基于提供商性能调整退避策略
            provider_stats = self.timeout_stats['provider'].get(provider, ProviderTimeoutStats())
            success_rate = provider_stats.success_rate
            
            # 成功率低的提供商，增加退避时间
            if success_rate < 0.7:
                backoff_delay *= 1.5
            
            logger.info(f"⏰ {provider} 指数退避: 第{attempt}次重试，延迟{backoff_delay:.1f}秒")
            return backoff_delay
            
        except Exception as e:
            logger.error(f"指数退避计算失败: {e}")
            return base_delay * (2 ** attempt)
    
    def check_retry_cost_limit(self, provider: str) -> bool:
        """检查重试成本是否超出限制"""
        try:
            # 检查每日成本限制
            if self.retry_cost_config['current_daily_cost'] >= self.retry_cost_config['max_daily_cost']:
                logger.warning(f"⚠️ {provider} 重试成本已达每日上限({self.retry_cost_config['max_daily_cost']})")
                return False
            
            # 计算提供商特定的成本权重
            cost_weight = self.retry_cost_config['cost_weights'].get(provider, 1.0)
            estimated_cost = cost_weight
            
            # 检查是否会超出限制
            if self.retry_cost_config['current_daily_cost'] + estimated_cost > self.retry_cost_config['max_daily_cost']:
                logger.warning(f"⚠️ {provider} 重试成本将超出限制，拒绝重试")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"重试成本检查失败: {e}")
            return False
    
    def update_retry_cost(self, provider: str):
        """更新重试成本"""
        try:
            cost_weight = self.retry_cost_config['cost_weights'].get(provider, 1.0)
            self.retry_cost_config['current_daily_cost'] += cost_weight
            
            logger.info(f"💰 重试成本更新: {provider} +{cost_weight:.1f}, 当前总计: {self.retry_cost_config['current_daily_cost']:.1f}")
            
        except Exception as e:
            logger.error(f"重试成本更新失败: {e}")
    
    def get_timeout_performance(self) -> Dict[str, Any]:
        """获取超时性能统计"""
        try:
            global_stats = self.timeout_stats['global']
            if global_stats.total_requests > 0:
                logger.info(f"📊 全局超时性能: 总请求={global_stats.total_requests}, 超时率={global_stats.timeout_rate:.2%}")
            
            # 输出各提供商的统计
            for provider, stats in self.timeout_stats['provider'].items():
                if stats.total_requests > 0:
                    logger.info(f"📊 {provider} 性能: 成功率={stats.success_rate:.2%}, 平均响应={stats.avg_response_time:.1f}s, 请求数={stats.total_requests}")
            
            return {
                'global': global_stats.to_dict(),
                'providers': {k: v.to_dict() for k, v in self.timeout_stats['provider'].items()}
            }
            
        except Exception as e:
            logger.error(f"超时性能记录失败: {e}")
            return {}
    
    def reset_daily_cost(self):
        """重置每日成本计数"""
        self.retry_cost_config['current_daily_cost'] = 0.0
        logger.info("🔄 每日重试成本已重置")
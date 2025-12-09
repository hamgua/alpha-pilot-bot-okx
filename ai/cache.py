"""
AI请求缓存模块
缓存AI请求结果，避免重复请求相同数据
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AIRequestCache:
    """AI请求缓存管理器"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}

    def _generate_cache_key(self, provider: str, prompt: str, model: str, **kwargs) -> str:
        """生成缓存键"""
        # 创建标准化的请求数据
        cache_data = {
            'provider': provider,
            'prompt': prompt.strip(),  # 去除首尾空格
            'model': model,
            'kwargs': {k: v for k, v in sorted(kwargs.items()) if k not in ['api_key', 'token']}  # 排除敏感信息
        }

        # 生成哈希键
        key_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, provider: str, prompt: str, model: str, **kwargs) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        try:
            cache_key = self._generate_cache_key(provider, prompt, model, **kwargs)
            current_time = time.time()

            # 检查缓存是否存在
            if cache_key not in self._cache:
                return None

            # 检查缓存是否过期
            cache_entry = self._cache[cache_key]
            if current_time - cache_entry['timestamp'] > self.ttl_seconds:
                # 缓存过期，删除条目
                del self._cache[cache_key]
                del self._access_times[cache_key]
                return None

            # 更新访问时间
            self._access_times[cache_key] = current_time

            logger.debug(f"缓存命中: {provider} - {cache_key[:8]}...")
            return cache_entry['data']

        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
            return None

    def set(self, provider: str, prompt: str, model: str, data: Dict[str, Any], **kwargs) -> None:
        """设置缓存结果"""
        try:
            cache_key = self._generate_cache_key(provider, prompt, model, **kwargs)
            current_time = time.time()

            # 清理过期缓存
            self._cleanup_expired()

            # 如果缓存已满，清理最久未使用的条目
            if len(self._cache) >= self.max_size:
                self._cleanup_lru()

            # 设置缓存
            self._cache[cache_key] = {
                'data': data,
                'timestamp': current_time,
                'provider': provider
            }
            self._access_times[cache_key] = current_time

            logger.debug(f"缓存设置: {provider} - {cache_key[:8]}...")

        except Exception as e:
            logger.error(f"缓存设置失败: {e}")

    def _cleanup_expired(self) -> None:
        """清理过期缓存"""
        try:
            current_time = time.time()
            expired_keys = []

            for key, entry in self._cache.items():
                if current_time - entry['timestamp'] > self.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                del self._access_times[key]

            if expired_keys:
                logger.debug(f"清理过期缓存: {len(expired_keys)} 条")

        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")

    def _cleanup_lru(self) -> None:
        """清理最久未使用的缓存（LRU）"""
        try:
            if not self._access_times:
                return

            # 找到最久未使用的键
            oldest_key = min(self._access_times, key=self._access_times.get)

            del self._cache[oldest_key]
            del self._access_times[oldest_key]

            logger.debug(f"LRU清理: {oldest_key[:8]}...")

        except Exception as e:
            logger.error(f"LRU清理失败: {e}")

    def clear_provider_cache(self, provider: str) -> None:
        """清理特定提供商的缓存"""
        try:
            keys_to_remove = []
            for key, entry in self._cache.items():
                if entry.get('provider') == provider:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]
                del self._access_times[key]

            logger.info(f"清理 {provider} 缓存: {len(keys_to_remove)} 条")

        except Exception as e:
            logger.error(f"清理提供商缓存失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'hit_rate': self._calculate_hit_rate(),
                'providers': self._get_provider_stats()
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {'error': str(e)}

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率（简化版）"""
        # 这里可以实现更复杂的命中率统计
        return 0.0  # 简化实现

    def _get_provider_stats(self) -> Dict[str, int]:
        """获取各提供商的缓存统计"""
        try:
            provider_stats = {}
            for entry in self._cache.values():
                provider = entry.get('provider', 'unknown')
                provider_stats[provider] = provider_stats.get(provider, 0) + 1
            return provider_stats
        except Exception as e:
            logger.error(f"获取提供商统计失败: {e}")
            return {}

# 全局缓存实例
ai_request_cache = AIRequestCache()
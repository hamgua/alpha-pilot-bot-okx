"""
缓存管理模块
提供内存缓存和数据持久化功能
"""

import time
import threading
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheItem:
    """缓存项"""
    data: Any
    timestamp: float
    duration: int
    expires_at: float = None
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.timestamp + self.duration
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at
    
    def time_remaining(self) -> float:
        """获取剩余时间"""
        return max(0, self.expires_at - time.time())

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 1000, default_duration: int = 900):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存项数量
            default_duration: 默认缓存时间（秒）
        """
        self._cache: Dict[str, CacheItem] = {}
        self._max_size = max_size
        self._default_duration = default_duration
        self._lock = threading.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据，如果不存在或已过期则返回None
        """
        with self._lock:
            self._stats['total_requests'] += 1
            
            item = self._cache.get(key)
            if item is None:
                self._stats['misses'] += 1
                return None
            
            if item.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return item.data
    
    def set(self, key: str, data: Any, duration: Optional[int] = None) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            duration: 缓存时间（秒），默认为None使用默认值
        """
        with self._lock:
            # 如果缓存已满，执行LRU清理
            if len(self._cache) >= self._max_size:
                self._evict_lru()
            
            duration = duration or self._default_duration
            self._cache[key] = CacheItem(data, time.time(), duration)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._reset_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            hit_rate = self._stats['hits'] / max(self._stats['total_requests'], 1)
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'total_requests': self._stats['total_requests']
            }
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存项
        
        Returns:
            清理的缓存项数量
        """
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, item in self._cache.items():
                if item.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """执行LRU清理（移除最久未使用的项）"""
        if not self._cache:
            return
        
        # 找到最久未使用的项（基于时间戳）
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]
        self._stats['evictions'] += 1
    
    def _reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取缓存数据
        
        Args:
            keys: 缓存键列表
            
        Returns:
            存在的缓存数据字典
        """
        results = {}
        for key in keys:
            data = self.get(key)
            if data is not None:
                results[key] = data
        return results
    
    def set_multiple(self, items: Dict[str, Any], duration: Optional[int] = None) -> None:
        """
        批量设置缓存数据
        
        Args:
            items: 键值对字典
            duration: 缓存时间（秒）
        """
        for key, data in items.items():
            self.set(key, data, duration)
    
    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        item = self._cache.get(key)
        return item is not None and not item.is_expired()
    
    def get_time_remaining(self, key: str) -> float:
        """
        获取缓存项剩余时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余时间（秒），如果键不存在返回0
        """
        item = self._cache.get(key)
        if item is None:
            return 0.0
        return item.time_remaining()

class MemoryManager:
    """内存管理器"""
    
    def __init__(self, max_history: int = 1000):
        """
        初始化内存管理器
        
        Args:
            max_history: 最大历史记录数
        """
        self._histories: Dict[str, List[Any]] = {}
        self._max_history = max_history
        self._lock = threading.Lock()
    
    def add_to_history(self, key: str, item: Any) -> int:
        """
        添加历史记录
        
        Args:
            key: 历史记录键
            item: 要添加的项
            
        Returns:
            当前历史记录数量
        """
        with self._lock:
            if key not in self._histories:
                self._histories[key] = []
            
            self._histories[key].append(item)
            
            # 限制历史长度
            if len(self._histories[key]) > self._max_history:
                self._histories[key].pop(0)
            
            return len(self._histories[key])
    
    def get_history(self, key: str, limit: Optional[int] = None) -> List[Any]:
        """
        获取历史记录
        
        Args:
            key: 历史记录键
            limit: 限制返回的记录数
            
        Returns:
            历史记录列表
        """
        with self._lock:
            history = self._histories.get(key, [])
            if limit:
                return history[-limit:]
            return history.copy()
    
    def clear_history(self, key: Optional[str] = None) -> bool:
        """
        清空历史记录
        
        Args:
            key: 历史记录键，如果为None则清空所有
            
        Returns:
            是否成功清空
        """
        with self._lock:
            if key is None:
                self._histories.clear()
                return True
            elif key in self._histories:
                del self._histories[key]
                return True
            return False
    
    def get_all_keys(self) -> List[str]:
        """获取所有历史记录键"""
        with self._lock:
            return list(self._histories.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取内存管理统计"""
        with self._lock:
            total_items = sum(len(h) for h in self._histories.values())
            return {
                'total_items': total_items,
                'keys_count': len(self._histories),
                'max_per_key': self._max_history,
                'memory_usage': total_items * 64,  # 粗略估计
                'keys': list(self._histories.keys())
            }

# 全局实例
cache_manager = CacheManager()
memory_manager = MemoryManager()

# 向后兼容的函数
def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计（向后兼容）"""
    return cache_manager.get_stats()

def get_memory_stats() -> Dict[str, Any]:
    """获取内存统计（向后兼容）"""
    return memory_manager.get_stats()

def clear_all_cache() -> None:
    """清空所有缓存（向后兼容）"""
    cache_manager.clear()

def clear_all_history() -> None:
    """清空所有历史记录（向后兼容）"""
    for key in memory_manager.get_all_keys():
        memory_manager.clear_history(key)

# 导出主要功能
__all__ = [
    'CacheManager',
    'MemoryManager',
    'cache_manager',
    'memory_manager',
    'get_cache_stats',
    'get_memory_stats',
    'clear_all_cache',
    'clear_all_history'
]
"""
工具子包 - 提供通用工具和功能
"""

# 由于utils.py文件不存在，我们需要创建基本的工具函数
# 这里定义一些基本的日志和工具函数

import logging
from datetime import datetime
from typing import Any, Dict, Optional

def log_info(message: str) -> None:
    """记录信息日志"""
    logging.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def log_warning(message: str) -> None:
    """记录警告日志"""
    logging.warning(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def log_error(message: str) -> None:
    """记录错误日志"""
    logging.error(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# 内存管理器（简化版本）
class MemoryManager:
    def __init__(self):
        self.data = {}
    
    def add_to_history(self, key: str, value: Any) -> None:
        """添加到历史记录"""
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)
        
        # 限制历史记录长度
        if len(self.data[key]) > 100:
            self.data[key] = self.data[key][-100:]
    
    def get_history(self, key: str, limit: int = 10) -> list:
        """获取历史记录"""
        return self.data.get(key, [])[-limit:]

# 缓存管理器（简化版本）
class CacheManager:
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, duration: int = 900) -> None:
        """设置缓存值"""
        self.cache[key] = value
    
    def cleanup_expired(self) -> None:
        """清理过期缓存"""
        # 简化实现，实际应该检查过期时间
        if len(self.cache) > 1000:
            # 保留最近100个
            items = list(self.cache.items())
            self.cache = dict(items[-100:])

# 系统监控器（简化版本）
class SystemMonitor:
    def __init__(self):
        self.counters = {
            'api_calls': 0,
            'trades': 0,
            'warnings': 0,
            'errors': 0
        }
        self.start_time = datetime.now()
    
    def increment_counter(self, counter: str) -> None:
        """增加计数器"""
        if counter in self.counters:
            self.counters[counter] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            'uptime_seconds': uptime,
            'uptime_formatted': f"{uptime/3600:.1f}小时",
            'api_calls': self.counters['api_calls'],
            'trades': self.counters['trades'],
            'warnings': self.counters['warnings'],
            'errors': self.counters['errors'],
            'error_rate': self.counters['errors'] / max(1, self.counters['api_calls']),
            'system_health': max(0, 100 - (self.counters['errors'] * 10))
        }

# 全局实例
memory_manager = MemoryManager()
cache_manager = CacheManager()
system_monitor = SystemMonitor()

__all__ = [
    'log_info',
    'log_warning',
    'log_error',
    'MemoryManager',
    'CacheManager',
    'SystemMonitor',
    'memory_manager',
    'cache_manager',
    'system_monitor'
]
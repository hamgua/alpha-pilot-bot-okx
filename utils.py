"""
Alpha Arena OKX 工具模块
包含通用工具函数和辅助功能
"""

import os
import time
import json
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from logger_config import log_info, log_warning, log_error
from trade_logger import trade_logger

@dataclass
class CacheItem:
    """缓存项数据结构"""
    data: Any
    timestamp: float
    duration: int

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, CacheItem] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            item = self._cache.get(key)
            if item and time.time() - item.timestamp < item.duration:
                return item.data
            elif item:
                # 过期，删除
                del self._cache[key]
            return None
    
    def set(self, key: str, data: Any, duration: int = 900) -> None:
        """设置缓存数据"""
        with self._lock:
            if len(self._cache) >= self._max_size:
                # LRU清理
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].timestamp)
                del self._cache[oldest_key]
            
            self._cache[key] = CacheItem(data, time.time(), duration)
    
    def clear(self, key: str = None) -> None:
        """清理缓存"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_size
            }

class MemoryManager:
    """内存管理器"""
    
    def __init__(self, max_history: int = 100):
        self._histories: Dict[str, List[Any]] = {}
        self._max_history = max_history
        self._lock = threading.Lock()
    
    def add_to_history(self, key: str, item: Any) -> int:
        """安全添加历史记录"""
        with self._lock:
            if key not in self._histories:
                self._histories[key] = []
            
            self._histories[key].append(item)
            
            # 限制历史长度
            if len(self._histories[key]) > self._max_history:
                self._histories[key].pop(0)
            
            return len(self._histories[key])
    
    def get_history(self, key: str, limit: int = None) -> List[Any]:
        """获取历史记录"""
        with self._lock:
            history = self._histories.get(key, [])
            if limit:
                return history[-limit:]
            return history
    
    def clear_history(self, key: str = None) -> None:
        """清理历史记录"""
        with self._lock:
            if key:
                self._histories.pop(key, None)
            else:
                self._histories.clear()
    
    def get_memory_stats(self) -> Dict[str, int]:
        """获取内存统计"""
        with self._lock:
            return {
                'total_items': sum(len(h) for h in self._histories.values()),
                'keys_count': len(self._histories),
                'max_per_key': self._max_history
            }

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.start_time = time.time()
        self._stats = {
            'trades': 0,
            'errors': 0,
            'warnings': 0,
            'api_calls': 0
        }
        self._lock = threading.Lock()
    
    def increment_counter(self, counter: str, value: int = 1) -> None:
        """增加计数器"""
        with self._lock:
            self._stats[counter] = self._stats.get(counter, 0) + value
    
    def get_uptime(self) -> float:
        """获取运行时间"""
        return time.time() - self.start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        with self._lock:
            return {
                **self._stats,
                'uptime_seconds': self.get_uptime(),
                'uptime_formatted': str(timedelta(seconds=int(self.get_uptime()))),
                'timestamp': datetime.now().isoformat()
            }
    
    def reset_stats(self) -> None:
        """重置统计"""
        with self._lock:
            self._stats = {k: 0 for k in self._stats}

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_price_data(data: Dict[str, Any]) -> bool:
        """验证价格数据"""
        required_fields = ['price', 'timestamp']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_signal_data(data: Dict[str, Any]) -> bool:
        """验证信号数据"""
        required_fields = ['signal', 'confidence', 'reason']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_position_data(data: Dict[str, Any]) -> bool:
        """验证持仓数据"""
        required_fields = ['side', 'size', 'entry_price']
        return all(field in data for field in required_fields)

class JSONHelper:
    """JSON工具类"""
    
    @staticmethod
    def safe_parse(json_str: str) -> Optional[Dict[str, Any]]:
        """安全解析JSON"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return None
    
    @staticmethod
    def safe_stringify(obj: Any) -> str:
        """安全序列化JSON"""
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(obj)

class TimeHelper:
    """时间工具类"""
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持续时间"""
        return str(timedelta(seconds=int(seconds)))
    
    @staticmethod
    def is_market_hours() -> bool:
        """检查是否为交易时间"""
        # 加密货币24小时交易
        return True
    
    @staticmethod
    def get_time_until_next(interval_minutes: int = 5) -> float:
        """获取到下个周期的时间"""
        now = datetime.now()
        minutes = now.minute
        next_interval = ((minutes // interval_minutes) + 1) * interval_minutes
        
        if next_interval >= 60:
            next_interval = 0
            next_hour = now.hour + 1
        else:
            next_hour = now.hour
        
        next_time = now.replace(hour=next_hour, minute=next_interval, second=0, microsecond=0)
        return (next_time - now).total_seconds()

class LoggerHelper:
    """日志辅助类"""
    
    @staticmethod
    def log_trade_event(event_type: str, data: Dict[str, Any]) -> None:
        """记录交易事件"""
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        trade_logger.log_event(log_data)
        log_info(f"📊 交易事件: {event_type} - {data}")
    
    @staticmethod
    def log_error_event(error_type: str, error_data: Dict[str, Any]) -> None:
        """记录错误事件"""
        error_info = {
            'error_type': error_type,
            'timestamp': datetime.now().isoformat(),
            'error_data': error_data
        }
        
        log_error(f"❌ 错误事件: {error_type} - {error_data}")
        trade_logger.log_error(error_info)

# 全局工具实例
cache_manager = CacheManager()
memory_manager = MemoryManager()
system_monitor = SystemMonitor()
data_validator = DataValidator()
json_helper = JSONHelper()
time_helper = TimeHelper()
logger_helper = LoggerHelper()
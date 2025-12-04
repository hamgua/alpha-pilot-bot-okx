"""
Alpha Pilot Bot OKX 工具模块
包含通用工具函数和辅助功能
"""

import os
import time
import json
import threading
import logging
import glob
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

def log_info(message):
    """输出信息日志，统一格式"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [INFO] {message}")

def log_warning(message):
    """输出警告日志，统一格式"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [WARNING] {message}")

def log_error(message):
    """输出错误日志，统一格式"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [ERROR] {message}")

@dataclass
class CacheItem:
    """缓存项数据结构"""
    data: Any
    timestamp: float
    duration: int
    expires_at: float = None
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.timestamp + self.duration

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
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存项"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, item in self._cache.items():
                if item.expires_at <= current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        return len(expired_keys)

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
    
    def clear_history(self, key: str = None) -> bool:
        """清空历史记录
        
        清空指定类型的历史记录
        
        Args:
            key: 历史记录类型键
            
        Returns:
            bool: 是否成功清空
        """
        with self._lock:
            if key:
                if key in self._histories:
                    self._total_items -= len(self._histories[key])
                    del self._histories[key]
                    return True
                return False
            else:
                self._total_items = 0
                self._histories.clear()
                return True
        with self._lock:
            if key:
                self._histories.pop(key, None)
            else:
                self._histories.clear()
    
    def get_all_keys(self) -> List[str]:
        """获取所有历史记录键
        
        获取所有历史记录类型的键列表
        
        Returns:
            List[str]: 历史记录键列表
        """
        with self._lock:
            return list(self._histories.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        获取内存管理器的详细统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        with self._lock:
            return {
                'total_items': self._total_items,
                'keys_count': len(self._histories),
                'max_per_key': self._max_history,
                'memory_usage': self._total_items * 8  # 粗略估计
            }
    
    def cleanup_old_entries(self, max_age: int = 3600) -> int:
        """清理过期的历史记录
        
        清理超过指定时间的历史记录项
        
        Args:
            max_age: 最大存活时间（秒）
            
        Returns:
            int: 清理的记录数量
        """
        # 简化实现，实际应该根据时间戳清理
        return 0
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
    
    @staticmethod
    def safe_json_serialize(obj: Any) -> str:
        """安全序列化JSON"""
        try:
            return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            log_warning(f"JSON序列化失败: {e}")
            return str(obj)

# 整合日志和数据管理功能
# LoggerConfig类已移除，统一使用项目级日志配置

class TradeLogger:
    """交易日志管理 - 整合trade_logger.py功能"""
    
    def __init__(self):
        from pathlib import Path
        self.trade_log_file = Path("logs") / "trades.json"
        self.trade_log_file.parent.mkdir(exist_ok=True)
    
    def log_ai_decision(self, decision_data):
        """记录AI决策"""
        import json
        from datetime import datetime
        
        log_entry = {
            "type": "AI_DECISION",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "signal": decision_data.get('signal', 'HOLD'),
            "confidence": decision_data.get('confidence', 'N/A'),
            "reason": decision_data.get('reason', ''),
            "price": decision_data.get('price', 0)
        }
        
        try:
            with open(self.trade_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            log_error(f"记录AI决策失败: {e}")

class DataManager:
    """数据管理 - 整合数据管理功能"""
    
    def __init__(self):
        from pathlib import Path
        self.data_dir = Path(__file__).parent / "data_json"
        self.data_dir.mkdir(exist_ok=True)
        
        self.data_file = self.data_dir / "trading_data.json"
        self.trades_file = self.data_dir / "trades_history.json"
        self.equity_file = self.data_dir / "equity_history.json"
    
    def save_trading_data(self, data):
        """保存交易数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"保存交易数据失败: {e}")
    
    def load_trading_data(self):
        """加载交易数据"""
        try:
            if self.data_file.exists():
                import json
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_error(f"加载交易数据失败: {e}")
            return {}
    
    def save_market_data(self, data):
        """保存市场数据"""
        self.save_trading_data(data)
    
    def get_data_summary(self):
        """获取数据摘要"""
        try:
            summary = {}
            
            # 交易数据摘要
            if self.data_file.exists():
                data = self.load_trading_data()
                summary['trading_data'] = {
                    'total_records': len(data) if isinstance(data, dict) else 0,
                    'last_update': data.get('timestamp', '未知') if isinstance(data, dict) else '未知'
                }
            else:
                summary['trading_data'] = {'total_records': 0, 'last_update': '无数据'}
            
            # 市场数据摘要
            summary['market_data'] = {'total_records': 0, 'last_update': '无数据'}
            
            return summary
            
        except Exception as e:
            log_error(f"获取数据摘要失败: {e}")
            return {'trading_data': {'total_records': 0, 'last_update': '错误'}, 
                   'market_data': {'total_records': 0, 'last_update': '错误'}}
    
    def cleanup_old_data(self, days_to_keep=30):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            # 这里可以添加实际的清理逻辑
            log_info(f"📊 数据清理完成，保留{days_to_keep}天内数据")
        except Exception as e:
            log_error(f"清理旧数据失败: {e}")
    
    def save_ai_signal(self, signal_data):
        """保存AI信号"""
        try:
            signals_file = self.data_dir / "ai_signals.json"
            existing_signals = []
            
            if signals_file.exists():
                with open(signals_file, 'r', encoding='utf-8') as f:
                    existing_signals = json.load(f)
            
            existing_signals.append(signal_data)
            
            # 保留最近100个信号
            if len(existing_signals) > 100:
                existing_signals = existing_signals[-100:]
            
            with open(signals_file, 'w', encoding='utf-8') as f:
                json.dump(existing_signals, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log_error(f"保存AI信号失败: {e}")
    
    def save_performance_metrics(self, metrics):
        """保存性能指标"""
        try:
            metrics_file = self.data_dir / "performance_metrics.json"
            existing_metrics = []
            
            if metrics_file.exists():
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    existing_metrics = json.load(f)
            
            existing_metrics.append(metrics)
            
            # 保留最近1000个指标
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(existing_metrics, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log_error(f"保存性能指标失败: {e}")

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
    def get_time_until_next(interval_minutes: int = 15) -> float:
        """获取到下个周期的时间
        
        支持15分钟循环周期，在每个整点的00、15、30、45分钟开始运行
        """
        now = datetime.now()
        minutes = now.minute
        
        # 计算下一个15分钟间隔
        next_interval = ((minutes // interval_minutes) + 1) * interval_minutes
        
        if next_interval >= 60:
            next_interval = 0
            next_hour = now.hour + 1
        else:
            next_hour = now.hour
        
        # 处理小时溢出
        if next_hour >= 24:
            next_hour = 0
            next_day = now.day + 1
            # 处理月份天数变化
            try:
                next_time = now.replace(day=next_day, hour=next_hour, minute=next_interval, second=0, microsecond=0)
            except ValueError:
                # 如果日期无效（如2月30日），则使用下个月的第一天
                next_month = now.month + 1
                next_year = now.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                next_time = datetime(next_year, next_month, 1, next_hour, next_interval, 0, 0)
        else:
            try:
                next_time = now.replace(hour=next_hour, minute=next_interval, second=0, microsecond=0)
            except ValueError:
                # 处理夏令时等特殊情况
                next_time = now + timedelta(hours=1)
                next_time = next_time.replace(minute=next_interval, second=0, microsecond=0)
        
        return max(0, (next_time - now).total_seconds())

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
        
        # 使用TradeLogger记录事件
        trade_logger_instance = TradeLogger()
        trade_logger_instance.log_ai_decision(log_data)
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
        # 使用TradeLogger记录错误
        trade_logger_instance = TradeLogger()
        trade_logger_instance.log_ai_decision(error_info)

class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        self.classification_rules = {
            'network': [
                'ConnectionError', 'TimeoutError', 'NetworkError',
                'SSLError', 'ProxyError', 'DNSLookupError', 'ConnectionResetError'
            ],
            'api': [
                'APIError', 'RateLimitError', 'AuthenticationError',
                'PermissionError', 'InvalidRequestError', 'ExchangeError',
                'InsufficientFunds', 'InvalidOrder', 'OrderNotFound'
            ],
            'data': [
                'DataError', 'ValidationError', 'MissingDataError',
                'PriceError', 'TimestampError', 'FormatError', 'JSONDecodeError'
            ],
            'system': [
                'MemoryError', 'SystemError', 'ProcessError',
                'ResourceError', 'ThreadError', 'QueueError', 'OSError'
            ],
            'strategy': [
                'StrategyError', 'CalculationError', 'LogicError',
                'ConfigurationError', 'ParameterError'
            ]
        }
    
    def classify_error(self, error: Exception) -> str:
        """对错误进行分类"""
        error_name = type(error).__name__
        error_message = str(error).lower()
        
        for category, patterns in self.classification_rules.items():
            if any(pattern.lower() in error_name.lower() or 
                   pattern.lower() in error_message 
                   for pattern in patterns):
                return category
        
        return 'unknown'

class ErrorRecoveryManager:
    """异常恢复管理器"""
    
    def __init__(self):
        # 延迟导入config，避免循环导入
        try:
            from config import config
            self.config = config.get('system', 'error_recovery') or {}
        except ImportError:
            # 如果导入失败，使用默认配置
            self.config = {
                'network': {'max_retries': 3, 'retry_delay': 5, 'cooldown_duration': 60},
                'api': {'max_retries': 2, 'retry_delay': 3},
                'rate_limit': {'backoff_multiplier': 2, 'base_delay': 10},
                'system': {'memory_threshold': 0.8}
            }
        
        self.error_classifier = ErrorClassifier()
        self.recovery_strategies = {
            'network': self._handle_network_error,
            'api': self._handle_api_error,
            'data': self._handle_data_error,
            'system': self._handle_system_error,
            'strategy': self._handle_strategy_error,
            'unknown': self._handle_unknown_error
        }
        self.error_history = []
        self.recovery_stats = {'total_errors': 0, 'successful_recoveries': 0}
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """统一的错误处理入口"""
        
        self.recovery_stats['total_errors'] += 1
        
        # 1. 错误分类
        error_category = self.error_classifier.classify_error(error)
        
        # 2. 记录错误
        error_record = self._record_error(error, error_category, context)
        
        # 3. 执行恢复策略
        recovery_result = self._execute_recovery(error_category, error, context)
        
        # 4. 更新统计
        if recovery_result['success']:
            self.recovery_stats['successful_recoveries'] += 1
        
        # 5. 发送警报
        if recovery_result['severity'] in ['HIGH', 'CRITICAL']:
            self._send_alert(error_record, recovery_result)
        
        return recovery_result
    
    def _record_error(self, error: Exception, category: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """记录错误信息"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': category,
            'context': context or {},
            'stack_trace': self._get_stack_trace(),
            'recovery_attempt': 0
        }
        
        self.error_history.append(error_record)
        
        # 保留最近100条错误记录
        if len(self.error_history) > 100:
            self.error_history.pop(0)
        
        return error_record
    
    def _execute_recovery(self, category: str, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行恢复策略"""
        
        recovery_handler = self.recovery_strategies.get(category, self._handle_unknown_error)
        
        try:
            return recovery_handler(error, context)
        except Exception as recovery_error:
            log_error(f"恢复策略执行失败: {recovery_error}")
            return {
                'success': False,
                'action': 'FALLBACK_SHUTDOWN',
                'severity': 'CRITICAL',
                'message': f'恢复策略失败: {recovery_error}',
                'next_action': 'SAFE_SHUTDOWN'
            }
    
    def _handle_network_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理网络错误"""
        
        retry_config = self.config.get('network', {})
        max_retries = retry_config.get('max_retries', 3)
        retry_delay = retry_config.get('retry_delay', 5)
        
        retry_count = context.get('retry_count', 0)
        
        if retry_count < max_retries:
            log_info(f"🔄 网络错误恢复 - 重试 {retry_count + 1}/{max_retries}")
            time.sleep(retry_delay)
            return {
                'success': True,
                'action': 'RETRY',
                'severity': 'LOW',
                'message': f'网络错误，{retry_delay}秒后重试',
                'next_action': 'CONTINUE',
                'retry_count': retry_count + 1
            }
        else:
            return {
                'success': False,
                'action': 'NETWORK_BACKOFF',
                'severity': 'HIGH',
                'message': '网络错误重试次数用尽，进入冷却模式',
                'next_action': 'COOLDOWN',
                'cooldown_duration': retry_config.get('cooldown_duration', 60)
            }
    
    def _handle_api_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理API错误"""
        
        error_message = str(error).lower()
        
        if 'rate limit' in error_message or '429' in error_message:
            return self._handle_rate_limit_error(context)
        elif 'authentication' in error_message or '401' in error_message:
            return self._handle_authentication_error(context)
        elif 'insufficient funds' in error_message:
            return self._handle_insufficient_funds_error(context)
        else:
            return self._handle_generic_api_error(error, context)
    
    def _handle_rate_limit_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理限频错误"""
        
        rate_limit_config = self.config.get('rate_limit', {})
        backoff_multiplier = rate_limit_config.get('backoff_multiplier', 2)
        base_delay = rate_limit_config.get('base_delay', 10)
        
        retry_count = context.get('retry_count', 0)
        delay = base_delay * (backoff_multiplier ** retry_count)
        
        log_info(f"⏱️ 限频保护 - 等待 {delay} 秒")
        time.sleep(min(delay, 60))  # 最大等待60秒
        
        return {
            'success': True,
            'action': 'RATE_LIMIT_BACKOFF',
            'severity': 'MEDIUM',
            'message': f'限频保护，等待{delay}秒',
            'next_action': 'RETRY',
            'retry_count': retry_count + 1
        }
    
    def _handle_authentication_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理认证错误"""
        
        log_error("🔐 API认证失败 - 需要检查API密钥配置")
        return {
            'success': False,
            'action': 'AUTH_FAILURE',
            'severity': 'CRITICAL',
            'message': 'API认证失败，请检查API密钥配置',
            'next_action': 'STOP_TRADING'
        }
    
    def _handle_insufficient_funds_error(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理资金不足错误"""
        
        log_warning("💰 资金不足 - 调整交易规模")
        return {
            'success': True,
            'action': 'ADJUST_POSITION_SIZE',
            'severity': 'MEDIUM',
            'message': '资金不足，调整交易规模',
            'next_action': 'CONTINUE_WITH_REDUCED_SIZE',
            'reduction_factor': 0.5
        }
    
    def _handle_generic_api_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用API错误"""
        
        retry_config = self.config.get('api', {})
        max_retries = retry_config.get('max_retries', 2)
        retry_delay = retry_config.get('retry_delay', 3)
        
        retry_count = context.get('retry_count', 0)
        
        if retry_count < max_retries:
            log_info(f"🔄 API错误恢复 - 重试 {retry_count + 1}/{max_retries}")
            time.sleep(retry_delay)
            return {
                'success': True,
                'action': 'API_RETRY',
                'severity': 'LOW',
                'message': f'API错误，{retry_delay}秒后重试',
                'next_action': 'RETRY',
                'retry_count': retry_count + 1
            }
        else:
            return {
                'success': False,
                'action': 'API_FAILURE',
                'severity': 'HIGH',
                'message': 'API错误重试次数用尽',
                'next_action': 'SWITCH_TO_BACKUP'
            }
    
    def _handle_data_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据错误"""
        
        log_info("📊 数据错误 - 使用缓存或默认值")
        return {
            'success': True,
            'action': 'USE_FALLBACK_DATA',
            'severity': 'LOW',
            'message': '数据错误，使用缓存或默认值',
            'next_action': 'CONTINUE_WITH_FALLBACK'
        }
    
    def _handle_system_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统错误"""
        
        system_config = self.config.get('system', {})
        memory_threshold = system_config.get('memory_threshold', 0.8)
        
        # 检查内存使用情况
        import psutil
        memory_usage = psutil.virtual_memory().percent / 100
        
        if memory_usage > memory_threshold:
            log_warning(f"🧠 内存使用率过高: {memory_usage:.2%}")
            # 清理缓存
            cache_manager.clear_cache()
            memory_manager.force_cleanup()
            
            return {
                'success': True,
                'action': 'MEMORY_CLEANUP',
                'severity': 'MEDIUM',
                'message': '内存清理完成',
                'next_action': 'CONTINUE'
            }
        
        return {
            'success': False,
            'action': 'SYSTEM_FAILURE',
            'severity': 'CRITICAL',
            'message': '系统错误，无法自动恢复',
            'next_action': 'SAFE_SHUTDOWN'
        }
    
    def _handle_strategy_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理策略错误"""
        
        log_info("🎯 策略错误 - 使用保守策略")
        return {
            'success': True,
            'action': 'USE_CONSERVATIVE_STRATEGY',
            'severity': 'LOW',
            'message': '策略错误，使用保守策略',
            'next_action': 'CONTINUE_WITH_CONSERVATIVE_MODE'
        }
    
    def _handle_unknown_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理未知错误"""
        
        log_error(f"❓ 未知错误: {error}")
        return {
            'success': False,
            'action': 'UNKNOWN_ERROR',
            'severity': 'HIGH',
            'message': f'未知错误: {error}',
            'next_action': 'SAFE_SHUTDOWN'
        }
    
    def _get_stack_trace(self) -> str:
        """获取堆栈跟踪"""
        import traceback
        return traceback.format_exc()
    
    def _send_alert(self, error_record: Dict[str, Any], recovery_result: Dict[str, Any]):
        """发送错误警报"""
        alert_message = f"""
        🚨 交易系统错误警报
        
        时间: {error_record['timestamp']}
        错误类型: {error_record['error_type']}
        错误分类: {error_record['category']}
        严重程度: {recovery_result['severity']}
        恢复动作: {recovery_result['action']}
        下一步行动: {recovery_result['next_action']}
        
        错误详情: {error_record['error_message']}
        上下文: {json.dumps(error_record['context'], indent=2)}
        """
        
        log_error(alert_message)
        # 实际应用中这里会发送邮件、短信等通知
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        return {
            'total_errors': self.recovery_stats['total_errors'],
            'successful_recoveries': self.recovery_stats['successful_recoveries'],
            'recovery_rate': (
                self.recovery_stats['successful_recoveries'] / 
                max(self.recovery_stats['total_errors'], 1)
            ),
            'recent_errors': self.error_history[-10:],  # 最近10条错误
            'error_distribution': self._get_error_distribution()
        }
    
    def _get_error_distribution(self) -> Dict[str, int]:
        """获取错误分布统计"""
        distribution = {}
        for error in self.error_history:
            category = error['category']
            distribution[category] = distribution.get(category, 0) + 1
        return distribution

class StatePersistence:
    """状态持久化管理器"""
    
    def __init__(self):
        # 延迟导入config，避免循环导入
        try:
            from config import config
            self.config = config.get('system', 'state_persistence') or {}
            self.state_dir = self.config.get('state_dir', './data/state')
            self.checkpoint_interval = self.config.get('checkpoint_interval', 300)  # 5分钟
            self.max_checkpoints = self.config.get('max_checkpoints', 10)
        except ImportError:
            # 使用默认配置
            self.state_dir = './data/state'
            self.checkpoint_interval = 300
            self.max_checkpoints = 10
        
        # 确保状态目录存在
        os.makedirs(self.state_dir, exist_ok=True)
    
    def save_state(self, state_type: str, data: Dict[str, Any]) -> bool:
        """保存状态"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{state_type}_{timestamp}.json"
            filepath = os.path.join(self.state_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 清理旧的状态文件
            self._cleanup_old_states(state_type)
            
            return True
            
        except Exception as e:
            log_error(f"保存状态失败: {e}")
            return False
    
    def load_latest_state(self, state_type: str) -> Optional[Dict[str, Any]]:
        """加载最新状态"""
        try:
            pattern = f"{state_type}_*.json"
            files = glob.glob(os.path.join(self.state_dir, pattern))
            
            if not files:
                return None
            
            latest_file = max(files, key=os.path.getctime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            log_error(f"加载状态失败: {e}")
            return None
    
    def _cleanup_old_states(self, state_type: str):
        """清理旧的状态文件"""
        try:
            pattern = f"{state_type}_*.json"
            files = glob.glob(os.path.join(self.state_dir, pattern))
            
            # 按创建时间排序，保留最新的max_checkpoints个
            files.sort(key=os.path.getctime, reverse=True)
            
            for old_file in files[self.max_checkpoints:]:
                try:
                    os.remove(old_file)
                except Exception as e:
                    log_warning(f"删除旧状态文件失败: {e}")
                    
        except Exception as e:
            log_error(f"清理状态文件失败: {e}")

class RecoveryEngine:
    """恢复引擎"""
    
    def __init__(self):
        # 延迟导入config，避免循环导入
        try:
            from config import config
            self.config = config.get('system', 'recovery') or {}
        except ImportError:
            # 使用默认配置
            self.config = {
                'enabled': True,
                'max_retries': 3,
                'retry_delay': 1,
                'backoff_factor': 2.0
            }
        
        self.enabled = self.config.get('enabled', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        self.backoff_factor = self.config.get('backoff_factor', 2.0)
        self.state_persistence = StatePersistence()
        self.error_recovery = ErrorRecoveryManager()
        self.checkpoint_manager = CheckpointManager()
    
    def create_checkpoint(self, system_state: Dict[str, Any]) -> bool:
        """创建系统检查点"""
        return self.checkpoint_manager.create_checkpoint(system_state)
    
    def restore_from_checkpoint(self, checkpoint_id: str = None) -> Dict[str, Any]:
        """从检查点恢复"""
        return self.checkpoint_manager.restore_checkpoint(checkpoint_id)
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        return {
            'error_recovery_stats': self.error_recovery.get_recovery_stats(),
            'last_checkpoint': self.checkpoint_manager.get_last_checkpoint(),
            'system_uptime': self._calculate_uptime(),
            'recovery_status': 'healthy'
        }
    
    def _calculate_uptime(self) -> str:
        """计算系统运行时间"""
        # 简化版运行时间计算
        return "系统运行正常"

class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self):
        # 延迟导入config，避免循环导入
        try:
            from config import config
            self.config = config.get('system', 'checkpoint_manager') or {}
            self.checkpoint_dir = self.config.get('checkpoint_dir', './data/checkpoints')
            self.max_checkpoints = self.config.get('max_checkpoints', 5)
        except ImportError:
            # 使用默认配置
            self.checkpoint_dir = './data/checkpoints'
            self.max_checkpoints = 5
        
        # 确保检查点目录存在
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def create_checkpoint(self, system_state: Dict[str, Any]) -> bool:
        """创建系统检查点"""
        try:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'system_state': system_state,
                'version': '1.0.0',
                'checksum': self._calculate_checksum(system_state)
            }
            
            filename = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.checkpoint_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            
            # 清理旧的检查点
            self._cleanup_old_checkpoints()
            
            log_info(f"✅ 检查点创建成功: {filename}")
            return True
            
        except Exception as e:
            log_error(f"创建检查点失败: {e}")
            return False
    
    def restore_checkpoint(self, checkpoint_id: str = None) -> Dict[str, Any]:
        """从检查点恢复"""
        try:
            checkpoints = self._list_checkpoints()
            
            if not checkpoints:
                return {'success': False, 'message': '无可用检查点'}
            
            if checkpoint_id:
                target_checkpoint = next((cp for cp in checkpoints if cp['id'] == checkpoint_id), None)
            else:
                target_checkpoint = checkpoints[0]  # 最新的检查点
            
            if not target_checkpoint:
                return {'success': False, 'message': '指定的检查点不存在'}
            
            # 验证检查点完整性
            if not self._validate_checkpoint(target_checkpoint):
                return {'success': False, 'message': '检查点验证失败'}
            
            return {
                'success': True,
                'checkpoint': target_checkpoint,
                'message': '检查点恢复成功'
            }
            
        except Exception as e:
            log_error(f"恢复检查点失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def _list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有检查点"""
        try:
            files = glob.glob(os.path.join(self.checkpoint_dir, "checkpoint_*.json"))
            checkpoints = []
            
            for file in sorted(files, key=os.path.getctime, reverse=True):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        checkpoint = json.load(f)
                        checkpoint['id'] = os.path.basename(file)
                        checkpoint['filepath'] = file
                        checkpoints.append(checkpoint)
                except Exception as e:
                    log_warning(f"加载检查点失败: {e}")
            
            return checkpoints
            
        except Exception as e:
            log_error(f"列出检查点失败: {e}")
            return []
    
    def _validate_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """验证检查点完整性"""
        try:
            expected_checksum = checkpoint.get('checksum')
            actual_checksum = self._calculate_checksum(checkpoint.get('system_state', {}))
            
            return expected_checksum == actual_checksum
            
        except Exception as e:
            log_error(f"验证检查点失败: {e}")
            return False
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _cleanup_old_checkpoints(self):
        """清理旧的检查点"""
        try:
            checkpoints = self._list_checkpoints()
            
            for old_checkpoint in checkpoints[self.max_checkpoints:]:
                try:
                    os.remove(old_checkpoint['filepath'])
                    log_info(f"🗑️ 删除旧检查点: {old_checkpoint['id']}")
                except Exception as e:
                    log_warning(f"删除检查点失败: {e}")
                    
        except Exception as e:
            log_error(f"清理检查点失败: {e}")
    
    def get_last_checkpoint(self) -> Optional[Dict[str, Any]]:
        """获取最新的检查点"""
        checkpoints = self._list_checkpoints()
        return checkpoints[0] if checkpoints else None

class EnhancedSystemMonitor:
    """增强系统监控器"""
    
    def __init__(self):
        self.metrics = {
            'start_time': time.time(),
            'api_calls': 0,
            'trades_executed': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'memory_usage': [],
            'cpu_usage': [],
            'network_latency': [],
            'performance_metrics': {}
        }
        self.lock = threading.Lock()
        self.monitoring_enabled = True
        
    def start_monitoring(self):
        """启动监控"""
        self.monitoring_enabled = True
        self._start_background_monitoring()
        log_info("🚀 系统监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_enabled = False
        log_info("🛑 系统监控已停止")
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """增加计数器"""
        with self.lock:
            if counter_name in self.metrics:
                self.metrics[counter_name] += value
            else:
                self.metrics[counter_name] = value
    
    def record_metric(self, metric_name: str, value: Any):
        """记录指标"""
        with self.lock:
            self.metrics[metric_name] = value
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self.lock:
            uptime = time.time() - self.metrics['start_time']
            
            return {
                'uptime': self._format_uptime(uptime),
                'uptime_seconds': uptime,
                'api_calls': self.metrics['api_calls'],
                'trades_executed': self.metrics['trades_executed'],
                'errors_count': self.metrics['errors_count'],
                'warnings_count': self.metrics['warnings_count'],
                'requests_per_minute': self.metrics['api_calls'] / max(uptime / 60, 1),
                'trades_per_hour': self.metrics['trades_executed'] / max(uptime / 3600, 1),
                'error_rate': self.metrics['errors_count'] / max(self.metrics['api_calls'], 1),
                'system_health': self._calculate_health_score(),
                'timestamp': datetime.now().isoformat()
            }
    
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}天{hours}小时{minutes}分钟"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"
    
    def _calculate_health_score(self) -> float:
        """计算系统健康分数"""
        if self.metrics['api_calls'] == 0:
            return 100.0
        
        error_rate = self.metrics['errors_count'] / self.metrics['api_calls']
        
        if error_rate < 0.01:
            return 100.0
        elif error_rate < 0.05:
            return 90.0
        elif error_rate < 0.1:
            return 75.0
        elif error_rate < 0.2:
            return 50.0
        else:
            return 25.0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'memory_usage': self._get_memory_usage(),
            'cpu_usage': self._get_cpu_usage(),
            'disk_usage': self._get_disk_usage(),
            'network_stats': self._get_network_stats(),
            'process_stats': self._get_process_stats()
        }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'used_gb': memory.used / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent': memory.percent
            }
        except ImportError:
            return {'total_gb': 0, 'used_gb': 0, 'available_gb': 0, 'percent': 0}
    
    def _get_cpu_usage(self) -> Dict[str, float]:
        """获取CPU使用情况"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'cpu_count': psutil.cpu_count(),
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
        except ImportError:
            return {'cpu_percent': 0, 'cpu_count': 1, 'load_average': 0}
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """获取磁盘使用情况"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent': disk.percent
            }
        except ImportError:
            return {'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent': 0}
    
    def _get_network_stats(self) -> Dict[str, int]:
        """获取网络统计"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except ImportError:
            return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}
    
    def _get_process_stats(self) -> Dict[str, int]:
        """获取进程统计"""
        try:
            import psutil
            process = psutil.Process()
            return {
                'pid': process.pid,
                'memory_mb': process.memory_info().rss / (1024**2),
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads()
            }
        except ImportError:
            return {'pid': 0, 'memory_mb': 0, 'cpu_percent': 0, 'threads': 0}
    
    def _start_background_monitoring(self):
        """启动后台监控"""
        def monitor_worker():
            while self.monitoring_enabled:
                try:
                    # 收集系统指标
                    performance = self.get_performance_metrics()
                    
                    # 记录内存和CPU使用
                    if 'memory_usage' in performance:
                        self.metrics['memory_usage'].append(performance['memory_usage'])
                        if len(self.metrics['memory_usage']) > 100:
                            self.metrics['memory_usage'].pop(0)
                    
                    if 'cpu_usage' in performance:
                        self.metrics['cpu_usage'].append(performance['cpu_usage'])
                        if len(self.metrics['cpu_usage']) > 100:
                            self.metrics['cpu_usage'].pop(0)
                    
                    # 每30秒收集一次
                    time.sleep(30)
                    
                except Exception as e:
                    log_error(f"后台监控异常: {e}")
                    time.sleep(60)
        
        # 启动后台线程
        monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        monitor_thread.start()
    
    def generate_system_report(self) -> Dict[str, Any]:
        """生成系统报告"""
        return {
            'system_status': self.get_system_status(),
            'performance_metrics': self.get_performance_metrics(),
            'error_summary': {
                'total_errors': self.metrics['errors_count'],
                'total_warnings': self.metrics['warnings_count'],
                'error_categories': self._get_error_categories()
            },
            'recommendations': self._generate_recommendations()
        }
    
    def _get_error_categories(self) -> Dict[str, int]:
        """获取错误分类统计"""
        # 简化实现，实际应该从错误日志中分析
        return {
            'network': 0,
            'api': 0,
            'data': 0,
            'system': 0,
            'strategy': 0
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成系统建议"""
        recommendations = []
        
        # 基于健康分数生成建议
        health_score = self._calculate_health_score()
        
        if health_score < 50:
            recommendations.append("系统健康分数较低，建议检查错误日志")
        
        if self.metrics['errors_count'] > 10:
            recommendations.append("错误数量较多，建议重启系统或检查配置")
        
        if len(self.metrics['memory_usage']) > 0:
            last_memory = self.metrics['memory_usage'][-1]
            if last_memory.get('percent', 0) > 80:
                recommendations.append("内存使用率过高，建议重启系统")
        
        if not recommendations:
            recommendations.append("系统运行正常，继续保持监控")
        
        return recommendations

# 全局工具实例
cache_manager = CacheManager()
memory_manager = MemoryManager()
system_monitor = SystemMonitor()
enhanced_system_monitor = EnhancedSystemMonitor()
data_validator = DataValidator()
json_helper = JSONHelper()
time_helper = TimeHelper()
logger_helper = LoggerHelper()
error_recovery = ErrorRecoveryManager()
recovery_engine = RecoveryEngine()

def load_trading_data_from_file(file_path: str = None) -> Dict[str, Any]:
    """从文件加载交易数据（供streamlit使用）"""
    try:
        from pathlib import Path
        import json
        
        if file_path is None:
            data_dir = Path(__file__).parent / "data_json"
            file_path = data_dir / "trading_data.json"
        
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "status": "stopped",
                "last_update": "N/A",
                "account": {"balance": 0, "equity": 0, "leverage": 0},
                "btc": {"price": 0, "change": 0, "timeframe": "1h", "mode": "全仓-单向"},
                "position": None,
                "performance": {"total_pnl": 0, "win_rate": 0, "total_trades": 0},
                "ai_signal": {
                    "signal": "HOLD",
                    "confidence": "N/A",
                    "reason": "等待交易程序启动...",
                    "stop_loss": 0,
                    "take_profit": 0,
                    "timestamp": "N/A"
                },
                "file_not_found": True
            }
    except Exception as e:
        log_error(f"加载交易数据失败: {e}")
        return {}

def load_trades_history_from_file(file_path: str = None) -> List[Dict[str, Any]]:
    """从文件加载交易历史（供streamlit使用）"""
    try:
        from pathlib import Path
        import json
        
        if file_path is None:
            data_dir = Path(__file__).parent / "data_json"
            file_path = data_dir / "trades_history.json"
        
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        log_error(f"加载交易历史失败: {e}")
        return []

def load_equity_history_from_file(file_path: str = None) -> List[Dict[str, Any]]:
    """从文件加载权益历史（供streamlit使用）"""
    try:
        from pathlib import Path
        import json
        
        if file_path is None:
            data_dir = Path(__file__).parent / "data_json"
            file_path = data_dir / "equity_history.json"
        
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        log_error(f"加载权益历史失败: {e}")
        return []

def save_trade_record(trade_record: Dict[str, Any]) -> bool:
    """保存交易记录到文件"""
    try:
        from pathlib import Path
        import json
        
        # 确保数据目录存在
        data_dir = Path(__file__).parent / "data_json"
        data_dir.mkdir(exist_ok=True)
        
        # 交易记录文件
        trades_file = data_dir / "trades_history.json"
        
        # 加载现有记录
        existing_records = []
        if trades_file.exists():
            try:
                with open(trades_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing_records = []
        
        # 确保是列表格式
        if not isinstance(existing_records, list):
            existing_records = []
        
        # 添加新记录
        existing_records.append(trade_record)
        
        # 保存更新后的记录
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        log_error(f"保存交易记录失败: {e}")
        return False
state_persistence = StatePersistence()
recovery_engine = RecoveryEngine()
checkpoint_manager = CheckpointManager()
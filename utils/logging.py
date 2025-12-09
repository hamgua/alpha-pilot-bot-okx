"""
日志系统模块
提供统一的日志管理和格式化功能
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import json
import threading
from dataclasses import dataclass

# 日志级别配置
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    message: str
    module: str
    function: str
    line: int
    extra_data: Optional[Dict[str, Any]] = None

class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.base_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        self.detailed_format = "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    
    def format(self, record):
        # 根据日志级别选择格式
        if record.levelno >= logging.WARNING:
            self._style._fmt = self.detailed_format
        else:
            self._style._fmt = self.base_format
        
        # 处理额外数据
        if hasattr(record, 'extra_data') and self.include_extra:
            extra_msg = f" | 额外数据: {json.dumps(record.extra_data, ensure_ascii=False)}"
            record.msg = str(record.msg) + extra_msg
        
        return super().format(record)

class FileRotationHandler(logging.Handler):
    """文件轮转处理器"""
    
    def __init__(self, log_dir: str, max_files: int = 30):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_files = max_files
        self.current_date = datetime.now().date()
        self.current_file = None
        self._lock = threading.Lock()
        self._update_current_file()
    
    def _update_current_file(self):
        """更新当前日志文件"""
        today = datetime.now().date()
        if today != self.current_date or self.current_file is None:
            self.current_date = today
            filename = f"trading_bot_{today.strftime('%Y%m%d')}.log"
            self.current_file = self.log_dir / filename
            self._cleanup_old_files()
    
    def _cleanup_old_files(self):
        """清理旧日志文件"""
        try:
            log_files = sorted(self.log_dir.glob("trading_bot_*.log"))
            if len(log_files) > self.max_files:
                for old_file in log_files[:-self.max_files]:
                    try:
                        old_file.unlink()
                    except Exception as e:
                        print(f"清理旧日志文件失败: {e}")
        except Exception as e:
            print(f"日志清理失败: {e}")
    
    def emit(self, record):
        """写入日志记录"""
        with self._lock:
            self._update_current_file()
            try:
                log_entry = self.format(record)
                with open(self.current_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + '\n')
                    f.flush()
            except Exception as e:
                print(f"写入日志文件失败: {e}")

class TradingLogger:
    """交易日志管理器"""
    
    def __init__(self, name: str = "TradingBot", log_level: str = "INFO", 
                 log_dir: str = "logs", max_log_files: int = 30):
        self.name = name
        self.log_level = LOG_LEVELS.get(log_level, logging.INFO)
        self.log_dir = Path(log_dir)
        self.max_log_files = max_log_files
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        # 创建日志器
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # 避免重复添加处理器
        if self.logger.handlers:
            return
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = CustomFormatter(include_extra=False)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        file_handler = FileRotationHandler(str(self.log_dir), self.max_log_files)
        file_handler.setLevel(self.log_level)
        file_formatter = CustomFormatter(include_extra=True)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def log_trade_event(self, event_type: str, data: Dict[str, Any]):
        """记录交易事件"""
        extra_data = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"交易事件: {event_type}", extra={'extra_data': extra_data})
    
    def log_signal(self, signal: str, confidence: float, reason: str, **kwargs):
        """记录信号"""
        extra_data = {
            'signal': signal,
            'confidence': confidence,
            'reason': reason,
            **kwargs
        }
        
        self.logger.info(f"信号: {signal} (信心: {confidence:.2f})", extra={'extra_data': extra_data})
    
    def log_risk_event(self, risk_type: str, risk_score: float, action: str, **kwargs):
        """记录风险事件"""
        extra_data = {
            'risk_type': risk_type,
            'risk_score': risk_score,
            'action': action,
            **kwargs
        }
        
        self.logger.warning(f"风险事件: {risk_type} (评分: {risk_score:.1f})", extra={'extra_data': extra_data})
    
    def log_error_event(self, error_type: str, error_message: str, **kwargs):
        """记录错误事件"""
        extra_data = {
            'error_type': error_type,
            'error_message': error_message,
            **kwargs
        }
        
        self.logger.error(f"错误事件: {error_type}", extra={'extra_data': extra_data})
    
    def log_performance(self, metric: str, value: float, **kwargs):
        """记录性能指标"""
        extra_data = {
            'metric': metric,
            'value': value,
            **kwargs
        }
        
        self.logger.info(f"性能指标: {metric} = {value:.4f}", extra={'extra_data': extra_data})
    
    def log_decision(self, decision_type: str, decision: str, confidence: float, **kwargs):
        """记录决策"""
        extra_data = {
            'decision_type': decision_type,
            'decision': decision,
            'confidence': confidence,
            **kwargs
        }
        
        self.logger.info(f"决策: {decision_type} -> {decision} (信心: {confidence:.2f})", extra={'extra_data': extra_data})
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        try:
            log_files = list(self.log_dir.glob("trading_bot_*.log"))
            total_size = sum(f.stat().st_size for f in log_files)
            
            return {
                'total_log_files': len(log_files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'log_directory': str(self.log_dir),
                'current_log_file': log_files[-1].name if log_files else None
            }
        except Exception as e:
            self.logger.error(f"获取日志统计失败: {e}")
            return {'error': str(e)}

# 全局日志实例
trading_logger = TradingLogger()

def get_log_stats() -> Dict[str, Any]:
    """获取日志统计信息"""
    return trading_logger.get_log_stats()

# 便捷的日志函数
def log_info(message: str, **kwargs):
    """记录信息日志"""
    trading_logger.logger.info(message, extra={'extra_data': kwargs} if kwargs else {})

def log_warning(message: str, **kwargs):
    """记录警告日志"""
    trading_logger.logger.warning(message, extra={'extra_data': kwargs} if kwargs else {})

def log_error(message: str, **kwargs):
    """记录错误日志"""
    trading_logger.logger.error(message, extra={'extra_data': kwargs} if kwargs else {})

def log_debug(message: str, **kwargs):
    """记录调试日志"""
    trading_logger.logger.debug(message, extra={'extra_data': kwargs} if kwargs else {})

# 向后兼容的日志函数
def log_trade_event(event_type: str, data: Dict[str, Any]):
    """记录交易事件（向后兼容）"""
    trading_logger.log_trade_event(event_type, data)

def log_signal(signal: str, confidence: float, reason: str, **kwargs):
    """记录信号（向后兼容）"""
    trading_logger.log_signal(signal, confidence, reason, **kwargs)

def log_risk_event(risk_type: str, risk_score: float, action: str, **kwargs):
    """记录风险事件（向后兼容）"""
    trading_logger.log_risk_event(risk_type, risk_score, action, **kwargs)

def log_error_event(error_type: str, error_message: str, **kwargs):
    """记录错误事件（向后兼容）"""
    trading_logger.log_error_event(error_type, error_message, **kwargs)

def log_performance(metric: str, value: float, **kwargs):
    """记录性能指标（向后兼容）"""
    trading_logger.log_performance(metric, value, **kwargs)

def log_decision(decision_type: str, decision: str, confidence: float, **kwargs):
    """记录决策（向后兼容）"""
    trading_logger.log_decision(decision_type, decision, confidence, **kwargs)

# 项目特定的日志函数
def log_ai_decision(decision_data: Dict[str, Any]):
    """记录AI决策"""
    trading_logger.log_decision(
        decision_type='AI',
        decision=decision_data.get('signal', 'UNKNOWN'),
        confidence=decision_data.get('confidence', 0.0),
        provider=decision_data.get('provider', 'unknown'),
        reason=decision_data.get('reason', '')
    )

def log_strategy_signal(strategy_type: str, signal: str, confidence: float, **kwargs):
    """记录策略信号"""
    trading_logger.log_signal(
        signal=signal,
        confidence=confidence,
        reason=f"{strategy_type}策略信号",
        strategy_type=strategy_type,
        **kwargs
    )

def log_risk_management(risk_action: str, risk_score: float, **kwargs):
    """记录风险管理操作"""
    trading_logger.log_risk_event(
        risk_type='risk_management',
        risk_score=risk_score,
        action=risk_action,
        **kwargs
    )

def log_execution_stats(trade_result: Dict[str, Any]):
    """记录执行统计"""
    trading_logger.log_performance(
        metric='trade_execution',
        value=trade_result.get('execution_time', 0),
        success=trade_result.get('success', False),
        signal=trade_result.get('signal', 'UNKNOWN')
    )

# 日志级别设置函数
def set_log_level(level: str):
    """设置日志级别"""
    try:
        log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
        trading_logger.logger.setLevel(log_level)
        
        for handler in trading_logger.logger.handlers:
            handler.setLevel(log_level)
        
        log_info(f"日志级别已设置为: {level}")
    except Exception as e:
        print(f"设置日志级别失败: {e}")

def get_log_level() -> str:
    """获取当前日志级别"""
    level = trading_logger.logger.level
    for name, value in LOG_LEVELS.items():
        if value == level:
            return name
    return "UNKNOWN"

# 日志文件管理
def rotate_logs():
    """手动轮转日志"""
    try:
        # 创建新的日志文件
        current_time = datetime.now()
        new_filename = f"trading_bot_manual_{current_time.strftime('%Y%m%d_%H%M%S')}.log"
        new_file = trading_logger.log_dir / new_filename
        
        # 触发文件更新
        trading_logger._setup_logger()
        
        log_info(f"日志已轮转，新文件: {new_filename}")
        return str(new_file)
    except Exception as e:
        log_error(f"日志轮转失败: {e}")
        return None

def cleanup_old_logs(days_to_keep: int = 7):
    """清理旧日志文件"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        log_files = list(trading_logger.log_dir.glob("trading_bot_*.log"))
        cleaned_count = 0
        
        for log_file in log_files:
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                log_error(f"清理日志文件失败 {log_file}: {e}")
        
        log_info(f"日志清理完成: 删除了 {cleaned_count} 个旧文件")
        return cleaned_count
        
    except Exception as e:
        log_error(f"清理旧日志失败: {e}")
        return 0

# 向后兼容的函数
def log_info_old(message: str):
    """旧版信息日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [INFO] {message}"
    print(formatted_message)
    trading_logger.logger.info(message)

def log_warning_old(message: str):
    """旧版警告日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [WARNING] {message}"
    print(formatted_message)
    trading_logger.logger.warning(message)

def log_error_old(message: str):
    """旧版错误日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [ERROR] {message}"
    print(formatted_message)
    trading_logger.logger.error(message)

def log_decision_old(message: str):
    """旧版决策日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [DECISION] 🎯 {message}"
    print(formatted_message)
    trading_logger.logger.info(f"[DECISION] {message}")

def log_performance_old(message: str):
    """旧版性能日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [PERFORMANCE] 📊 {message}"
    print(formatted_message)
    trading_logger.logger.info(f"[PERFORMANCE] {message}")

def log_strategy_old(message: str):
    """旧版策略日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [STRATEGY] 🎯 {message}"
    print(formatted_message)
    trading_logger.logger.info(f"[STRATEGY] {message}")

def log_risk_old(message: str):
    """旧版风险日志函数（向后兼容）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] [RISK] 🛡️ {message}"
    print(formatted_message)
    trading_logger.logger.warning(f"[RISK] {message}")

# 初始化时创建必要的目录
try:
    trading_logger.log_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"创建日志目录失败: {e}")

# 导出主要功能
__all__ = [
    'TradingLogger',
    'log_info',
    'log_warning', 
    'log_error',
    'log_debug',
    'log_trade_event',
    'log_signal',
    'log_risk_event',
    'log_error_event',
    'log_performance',
    'log_decision',
    'log_ai_decision',
    'log_strategy_signal',
    'log_risk_management',
    'log_execution_stats',
    'set_log_level',
    'get_log_level',
    'rotate_logs',
    'cleanup_old_logs',
    'get_log_stats',
    'trading_logger'
]
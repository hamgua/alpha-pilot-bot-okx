#!/usr/bin/env python3
"""
日志配置模块 - 支持每日归档
格式：logs/deepseekok2-20251123.log
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 创建logs目录
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

class DailyRotatingLogger:
    """每日轮转日志器"""
    
    def __init__(self, name="deepseekok2", log_level=logging.INFO):
        self.name = name
        self.log_level = log_level
        self.logger = None
        self.current_date = None
        self.file_handler = None
        self.console_handler = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 设置格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(formatter)
        self.logger.addHandler(self.console_handler)
        
        # 文件处理器
        self._update_file_handler()
    
    def _update_file_handler(self):
        """更新文件处理器（按日期）"""
        today = datetime.now().strftime('%Y%m%d')
        
        if self.current_date != today:
            # 移除旧的文件处理器
            if self.file_handler:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
            
            # 创建新的文件处理器
            log_file = LOG_DIR / f"{self.name}-{today}.log"
            self.file_handler = logging.FileHandler(
                log_file, 
                encoding='utf-8',
                mode='a'
            )
            self.file_handler.setFormatter(
                logging.Formatter(
                    '[%(asctime)s] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
            self.logger.addHandler(self.file_handler)
            self.current_date = today
            
            # 清理旧日志（保留最近30天）
            self._cleanup_old_logs()
    
    def _cleanup_old_logs(self, days_to_keep=30):
        """清理旧日志文件"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            
            for log_file in LOG_DIR.glob(f"{self.name}-*.log"):
                try:
                    file_mtime = log_file.stat().st_mtime
                    if file_mtime < cutoff_date:
                        log_file.unlink()
                except (OSError, IOError):
                    continue
        except Exception:
            pass  # 清理失败不影响主程序
    
    def log(self, level, message):
        """记录日志"""
        self._update_file_handler()
        self.logger.log(level, message)
    
    def info(self, message):
        """记录INFO级别日志"""
        self.log(logging.INFO, message)
    
    def warning(self, message):
        """记录WARNING级别日志"""
        self.log(logging.WARNING, message)
    
    def error(self, message):
        """记录ERROR级别日志"""
        self.log(logging.ERROR, message)
    
    def debug(self, message):
        """记录DEBUG级别日志"""
        self.log(logging.DEBUG, message)

# 创建全局日志器实例
logger = DailyRotatingLogger()

# 便捷的日志函数
def log_info(message):
    """记录信息日志"""
    logger.info(message)

def log_warning(message):
    """记录警告日志"""
    logger.warning(message)

def log_error(message):
    """记录错误日志"""
    logger.error(message)

def log_debug(message):
    """记录调试日志"""
    logger.debug(message)

# 替换原有的print日志函数
def print_to_log(message):
    """将print输出转换为日志"""
    log_info(message.replace('🤖', '[BOT]').replace('⚠️', '[WARN]').replace('❌', '[ERROR]').replace('✅', '[OK]').replace('📊', '[DATA]').replace('💰', '[BALANCE]').replace('🎯', '[TARGET]'))
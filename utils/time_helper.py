
"""
时间工具模块
提供时间相关的辅助功能
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TimeHelper:
    """时间工具类"""
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持续时间"""
        try:
            return str(timedelta(seconds=int(seconds)))
        except Exception as e:
            logger.error(f"格式化持续时间失败: {e}")
            return "0:00:00"
    
    @staticmethod
    def is_market_hours() -> bool:
        """检查是否为交易时间"""
        try:
            # 加密货币24小时交易
            return True
        except Exception as e:
            logger.error(f"检查交易时间失败: {e}")
            return True
    
    @staticmethod
    def get_time_until_next(interval_minutes: int = 15) -> float:
        """
        获取到下个周期的时间
        
        支持15分钟循环周期，在每个整点的00、15、30、45分钟开始运行
        """
        try:
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
                    # 如果日期无效，使用下个月的第一天
                    if now.month == 12:
                        next_time = now.replace(year=now.year + 1, month=1, day=1, hour=next_hour, minute=next_interval, second=0, microsecond=0)
                    else:
                        next_time = now.replace(month=now.month + 1, day=1, hour=next_hour, minute=next_interval, second=0, microsecond=0)
            else:
                try:
                    next_time = now.replace(hour=next_hour, minute=next_interval, second=0, microsecond=0)
                except ValueError:
                    # 处理夏令时等特殊情况
                    next_time = now + timedelta(hours=1)
                    next_time = next_time.replace(minute=next_interval, second=0, microsecond=0)

            return max(0, (next_time - now).total_seconds())

        except Exception as e:
            logger.error(f"计算到下个周期的时间失败: {e}")
            return 900.0  # 默认15分钟
    
    @staticmethod
    def get_current_timestamp() -> str:
        """获取当前时间戳"""
        try:
            return datetime.now().isoformat()
        except Exception as e:
            logger.error(f"获取当前时间戳失败: {e}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """解析时间戳字符串"""
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.error(f"解析时间戳失败: {e}")
            try:
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                return None
    
    @staticmethod
    def calculate_time_difference(start_time: str, end_time: str) -> float:
        """计算时间差（秒）"""
        try:
            start = TimeHelper.parse_timestamp(start_time)
            end = TimeHelper.parse_timestamp(end_time)
            
            if start and end:
                return (end - start).total_seconds()
            return 0.0
            
        except Exception as e:
            logger.error(f"计算时间差失败: {e}")
            return 0.0

# 全局实例
time_helper = TimeHelper()
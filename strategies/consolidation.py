"""
盘整检测模块
检测市场横盘状态并管理相关交易策略
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from core.base import BaseComponent, BaseConfig

logger = logging.getLogger(__name__)

@dataclass
class ConsolidationStatus:
    """盘整状态"""
    is_active: bool
    duration_minutes: float
    partial_close_done: bool
    start_price: float
    current_price: float
    price_range_percent: float
    start_time: datetime
    last_update: datetime

class ConsolidationDetector(BaseComponent):
    """盘整检测器"""

    def __init__(self, config: Optional[BaseConfig] = None):
        super().__init__(config or BaseConfig(name="ConsolidationDetector"))
        self.consolidation_active = False
        self.consolidation_start_time = None
        self.consolidation_start_price = 0.0
        self.price_history: List[float] = []
        self.timestamp_history: List[datetime] = []
        self.partial_close_executed = False
        self.max_history_minutes = 60  # 保留60分钟的历史数据

    async def initialize(self) -> bool:
        """初始化"""
        try:
            self._initialized = True
            logger.info("✅ 盘整检测器初始化成功")
            return True
        except Exception as e:
            logger.error(f"盘整检测器初始化失败: {e}")
            self._initialized = False
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            self.price_history.clear()
            self.timestamp_history.clear()
            self.consolidation_active = False
            self.consolidation_start_time = None
            self.consolidation_start_price = 0.0
            self.partial_close_executed = False
            self._initialized = False
            logger.info("🧹 盘整检测器资源已清理")
        except Exception as e:
            logger.error(f"清理盘整检测器资源失败: {e}")

    def detect_consolidation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """检测是否处于盘整状态"""
        try:
            current_price = market_data.get('price', 0)
            if current_price <= 0:
                return {'is_consolidating': False, 'reason': '无效价格'}

            # 添加当前价格到历史记录
            self.price_history.append(current_price)
            self.timestamp_history.append(datetime.now())

            # 清理旧数据
            self._cleanup_old_data()

            # 需要至少20个数据点才能判断
            if len(self.price_history) < 20:
                return {'is_consolidating': False, 'reason': '数据不足'}

            # 计算价格波动范围
            recent_prices = self.price_history[-20:]
            max_price = max(recent_prices)
            min_price = min(recent_prices)
            price_range_percent = ((max_price - min_price) / min_price) * 100

            # 判断标准：价格波动小于2%且持续超过30分钟
            is_consolidating = (
                price_range_percent < 2.0 and
                len(self.price_history) >= 30 and
                self._get_duration_minutes() > 30
            )

            # 更新盘整状态
            if is_consolidating and not self.consolidation_active:
                self._start_consolidation(current_price)
            elif not is_consolidating and self.consolidation_active:
                self._end_consolidation()

            return {
                'is_consolidating': is_consolidating,
                'price_range_percent': price_range_percent,
                'duration_minutes': self._get_duration_minutes(),
                'data_points': len(self.price_history)
            }

        except Exception as e:
            logger.error(f"检测盘整失败: {e}")
            return {'is_consolidating': False, 'reason': f'检测异常: {e}'}

    def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=self.max_history_minutes)

            # 找到第一个不早于截止时间的索引
            valid_indices = [
                i for i, ts in enumerate(self.timestamp_history)
                if ts >= cutoff_time
            ]

            if valid_indices:
                start_idx = min(valid_indices)
                self.price_history = self.price_history[start_idx:]
                self.timestamp_history = self.timestamp_history[start_idx:]
            else:
                # 所有数据都过期了
                self.price_history.clear()
                self.timestamp_history.clear()

        except Exception as e:
            logger.error(f"清理历史数据失败: {e}")

    def _start_consolidation(self, start_price: float):
        """开始盘整"""
        self.consolidation_active = True
        self.consolidation_start_time = datetime.now()
        self.consolidation_start_price = start_price
        self.partial_close_executed = False
        logger.info(f"📊 检测到盘整开始，起始价格: {start_price}")

    def _end_consolidation(self):
        """结束盘整"""
        duration = self._get_duration_minutes()
        self.consolidation_active = False
        self.consolidation_start_time = None
        self.consolidation_start_price = 0.0
        logger.info(f"📊 盘整结束，持续时间: {duration:.1f}分钟")

    def _get_duration_minutes(self) -> float:
        """获取当前盘整持续时间（分钟）"""
        if not self.consolidation_active or not self.consolidation_start_time:
            return 0.0
        return (datetime.now() - self.consolidation_start_time).total_seconds() / 60

    def get_consolidation_status(self) -> Dict[str, Any]:
        """获取当前盘整状态"""
        try:
            current_price = self.price_history[-1] if self.price_history else 0

            return {
                'is_active': self.consolidation_active,
                'duration_minutes': self._get_duration_minutes(),
                'partial_close_done': self.partial_close_executed,
                'start_price': self.consolidation_start_price,
                'current_price': current_price,
                'price_range_percent': self._calculate_price_range(),
                'start_time': self.consolidation_start_time.isoformat() if self.consolidation_start_time else None,
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取盘整状态失败: {e}")
            return {
                'is_active': False,
                'error': str(e)
            }

    def _calculate_price_range(self) -> float:
        """计算价格波动范围百分比"""
        try:
            if len(self.price_history) < 2:
                return 0.0

            recent_prices = self.price_history[-20:]  # 最近20个价格
            max_price = max(recent_prices)
            min_price = min(recent_prices)

            if min_price > 0:
                return ((max_price - min_price) / min_price) * 100
            return 0.0

        except Exception as e:
            logger.error(f"计算价格范围失败: {e}")
            return 0.0

    def should_lock_profit(self, position_info: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """是否应该锁定利润（部分平仓）"""
        try:
            if not self.consolidation_active or self.partial_close_executed:
                return False

            # 检查是否已盈利
            if position_info.get('unrealized_pnl', 0) <= 0:
                return False

            # 盘整持续时间超过45分钟且盈利超过1%
            duration = self._get_duration_minutes()
            pnl_percent = position_info.get('unrealized_pnl_percent', 0)

            should_lock = (
                duration > 45 and
                pnl_percent > 1.0 and
                not self.partial_close_executed
            )

            if should_lock:
                self.partial_close_executed = True
                logger.info(f"🔒 建议锁定利润: 盈利={pnl_percent:.2f}%, 盘整时间={duration:.1f}分钟")

            return should_lock

        except Exception as e:
            logger.error(f"判断是否应该锁定利润失败: {e}")
            return False

    def should_exit_consolidation(self, market_data: Dict[str, Any]) -> bool:
        """是否应该退出盘整状态"""
        try:
            if not self.consolidation_active:
                return False

            current_price = market_data.get('price', 0)
            if current_price <= 0:
                return False

            # 价格波动超过3%时退出盘整
            if self.consolidation_start_price > 0:
                price_change_percent = abs(current_price - self.consolidation_start_price) / self.consolidation_start_price * 100
                if price_change_percent > 3.0:
                    logger.info(f"📈 价格波动超过3%，退出盘整状态: {price_change_percent:.2f}%")
                    return True

            # 盘整时间超过120分钟也退出
            duration = self._get_duration_minutes()
            if duration > 120:
                logger.info(f"⏰ 盘整时间超过120分钟，自动退出")
                return True

            return False

        except Exception as e:
            logger.error(f"判断是否应该退出盘整失败: {e}")
            return False

    def reset_consolidation_state(self):
        """重置盘整状态"""
        try:
            self.consolidation_active = False
            self.consolidation_start_time = None
            self.consolidation_start_price = 0.0
            self.partial_close_executed = False
            logger.info("🔄 盘整状态已重置")
        except Exception as e:
            logger.error(f"重置盘整状态失败: {e}")

# 全局盘整检测器实例
consolidation_detector = ConsolidationDetector()
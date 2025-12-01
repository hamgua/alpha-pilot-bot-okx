"""
动态追踪止损管理系统
基于原项目功能.md第894-975行的设计规范
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DynamicStopManager:
    """
    动态追踪止损管理系统
    实现保本触发、利润锁定、标准追踪等多级止损策略
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('trailing_stop', {})
        self.price_tracker = PriceTracker()
        self.profit_calculator = ProfitCalculator()
        
        # 止损参数配置
        self.breakeven_at = self.config.get('breakeven_at', 0.01)  # 1%盈利触发保本
        self.lock_profit_at = self.config.get('lock_profit_at', 0.03)  # 3%盈利触发利润锁定
        self.aggressive_lock_at = self.config.get('aggressive_lock_at', 0.05)  # 5%盈利触发激进锁定
        self.trailing_distance = self.config.get('trailing_distance', 0.015)  # 1.5%追踪距离
        self.conservative_distance = self.config.get('conservative_distance', 0.02)  # 2%保守距离
        
        # 价格历史记录
        self.price_history = {}
        self.position_states = {}
        
        logger.info("📊 动态追踪止损管理器初始化完成")
    
    def calculate_trailing_stops(self, position_data: Dict[str, Any], 
                               current_price: float) -> Dict[str, Any]:
        """
        计算动态追踪止损
        
        Args:
            position_data: 持仓数据
            current_price: 当前价格
            
        Returns:
            止损止盈调整结果
        """
        
        if not position_data or position_data.get('size', 0) <= 0:
            return {'should_adjust': False, 'reason': '无有效持仓'}
        
        position_id = position_data.get('id', 'default')
        entry_price = position_data.get('entry_price', 0)
        side = position_data.get('side', 'long')
        
        if entry_price <= 0:
            return {'should_adjust': False, 'reason': '无效的入场价格'}
        
        # 计算当前盈亏百分比
        if side == 'long':
            current_pnl_percentage = (current_price - entry_price) / entry_price
        else:  # short
            current_pnl_percentage = (entry_price - current_price) / entry_price
        
        # 获取当前状态
        current_state = self.position_states.get(position_id, {
            'stage': 'initial',
            'highest_pnl': 0,
            'locked_profit': 0,
            'last_adjustment': None
        })
        
        # 更新最高盈亏
        if current_pnl_percentage > current_state['highest_pnl']:
            current_state['highest_pnl'] = current_pnl_percentage
        
        # 根据盈亏阶段调整止损
        adjustment_result = self._adjust_stops_by_stage(
            position_data, current_price, current_pnl_percentage, current_state
        )
        
        # 保存状态
        current_state['last_adjustment'] = datetime.now().isoformat()
        self.position_states[position_id] = current_state
        
        return adjustment_result
    
    def _adjust_stops_by_stage(self, position_data: Dict, current_price: float,
                             pnl_percentage: float, state: Dict) -> Dict[str, Any]:
        """根据盈亏阶段调整止损"""
        
        entry_price = position_data['entry_price']
        side = position_data['side']
        
        # 1. 保本触发阶段
        if pnl_percentage >= self.breakeven_at and state['stage'] == 'initial':
            breakeven_stop = self._calculate_breakeven_stop(entry_price, side)
            
            state['stage'] = 'breakeven'
            logger.info(f"🛡️ 保本保护触发: 盈利{pnl_percentage:.2%}, 止损调整至保本线")
            
            return {
                'should_adjust': True,
                'action': 'UPDATE_STOP_LOSS',
                'new_stop_loss': breakeven_stop,
                'trigger': 'breakeven',
                'reason': f'达到保本点 ({pnl_percentage:.2%}盈利)',
                'stage': 'breakeven'
            }
        
        # 2. 利润锁定阶段
        elif pnl_percentage >= self.lock_profit_at:
            if pnl_percentage >= self.aggressive_lock_at:
                # 激进锁定：锁定80%利润
                locked_profit = pnl_percentage * 0.8
                final_sl_pct = max(0, locked_profit - self.conservative_distance)
                state['stage'] = 'aggressive_lock'
                state['locked_profit'] = locked_profit
                
                logger.info(f"🔒 激进利润锁定: 盈利{pnl_percentage:.2%}, 锁定{locked_profit:.2%}")
            else:
                # 标准锁定：锁定70%利润
                locked_profit = pnl_percentage * 0.7
                final_sl_pct = max(0, locked_profit - self.trailing_distance)
                state['stage'] = 'profit_lock'
                state['locked_profit'] = locked_profit
                
                logger.info(f"🔒 标准利润锁定: 盈利{pnl_percentage:.2%}, 锁定{locked_profit:.2%}")
            
            new_stop_loss = self._calculate_locked_stop(entry_price, final_sl_pct, side)
            
            return {
                'should_adjust': True,
                'action': 'UPDATE_STOP_LOSS',
                'new_stop_loss': new_stop_loss,
                'trigger': 'profit_lock',
                'reason': f'利润锁定触发 ({pnl_percentage:.2%}盈利)',
                'stage': state['stage'],
                'locked_profit': locked_profit
            }
        
        # 3. 标准追踪阶段
        elif pnl_percentage > 0:
            trailing_stop = self._calculate_trailing_stop(
                current_price, entry_price, side, pnl_percentage
            )
            
            return {
                'should_adjust': True,
                'action': 'UPDATE_STOP_LOSS',
                'new_stop_loss': trailing_stop,
                'trigger': 'trailing',
                'reason': f'标准追踪止损 ({pnl_percentage:.2%}盈利)',
                'stage': 'trailing'
            }
        
        return {'should_adjust': False, 'reason': '未达到调整条件'}
    
    def _calculate_breakeven_stop(self, entry_price: float, side: str) -> float:
        """计算保本止损价格"""
        if side == 'long':
            return entry_price * 1.001  # 略高于入场价
        else:  # short
            return entry_price * 0.999  # 略低于入场价
    
    def _calculate_locked_stop(self, entry_price: float, 
                             locked_profit_pct: float, side: str) -> float:
        """计算锁定利润的止损价格"""
        if side == 'long':
            return entry_price * (1 + locked_profit_pct)
        else:  # short
            return entry_price * (1 - locked_profit_pct)
    
    def _calculate_trailing_stop(self, current_price: float, entry_price: float,
                               side: str, pnl_percentage: float) -> float:
        """计算追踪止损价格"""
        
        # 动态调整追踪距离
        if pnl_percentage > 0.05:  # 盈利超过5%
            dynamic_distance = self.trailing_distance * 0.8  # 缩小追踪距离
        elif pnl_percentage > 0.02:  # 盈利超过2%
            dynamic_distance = self.trailing_distance
        else:
            dynamic_distance = self.trailing_distance * 1.2  # 扩大追踪距离
        
        if side == 'long':
            trailing_stop = current_price * (1 - dynamic_distance)
            # 确保止损价不低于入场价
            return max(trailing_stop, entry_price * 1.001)
        else:  # short
            trailing_stop = current_price * (1 + dynamic_distance)
            # 确保止损价不高于入场价
            return min(trailing_stop, entry_price * 0.999)
    
    def calculate_consolidation_profit_lock(self, position_data: Dict, 
                                          market_data: Dict) -> Dict[str, Any]:
        """
        计算横盘利润锁定
        当市场进入横盘整理阶段时，提前锁定利润
        """
        
        if not position_data or position_data.get('size', 0) <= 0:
            return {'should_lock': False, 'reason': '无有效持仓'}
        
        # 检查是否处于横盘状态
        consolidation_detector = ConsolidationDetector()
        is_consolidating = consolidation_detector.detect_consolidation(market_data)
        
        if not is_consolidating:
            return {'should_lock': False, 'reason': '未检测到横盘状态'}
        
        position_id = position_data.get('id', 'default')
        entry_price = position_data['entry_price']
        current_price = market_data['price']
        side = position_data['side']
        
        # 计算当前盈亏
        if side == 'long':
            current_pnl = (current_price - entry_price) / entry_price
        else:
            current_pnl = (entry_price - current_price) / entry_price
        
        # 只有在盈利状态下才触发横盘锁定
        if current_pnl <= 0:
            return {'should_lock': False, 'reason': '当前持仓未盈利'}
        
        # 计算横盘锁定价格
        consolidation_lock_price = self._calculate_consolidation_lock_price(
            entry_price, current_pnl, side
        )
        
        logger.info(f"🔒 横盘利润锁定触发: 盈利{current_pnl:.2%}, 锁定价格{consolidation_lock_price:.2f}")
        
        return {
            'should_lock': True,
            'action': 'CONSOLIDATION_LOCK',
            'new_stop_loss': consolidation_lock_price,
            'trigger': 'consolidation',
            'reason': f'横盘整理阶段，提前锁定{current_pnl * 0.8:.2%}利润',
            'current_pnl': current_pnl
        }
    
    def _calculate_consolidation_lock_price(self, entry_price: float, 
                                          pnl_percentage: float, side: str) -> float:
        """计算横盘锁定价格"""
        # 锁定80%的利润
        locked_profit_pct = pnl_percentage * 0.8
        
        if side == 'long':
            return entry_price * (1 + locked_profit_pct)
        else:  # short
            return entry_price * (1 - locked_profit_pct)
    
    def get_position_summary(self, position_id: str) -> Dict[str, Any]:
        """获取持仓止损状态摘要"""
        
        state = self.position_states.get(position_id, {})
        
        return {
            'position_id': position_id,
            'current_stage': state.get('stage', 'initial'),
            'highest_pnl': state.get('highest_pnl', 0),
            'locked_profit': state.get('locked_profit', 0),
            'last_adjustment': state.get('last_adjustment'),
            'config': {
                'breakeven_at': self.breakeven_at,
                'lock_profit_at': self.lock_profit_at,
                'aggressive_lock_at': self.aggressive_lock_at,
                'trailing_distance': self.trailing_distance
            }
        }
    
    def reset_position(self, position_id: str):
        """重置持仓状态"""
        if position_id in self.position_states:
            del self.position_states[position_id]
            logger.info(f"🔄 重置持仓{position_id}的止损状态")
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            'position_states': self.position_states,
            'config': {
                'breakeven_at': self.breakeven_at,
                'lock_profit_at': self.lock_profit_at,
                'aggressive_lock_at': self.aggressive_lock_at,
                'trailing_distance': self.trailing_distance,
                'conservative_distance': self.conservative_distance
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def load_state(self, state_data: Dict[str, Any]):
        """从字典加载状态"""
        self.position_states = state_data.get('position_states', {})
        config = state_data.get('config', {})
        
        self.breakeven_at = config.get('breakeven_at', 0.01)
        self.lock_profit_at = config.get('lock_profit_at', 0.03)
        self.aggressive_lock_at = config.get('aggressive_lock_at', 0.05)
        self.trailing_distance = config.get('trailing_distance', 0.015)
        self.conservative_distance = config.get('conservative_distance', 0.02)


class PriceTracker:
    """价格追踪器"""
    
    def __init__(self):
        self.price_history = []
        self.max_history_length = 1000
    
    def add_price(self, price: float, timestamp: datetime = None):
        """添加价格记录"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.price_history.append({
            'price': price,
            'timestamp': timestamp.isoformat()
        })
        
        # 限制历史记录长度
        if len(self.price_history) > self.max_history_length:
            self.price_history = self.price_history[-self.max_history_length:]
    
    def get_price_history(self, hours: int = 24) -> List[Dict]:
        """获取指定时间范围内的价格历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            record for record in self.price_history
            if datetime.fromisoformat(record['timestamp']) >= cutoff_time
        ]


class ProfitCalculator:
    """利润计算器"""
    
    @staticmethod
    def calculate_pnl(entry_price: float, current_price: float, 
                     position_size: float, side: str) -> Dict[str, float]:
        """计算盈亏"""
        
        if side == 'long':
            pnl_percentage = (current_price - entry_price) / entry_price
        else:  # short
            pnl_percentage = (entry_price - current_price) / entry_price
        
        pnl_amount = position_size * pnl_percentage
        
        return {
            'pnl_percentage': pnl_percentage,
            'pnl_amount': pnl_amount,
            'current_price': current_price,
            'entry_price': entry_price
        }


class ConsolidationDetector:
    """横盘检测器"""
    
    def __init__(self):
        self.consolidation_threshold = 0.02  # 2%的价格波动阈值
        self.period_hours = 4  # 检测4小时内的横盘
    
    def detect_consolidation(self, market_data: Dict[str, Any]) -> bool:
        """检测是否处于横盘状态"""
        
        # 简化的横盘检测逻辑
        price_history = market_data.get('price_history', [])
        if len(price_history) < 10:
            return False
        
        # 计算价格波动范围
        prices = [record['price'] for record in price_history[-20:]]  # 最近20个数据点
        if not prices:
            return False
        
        max_price = max(prices)
        min_price = min(prices)
        price_range = (max_price - min_price) / min_price
        
        # 如果价格波动小于阈值，认为是横盘
        return price_range < self.consolidation_threshold
    
    def should_lock_profit(self, position_data: Dict, market_data: Dict) -> bool:
        """判断是否应该在横盘时锁定利润"""
        
        # 检查是否盈利
        current_price = market_data.get('price', 0)
        entry_price = position_data.get('entry_price', 0)
        side = position_data.get('side', 'long')
        
        if side == 'long':
            pnl = (current_price - entry_price) / entry_price
        else:
            pnl = (entry_price - current_price) / entry_price
        
        # 只有在盈利且横盘时才建议锁定
        return pnl > 0.01 and self.detect_consolidation(market_data)


# 全局动态止损管理器实例
dynamic_stop_manager = DynamicStopManager({
    'trailing_stop': {
        'breakeven_at': 0.01,
        'lock_profit_at': 0.03,
        'aggressive_lock_at': 0.05,
        'trailing_distance': 0.015,
        'conservative_distance': 0.02
    }
})
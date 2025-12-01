"""
Alpha Arena OKX 策略模块
包含所有交易策略的实现
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from config import config
from logger_config import log_info, log_warning
from trade_logger import trade_logger

class MarketAnalyzer:
    """市场分析器"""
    
    @staticmethod
    def calculate_atr(high: list, low: list, close: list, period: int = 14) -> float:
        """计算ATR波动率"""
        if len(high) < period:
            return 2.0
        
        high = np.array(high[-period:])
        low = np.array(low[-period:])
        close = np.array(close[-period:])
        
        tr = np.maximum(high - low, 
                       np.maximum(np.abs(high - np.roll(close, 1)), 
                                 np.abs(low - np.roll(close, 1))))
        atr = np.mean(tr[1:])
        current_price = close[-1]
        
        return (atr / current_price) * 100
    
    @staticmethod
    def identify_trend(prices: list, period: int = 20) -> str:
        """识别趋势"""
        if len(prices) < period:
            return '震荡'
        
        prices = np.array(prices[-period:])
        sma = np.mean(prices)
        current_price = prices[-1]
        
        # 计算趋势强度
        slope = (prices[-1] - prices[0]) / period
        volatility = np.std(prices)
        
        if abs(slope) > volatility * 0.5:
            if slope > 0:
                return '强上涨' if slope > volatility else '弱上涨'
            else:
                return '强下跌' if abs(slope) > volatility else '弱下跌'
        else:
            return '震荡'
    
    @staticmethod
    def detect_consolidation(prices: list, threshold: float = 0.008, 
                           lookback: int = 6) -> bool:
        """检测横盘"""
        if len(prices) < lookback:
            return False
        
        recent_prices = np.array(prices[-lookback:])
        max_price = np.max(recent_prices)
        min_price = np.min(recent_prices)
        
        return (max_price - min_price) / max_price <= threshold

class RiskManager:
    """风险管理器"""
    
    @staticmethod
    def calculate_dynamic_tp_sl(signal: str, current_price: float, 
                              market_state: Dict[str, Any], 
                              position: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """计算动态止盈止损"""
        smart_config = config.get('strategies', 'smart_tp_sl')
        
        if not smart_config.get('enabled', False):
            return RiskManager._calculate_traditional_tp_sl(signal, current_price)
        
        # 获取市场数据
        atr_pct = market_state.get('atr_pct', 2.0)
        trend_strength = market_state.get('trend_strength', '中性')
        
        # 基础参数
        base_sl_pct = smart_config.get('base_sl_pct', 0.02)
        base_tp_pct = smart_config.get('base_tp_pct', 0.06)
        
        # 波动率调整
        if smart_config.get('adaptive_mode', True):
            if atr_pct > 3.0:  # 高波动
                base_sl_pct *= smart_config.get('high_vol_multiplier', 1.5)
                base_tp_pct *= smart_config.get('high_vol_multiplier', 1.5)
            elif atr_pct < 1.0:  # 低波动
                base_sl_pct *= smart_config.get('low_vol_multiplier', 0.8)
                base_tp_pct *= smart_config.get('low_vol_multiplier', 0.8)
        
        # 趋势强度调整
        trend_multipliers = {
            '强上涨': {'tp': 1.3, 'sl': 0.9},
            '强下跌': {'tp': 1.3, 'sl': 0.8},
            '弱上涨': {'tp': 1.1, 'sl': 1.0},
            '弱下跌': {'tp': 1.1, 'sl': 1.0},
            '震荡': {'tp': 0.9, 'sl': 1.1}
        }
        
        if trend_strength in trend_multipliers:
            multipliers = trend_multipliers[trend_strength]
            base_tp_pct *= multipliers['tp']
            base_sl_pct *= multipliers['sl']
        
        # 盈利保护
        final_sl_pct, final_tp_pct = RiskManager._apply_profit_protection(
            base_sl_pct, base_tp_pct, position, current_price
        )
        
        # 计算最终价格
        if signal.upper() == 'BUY':
            stop_loss = current_price * (1 - final_sl_pct)
            take_profit = current_price * (1 + final_tp_pct)
        elif signal.upper() == 'SELL':
            stop_loss = current_price * (1 + final_sl_pct)
            take_profit = current_price * (1 - final_tp_pct)
        else:
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02
        
        return {
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'sl_pct': final_sl_pct,
            'tp_pct': final_tp_pct
        }
    
    @staticmethod
    def _calculate_traditional_tp_sl(signal: str, current_price: float) -> Dict[str, float]:
        """传统止盈止损计算"""
        if signal.upper() == 'BUY':
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.06,
                'sl_pct': 0.02,
                'tp_pct': 0.06
            }
        elif signal.upper() == 'SELL':
            return {
                'stop_loss': current_price * 1.02,
                'take_profit': current_price * 0.94,
                'sl_pct': 0.02,
                'tp_pct': 0.06
            }
        else:
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.02,
                'sl_pct': 0.02,
                'tp_pct': 0.02
            }
    
    @staticmethod
    def _apply_profit_protection(base_sl_pct: float, base_tp_pct: float, 
                               position: Optional[Dict[str, Any]], current_price: float) -> Tuple[float, float]:
        """应用盈利保护"""
        final_sl_pct, final_tp_pct = base_sl_pct, base_tp_pct
        
        if not position or position.get('unrealized_pnl', 0) <= 0:
            return final_sl_pct, final_tp_pct
        
        entry_price = position.get('entry_price', current_price)
        position_size = position.get('size', 0)
        
        if entry_price <= 0 or position_size <= 0:
            return final_sl_pct, final_tp_pct
        
        unrealized_pnl = position['unrealized_pnl']
        invested_amount = entry_price * position_size
        profit_pct = unrealized_pnl / invested_amount
        
        # 盈利保护配置
        profit_config = config.get('risk', 'trailing_stop')
        
        if profit_config.get('enabled', True):
            breakeven_at = profit_config.get('breakeven_at', 0.01)
            lock_profit_at = profit_config.get('lock_profit_at', 0.03)
            trailing_distance = profit_config.get('trailing_distance', 0.015)
            
            if profit_pct >= breakeven_at:
                final_sl_pct = max(final_sl_pct, profit_pct - trailing_distance)
                log_info(f"🛡️ 保本保护: 盈利{profit_pct:.2%}, 止损调整至{final_sl_pct:.2%}")
            
            if profit_pct >= lock_profit_at:
                locked_profit = profit_pct * 0.7
                final_sl_pct = max(final_sl_pct, locked_profit)
                log_info(f"🔒 利润锁定: 盈利{profit_pct:.2%}, 锁定{locked_profit:.2%}")
        
        return final_sl_pct, final_tp_pct

class SignalProcessor:
    """信号处理器"""
    
    @staticmethod
    def process_signal(signal_data: Dict[str, Any], position: Optional[Dict[str, Any]]) -> str:
        """处理信号，考虑做空开关"""
        signal = signal_data.get('signal', 'HOLD').upper()
        confidence = signal_data.get('confidence', 0.5)
        
        # 做空开关检查
        if not config.get('trading', 'allow_short_selling') and signal == 'SELL':
            if position and position.get('size', 0) > 0:
                # 有持仓时，SELL信号作为清仓
                log_info(f"🚨 做空功能已禁用，SELL信号作为清仓条件 (信心: {confidence:.3f})")
                signal_data['is_liquidation'] = True
                return 'SELL'
            else:
                # 无持仓时，SELL信号转换为HOLD
                log_info(f"🚫 做空功能已禁用，无持仓时SELL信号转换为HOLD (信心: {confidence:.3f})")
                return 'HOLD'
        
        return signal
    
    @staticmethod
    def calculate_order_size(balance: Dict[str, float], signal: str, 
                           price: float, risk_pct: float = 0.02) -> float:
        """计算订单大小"""
        available_balance = balance.get('free', 0)
        max_position_size = config.get('trading', 'max_position_size')
        
        # 基于风险计算订单大小
        risk_amount = available_balance * risk_pct
        position_size = risk_amount / price
        
        # 限制最大仓位
        return min(position_size, max_position_size)

class ConsolidationDetector:
    """横盘检测器"""
    
    @staticmethod
    def should_lock_profit(position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """判断是否应锁定横盘利润"""
        profit_config = config.get('strategies', 'profit_lock_strategy')
        
        if not profit_config.get('enabled', False):
            return False
        
        if not position or position.get('size', 0) <= 0:
            return False
        
        # 检查是否盈利
        entry_price = position.get('entry_price', 0)
        current_price = market_data.get('price', 0)
        
        if entry_price <= 0 or current_price <= 0:
            return False
        
        profit_pct = abs(current_price - entry_price) / entry_price
        min_profit = profit_config.get('min_profit_pct', 0.005)
        
        if profit_pct < min_profit:
            return False
        
        # 检测横盘
        # 这里需要传入价格历史数据，实际使用时从外部传入
        return True

# 全局策略实例
market_analyzer = MarketAnalyzer()
risk_manager = RiskManager()
signal_processor = SignalProcessor()
consolidation_detector = ConsolidationDetector()
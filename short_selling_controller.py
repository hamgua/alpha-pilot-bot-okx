"""
多维做空逻辑控制器
基于原项目功能.md第500-799行的设计规范
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ShortSellingController:
    """
    多维做空逻辑控制器
    实现完整的做空策略，包括市场环境评估、账户状态检查、风险控制等
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('short_selling', {})
        self.enabled = self.config.get('enabled', False)
        self.max_short_positions = self.config.get('max_positions', 3)
        self.max_short_ratio = self.config.get('max_ratio', 0.3)
        self.min_account_balance = self.config.get('min_balance', 1000)
        
        # 风险控制参数
        self.risk_limits = {
            'max_daily_loss': self.config.get('max_daily_loss', 0.05),
            'max_position_loss': self.config.get('max_position_loss', 0.02),
            'margin_requirement': self.config.get('margin_requirement', 0.5)
        }
        
        # 市场条件阈值
        self.market_thresholds = {
            'min_volume_ratio': 0.8,
            'max_spread_ratio': 2.0,
            'min_liquidity_usd': 100000,
            'trend_confirmation_periods': 3
        }
        
        logger.info("🐻 做空控制器初始化完成")
    
    def evaluate_short_conditions(self, signal_data: Dict, market_data: Dict, 
                                account_data: Dict) -> Dict[str, Any]:
        """
        评估做空条件的多维检查
        
        Args:
            signal_data: AI信号数据
            market_data: 市场数据
            account_data: 账户数据
            
        Returns:
            做空决策结果
        """
        # 1. 全局开关检查
        if not self.enabled:
            return {
                'can_short': False,
                'reason': '做空功能已关闭',
                'risk_level': 'BLOCKED'
            }
        
        # 2. 市场环境评估
        market_check = self._check_market_conditions(market_data)
        if not market_check.get('allow_short', True):
            return market_check
        
        # 3. 账户状态检查
        account_check = self._check_account_constraints(account_data)
        if not account_check.get('allow_short', True):
            return account_check
        
        # 4. 风险评估
        risk_check = self._assess_short_risk(signal_data, market_data, account_data)
        if not risk_check.get('allow_short', True):
            return risk_check
        
        # 5. 信号验证
        signal_check = self._validate_short_signal(signal_data, market_data)
        if not signal_check.get('allow_short', True):
            return signal_check
        
        # 所有检查通过
        return {
            'can_short': True,
            'reason': '所有条件满足',
            'risk_level': risk_check['risk_level'],
            'optimal_position_size': self._calculate_optimal_position_size(
                signal_data, account_data
            ),
            'stop_loss_price': self._calculate_stop_loss(signal_data, market_data),
            'take_profit_price': self._calculate_take_profit(signal_data, market_data),
            'margin_requirement': self._calculate_margin_requirement(
                signal_data, account_data
            )
        }
    
    def _check_market_conditions(self, market_data: Dict) -> Dict[str, Any]:
        """检查市场环境是否适合做空"""
        
        # 检查交易量
        current_volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume_24h', current_volume)
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio < self.market_thresholds['min_volume_ratio']:
            return {
                'can_short': False,
                'reason': f'交易量过低 ({volume_ratio:.2f} < {self.market_thresholds["min_volume_ratio"]})',
                'risk_level': 'HIGH'
            }
        
        # 检查买卖价差
        bid = market_data.get('bid', 0)
        ask = market_data.get('ask', 0)
        if bid > 0 and ask > 0:
            spread_ratio = (ask - bid) / bid
            if spread_ratio > self.market_thresholds['max_spread_ratio']:
                return {
                    'can_short': False,
                    'reason': f'买卖价差过大 ({spread_ratio:.2f} > {self.market_thresholds["max_spread_ratio"]})',
                    'risk_level': 'HIGH'
                }
        
        # 检查流动性
        orderbook_depth = market_data.get('orderbook_depth_1pct', 0)
        if orderbook_depth < self.market_thresholds['min_liquidity_usd']:
            return {
                'can_short': False,
                'reason': f'流动性不足 ({orderbook_depth:.0f} < {self.market_thresholds["min_liquidity_usd"]})',
                'risk_level': 'MEDIUM'
            }
        
        # 检查趋势确认
        price_trend = market_data.get('price_trend', {})
        if price_trend.get('direction') != 'down':
            return {
                'can_short': False,
                'reason': '趋势方向不符合做空条件',
                'risk_level': 'MEDIUM'
            }
        
        return {'can_short': True, 'reason': '市场环境良好'}
    
    def _check_account_constraints(self, account_data: Dict) -> Dict[str, Any]:
        """检查账户约束条件"""
        
        # 检查账户余额
        available_balance = account_data.get('available_balance', 0)
        if available_balance < self.min_account_balance:
            return {
                'can_short': False,
                'reason': f'账户余额不足 ({available_balance:.2f} < {self.min_account_balance})',
                'risk_level': 'BLOCKED'
            }
        
        # 检查杠杆限制
        max_leverage = account_data.get('max_leverage', 10)
        if max_leverage < 2:  # 至少需要2倍杠杆才能做空
            return {
                'can_short': False,
                'reason': f'杠杆限制过低 ({max_leverage} < 2)',
                'risk_level': 'BLOCKED'
            }
        
        # 检查当前做空仓位数量
        current_short_positions = account_data.get('short_positions', [])
        if len(current_short_positions) >= self.max_short_positions:
            return {
                'can_short': False,
                'reason': f'做空仓位数量已达上限 ({len(current_short_positions)} >= {self.max_short_positions})',
                'risk_level': 'MEDIUM'
            }
        
        # 检查做空比例
        total_position_value = account_data.get('total_position_value', 0)
        current_short_value = sum(pos.get('value', 0) for pos in current_short_positions)
        short_ratio = current_short_value / total_position_value if total_position_value > 0 else 0
        
        if short_ratio >= self.max_short_ratio:
            return {
                'can_short': False,
                'reason': f'做空比例过高 ({short_ratio:.2f} >= {self.max_short_ratio})',
                'risk_level': 'HIGH'
            }
        
        return {'can_short': True, 'reason': '账户状态正常'}
    
    def _assess_short_risk(self, signal_data: Dict, market_data: Dict, 
                          account_data: Dict) -> Dict[str, Any]:
        """评估做空风险等级"""
        
        risk_score = 0
        max_score = 10
        
        # 信号强度评分
        confidence = signal_data.get('confidence', 0)
        if confidence < 0.7:
            risk_score += 2
        elif confidence < 0.5:
            risk_score += 4
        
        # 波动率评分
        volatility = market_data.get('volatility_24h', 0)
        if volatility > 0.05:  # 5%以上波动率
            risk_score += 2
        elif volatility > 0.1:  # 10%以上波动率
            risk_score += 3
        
        # 持仓时间评分
        avg_hold_time = account_data.get('avg_hold_time_hours', 0)
        if avg_hold_time > 24:  # 超过24小时
            risk_score += 1
        elif avg_hold_time > 48:  # 超过48小时
            risk_score += 2
        
        # 连续亏损评分
        consecutive_losses = account_data.get('consecutive_losses', 0)
        if consecutive_losses >= 3:
            risk_score += 2
        elif consecutive_losses >= 5:
            risk_score += 3
        
        # 风险等级判定
        if risk_score >= 7:
            risk_level = 'CRITICAL'
            allow_short = False
        elif risk_score >= 5:
            risk_level = 'HIGH'
            allow_short = True
        elif risk_score >= 3:
            risk_level = 'MEDIUM'
            allow_short = True
        else:
            risk_level = 'LOW'
            allow_short = True
        
        return {
            'can_short': allow_short,
            'reason': f'风险评分: {risk_score}/{max_score}',
            'risk_level': risk_level,
            'risk_score': risk_score
        }
    
    def _validate_short_signal(self, signal_data: Dict, market_data: Dict) -> Dict[str, Any]:
        """验证做空信号的合理性"""
        
        signal = signal_data.get('signal', '').upper()
        if signal != 'SELL':
            return {
                'allow_short': False,
                'reason': '信号不是做空信号',
                'risk_level': 'BLOCKED'
            }
        
        # 检查信号与市场价格的一致性
        current_price = market_data.get('price', 0)
        suggested_price = signal_data.get('suggested_price', 0)
        
        if suggested_price > 0 and abs(current_price - suggested_price) / current_price > 0.02:
            return {
                'allow_short': False,
                'reason': '信号价格与市场价格偏差过大',
                'risk_level': 'MEDIUM'
            }
        
        return {'can_short': True, 'reason': '信号验证通过'}
    
    def _calculate_optimal_position_size(self, signal_data: Dict, 
                                       account_data: Dict) -> float:
        """计算最优做空仓位大小"""
        
        # 基础仓位大小
        account_balance = account_data.get('available_balance', 0)
        base_position = account_balance * 0.1  # 基础10%仓位
        
        # 根据信号强度调整
        confidence = signal_data.get('confidence', 0.5)
        confidence_multiplier = min(confidence * 2, 1.5)  # 0.5-1.5倍
        
        # 根据风险等级调整
        risk_score = self._assess_short_risk(signal_data, {}, account_data).get('risk_score', 0)
        risk_multiplier = max(1 - risk_score * 0.1, 0.3)  # 0.3-1.0倍
        
        # 计算最终仓位
        optimal_size = base_position * confidence_multiplier * risk_multiplier
        
        # 确保不超过最大限制
        max_position = account_balance * self.max_short_ratio
        return min(optimal_size, max_position)
    
    def _calculate_stop_loss(self, signal_data: Dict, market_data: Dict) -> float:
        """计算做空止损价格"""
        
        current_price = market_data.get('price', 0)
        volatility = market_data.get('volatility_24h', 0.02)
        
        # 基于波动率的动态止损
        base_stop_distance = max(volatility * 2, 0.02)
        stop_loss_price = current_price * (1 + base_stop_distance)
        
        return stop_loss_price
    
    def _calculate_take_profit(self, signal_data: Dict, market_data: Dict) -> float:
        """计算做空止盈价格"""
        
        current_price = market_data.get('price', 0)
        
        # 基于信号强度的动态止盈
        confidence = signal_data.get('confidence', 0.5)
        base_tp_distance = 0.03 + confidence * 0.02
        take_profit_price = current_price * (1 - base_tp_distance)
        
        return take_profit_price
    
    def _calculate_margin_requirement(self, signal_data: Dict, 
                                    account_data: Dict) -> float:
        """计算保证金要求"""
        
        position_size = self._calculate_optimal_position_size(signal_data, account_data)
        margin_ratio = self.risk_limits['margin_requirement']
        
        return position_size * margin_ratio
    
    def get_short_positions_summary(self, account_data: Dict) -> Dict[str, Any]:
        """获取做空仓位摘要"""
        
        short_positions = account_data.get('short_positions', [])
        
        summary = {
            'total_positions': len(short_positions),
            'total_value': sum(pos.get('value', 0) for pos in short_positions),
            'total_pnl': sum(pos.get('pnl', 0) for pos in short_positions),
            'avg_leverage': sum(pos.get('leverage', 0) for pos in short_positions) / len(short_positions) if short_positions else 0,
            'risk_exposure': self._calculate_risk_exposure(short_positions)
        }
        
        return summary
    
    def _calculate_risk_exposure(self, short_positions: List[Dict]) -> Dict[str, float]:
        """计算风险敞口"""
        
        if not short_positions:
            return {'total_exposure': 0, 'max_single_exposure': 0, 'avg_exposure': 0}
        
        exposures = [pos.get('value', 0) for pos in short_positions]
        return {
            'total_exposure': sum(exposures),
            'max_single_exposure': max(exposures),
            'avg_exposure': sum(exposures) / len(exposures)
        }

# 全局做空控制器实例
short_controller = ShortSellingController({
    'short_selling': {
        'enabled': True,
        'max_positions': 3,
        'max_ratio': 0.3,
        'min_balance': 1000,
        'max_daily_loss': 0.05,
        'max_position_loss': 0.02,
        'margin_requirement': 0.5
    }
})
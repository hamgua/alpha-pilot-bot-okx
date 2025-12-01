"""
智能仓位管理系统
基于原项目功能.md的设计规范，实现动态仓位调整、风险分级管理、资金分配优化
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)

class IntelligentPositionManager:
    """
    智能仓位管理系统
    实现基于风险等级、市场条件、账户状态的动态仓位管理
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('position_management', {})
        self.risk_levels = {
            'CRITICAL': {'max_position': 0.0, 'leverage': 0.0, 'enabled': False},
            'HIGH': {'max_position': 0.1, 'leverage': 1.0, 'enabled': True},
            'MEDIUM': {'max_position': 0.3, 'leverage': 3.0, 'enabled': True},
            'LOW': {'max_position': 0.5, 'leverage': 5.0, 'enabled': True},
            'SAFE': {'max_position': 0.8, 'leverage': 10.0, 'enabled': True}
        }
        
        # 资金分配策略
        self.allocation_strategies = {
            'conservative': {'max_single_position': 0.1, 'max_total_exposure': 0.5},
            'balanced': {'max_single_position': 0.2, 'max_total_exposure': 0.7},
            'aggressive': {'max_single_position': 0.3, 'max_total_exposure': 0.9}
        }
        
        # 动态调整参数
        self.adjustment_params = {
            'volatility_weight': 0.3,
            'confidence_weight': 0.4,
            'risk_weight': 0.3,
            'min_position_size': 0.01,
            'max_position_size': 0.5
        }
        
        self.position_history = {}
        self.risk_metrics = {}
        
        logger.info("🎯 智能仓位管理器初始化完成")
    
    def calculate_optimal_position(self, signal_data: Dict, market_data: Dict,
                                 account_data: Dict) -> Dict[str, Any]:
        """
        计算最优仓位大小
        
        Args:
            signal_data: AI信号数据
            market_data: 市场数据
            account_data: 账户数据
            
        Returns:
            仓位调整建议
        """
        
        # 1. 风险评估
        risk_level = self._assess_overall_risk(signal_data, market_data, account_data)
        
        # 2. 信号强度评估
        signal_strength = self._calculate_signal_strength(signal_data)
        
        # 3. 市场条件评估
        market_condition = self._assess_market_condition(market_data)
        
        # 4. 账户状态评估
        account_health = self._assess_account_health(account_data)
        
        # 5. 计算综合权重
        position_size = self._calculate_position_size(
            risk_level, signal_strength, market_condition, account_health, account_data
        )
        
        # 6. 计算杠杆倍数
        leverage = self._calculate_optimal_leverage(
            risk_level, signal_strength, account_data
        )
        
        # 7. 计算止损止盈
        stop_loss, take_profit = self._calculate_stop_levels(
            position_size, signal_data, market_data, risk_level
        )
        
        result = {
            'position_size': position_size,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_level': risk_level,
            'signal_strength': signal_strength,
            'market_condition': market_condition,
            'account_health': account_health,
            'confidence_score': self._calculate_confidence_score(
                risk_level, signal_strength, market_condition, account_health
            ),
            'reasoning': self._generate_position_reasoning(
                risk_level, signal_strength, market_condition, account_health
            )
        }
        
        logger.info(f"🎯 仓位计算结果: 大小={position_size:.4f}, 杠杆={leverage:.1f}, 风险等级={risk_level}")
        
        return result
    
    def _assess_overall_risk(self, signal_data: Dict, market_data: Dict, 
                           account_data: Dict) -> str:
        """评估整体风险等级"""
        
        risk_score = 0
        max_score = 10
        
        # 1. 市场波动率风险 (0-3分)
        volatility = market_data.get('volatility_24h', 0)
        if volatility > 0.08:  # 8%以上波动率
            risk_score += 3
        elif volatility > 0.05:  # 5%以上波动率
            risk_score += 2
        elif volatility > 0.03:  # 3%以上波动率
            risk_score += 1
        
        # 2. 信号置信度风险 (0-2分)
        confidence = signal_data.get('confidence', 0.5)
        if confidence < 0.5:
            risk_score += 2
        elif confidence < 0.7:
            risk_score += 1
        
        # 3. 账户风险 (0-3分)
        account_risk = self._calculate_account_risk_score(account_data)
        risk_score += account_risk
        
        # 4. 市场环境风险 (0-2分)
        market_risk = self._calculate_market_risk_score(market_data)
        risk_score += market_risk
        
        # 风险等级判定
        if risk_score >= 8:
            return 'CRITICAL'
        elif risk_score >= 6:
            return 'HIGH'
        elif risk_score >= 4:
            return 'MEDIUM'
        elif risk_score >= 2:
            return 'LOW'
        else:
            return 'SAFE'
    
    def _calculate_signal_strength(self, signal_data: Dict) -> float:
        """计算信号强度 (0-1)"""
        
        base_confidence = signal_data.get('confidence', 0.5)
        
        # 考虑多个因素
        factors = {
            'confidence': base_confidence,
            'price_alignment': self._check_price_alignment(signal_data),
            'volume_confirmation': self._check_volume_confirmation(signal_data),
            'technical_confirmation': self._check_technical_confirmation(signal_data)
        }
        
        # 加权计算
        weights = {'confidence': 0.4, 'price_alignment': 0.2, 
                  'volume_confirmation': 0.2, 'technical_confirmation': 0.2}
        
        signal_strength = sum(factors[key] * weights[key] for key in factors)
        return min(max(signal_strength, 0), 1)
    
    def _assess_market_condition(self, market_data: Dict) -> str:
        """评估市场条件"""
        
        condition_score = 0
        
        # 1. 流动性评估
        liquidity_score = self._assess_liquidity(market_data)
        condition_score += liquidity_score
        
        # 2. 趋势强度评估
        trend_score = self._assess_trend_strength(market_data)
        condition_score += trend_score
        
        # 3. 波动性评估
        volatility_score = self._assess_volatility_condition(market_data)
        condition_score += volatility_score
        
        # 条件等级判定
        if condition_score >= 8:
            return 'EXCELLENT'
        elif condition_score >= 6:
            return 'GOOD'
        elif condition_score >= 4:
            return 'FAIR'
        elif condition_score >= 2:
            return 'POOR'
        else:
            return 'BAD'
    
    def _assess_account_health(self, account_data: Dict) -> str:
        """评估账户健康状况"""
        
        health_score = 0
        
        # 1. 资金充足度
        balance_score = self._assess_balance_health(account_data)
        health_score += balance_score
        
        # 2. 风险敞口
        exposure_score = self._assess_exposure_health(account_data)
        health_score += exposure_score
        
        # 3. 历史表现
        performance_score = self._assess_performance_health(account_data)
        health_score += performance_score
        
        # 健康等级判定
        if health_score >= 8:
            return 'EXCELLENT'
        elif health_score >= 6:
            return 'GOOD'
        elif health_score >= 4:
            return 'FAIR'
        elif health_score >= 2:
            return 'POOR'
        else:
            return 'CRITICAL'
    
    def _calculate_position_size(self, risk_level: str, signal_strength: float,
                               market_condition: str, account_health: str,
                               account_data: Dict) -> float:
        """计算最优仓位大小"""
        
        # 获取基础限制
        risk_config = self.risk_levels.get(risk_level, self.risk_levels['SAFE'])
        max_position_ratio = risk_config['max_position']
        
        # 账户可用余额
        available_balance = account_data.get('available_balance', 0)
        
        # 基础仓位大小
        base_position = available_balance * max_position_ratio
        
        # 信号强度调整
        signal_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5-1.0倍
        
        # 市场条件调整
        market_multipliers = {
            'EXCELLENT': 1.2, 'GOOD': 1.0, 'FAIR': 0.8, 'POOR': 0.6, 'BAD': 0.4
        }
        market_multiplier = market_multipliers.get(market_condition, 1.0)
        
        # 账户健康调整
        health_multipliers = {
            'EXCELLENT': 1.2, 'GOOD': 1.0, 'FAIR': 0.8, 'POOR': 0.6, 'CRITICAL': 0.3
        }
        health_multiplier = health_multipliers.get(account_health, 1.0)
        
        # 计算最终仓位
        optimal_size = base_position * signal_multiplier * market_multiplier * health_multiplier
        
        # 确保在合理范围内
        min_size = available_balance * self.adjustment_params['min_position_size']
        max_size = available_balance * self.adjustment_params['max_position_size']
        
        return max(min(optimal_size, max_size), min_size)
    
    def _calculate_optimal_leverage(self, risk_level: str, signal_strength: float,
                                  account_data: Dict) -> float:
        """计算最优杠杆倍数"""
        
        risk_config = self.risk_levels.get(risk_level, self.risk_levels['SAFE'])
        base_leverage = risk_config['leverage']
        
        # 信号强度调整
        leverage_multiplier = 0.8 + (signal_strength * 0.4)  # 0.8-1.2倍
        
        # 账户风险调整
        account_risk = self._calculate_account_risk_score(account_data)
        account_adjustment = max(1 - account_risk * 0.1, 0.5)  # 0.5-1.0倍
        
        optimal_leverage = base_leverage * leverage_multiplier * account_adjustment
        
        # 确保不超过账户最大杠杆限制
        max_leverage = account_data.get('max_leverage', 10)
        return min(optimal_leverage, max_leverage)
    
    def _calculate_stop_levels(self, position_size: float, signal_data: Dict,
                             market_data: Dict, risk_level: str) -> Tuple[float, float]:
        """计算止损止盈水平"""
        
        current_price = market_data.get('price', 0)
        volatility = market_data.get('volatility_24h', 0.02)
        
        # 基础止损距离
        base_stop_distance = volatility * 2
        
        # 风险等级调整
        risk_adjustments = {
            'CRITICAL': 0.5, 'HIGH': 0.7, 'MEDIUM': 0.9, 'LOW': 1.0, 'SAFE': 1.2
        }
        risk_multiplier = risk_adjustments.get(risk_level, 1.0)
        
        # 信号强度调整
        confidence = signal_data.get('confidence', 0.5)
        confidence_multiplier = 1.5 - (confidence * 0.5)  # 0.5-1.5倍
        
        # 计算最终止损距离
        stop_distance = base_stop_distance * risk_multiplier * confidence_multiplier
        
        # 计算止损价格
        signal = signal_data.get('signal', 'BUY').upper()
        if signal == 'BUY':
            stop_loss = current_price * (1 - stop_distance)
            take_profit = current_price * (1 + stop_distance * 2)  # 盈亏比2:1
        else:  # SELL
            stop_loss = current_price * (1 + stop_distance)
            take_profit = current_price * (1 - stop_distance * 2)
        
        return stop_loss, take_profit
    
    def _calculate_confidence_score(self, risk_level: str, signal_strength: float,
                                  market_condition: str, account_health: str) -> float:
        """计算整体置信度分数"""
        
        # 风险等级权重
        risk_weights = {
            'CRITICAL': 0.1, 'HIGH': 0.3, 'MEDIUM': 0.5, 'LOW': 0.7, 'SAFE': 0.9
        }
        risk_weight = risk_weights.get(risk_level, 0.5)
        
        # 市场条件权重
        market_weights = {
            'EXCELLENT': 0.9, 'GOOD': 0.7, 'FAIR': 0.5, 'POOR': 0.3, 'BAD': 0.1
        }
        market_weight = market_weights.get(market_condition, 0.5)
        
        # 账户健康权重
        health_weights = {
            'EXCELLENT': 0.9, 'GOOD': 0.7, 'FAIR': 0.5, 'POOR': 0.3, 'CRITICAL': 0.1
        }
        health_weight = health_weights.get(account_health, 0.5)
        
        # 综合计算
        confidence = (signal_strength * 0.4 + 
                     risk_weight * 0.3 + 
                     market_weight * 0.2 + 
                     health_weight * 0.1)
        
        return min(max(confidence, 0), 1)
    
    def _generate_position_reasoning(self, risk_level: str, signal_strength: float,
                                   market_condition: str, account_health: str) -> str:
        """生成仓位决策理由"""
        
        reasons = []
        
        reasons.append(f"风险等级: {risk_level}")
        reasons.append(f"信号强度: {signal_strength:.2f}")
        reasons.append(f"市场条件: {market_condition}")
        reasons.append(f"账户健康: {account_health}")
        
        return " | ".join(reasons)
    
    def _check_price_alignment(self, signal_data: Dict) -> float:
        """检查价格与信号的一致性"""
        return signal_data.get('price_alignment', 0.8)
    
    def _check_volume_confirmation(self, signal_data: Dict) -> float:
        """检查成交量确认"""
        return signal_data.get('volume_confirmation', 0.7)
    
    def _check_technical_confirmation(self, signal_data: Dict) -> float:
        """检查技术指标确认"""
        return signal_data.get('technical_confirmation', 0.75)
    
    def _assess_liquidity(self, market_data: Dict) -> float:
        """评估市场流动性"""
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume_24h', volume)
        
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            return min(volume_ratio, 1.0)
        return 0.5
    
    def _assess_trend_strength(self, market_data: Dict) -> float:
        """评估趋势强度"""
        trend_data = market_data.get('trend_data', {})
        strength = trend_data.get('strength', 0.5)
        return min(max(strength, 0), 1)
    
    def _assess_volatility_condition(self, market_data: Dict) -> float:
        """评估波动性条件"""
        volatility = market_data.get('volatility_24h', 0)
        
        # 适中波动率最佳 (2%-5%)
        if 0.02 <= volatility <= 0.05:
            return 1.0
        elif volatility < 0.01 or volatility > 0.08:
            return 0.2
        else:
            return 0.7
    
    def _assess_balance_health(self, account_data: Dict) -> float:
        """评估资金充足度"""
        total_balance = account_data.get('total_balance', 0)
        available_balance = account_data.get('available_balance', 0)
        
        if total_balance > 0:
            available_ratio = available_balance / total_balance
            return min(available_ratio * 1.25, 1.0)
        return 0.5
    
    def _assess_exposure_health(self, account_data: Dict) -> float:
        """评估风险敞口健康度"""
        total_balance = account_data.get('total_balance', 0)
        total_exposure = account_data.get('total_position_value', 0)
        
        if total_balance > 0:
            exposure_ratio = total_exposure / total_balance
            # 理想敞口比例在30%-60%
            if 0.3 <= exposure_ratio <= 0.6:
                return 1.0
            elif exposure_ratio > 0.8:
                return 0.3
            elif exposure_ratio < 0.1:
                return 0.7
            else:
                return 0.8
        return 0.5
    
    def _assess_performance_health(self, account_data: Dict) -> float:
        """评估历史表现健康度"""
        win_rate = account_data.get('win_rate', 0.5)
        sharpe_ratio = account_data.get('sharpe_ratio', 0)
        
        # 综合评估
        performance_score = (win_rate * 0.6 + 
                          min(max(sharpe_ratio / 2.0, 0), 1) * 0.4)
        
        return min(max(performance_score, 0), 1)
    
    # 辅助评估方法
    def _calculate_account_risk_score(self, account_data: Dict) -> float:
        """计算账户风险评分"""
        score = 0
        
        # 可用余额比例
        total_balance = account_data.get('total_balance', 0)
        available_balance = account_data.get('available_balance', 0)
        if total_balance > 0:
            available_ratio = available_balance / total_balance
            if available_ratio < 0.2:
                score += 3
            elif available_ratio < 0.5:
                score += 2
            elif available_ratio < 0.8:
                score += 1
        
        # 当前风险敞口
        total_exposure = account_data.get('total_position_value', 0)
        if total_balance > 0:
            exposure_ratio = total_exposure / total_balance
            if exposure_ratio > 0.8:
                score += 3
            elif exposure_ratio > 0.6:
                score += 2
            elif exposure_ratio > 0.4:
                score += 1
        
        # 连续亏损
        consecutive_losses = account_data.get('consecutive_losses', 0)
        if consecutive_losses >= 5:
            score += 3
        elif consecutive_losses >= 3:
            score += 2
        elif consecutive_losses >= 1:
            score += 1
        
        return score
    
    def _calculate_market_risk_score(self, market_data: Dict) -> float:
        """计算市场风险评分"""
        score = 0
        
        # 波动率风险
        volatility = market_data.get('volatility_24h', 0)
        if volatility > 0.1:
            score += 2
        elif volatility > 0.05:
            score += 1
        
        # 流动性风险
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume_24h', volume)
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio < 0.5:
                score += 2
            elif volume_ratio < 0.8:
                score += 1
        
        return score
    
    def get_portfolio_summary(self, account_data: Dict) -> Dict[str, Any]:
        """获取投资组合摘要"""
        
        positions = account_data.get('positions', [])
        total_balance = account_data.get('total_balance', 0)
        
        summary = {
            'total_positions': len(positions),
            'total_exposure': sum(pos.get('value', 0) for pos in positions),
            'total_pnl': sum(pos.get('pnl', 0) for pos in positions),
            'long_positions': len([p for p in positions if p.get('side') == 'long']),
            'short_positions': len([p for p in positions if p.get('side') == 'short']),
            'avg_position_size': 0,
            'max_position_size': 0,
            'portfolio_heat': 0
        }
        
        if positions:
            position_values = [pos.get('value', 0) for pos in positions]
            summary['avg_position_size'] = sum(position_values) / len(position_values)
            summary['max_position_size'] = max(position_values)
            
            if total_balance > 0:
                summary['portfolio_heat'] = summary['total_exposure'] / total_balance
        
        return summary
    
    def rebalance_portfolio(self, account_data: Dict, target_allocation: Dict[str, float]) -> Dict[str, Any]:
        """重新平衡投资组合"""
        
        current_summary = self.get_portfolio_summary(account_data)
        positions = account_data.get('positions', [])
        
        rebalance_actions = []
        
        for position in positions:
            current_allocation = position.get('value', 0) / current_summary['total_exposure']
            target_allocation_pct = target_allocation.get(position.get('symbol', ''), 0)
            
            allocation_diff = current_allocation - target_allocation_pct
            
            if abs(allocation_diff) > 0.05:  # 5%以上的偏差需要调整
                action = {
                    'position_id': position.get('id'),
                    'symbol': position.get('symbol'),
                    'current_allocation': current_allocation,
                    'target_allocation': target_allocation_pct,
                    'action': 'REDUCE' if allocation_diff > 0 else 'INCREASE',
                    'adjustment_amount': abs(allocation_diff) * current_summary['total_exposure']
                }
                rebalance_actions.append(action)
        
        return {
            'rebalance_needed': len(rebalance_actions) > 0,
            'actions': rebalance_actions,
            'current_summary': current_summary
        }


# 全局智能仓位管理器实例
position_manager = IntelligentPositionManager({
    'position_management': {
        'max_single_position': 0.2,
        'max_total_exposure': 0.8,
        'min_position_size': 0.01,
        'max_position_size': 0.5
    }
})
        
"""
多维度风险评估模块
实现综合风险评估和管理功能
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessmentResult:
    """风险评估结果"""
    overall_risk_score: float  # 0-100
    risk_level: str  # low, medium, high, extreme
    confidence_score: float  # 0-1
    risk_breakdown: Dict[str, float]
    risk_factors: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_risk_score': self.overall_risk_score,
            'risk_level': self.risk_level,
            'confidence_score': self.confidence_score,
            'risk_breakdown': self.risk_breakdown,
            'risk_factors': self.risk_factors,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class RiskConfig(BaseConfig):
    """风险评估配置"""
    def __init__(self, **kwargs):
        super().__init__(name="RiskAssessment", **kwargs)
        self.max_position_risk = kwargs.get('max_position_risk', 0.05)  # 5%
        self.max_daily_loss = kwargs.get('max_daily_loss', 100.0)
        self.max_leverage = kwargs.get('max_leverage', 20)
        self.volatility_threshold = kwargs.get('volatility_threshold', 0.03)  # 3%
        self.correlation_threshold = kwargs.get('correlation_threshold', 0.7)
        self.enable_dynamic_adjustment = kwargs.get('enable_dynamic_adjustment', True)

class MultiDimensionalRiskAssessment(BaseComponent):
    """多维度风险评估器"""
    
    def __init__(self, config: Optional[RiskConfig] = None):
        super().__init__(config or RiskConfig())
        self.config = config or RiskConfig()
        self.risk_history: List[RiskAssessmentResult] = []
        self.risk_factors_cache: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """初始化风险评估器"""
        try:
            logger.info("🛡️ 多维度风险评估器初始化...")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"风险评估器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理风险评估器"""
        self.risk_history.clear()
        self.risk_factors_cache.clear()
        self._initialized = False
        logger.info("🛑 风险评估器已清理")
    
    async def perform_comprehensive_risk_assessment(self, portfolio_data: Optional[Dict[str, Any]] = None,
                                                  market_data: Optional[Dict[str, Any]] = None) -> RiskAssessmentResult:
        """执行综合风险评估"""
        try:
            logger.info("🔍 开始综合风险评估...")
            
            # 1. 市场风险评估
            market_risk = await self._assess_market_risk(market_data)
            
            # 2. 投资组合风险评估
            portfolio_risk = await self._assess_portfolio_risk(portfolio_data)
            
            # 3. 波动性风险评估
            volatility_risk = await self._assess_volatility_risk(market_data)
            
            # 4. 流动性风险评估
            liquidity_risk = await self._assess_liquidity_risk(market_data)
            
            # 5. 相关性风险评估
            correlation_risk = await self._assess_correlation_risk(portfolio_data)
            
            # 6. 系统性风险评估
            systemic_risk = await self._assess_systemic_risk(market_data)
            
            # 7. 时间风险评估
            time_risk = await self._assess_time_risk(portfolio_data)
            
            # 8. 综合风险评分
            overall_risk_score = self._calculate_overall_risk_score({
                'market_risk': market_risk,
                'portfolio_risk': portfolio_risk,
                'volatility_risk': volatility_risk,
                'liquidity_risk': liquidity_risk,
                'correlation_risk': correlation_risk,
                'systemic_risk': systemic_risk,
                'time_risk': time_risk
            })
            
            # 9. 确定风险等级
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # 10. 计算置信度
            confidence_score = self._calculate_confidence_score({
                'market_risk': market_risk,
                'portfolio_risk': portfolio_risk,
                'volatility_risk': volatility_risk,
                'data_quality': self._assess_data_quality(market_data, portfolio_data)
            })
            
            # 11. 生成风险因素列表
            risk_factors = self._generate_risk_factors({
                'market_risk': market_risk,
                'portfolio_risk': portfolio_risk,
                'volatility_risk': volatility_risk,
                'liquidity_risk': liquidity_risk,
                'correlation_risk': correlation_risk,
                'systemic_risk': systemic_risk,
                'time_risk': time_risk
            })
            
            # 12. 生成建议
            recommendations = self._generate_risk_recommendations(overall_risk_score, risk_factors)
            
            result = RiskAssessmentResult(
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                confidence_score=confidence_score,
                risk_breakdown={
                    'market_risk': market_risk,
                    'portfolio_risk': portfolio_risk,
                    'volatility_risk': volatility_risk,
                    'liquidity_risk': liquidity_risk,
                    'correlation_risk': correlation_risk,
                    'systemic_risk': systemic_risk,
                    'time_risk': time_risk
                },
                risk_factors=risk_factors,
                recommendations=recommendations,
                timestamp=datetime.now()
            )
            
            # 记录历史
            self.risk_history.append(result)
            
            # 保持历史记录在合理范围内
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-500:]
            
            logger.info(f"✅ 综合风险评估完成: 风险评分 {overall_risk_score:.1f}, 等级 {risk_level}")
            return result
            
        except Exception as e:
            logger.error(f"综合风险评估失败: {e}")
            return self._get_default_risk_result()
    
    async def _assess_market_risk(self, market_data: Optional[Dict[str, Any]]) -> float:
        """评估市场风险"""
        try:
            if not market_data:
                return 30.0  # 默认中等风险
            
            # 基于市场指标计算风险
            technical_data = market_data.get('technical_data', {})
            
            # RSI风险 (超买超卖)
            rsi = technical_data.get('rsi', 50)
            rsi_risk = self._calculate_rsi_risk(rsi)
            
            # MACD风险
            macd = technical_data.get('macd', {})
            macd_risk = self._calculate_macd_risk(macd)
            
            # 趋势风险
            trend_analysis = market_data.get('trend_analysis', {})
            trend_risk = self._calculate_trend_risk(trend_analysis)
            
            # 综合市场风险
            market_risk = (rsi_risk * 0.4 + macd_risk * 0.3 + trend_risk * 0.3)
            
            return max(0, min(100, market_risk))
            
        except Exception as e:
            logger.error(f"评估市场风险失败: {e}")
            return 30.0
    
    def _calculate_rsi_risk(self, rsi: float) -> float:
        """计算RSI风险"""
        try:
            if rsi < 20 or rsi > 80:  # 极端区域
                return 80.0
            elif rsi < 30 or rsi > 70:  # 超买超卖
                return 60.0
            elif rsi < 40 or rsi > 60:  # 偏极端
                return 40.0
            else:  # 中性区域
                return 20.0
                
        except Exception as e:
            logger.error(f"计算RSI风险失败: {e}")
            return 30.0
    
    def _calculate_macd_risk(self, macd: Dict[str, Any]) -> float:
        """计算MACD风险"""
        try:
            if not macd or not isinstance(macd, dict):
                return 30.0
            
            macd_line = macd.get('macd', 0)
            signal_line = macd.get('signal', 0)
            
            # 死叉风险
            if macd_line < signal_line and macd_line < 0:
                return 70.0
            elif macd_line < signal_line and macd_line > 0:
                return 50.0
            elif macd_line > signal_line and macd_line < 0:
                return 30.0
            else:  # 金叉
                return 20.0
                
        except Exception as e:
            logger.error(f"计算MACD风险失败: {e}")
            return 30.0
    
    def _calculate_trend_risk(self, trend_analysis: Dict[str, Any]) -> float:
        """计算趋势风险"""
        try:
            trend_direction = trend_analysis.get('overall', 'neutral')
            trend_strength = trend_analysis.get('strength', 0.0)
            
            if trend_direction == 'bullish':
                return max(10, 40 - trend_strength * 20)  # 趋势越强，风险越低
            elif trend_direction == 'bearish':
                return min(90, 60 + trend_strength * 20)  # 趋势越强，风险越高
            else:
                return 40.0  # 震荡市场中等风险
                
        except Exception as e:
            logger.error(f"计算趋势风险失败: {e}")
            return 40.0
    
    async def _assess_portfolio_risk(self, portfolio_data: Optional[Dict[str, Any]]) -> float:
        """评估投资组合风险"""
        try:
            if not portfolio_data:
                return 25.0  # 默认中等风险
            
            # 仓位大小风险
            position_size = portfolio_data.get('position_size', 0)
            size_risk = self._calculate_position_size_risk(position_size)
            
            # 杠杆风险
            leverage = portfolio_data.get('leverage', 1)
            leverage_risk = self._calculate_leverage_risk(leverage)
            
            # 集中度风险
            concentration = portfolio_data.get('concentration', 0)
            concentration_risk = self._calculate_concentration_risk(concentration)
            
            # 综合投资组合风险
            portfolio_risk = (size_risk * 0.5 + leverage_risk * 0.3 + concentration_risk * 0.2)
            
            return max(0, min(100, portfolio_risk))
            
        except Exception as e:
            logger.error(f"评估投资组合风险失败: {e}")
            return 25.0
    
    def _calculate_position_size_risk(self, position_size: float) -> float:
        """计算仓位大小风险"""
        try:
            # 仓位越大，风险越高
            if position_size > 0.8:
                return 80.0
            elif position_size > 0.6:
                return 60.0
            elif position_size > 0.4:
                return 40.0
            elif position_size > 0.2:
                return 25.0
            else:
                return 15.0
                
        except Exception as e:
            logger.error(f"计算仓位大小风险失败: {e}")
            return 25.0
    
    def _calculate_leverage_risk(self, leverage: float) -> float:
        """计算杠杆风险"""
        try:
            # 杠杆越高，风险越高
            if leverage > 50:
                return 90.0
            elif leverage > 20:
                return 70.0
            elif leverage > 10:
                return 50.0
            elif leverage > 5:
                return 30.0
            else:
                return 15.0
                
        except Exception as e:
            logger.error(f"计算杠杆风险失败: {e}")
            return 30.0
    
    def _calculate_concentration_risk(self, concentration: float) -> float:
        """计算集中度风险"""
        try:
            # 集中度越高，风险越高
            if concentration > 0.8:
                return 75.0
            elif concentration > 0.6:
                return 55.0
            elif concentration > 0.4:
                return 35.0
            else:
                return 20.0
                
        except Exception as e:
            logger.error(f"计算集中度风险失败: {e}")
            return 35.0
    
    async def _assess_volatility_risk(self, market_data: Optional[Dict[str, Any]]) -> float:
        """评估波动性风险"""
        try:
            if not market_data:
                return 35.0
            
            technical_data = market_data.get('technical_data', {})
            atr_pct = technical_data.get('atr_pct', 2.0)
            
            # ATR风险映射
            if atr_pct > 5.0:  # 极高波动
                return 85.0
            elif atr_pct > 3.0:  # 高波动
                return 65.0
            elif atr_pct > 2.0:  # 中等波动
                return 45.0
            elif atr_pct > 1.0:  # 低波动
                return 25.0
            else:  # 极低波动
                return 15.0
                
        except Exception as e:
            logger.error(f"评估波动性风险失败: {e}")
            return 35.0
    
    async def _assess_liquidity_risk(self, market_data: Optional[Dict[str, Any]]) -> float:
        """评估流动性风险"""
        try:
            if not market_data:
                return 30.0
            
            # 基于交易量和市场深度评估流动性
            # 这里使用简化的逻辑，实际应该获取真实的流动性数据
            
            price_history = market_data.get('price_history', [])
            if len(price_history) < 10:
                return 30.0
            
            # 计算买卖价差模拟流动性
            recent_data = price_history[-10:]
            spreads = []
            for data in recent_data:
                if isinstance(data, dict) and 'bid' in data and 'ask' in data:
                    spread = (data['ask'] - data['bid']) / data['bid']
                    spreads.append(spread)
            
            if spreads:
                avg_spread = np.mean(spreads)
                # 价差越大，流动性越差，风险越高
                if avg_spread > 0.01:  # 1%以上价差
                    return 70.0
                elif avg_spread > 0.005:  # 0.5%以上价差
                    return 50.0
                else:
                    return 25.0
            else:
                return 30.0
                
        except Exception as e:
            logger.error(f"评估流动性风险失败: {e}")
            return 30.0
    
    async def _assess_correlation_risk(self, portfolio_data: Optional[Dict[str, Any]]) -> float:
        """评估相关性风险"""
        try:
            if not portfolio_data:
                return 20.0
            
            # 这里应该计算资产间的相关性
            # 简化处理，返回中等风险
            return 25.0
            
        except Exception as e:
            logger.error(f"评估相关性风险失败: {e}")
            return 20.0
    
    async def _assess_systemic_risk(self, market_data: Optional[Dict[str, Any]]) -> float:
        """评估系统性风险"""
        try:
            if not market_data:
                return 25.0
            
            # 基于市场异常指标评估系统性风险
            # 这里使用简化的逻辑
            
            technical_data = market_data.get('technical_data', {})
            
            # 多个指标同时异常可能表示系统性风险
            risk_indicators = []
            
            # RSI极端值
            rsi = technical_data.get('rsi', 50)
            if rsi < 20 or rsi > 80:
                risk_indicators.append(1)
            
            # 波动率异常
            atr_pct = technical_data.get('atr_pct', 2.0)
            if atr_pct > 4.0:
                risk_indicators.append(1)
            
            # 趋势强度异常
            trend_analysis = market_data.get('trend_analysis', {})
            trend_strength = trend_analysis.get('strength', 0.0)
            if abs(trend_strength) > 0.8:
                risk_indicators.append(1)
            
            # 计算系统性风险
            systemic_risk = len(risk_indicators) * 25.0  # 每个指标25分
            
            return min(100, systemic_risk)
            
        except Exception as e:
            logger.error(f"评估系统性风险失败: {e}")
            return 25.0
    
    async def _assess_time_risk(self, portfolio_data: Optional[Dict[str, Any]]) -> float:
        """评估时间风险"""
        try:
            if not portfolio_data:
                return 15.0
            
            # 基于持仓时间评估风险
            holding_period = portfolio_data.get('holding_period', 0)  # 小时
            
            # 持仓时间越长，时间风险越高
            if holding_period > 168:  # 超过1周
                return 60.0
            elif holding_period > 72:  # 超过3天
                return 40.0
            elif holding_period > 24:  # 超过1天
                return 25.0
            else:
                return 15.0
                
        except Exception as e:
            logger.error(f"评估时间风险失败: {e}")
            return 15.0
    
    def _calculate_overall_risk_score(self, risk_components: Dict[str, float]) -> float:
        """计算综合风险评分"""
        try:
            # 风险权重配置
            weights = {
                'market_risk': 0.25,
                'portfolio_risk': 0.20,
                'volatility_risk': 0.20,
                'liquidity_risk': 0.15,
                'correlation_risk': 0.10,
                'systemic_risk': 0.05,
                'time_risk': 0.05
            }
            
            overall_score = 0.0
            total_weight = 0.0
            
            for risk_type, score in risk_components.items():
                if risk_type in weights:
                    overall_score += score * weights[risk_type]
                    total_weight += weights[risk_type]
            
            if total_weight > 0:
                overall_score /= total_weight
            
            # 应用动态调整
            if self.config.enable_dynamic_adjustment:
                overall_score = self._apply_dynamic_adjustment(overall_score, risk_components)
            
            return max(0, min(100, overall_score))
            
        except Exception as e:
            logger.error(f"计算综合风险评分失败: {e}")
            return 50.0
    
    def _apply_dynamic_adjustment(self, base_score: float, risk_components: Dict[str, float]) -> float:
        """应用动态风险调整"""
        try:
            # 如果多个风险因素同时很高，增加总体风险
            high_risk_count = sum(1 for score in risk_components.values() if score > 70)
            
            if high_risk_count >= 3:
                adjustment = 1.2  # 增加20%
            elif high_risk_count >= 2:
                adjustment = 1.1  # 增加10%
            else:
                adjustment = 1.0
            
            adjusted_score = base_score * adjustment
            
            return max(0, min(100, adjusted_score))
            
        except Exception as e:
            logger.error(f"应用动态风险调整失败: {e}")
            return base_score
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """确定风险等级"""
        try:
            if risk_score >= 80:
                return 'extreme'
            elif risk_score >= 60:
                return 'high'
            elif risk_score >= 40:
                return 'medium'
            elif risk_score >= 20:
                return 'low'
            else:
                return 'minimal'
                
        except Exception as e:
            logger.error(f"确定风险等级失败: {e}")
            return 'medium'
    
    def _calculate_confidence_score(self, risk_data: Dict[str, Any]) -> float:
        """计算置信度评分"""
        try:
            # 基于数据质量和一致性计算置信度
            data_quality = risk_data.get('data_quality', 0.5)
            
            # 基于风险因素的一致性
            risk_scores = [risk_data.get('market_risk', 30), 
                          risk_data.get('portfolio_risk', 25),
                          risk_data.get('volatility_risk', 35)]
            
            consistency = 1.0 - (np.std(risk_scores) / 100.0)  # 标准化
            
            # 基于历史稳定性
            stability = self._calculate_historical_stability()
            
            confidence = (data_quality * 0.4 + consistency * 0.4 + stability * 0.2)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"计算置信度评分失败: {e}")
            return 0.5
    
    def _calculate_historical_stability(self) -> float:
        """计算历史稳定性"""
        try:
            if len(self.risk_history) < 5:
                return 0.8  # 默认高稳定性
            
            recent_scores = [r.overall_risk_score for r in self.risk_history[-5:]]
            
            # 计算标准差
            std_dev = np.std(recent_scores)
            
            # 稳定性 = 1 - 标准化标准差
            stability = max(0, 1.0 - (std_dev / 50.0))  # 50作为基准
            
            return stability
            
        except Exception as e:
            logger.error(f"计算历史稳定性失败: {e}")
            return 0.8
    
    def _assess_data_quality(self, market_data: Optional[Dict[str, Any]], 
                           portfolio_data: Optional[Dict[str, Any]]) -> float:
        """评估数据质量"""
        try:
            score = 0.0
            
            # 市场数据质量
            if market_data and isinstance(market_data, dict):
                if 'technical_data' in market_data and market_data['technical_data']:
                    score += 0.3
                if 'price_history' in market_data and len(market_data['price_history']) > 10:
                    score += 0.2
            
            # 投资组合数据质量
            if portfolio_data and isinstance(portfolio_data, dict):
                if 'position_size' in portfolio_data:
                    score += 0.2
                if 'leverage' in portfolio_data:
                    score += 0.1
            
            # 基础分
            score += 0.2
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"评估数据质量失败: {e}")
            return 0.5
    
    def _generate_risk_factors(self, risk_components: Dict[str, float]) -> List[Dict[str, Any]]:
        """生成风险因素列表"""
        try:
            risk_factors = []
            
            factor_names = {
                'market_risk': '市场风险',
                'portfolio_risk': '投资组合风险',
                'volatility_risk': '波动性风险',
                'liquidity_risk': '流动性风险',
                'correlation_risk': '相关性风险',
                'systemic_risk': '系统性风险',
                'time_risk': '时间风险'
            }
            
            for risk_type, score in risk_components.items():
                if risk_type in factor_names:
                    severity = self._determine_risk_level(score)
                    
                    risk_factors.append({
                        'name': factor_names[risk_type],
                        'type': risk_type,
                        'score': score,
                        'severity': severity,
                        'weight': self._get_risk_weight(risk_type),
                        'description': self._get_risk_description(risk_type, score)
                    })
            
            # 按风险评分排序
            risk_factors.sort(key=lambda x: x['score'], reverse=True)
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"生成风险因素列表失败: {e}")
            return []
    
    def _get_risk_weight(self, risk_type: str) -> float:
        """获取风险权重"""
        weights = {
            'market_risk': 0.25,
            'portfolio_risk': 0.20,
            'volatility_risk': 0.20,
            'liquidity_risk': 0.15,
            'correlation_risk': 0.10,
            'systemic_risk': 0.05,
            'time_risk': 0.05
        }
        return weights.get(risk_type, 0.1)
    
    def _get_risk_description(self, risk_type: str, score: float) -> str:
        """获取风险描述"""
        try:
            if risk_type == 'market_risk':
                if score > 70:
                    return "市场处于极端状态，存在较高不确定性"
                elif score > 50:
                    return "市场风险偏高，需要谨慎操作"
                else:
                    return "市场风险可控"
                    
            elif risk_type == 'portfolio_risk':
                if score > 70:
                    return "投资组合风险过高，建议调整仓位"
                elif score > 50:
                    return "投资组合风险偏高，需要关注"
                else:
                    return "投资组合风险适中"
                    
            elif risk_type == 'volatility_risk':
                if score > 70:
                    return "市场波动剧烈，风险较高"
                elif score > 50:
                    return "市场波动较大，需要注意"
                else:
                    return "市场波动正常"
                    
            else:
                return f"{risk_type}风险评分: {score:.1f}"
                
        except Exception as e:
            logger.error(f"获取风险描述失败: {e}")
            return "风险分析失败"
    
    def _generate_risk_recommendations(self, overall_risk_score: float, risk_factors: List[Dict[str, Any]]) -> List[str]:
        """生成风险建议"""
        try:
            recommendations = []
            
            # 基于总体风险评分的建议
            if overall_risk_score > 80:
                recommendations.extend([
                    "⚠️ 风险极高，建议立即减仓或平仓",
                    "🔒 启用更严格的风险控制措施",
                    "📊 重新评估投资策略和市场条件"
                ])
            elif overall_risk_score > 60:
                recommendations.extend([
                    "⚠️ 风险较高，建议降低仓位",
                    "🛡️ 加强风险监控和止损设置",
                    "📈 考虑对冲或分散投资"
                ])
            elif overall_risk_score > 40:
                recommendations.extend([
                    "⚡ 风险中等，保持适度谨慎",
                    "📊 密切关注市场变化",
                    "🔄 考虑调整投资组合配置"
                ])
            else:
                recommendations.extend([
                    "✅ 风险较低，可以正常操作",
                    "📈 关注市场机会",
                    "🔄 保持定期风险评估"
                ])
            
            # 基于具体风险因素的建议
            for factor in risk_factors[:3]:  # 只考虑前3个最高风险
                if factor['score'] > 60:
                    specific_recs = self._get_specific_recommendations(factor['type'], factor['score'])
                    recommendations.extend(specific_recs)
            
            # 去重并保持合理数量
            unique_recommendations = list(dict.fromkeys(recommendations))[:8]
            
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"生成风险建议失败: {e}")
            return ["风险评估失败，建议谨慎操作"]
    
    def _get_specific_recommendations(self, risk_type: str, score: float) -> List[str]:
        """获取具体风险建议"""
        try:
            recommendations = []
            
            if risk_type == 'market_risk' and score > 60:
                recommendations.extend([
                    "📊 减少对市场敏感资产的敞口",
                    "🛡️ 考虑使用对冲工具",
                    "⏰ 等待更明确的市场信号"
                ])
            elif risk_type == 'portfolio_risk' and score > 60:
                recommendations.extend([
                    "📉 降低仓位规模",
                    "🔄 分散投资组合",
                    "⚖️ 重新平衡资产配置"
                ])
            elif risk_type == 'volatility_risk' and score > 60:
                recommendations.extend([
                    "🎯 设置更紧密的止损",
                    "📈 考虑波动率交易策略",
                    "⏱️ 缩短持仓时间"
                ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取具体风险建议失败: {e}")
            return []
    
    def _get_default_risk_result(self) -> RiskAssessmentResult:
        """获取默认风险评估结果"""
        now = datetime.now()
        return RiskAssessmentResult(
            overall_risk_score=50.0,
            risk_level='medium',
            confidence_score=0.5,
            risk_breakdown={
                'market_risk': 30.0,
                'portfolio_risk': 25.0,
                'volatility_risk': 35.0,
                'liquidity_risk': 30.0,
                'correlation_risk': 20.0,
                'systemic_risk': 25.0,
                'time_risk': 15.0
            },
            risk_factors=[],
            recommendations=["风险评估失败，建议谨慎操作"],
            timestamp=now
        )
    
    def get_risk_trend(self, period: int = 10) -> Dict[str, Any]:
        """获取风险趋势"""
        try:
            if len(self.risk_history) < period:
                return {'error': '历史数据不足'}
            
            recent_risks = self.risk_history[-period:]
            
            # 计算趋势
            risk_scores = [r.overall_risk_score for r in recent_risks]
            x = np.arange(len(risk_scores))
            slope, _ = np.polyfit(x, risk_scores, 1)
            
            # 计算变化
            risk_change = risk_scores[-1] - risk_scores[0]
            
            # 计算稳定性
            stability = 1.0 - (np.std(risk_scores) / 50.0)  # 标准化
            
            return {
                'period': period,
                'risk_trend': 'increasing' if slope > 2 else 'decreasing' if slope < -2 else 'stable',
                'risk_change': risk_change,
                'slope': slope,
                'stability': max(0, min(1.0, stability)),
                'current_risk': risk_scores[-1],
                'average_risk': np.mean(risk_scores)
            }
            
        except Exception as e:
            logger.error(f"获取风险趋势失败: {e}")
            return {'error': str(e)}
    
    def get_extreme_risk_alerts(self) -> List[Dict[str, Any]]:
        """获取极端风险警报"""
        try:
            alerts = []
            
            if len(self.risk_history) < 3:
                return alerts
            
            recent_risks = self.risk_history[-3:]
            
            for i, risk in enumerate(recent_risks):
                if risk.overall_risk_score > 80:
                    alerts.append({
                        'type': 'extreme_risk',
                        'severity': 'high',
                        'risk_score': risk.overall_risk_score,
                        'risk_level': risk.risk_level,
                        'timestamp': risk.timestamp,
                        'message': f"检测到极高风险: {risk.overall_risk_score:.1f}"
                    })
                elif risk.overall_risk_score > 60:
                    alerts.append({
                        'type': 'high_risk',
                        'severity': 'medium',
                        'risk_score': risk.overall_risk_score,
                        'risk_level': risk.risk_level,
                        'timestamp': risk.timestamp,
                        'message': f"检测到高风险: {risk.overall_risk_score:.1f}"
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取极端风险警报失败: {e}")
            return []
    
    def calculate_dynamic_position_size(self, base_size: float, risk_score: float) -> float:
        """计算动态仓位大小"""
        try:
            # 基于风险评分调整仓位大小
            if risk_score > 80:  # 极高风险
                multiplier = 0.3
            elif risk_score > 60:  # 高风险
                multiplier = 0.5
            elif risk_score > 40:  # 中等风险
                multiplier = 0.8
            else:  # 低风险
                multiplier = 1.0
            
            adjusted_size = base_size * multiplier
            
            # 确保在最小和最大范围内
            adjusted_size = max(self.config.min_order_size, 
                              min(adjusted_size, self.config.max_position_risk))
            
            logger.info(f"📊 动态仓位调整: {base_size} -> {adjusted_size} (风险评分: {risk_score:.1f})")
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"计算动态仓位大小失败: {e}")
            return base_size * 0.5  # 保守回退

# 全局风险评估实例
risk_assessment = MultiDimensionalRiskAssessment()
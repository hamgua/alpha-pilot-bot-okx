"""
回退信号生成器
当AI信号不可用时提供智能回退信号
"""

import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import AIError
from .signals import FallbackSignal

logger = logging.getLogger(__name__)

class FallbackSignalGenerator(BaseComponent):
    """回退信号生成器"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        super().__init__(config or BaseConfig(name="FallbackSignalGenerator"))
    
    async def initialize(self) -> bool:
        """初始化回退信号生成器"""
        try:
            logger.info("🛡️ 回退信号生成器初始化...")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"回退信号生成器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False
        logger.info("🛑 回退信号生成器已清理")
    
    def generate_fallback_signal(self, market_data: Dict[str, Any], signal_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成智能回退信号"""
        try:
            logger.info("🛡️ 启动增强兜底信号生成...")
            
            # 获取技术指标
            technical_data = market_data.get('technical_data', {})
            price = float(market_data.get('price', 50000.0))
            
            # 基础技术指标
            rsi = float(technical_data.get('rsi', 50))
            macd = technical_data.get('macd', {})
            ma_status = technical_data.get('ma_status', 'N/A')
            
            # 扩展技术指标
            atr_pct = float(technical_data.get('atr_pct', 0))
            bollinger = technical_data.get('bollinger', {})
            volume_ratio = float(technical_data.get('volume_ratio', 1.0))
            support_resistance = technical_data.get('support_resistance', {})
            
            # 获取价格历史数据
            price_history = market_data.get('price_history', [])
            price_position = 50  # 默认中位
            
            if price_history and len(price_history) >= 20:
                recent_prices = price_history[-20:]
                min_price = min(recent_prices)
                max_price = max(recent_prices)
                if max_price > min_price:
                    price_position = ((price - min_price) / (max_price - min_price)) * 100
            
            # 获取市场环境数据
            trend_analysis = market_data.get('trend_analysis', {})
            market_volatility = str(market_data.get('volatility', 'normal'))
            
            # 多因子信号生成算法
            signal_score = 0.0  # 信号得分 (-1.0 到 1.0)
            confidence_factors = []  # 信心因子
            
            # 1. RSI因子分析
            rsi_factor = self._calculate_rsi_factor(rsi, price_position)
            signal_score += rsi_factor['score']
            confidence_factors.append(rsi_factor['confidence'])
            
            # 2. MACD因子分析
            macd_factor = self._calculate_macd_factor(macd)
            signal_score += macd_factor['score'] * 0.8
            confidence_factors.append(macd_factor['confidence'])
            
            # 3. 均线因子分析
            ma_factor = self._calculate_ma_factor(ma_status)
            signal_score += ma_factor['score'] * 0.6
            confidence_factors.append(ma_factor['confidence'])
            
            # 4. 布林带因子分析
            bollinger_factor = self._calculate_bollinger_factor(bollinger, price)
            signal_score += bollinger_factor['score'] * 0.7
            confidence_factors.append(bollinger_factor['confidence'])
            
            # 5. 成交量因子分析
            volume_factor = self._calculate_volume_factor(volume_ratio)
            signal_score += volume_factor['score'] * 0.5
            confidence_factors.append(volume_factor['confidence'])
            
            # 6. 支撑阻力因子分析
            sr_factor = self._calculate_support_resistance_factor(support_resistance, price)
            signal_score += sr_factor['score'] * 0.9
            confidence_factors.append(sr_factor['confidence'])
            
            # 7. 市场环境识别
            market_factor = self._calculate_market_environment_factor(market_volatility, trend_analysis)
            signal_score += market_factor['score'] * 0.4
            confidence_factors.append(market_factor['confidence'])
            
            # 计算最终信号和信心值
            final_signal = self._determine_signal_from_score(signal_score)
            final_confidence = self._calculate_weighted_confidence(confidence_factors, signal_score)
            
            # 生成详细理由
            reason = self._generate_enhanced_reason(
                final_signal, signal_score, confidence_factors,
                rsi, macd, ma_status, bollinger, volume_ratio,
                support_resistance, market_volatility, price_position, price
            )
            
            logger.info(f"🤖 增强智能回退信号生成: {final_signal} (信心: {final_confidence:.2f}, 得分: {signal_score:.2f})")
            logger.info(f"📊 回退理由: {reason}")
            
            return {
                'signal': final_signal,
                'confidence': final_confidence,
                'reason': reason,
                'signal_score': signal_score,
                'confidence_factors': confidence_factors,
                'is_fallback': True,
                'fallback_type': 'enhanced_technical',
                'quality_score': self._calculate_quality_score(confidence_factors, signal_score),
                'market_condition': self._determine_market_condition(market_data)
            }
            
        except Exception as e:
            logger.error(f"增强智能回退信号生成失败: {e}")
            # 极端情况下的最终回退
            return {
                'signal': 'HOLD',
                'confidence': 0.5,
                'reason': '增强智能回退生成失败，使用保守HOLD信号',
                'signal_score': 0.0,
                'confidence_factors': [],
                'is_fallback': True,
                'fallback_type': 'error',
                'quality_score': 0.0,
                'market_condition': 'unknown'
            }
    
    def generate_enhanced_fallback_signal(self, market_data: Dict[str, Any], signal_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成增强兜底信号 - 使用专门的兜底策略模块"""
        try:
            logger.info("🛡️ 启动增强兜底信号生成...")
            
            # 获取AI信号历史用于兜底分析
            enhanced_fallback = self.generate_fallback_signal(market_data, signal_history)
            
            if enhanced_fallback and enhanced_fallback.get('is_fallback'):
                logger.info(f"✅ 增强兜底信号生成成功: {enhanced_fallback['signal']} (信心: {enhanced_fallback['confidence']:.2f}, 质量: {enhanced_fallback['quality_score']:.2f})")
                logger.info(f"📊 兜底类型: {enhanced_fallback['fallback_type']}")
                logger.info(f"💡 兜底理由: {enhanced_fallback['reason']}")
                
                # 记录兜底信号使用统计
                self._update_fallback_stats(enhanced_fallback)
                
                return enhanced_fallback
            else:
                logger.warning("⚠️ 增强兜底信号生成失败，回退到传统兜底")
                return self._generate_basic_fallback_signal(market_data)
                
        except Exception as e:
            logger.error(f"增强兜底信号生成异常: {e}")
            logger.warning("⚠️ 增强兜底失败，回退到传统兜底")
            return self._generate_basic_fallback_signal(market_data)
    
    def _generate_basic_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成基础回退信号"""
        try:
            # 简化的技术指标回退
            technical_data = market_data.get('technical_data', {})
            rsi = float(technical_data.get('rsi', 50))
            
            if rsi < 35:
                signal = 'BUY'
                confidence = 0.6
                reason = f"RSI超卖回退: RSI={rsi:.1f}"
            elif rsi > 65:
                signal = 'SELL'
                confidence = 0.6
                reason = f"RSI超买回退: RSI={rsi:.1f}"
            else:
                signal = 'HOLD'
                confidence = 0.4
                reason = f"RSI中性回退: RSI={rsi:.1f}"
            
            return {
                'signal': signal,
                'confidence': confidence,
                'reason': reason,
                'is_fallback': True,
                'fallback_type': 'basic_rsi',
                'quality_score': 0.3
            }
            
        except Exception as e:
            logger.error(f"基础回退信号生成失败: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.3,
                'reason': '基础回退生成失败，使用保守HOLD',
                'is_fallback': True,
                'fallback_type': 'error',
                'quality_score': 0.0
            }
    
    def _calculate_rsi_factor(self, rsi: float, price_position: float) -> Dict[str, Any]:
        """计算RSI因子"""
        try:
            if rsi < 30:  # 超卖
                rsi_score = -0.8
                confidence = 0.8
            elif rsi > 70:  # 超买
                rsi_score = 0.8
                confidence = 0.8
            elif 30 <= rsi <= 40:  # 弱势
                rsi_score = -0.4
                confidence = 0.6
            elif 60 <= rsi <= 70:  # 强势
                rsi_score = 0.4
                confidence = 0.6
            else:  # 中性
                rsi_score = 0.0
                confidence = 0.4
            
            # 结合价格位置调整
            if price_position < 30 and rsi < 40:
                rsi_score *= 1.2
                confidence *= 1.1
            elif price_position > 70 and rsi > 60:
                rsi_score *= 1.2
                confidence *= 1.1
            
            return {'score': rsi_score, 'confidence': confidence, 'factor_name': 'RSI'}
            
        except Exception as e:
            logger.error(f"RSI因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.3, 'factor_name': 'RSI'}
    
    def _calculate_macd_factor(self, macd: Dict[str, Any]) -> Dict[str, Any]:
        """计算MACD因子"""
        try:
            if not macd or not isinstance(macd, dict):
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MACD'}
            
            macd_line = float(macd.get('macd', 0))
            signal_line = float(macd.get('signal', 0))
            
            score = 0.0
            confidence = 0.6
            
            if macd_line > signal_line and macd_line > 0:
                score = 0.7
                confidence = 0.8
            elif macd_line < signal_line and macd_line < 0:
                score = -0.7
                confidence = 0.8
            elif macd_line > signal_line and macd_line < 0:
                score = -0.3
                confidence = 0.5
            elif macd_line < signal_line and macd_line > 0:
                score = 0.3
                confidence = 0.5
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'MACD'}
            
        except Exception as e:
            logger.error(f"MACD因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MACD'}
    
    def _calculate_ma_factor(self, ma_status: str) -> Dict[str, Any]:
        """计算均线因子"""
        try:
            if not ma_status or not isinstance(ma_status, str):
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MA'}
            
            score = 0.0
            confidence = 0.5
            
            ma_status_lower = ma_status.lower()
            
            if '多头排列' in ma_status_lower or 'bullish' in ma_status_lower:
                score = -0.6
                confidence = 0.7
            elif '空头排列' in ma_status_lower or 'bearish' in ma_status_lower:
                score = 0.6
                confidence = 0.7
            elif '金叉' in ma_status_lower or 'golden cross' in ma_status_lower:
                score = -0.8
                confidence = 0.8
            elif '死叉' in ma_status_lower or 'death cross' in ma_status_lower:
                score = 0.8
                confidence = 0.8
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'MA'}
            
        except Exception as e:
            logger.error(f"均线因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MA'}
    
    def _calculate_bollinger_factor(self, bollinger: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """计算布林带因子"""
        try:
            if not bollinger or not isinstance(bollinger, dict) or current_price <= 0:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
            
            upper_band = float(bollinger.get('upper', 0))
            lower_band = float(bollinger.get('lower', 0))
            
            if upper_band <= lower_band:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
            
            score = 0.0
            confidence = 0.6
            
            band_range = upper_band - lower_band
            if band_range > 0:
                price_position_in_band = (current_price - lower_band) / band_range
                
                if price_position_in_band < 0.2:
                    score = -0.7
                    confidence = 0.8
                elif price_position_in_band > 0.8:
                    score = 0.7
                    confidence = 0.8
                elif 0.4 <= price_position_in_band <= 0.6:
                    score = 0.0
                    confidence = 0.4
                else:
                    if price_position_in_band < 0.4:
                        score = -0.3
                    else:
                        score = 0.3
                    confidence = 0.5
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'Bollinger'}
            
        except Exception as e:
            logger.error(f"布林带因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
    
    def _calculate_volume_factor(self, volume_ratio: float) -> Dict[str, Any]:
        """计算成交量因子"""
        try:
            score = 0.0
            confidence = 0.4
            
            if volume_ratio > 2.0:
                score = 0.0
                confidence = 0.7
            elif volume_ratio > 1.5:
                score = 0.0
                confidence = 0.6
            elif volume_ratio < 0.5:
                score = 0.0
                confidence = 0.5
            else:
                score = 0.0
                confidence = 0.3
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'Volume'}
            
        except Exception as e:
            logger.error(f"成交量因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Volume'}
    
    def _calculate_support_resistance_factor(self, sr_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """计算支撑阻力因子"""
        try:
            if not sr_data or not isinstance(sr_data, dict) or current_price <= 0:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
            
            support = float(sr_data.get('support', 0))
            resistance = float(sr_data.get('resistance', 0))
            
            if support <= 0 or resistance <= 0 or support >= resistance:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
            
            score = 0.0
            confidence = 0.7
            
            support_distance = abs(current_price - support) / current_price * 100
            resistance_distance = abs(current_price - resistance) / current_price * 100
            
            if support_distance < 1.0:
                score = -0.8
                confidence = 0.9
            elif resistance_distance < 1.0:
                score = 0.8
                confidence = 0.9
            elif support_distance < 2.0:
                score = -0.5
                confidence = 0.7
            elif resistance_distance < 2.0:
                score = 0.5
                confidence = 0.7
            else:
                total_range = resistance - support
                if total_range > 0:
                    position_in_range = (current_price - support) / total_range
                    if position_in_range < 0.3:
                        score = -0.3
                    elif position_in_range > 0.7:
                        score = 0.3
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'SupportResistance'}
            
        except Exception as e:
            logger.error(f"支撑阻力因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
    
    def _calculate_market_environment_factor(self, volatility: str, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """计算市场环境因子"""
        try:
            score = 0.0
            confidence = 0.5
            
            volatility_lower = str(volatility).lower()
            if 'high' in volatility_lower or '高' in volatility_lower:
                confidence *= 0.8
            elif 'low' in volatility_lower or '低' in volatility_lower:
                confidence *= 1.0
            else:
                confidence *= 0.9
            
            if trend_analysis and isinstance(trend_analysis, dict):
                overall_trend = str(trend_analysis.get('overall', 'neutral')).lower()
                if 'bullish' in overall_trend or '上涨' in overall_trend:
                    score = -0.2
                elif 'bearish' in overall_trend or '下跌' in overall_trend:
                    score = 0.2
            
            return {'score': score, 'confidence': confidence, 'factor_name': 'MarketEnvironment'}
            
        except Exception as e:
            logger.error(f"市场环境因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MarketEnvironment'}
    
    def _determine_signal_from_score(self, signal_score: float) -> str:
        """根据信号得分确定最终信号"""
        try:
            if signal_score <= -0.5:
                return 'BUY'
            elif signal_score >= 0.5:
                return 'SELL'
            elif -0.2 <= signal_score <= 0.2:
                return 'HOLD'
            elif signal_score < -0.2:
                return 'BUY'
            else:
                return 'SELL'
                
        except Exception as e:
            logger.error(f"信号得分转换失败: {e}")
            return 'HOLD'
    
    def _calculate_weighted_confidence(self, confidence_factors: List[float], signal_score: float) -> float:
        """计算加权信心值"""
        try:
            if not confidence_factors:
                return 0.5
            
            avg_confidence = sum(confidence_factors) / len(confidence_factors)
            
            signal_strength = abs(signal_score)
            if signal_strength > 0.7:
                confidence_multiplier = 1.1
            elif signal_strength > 0.4:
                confidence_multiplier = 1.0
            else:
                confidence_multiplier = 0.8
            
            if confidence_factors:
                confidence_std = (sum((c - avg_confidence) ** 2 for c in confidence_factors) / len(confidence_factors)) ** 0.5
                if confidence_std < 0.1:
                    consistency_multiplier = 1.1
                elif confidence_std < 0.2:
                    consistency_multiplier = 1.0
                else:
                    consistency_multiplier = 0.9
            else:
                consistency_multiplier = 1.0
            
            final_confidence = avg_confidence * confidence_multiplier * consistency_multiplier
            
            return max(0.3, min(0.95, final_confidence))
            
        except Exception as e:
            logger.error(f"加权信心值计算失败: {e}")
            return 0.5
    
    def _generate_enhanced_reason(self, signal: str, signal_score: float, confidence_factors: List[float],
                                  rsi: float, macd: Dict[str, Any], ma_status: str, bollinger: Dict[str, Any],
                                  volume_ratio: float, support_resistance: Dict[str, Any], volatility: str,
                                  price_position: float, current_price: float = 50000.0) -> str:
        """生成增强的详细理由"""
        try:
            reason_parts = []
            
            if signal == 'BUY':
                reason_parts.append(f"多因子分析显示买入信号(得分: {signal_score:.2f})")
            elif signal == 'SELL':
                reason_parts.append(f"多因子分析显示卖出信号(得分: {signal_score:.2f})")
            else:
                reason_parts.append(f"多因子分析显示观望信号(得分: {signal_score:.2f})")
            
            if rsi < 30:
                reason_parts.append(f"RSI超卖({rsi:.1f})")
            elif rsi > 70:
                reason_parts.append(f"RSI超买({rsi:.1f})")
            elif 30 <= rsi <= 70:
                reason_parts.append(f"RSI中性({rsi:.1f})")
            
            if macd and isinstance(macd, dict):
                macd_line = float(macd.get('macd', 0))
                signal_line = float(macd.get('signal', 0))
                if macd_line > signal_line:
                    reason_parts.append("MACD金叉")
                else:
                    reason_parts.append("MACD死叉")
            
            if bollinger and isinstance(bollinger, dict):
                upper = float(bollinger.get('upper', 0))
                lower = float(bollinger.get('lower', 0))
                if upper > lower:
                    band_position = (current_price - lower) / (upper - lower)
                    if band_position < 0.2:
                        reason_parts.append("价格靠近布林带下轨")
                    elif band_position > 0.8:
                        reason_parts.append("价格靠近布林带上轨")
            
            if support_resistance and isinstance(support_resistance, dict):
                support = float(support_resistance.get('support', 0))
                resistance = float(support_resistance.get('resistance', 0))
                if support > 0 and resistance > 0:
                    support_dist = abs(current_price - support) / current_price * 100
                    resistance_dist = abs(current_price - resistance) / current_price * 100
                    
                    if support_dist < 1.0:
                        reason_parts.append("靠近支撑位")
                    if resistance_dist < 1.0:
                        reason_parts.append("靠近阻力位")
            
            if 'high' in str(volatility).lower():
                reason_parts.append("高波动环境")
            elif 'low' in str(volatility).lower():
                reason_parts.append("低波动环境")
            
            if price_position < 30:
                reason_parts.append("价格处于相对低位")
            elif price_position > 70:
                reason_parts.append("价格处于相对高位")
            
            avg_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
            if avg_confidence > 0.7:
                reason_parts.append("高信心水平")
            elif avg_confidence > 0.5:
                reason_parts.append("中等信心水平")
            else:
                reason_parts.append("低信心水平")
            
            if reason_parts:
                return "；".join(reason_parts) + "。"
            else:
                return "基于多因子技术分析的综合判断"
                
        except Exception as e:
            logger.error(f"增强理由生成失败: {e}")
            return "基于技术指标的智能回退信号"
    
    def _calculate_quality_score(self, confidence_factors: List[float], signal_score: float) -> float:
        """计算质量评分"""
        try:
            if not confidence_factors:
                return 0.0
            
            avg_confidence = sum(confidence_factors) / len(confidence_factors)
            signal_strength = abs(signal_score)
            
            # 质量评分 = 平均信心 * 信号强度
            quality = avg_confidence * (0.5 + signal_strength * 0.5)
            
            return min(quality, 1.0)
            
        except Exception as e:
            logger.error(f"质量评分计算失败: {e}")
            return 0.5
    
    def _determine_market_condition(self, market_data: Dict[str, Any]) -> str:
        """确定市场条件"""
        try:
            technical_data = market_data.get('technical_data', {})
            rsi = float(technical_data.get('rsi', 50))
            atr_pct = float(technical_data.get('atr_pct', 1.0))
            trend = str(market_data.get('trend_strength', 'neutral'))
            
            if rsi < 30:
                return 'oversold'
            elif rsi > 70:
                return 'overbought'
            elif atr_pct < 1.0:
                return 'low_volatility'
            elif atr_pct > 3.0:
                return 'high_volatility'
            elif 'bullish' in trend.lower():
                return 'bullish'
            elif 'bearish' in trend.lower():
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"市场条件判断失败: {e}")
            return 'unknown'
    
    def _update_fallback_stats(self, fallback_signal: Dict[str, Any]) -> None:
        """更新兜底信号使用统计"""
        try:
            fallback_type = fallback_signal.get('fallback_type', 'unknown')
            quality_score = fallback_signal.get('quality_score', 0)
            
            logger.info(f"📊 兜底统计: 类型={fallback_type}, 质量={quality_score:.2f}")
            
        except Exception as e:
            logger.warning(f"兜底统计更新失败: {e}")
    
    def get_fallback_performance_stats(self) -> Dict[str, Any]:
        """获取回退信号性能统计"""
        return {
            'total_fallbacks': 0,  # 应该记录实际使用次数
            'quality_distribution': {},
            'fallback_types': {},
            'success_rate': 0.0
        }
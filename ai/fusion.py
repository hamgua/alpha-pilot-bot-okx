"""
信号融合引擎
实现多AI信号的智能融合和决策
"""

import asyncio
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.base import BaseComponent, BaseConfig
from core.exceptions import AIError
from .signals import AISignal, SignalFusionResult, SignalStatistics, DiversityAnalysis
from .timeout import TimeoutManager

logger = logging.getLogger(__name__)

class SignalFusionEngine(BaseComponent):
    """信号融合引擎"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        super().__init__(config or BaseConfig(name="SignalFusionEngine"))
        self.timeout_manager = TimeoutManager()
    
    async def initialize(self) -> bool:
        """初始化融合引擎"""
        try:
            logger.info("🚀 信号融合引擎初始化...")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"信号融合引擎初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False
        logger.info("🛑 信号融合引擎已清理")
    
    def fuse_signals(self, signals: List[AISignal], market_data: Dict[str, Any] = None) -> SignalFusionResult:
        """融合多AI信号"""
        logger.info(f"🔍 开始融合AI信号，共收到 {len(signals)} 个信号")
        
        # 分析信号多样性
        diversity_analysis = self._analyze_signal_diversity(signals)
        
        # 获取配置的AI提供商总数
        total_configured = len(['deepseek', 'kimi', 'qwen', 'openai'])
        
        if not signals:
            logger.warning("⚠️ 没有可用的AI信号，使用增强智能回退信号")
            # 使用增强的智能回退信号
            smart_fallback = self._generate_smart_fallback_signal(market_data or {})
            return SignalFusionResult(
                signal=smart_fallback['signal'],
                confidence=smart_fallback['confidence'],
                reason=smart_fallback['reason'],
                providers=[],
                fusion_method='enhanced_smart_fallback',
                fusion_analysis=self._generate_enhanced_fusion_analysis(0, total_configured, '所有AI信号获取失败，使用多因子智能回退策略'),
                signal_statistics=self._generate_detailed_signal_statistics([]),
                diversity_analysis=diversity_analysis.to_dict(),
                raw_signals=[],
                votes={'BUY': 0, 'SELL': 0, 'HOLD': 0},
                confidences={'BUY': 0, 'SELL': 0, 'HOLD': 0}
            )
        
        if len(signals) == 1:
            signal = signals[0]
            logger.info(f"📊 单信号模式: {signal.provider} -> {signal.signal} (信心: {signal.confidence:.2f})")
            return SignalFusionResult(
                signal=signal.signal,
                confidence=signal.confidence,
                reason=f"{signal.provider}: {signal.reason}",
                providers=[signal.provider],
                fusion_method='single_enhanced',
                fusion_analysis=self._generate_enhanced_fusion_analysis(1, total_configured, f'仅{signal.provider}信号可用'),
                signal_statistics=self._generate_detailed_signal_statistics(signals),
                diversity_analysis=diversity_analysis.to_dict(),
                raw_signals=[signal.to_dict()],
                votes={'BUY': 1 if signal.signal == 'BUY' else 0, 
                       'SELL': 1 if signal.signal == 'SELL' else 0, 
                       'HOLD': 1 if signal.signal == 'HOLD' else 0},
                confidences={'BUY': signal.confidence if signal.signal == 'BUY' else 0,
                            'SELL': signal.confidence if signal.signal == 'SELL' else 0,
                            'HOLD': signal.confidence if signal.signal == 'HOLD' else 0}
            )
        
        # 多信号融合 - 增强版逻辑
        buy_votes = sum(1 for s in signals if s.signal == 'BUY')
        sell_votes = sum(1 for s in signals if s.signal == 'SELL')
        hold_votes = sum(1 for s in signals if s.signal == 'HOLD')
        
        total_signals = len(signals)
        
        # 计算加权信心
        buy_confidence = sum(s.confidence for s in signals if s.signal == 'BUY') / total_signals if total_signals > 0 else 0
        sell_confidence = sum(s.confidence for s in signals if s.signal == 'SELL') / total_signals if total_signals > 0 else 0
        hold_confidence = sum(s.confidence for s in signals if s.signal == 'HOLD') / total_signals if total_signals > 0 else 0
        
        logger.info(f"🗳️ 投票统计: BUY={buy_votes}, SELL={sell_votes}, HOLD={hold_votes}")
        logger.info(f"📈 信心分布: BUY={buy_confidence:.2f}, SELL={sell_confidence:.2f}, HOLD={hold_confidence:.2f}")
        
        # 生成详细的信号统计
        signal_statistics = self._generate_detailed_signal_statistics(signals)
        
        # 智能信号融合
        final_signal, confidence, reason = self._intelligent_signal_fusion(
            buy_votes, sell_votes, hold_votes,
            buy_confidence, sell_confidence, hold_confidence,
            total_signals, market_data
        )
        
        # 基于成功率调整信心
        success_rate = total_signals / total_configured if total_configured > 0 else 1.0
        if success_rate < 0.3:
            confidence *= 0.6
            reason += f" (AI成功率仅{success_rate*100:.0f}%，降低信心)"
        elif success_rate < 0.5:
            confidence *= 0.85
            reason += f" (AI成功率{success_rate*100:.0f}%，轻微降低信心)"
        
        # 增强信心调整
        max_ratio = max(buy_votes/total_signals, sell_votes/total_signals, hold_votes/total_signals)
        confidence_multiplier = max(0.7, max_ratio)
        confidence *= confidence_multiplier
        
        result = SignalFusionResult(
            signal=final_signal,
            confidence=confidence,
            reason=reason,
            providers=[s.provider for s in signals],
            fusion_method='enhanced_multi_factor_voting',
            fusion_analysis=self._generate_enhanced_fusion_analysis(total_signals, total_configured, reason),
            signal_statistics=signal_statistics,
            raw_signals=[s.to_dict() for s in signals],
            votes={'BUY': buy_votes, 'SELL': sell_votes, 'HOLD': hold_votes},
            confidences={'BUY': buy_confidence, 'SELL': sell_confidence, 'HOLD': hold_confidence},
            diversity_analysis=diversity_analysis.to_dict()
        )
        
        # 如果信号过度一致，启动强制干预机制
        if diversity_analysis.requires_intervention:
            logger.warning(f"🚨 检测到AI信号过度一致，启动强制多样性干预机制")
            return self._apply_diversity_intervention(signals, market_data)
        
        logger.info(f"✅ AI信号融合完成: {final_signal} (信心: {confidence:.2f})")
        return result
    
    def _analyze_signal_diversity(self, signals: List[AISignal]) -> DiversityAnalysis:
        """分析信号多样性"""
        if not signals or len(signals) < 2:
            return DiversityAnalysis(
                diversity_score=0,
                is_homogeneous=True,
                unique_signals=[],
                signal_distribution={'BUY': 0, 'SELL': 0, 'HOLD': 0},
                confidence_stats={'mean': 0, 'std': 0, 'min': 0, 'max': 0},
                analysis='信号数量不足',
                requires_intervention=False
            )
        
        # 计算信号一致性
        signals_types = [s.signal for s in signals]
        unique_signals = list(set(signals_types))
        
        # 计算信心值的标准差
        confidences = [s.confidence for s in signals]
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
        std_confidence = variance ** 0.5
        
        # 计算多样性分数
        signal_diversity = len(unique_signals) / 3  # 3种可能的信号类型
        confidence_diversity = min(std_confidence / 0.2, 1.0)  # 标准化标准差
        diversity_score = (signal_diversity + confidence_diversity) / 2
        
        # 判断是否需要干预
        is_homogeneous = (len(unique_signals) == 1 and std_confidence < 0.15) or diversity_score < 0.3
        requires_intervention = is_homogeneous and len(signals) >= 2
        
        # 信号分布统计
        signal_distribution = {
            'BUY': signals_types.count('BUY'),
            'SELL': signals_types.count('SELL'),
            'HOLD': signals_types.count('HOLD')
        }
        
        # 信心统计
        confidence_stats = {
            'mean': mean_confidence,
            'std': std_confidence,
            'min': min(confidences),
            'max': max(confidences)
        }
        
        analysis = '信号高度一致' if is_homogeneous else '信号存在差异'
        
        logger.info(f"📊 【AI信号多样性分析】")
        logger.info(f"   多样性分数: {diversity_score:.2f} (0-1，越高越多样)")
        logger.info(f"   信号分布: BUY={signal_distribution['BUY']}, SELL={signal_distribution['SELL']}, HOLD={signal_distribution['HOLD']}")
        logger.info(f"   信心均值: {mean_confidence:.2f}，标准差: {std_confidence:.2f}")
        logger.info(f"   是否过度一致: {'⚠️ 是' if is_homogeneous else '✅ 否'}")
        logger.info(f"   需要干预: {'🚨 是' if requires_intervention else '✅ 否'}")
        
        if requires_intervention:
            logger.warning(f"🚨 AI信号过度一致，将启动强制干预机制")
        
        return DiversityAnalysis(
            diversity_score=diversity_score,
            is_homogeneous=is_homogeneous,
            unique_signals=unique_signals,
            signal_distribution=signal_distribution,
            confidence_stats=confidence_stats,
            analysis=analysis,
            requires_intervention=requires_intervention
        )
    
    def _intelligent_signal_fusion(self, buy_votes: int, sell_votes: int, hold_votes: int,
                                 buy_confidence: float, sell_confidence: float, hold_confidence: float,
                                 total_signals: int, market_data: Optional[Dict[str, Any]]) -> tuple:
        """智能信号融合"""
        # 计算各信号的占比
        buy_ratio = buy_votes / total_signals
        sell_ratio = sell_votes / total_signals
        hold_ratio = hold_votes / total_signals
        
        # 🚀 增强决策逻辑 - 优化加密货币市场敏感度
        majority_threshold = 0.4  # 从0.5降低到0.4，更容易达成共识
        strong_consensus_threshold = 0.6  # 从0.7降低到0.6
        weak_consensus_threshold = 0.5  # 从0.6降低到0.5
        
        # 🔥 动态信心调整
        confidence_adjustment = self._calculate_dynamic_confidence_adjustment(market_data)
        
        # 🎯 智能信号融合
        if buy_ratio >= strong_consensus_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence * confidence_adjustment['buy_multiplier']
            reason = f"强共识买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
        elif sell_ratio >= strong_consensus_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence * confidence_adjustment['sell_multiplier']
            reason = f"强共识卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
        elif hold_ratio >= strong_consensus_threshold:
            # 即使是强HOLD共识，也要考虑是否有交易机会
            if buy_ratio > 0.2 or sell_ratio > 0.2:
                # 选择信心更高的方向
                if buy_confidence > sell_confidence:
                    final_signal = 'BUY'
                    confidence = buy_confidence * 0.8
                    reason = f"HOLD共识中存在买入机会: 选择BUY方向 (信心: {confidence:.2f})"
                else:
                    final_signal = 'SELL'
                    confidence = sell_confidence * 0.8
                    reason = f"HOLD共识中存在卖出机会: 选择SELL方向 (信心: {confidence:.2f})"
            else:
                final_signal = 'HOLD'
                confidence = hold_confidence * confidence_adjustment['hold_multiplier']
                reason = f"强共识持仓: {hold_votes}/{total_signals}票支持 ({hold_ratio*100:.0f}%)"
        elif buy_ratio >= weak_consensus_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence * confidence_adjustment['buy_multiplier'] * 0.95
            reason = f"多数支持买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
        elif sell_ratio >= weak_consensus_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence * confidence_adjustment['sell_multiplier'] * 0.95
            reason = f"多数支持卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
        else:
            # 没有明显多数，但减少过度保守
            if buy_confidence > sell_confidence and buy_confidence > hold_confidence:
                final_signal = 'BUY'
                confidence = buy_confidence * 0.7
                reason = f"无明显共识但买入信心最高: 选择BUY方向 (信心: {confidence:.2f})"
            elif sell_confidence > buy_confidence and sell_confidence > hold_confidence:
                final_signal = 'SELL'
                confidence = sell_confidence * 0.7
                reason = f"无明显共识但卖出信心最高: 选择SELL方向 (信心: {confidence:.2f})"
            else:
                final_signal = 'HOLD'
                confidence = hold_confidence * confidence_adjustment['hold_multiplier']
                reason = f"无明显共识，建议观望: HOLD {hold_votes}/{total_signals}票 ({hold_ratio*100:.0f}%)"
        
        return final_signal, confidence, reason
    
    def _calculate_dynamic_confidence_adjustment(self, market_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """计算动态信心调整因子"""
        try:
            if not market_data:
                return {'buy_multiplier': 1.0, 'sell_multiplier': 1.0, 'hold_multiplier': 1.0}
            
            # 获取技术指标
            technical_data = market_data.get('technical_data', {})
            rsi = float(technical_data.get('rsi', 50))
            atr_pct = float(technical_data.get('atr_pct', 1.0))
            trend = str(market_data.get('trend_strength', '震荡'))
            
            # 基础调整因子
            buy_multiplier = 1.0
            sell_multiplier = 1.0
            hold_multiplier = 1.0
            
            # RSI-based adjustments
            if rsi < 30:  # 超卖区域
                buy_multiplier *= 1.3
                sell_multiplier *= 0.7
                hold_multiplier *= 0.8
            elif rsi > 70:  # 超买区域
                buy_multiplier *= 0.7
                sell_multiplier *= 1.3
                hold_multiplier *= 0.8
            elif 35 <= rsi <= 65:  # 中性区域
                buy_multiplier *= 1.0
                sell_multiplier *= 1.0
                hold_multiplier *= 1.1
            
            # 波动率-based adjustments
            if atr_pct < 0.5:  # 极低波动
                buy_multiplier *= 0.8
                sell_multiplier *= 0.8
                hold_multiplier *= 1.2
            elif atr_pct < 1.0:  # 低波动
                buy_multiplier *= 0.9
                sell_multiplier *= 0.9
                hold_multiplier *= 1.1
            elif atr_pct > 3.0:  # 高波动
                buy_multiplier *= 1.1
                sell_multiplier *= 1.1
                hold_multiplier *= 0.9
            
            # 趋势-based adjustments
            trend_lower = str(trend).lower()
            if 'bullish' in trend_lower or '上涨' in trend_lower:
                buy_multiplier *= 1.2
                sell_multiplier *= 0.8
                hold_multiplier *= 0.9
            elif 'bearish' in trend_lower or '下跌' in trend_lower:
                buy_multiplier *= 0.8
                sell_multiplier *= 1.2
                hold_multiplier *= 0.9
            elif '震荡' in trend_lower or 'consolidation' in trend_lower:
                buy_multiplier *= 0.9
                sell_multiplier *= 0.9
                hold_multiplier *= 1.3
            
            # 确保调整因子在合理范围内
            buy_multiplier = max(0.5, min(1.5, buy_multiplier))
            sell_multiplier = max(0.5, min(1.5, sell_multiplier))
            hold_multiplier = max(0.5, min(1.5, hold_multiplier))
            
            logger.info(f"📊 动态信心调整: BUY×{buy_multiplier:.2f}, SELL×{sell_multiplier:.2f}, HOLD×{hold_multiplier:.2f}")
            
            return {
                'buy_multiplier': buy_multiplier,
                'sell_multiplier': sell_multiplier,
                'hold_multiplier': hold_multiplier
            }
            
        except Exception as e:
            logger.error(f"动态信心调整计算失败: {e}")
            return {'buy_multiplier': 1.0, 'sell_multiplier': 1.0, 'hold_multiplier': 1.0}
    
    def _apply_diversity_intervention(self, signals: List[AISignal], market_data: Dict[str, Any]) -> SignalFusionResult:
        """应用多样性干预"""
        try:
            import random
            
            # 获取当前一致的信号类型
            current_signal = signals[0].signal
            available_signals = ['BUY', 'SELL', 'HOLD']
            available_signals.remove(current_signal)
            
            # 选择1个信号进行强制类型改变
            signal_to_change = random.choice(signals)
            new_signal = random.choice(available_signals)
            
            logger.info(f"🔄 强制干预: 将{signal_to_change.provider}的信号从{signal_to_change.signal}改为{new_signal}")
            
            # 改变信号类型并调整信心值
            signal_to_change.signal = new_signal
            signal_to_change.confidence = max(0.4, min(0.8, signal_to_change.confidence * random.uniform(0.8, 1.2)))
            
            logger.info(f"🔄 干预后信心值: {signal_to_change.confidence:.2f}")
            
            # 重新融合调整后的信号
            logger.info(f"🔄 重新融合强制干预后的信号...")
            return self.fuse_signals(signals, market_data)
            
        except Exception as e:
            logger.error(f"多样性干预失败: {e}")
            # 回退到原始融合结果
            return self.fuse_signals(signals, market_data)
    
    def _generate_smart_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成智能回退信号"""
        try:
            logger.info("📊 使用智能技术回退信号")
            
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
                'fallback_type': 'enhanced_technical'
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
                'fallback_type': 'error'
            }
    
    def _calculate_rsi_factor(self, rsi: float, price_position: float) -> Dict[str, Any]:
        """计算RSI因子"""
        try:
            if rsi < 30:  # 超卖
                rsi_score = -0.8  # 买入信号为负分
                confidence = 0.8
            elif rsi > 70:  # 超买
                rsi_score = 0.8  # 卖出信号为正分
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
            
            # 获取MACD数据
            macd_line = float(macd.get('macd', 0))
            signal_line = float(macd.get('signal', 0))
            
            score = 0.0
            confidence = 0.6
            
            # MACD金叉/死叉判断
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
            
            # 解析均线状态
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
            
            # 获取布林带数据
            upper_band = float(bollinger.get('upper', 0))
            lower_band = float(bollinger.get('lower', 0))
            
            if upper_band <= lower_band:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
            
            score = 0.0
            confidence = 0.6
            
            # 计算价格在布林带中的位置
            band_range = upper_band - lower_band
            if band_range > 0:
                price_position_in_band = (current_price - lower_band) / band_range
                
                # 布林带交易策略
                if price_position_in_band < 0.2:  # 靠近下轨
                    score = -0.7
                    confidence = 0.8
                elif price_position_in_band > 0.8:  # 靠近上轨
                    score = 0.7
                    confidence = 0.8
                elif 0.4 <= price_position_in_band <= 0.6:  # 靠近中轨
                    score = 0.0
                    confidence = 0.4
                else:
                    # 中间区域
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
            
            # 成交量比率分析
            if volume_ratio > 2.0:  # 成交量放大2倍以上
                score = 0.0
                confidence = 0.7
            elif volume_ratio > 1.5:  # 成交量放大1.5倍以上
                score = 0.0
                confidence = 0.6
            elif volume_ratio < 0.5:  # 成交量萎缩50%以上
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
            
            # 获取支撑阻力位
            support = float(sr_data.get('support', 0))
            resistance = float(sr_data.get('resistance', 0))
            
            if support <= 0 or resistance <= 0 or support >= resistance:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
            
            score = 0.0
            confidence = 0.7
            
            # 计算与支撑阻力的距离
            support_distance = abs(current_price - support) / current_price * 100
            resistance_distance = abs(current_price - resistance) / current_price * 100
            
            # 支撑阻力策略
            if support_distance < 1.0:  # 靠近支撑位
                score = -0.8
                confidence = 0.9
            elif resistance_distance < 1.0:  # 靠近阻力位
                score = 0.8
                confidence = 0.9
            elif support_distance < 2.0:  # 接近支撑位
                score = -0.5
                confidence = 0.7
            elif resistance_distance < 2.0:  # 接近阻力位
                score = 0.5
                confidence = 0.7
            else:
                # 在中间区域
                total_range = resistance - support
                if total_range > 0:
                    position_in_range = (current_price - support) / total_range
                    if position_in_range < 0.3:  # 靠近支撑
                        score = -0.3
                    elif position_in_range > 0.7:  # 靠近阻力
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
            
            # 波动率分析
            volatility_lower = str(volatility).lower()
            if 'high' in volatility_lower or '高' in volatility_lower:
                confidence *= 0.8
            elif 'low' in volatility_lower or '低' in volatility_lower:
                confidence *= 1.0
            else:
                confidence *= 0.9
            
            # 趋势分析
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
            if signal_score <= -0.5:  # 强买入信号
                return 'BUY'
            elif signal_score >= 0.5:  # 强卖出信号
                return 'SELL'
            elif -0.2 <= signal_score <= 0.2:  # 中性区域
                return 'HOLD'
            elif signal_score < -0.2:  # 弱买入信号
                return 'BUY'
            else:  # 弱卖出信号
                return 'SELL'
                
        except Exception as e:
            logger.error(f"信号得分转换失败: {e}")
            return 'HOLD'
    
    def _calculate_weighted_confidence(self, confidence_factors: List[float], signal_score: float) -> float:
        """计算加权信心值"""
        try:
            if not confidence_factors:
                return 0.5
            
            # 计算加权平均信心
            avg_confidence = sum(confidence_factors) / len(confidence_factors)
            
            # 基于信号强度调整信心值
            signal_strength = abs(signal_score)
            if signal_strength > 0.7:
                confidence_multiplier = 1.1
            elif signal_strength > 0.4:
                confidence_multiplier = 1.0
            else:
                confidence_multiplier = 0.8
            
            # 基于因子一致性调整信心值
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
            
            # 确保信心值在合理范围内
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
            
            # 信号概述
            if signal == 'BUY':
                reason_parts.append(f"多因子分析显示买入信号(得分: {signal_score:.2f})")
            elif signal == 'SELL':
                reason_parts.append(f"多因子分析显示卖出信号(得分: {signal_score:.2f})")
            else:
                reason_parts.append(f"多因子分析显示观望信号(得分: {signal_score:.2f})")
            
            # RSI分析
            if rsi < 30:
                reason_parts.append(f"RSI超卖({rsi:.1f})")
            elif rsi > 70:
                reason_parts.append(f"RSI超买({rsi:.1f})")
            elif 30 <= rsi <= 70:
                reason_parts.append(f"RSI中性({rsi:.1f})")
            
            # MACD分析
            if macd and isinstance(macd, dict):
                macd_line = float(macd.get('macd', 0))
                signal_line = float(macd.get('signal', 0))
                if macd_line > signal_line:
                    reason_parts.append("MACD金叉")
                else:
                    reason_parts.append("MACD死叉")
            
            # 布林带分析
            if bollinger and isinstance(bollinger, dict):
                upper = float(bollinger.get('upper', 0))
                lower = float(bollinger.get('lower', 0))
                if upper > lower:
                    band_position = (current_price - lower) / (upper - lower)
                    if band_position < 0.2:
                        reason_parts.append("价格靠近布林带下轨")
                    elif band_position > 0.8:
                        reason_parts.append("价格靠近布林带上轨")
            
            # 支撑阻力分析
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
            
            # 市场环境
            if 'high' in str(volatility).lower():
                reason_parts.append("高波动环境")
            elif 'low' in str(volatility).lower():
                reason_parts.append("低波动环境")
            
            # 价格位置
            if price_position < 30:
                reason_parts.append("价格处于相对低位")
            elif price_position > 70:
                reason_parts.append("价格处于相对高位")
            
            # 信心水平
            avg_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
            if avg_confidence > 0.7:
                reason_parts.append("高信心水平")
            elif avg_confidence > 0.5:
                reason_parts.append("中等信心水平")
            else:
                reason_parts.append("低信心水平")
            
            # 组合最终理由
            if reason_parts:
                return "；".join(reason_parts) + "。"
            else:
                return "基于多因子技术分析的综合判断"
                
        except Exception as e:
            logger.error(f"增强理由生成失败: {e}")
            return "基于技术指标的智能回退信号"
    
    def _generate_detailed_signal_statistics(self, signals: List[AISignal]) -> SignalStatistics:
        """生成详细的信号统计"""
        try:
            if not signals:
                return SignalStatistics(
                    total_signals=0,
                    signal_distribution={'BUY': 0, 'SELL': 0, 'HOLD': 0},
                    confidence_stats={'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0},
                    provider_breakdown={},
                    quality_score=0.0,
                    diversity_index=0.0,
                    consensus_level=0.0
                )
            
            # 信号分布统计
            signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            provider_breakdown = {}
            confidences = []
            
            for signal in signals:
                # 统计信号类型
                signal_counts[signal.signal] += 1
                
                # 统计提供商表现
                if signal.provider not in provider_breakdown:
                    provider_breakdown[signal.provider] = {
                        'signal': signal.signal,
                        'confidence': signal.confidence,
                        'reason': signal.reason[:100] + '...' if len(signal.reason) > 100 else signal.reason,
                        'timestamp': signal.timestamp
                    }
                
                # 收集信心值
                confidences.append(signal.confidence)
            
            # 信心值统计
            if confidences:
                confidence_mean = sum(confidences) / len(confidences)
                if len(confidences) > 1:
                    variance = sum((c - confidence_mean) ** 2 for c in confidences) / len(confidences)
                    confidence_std = variance ** 0.5
                else:
                    confidence_std = 0.0
                confidence_min = min(confidences)
                confidence_max = max(confidences)
            else:
                confidence_mean = confidence_std = confidence_min = confidence_max = 0.0
            
            # 计算信号质量评分
            quality_score = self._calculate_signal_quality(signals, confidence_mean, confidence_std)
            
            # 计算多样性指数
            diversity_index = self._calculate_diversity_index(signal_counts)
            
            # 计算共识水平
            consensus_level = self._calculate_consensus_level(signal_counts)
            
            return SignalStatistics(
                total_signals=len(signals),
                signal_distribution=signal_counts,
                confidence_stats={
                    'mean': confidence_mean,
                    'std': confidence_std,
                    'min': confidence_min,
                    'max': confidence_max
                },
                provider_breakdown=provider_breakdown,
                quality_score=quality_score,
                diversity_index=diversity_index,
                consensus_level=consensus_level
            )
            
        except Exception as e:
            logger.error(f"详细信号统计生成失败: {e}")
            return SignalStatistics(
                total_signals=len(signals) if 'signals' in locals() else 0,
                signal_distribution={'BUY': 0, 'SELL': 0, 'HOLD': 0},
                confidence_stats={'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0},
                provider_breakdown={},
                quality_score=0.0,
                diversity_index=0.0,
                consensus_level=0.0
            )
    
    def _calculate_signal_quality(self, signals: List[AISignal], confidence_mean: float, confidence_std: float) -> float:
        """计算信号质量评分"""
        try:
            if not signals:
                return 0.0
            
            # 基础质量 = 平均信心值
            base_quality = confidence_mean
            
            # 一致性奖励
            consistency_bonus = max(0, 1.0 - confidence_std) * 0.2
            
            # 多样性奖励
            unique_signals = len(set(s.signal for s in signals))
            diversity_bonus = (unique_signals / 3.0) * 0.1
            
            # 提供商数量奖励
            unique_providers = len(set(s.provider for s in signals))
            provider_bonus = min(unique_providers / 4.0, 0.1) * 0.1
            
            total_quality = base_quality + consistency_bonus + diversity_bonus + provider_bonus
            
            return min(total_quality, 1.0)
            
        except Exception as e:
            logger.error(f"信号质量计算失败: {e}")
            return 0.5
    
    def _calculate_diversity_index(self, signal_counts: Dict[str, int]) -> float:
        """计算信号多样性指数"""
        try:
            total = sum(signal_counts.values())
            if total == 0:
                return 0.0
            
            # 使用香农多样性指数
            diversity = 0.0
            for count in signal_counts.values():
                if count > 0:
                    proportion = count / total
                    diversity -= proportion * (proportion ** 0.5)
            
            return min(diversity * 3.0, 1.0)
            
        except Exception as e:
            logger.error(f"多样性指数计算失败: {e}")
            return 0.0
    
    def _calculate_consensus_level(self, signal_counts: Dict[str, int]) -> float:
        """计算共识水平"""
        try:
            total = sum(signal_counts.values())
            if total == 0:
                return 0.0
            
            # 找到最大共识度
            max_count = max(signal_counts.values())
            consensus_level = max_count / total
            
            return consensus_level
            
        except Exception as e:
            logger.error(f"共识水平计算失败: {e}")
            return 0.0
    
    def _generate_enhanced_fusion_analysis(self, successful_providers: int, total_configured: int, fusion_reason: str) -> Dict[str, Any]:
        """生成增强的融合分析统计"""
        try:
            # 计算修正的成功率
            success_rate = successful_providers / total_configured if total_configured > 0 else 0.0
            
            # 部分成功状态判断
            partial_success = 0 < successful_providers < total_configured
            
            # 成功级别分类
            if successful_providers == 0:
                success_level = 'complete_failure'
            elif successful_providers == total_configured:
                success_level = 'complete_success'
            elif successful_providers >= total_configured * 0.75:
                success_level = 'high_partial_success'
            elif successful_providers >= total_configured * 0.5:
                success_level = 'medium_partial_success'
            elif successful_providers >= total_configured * 0.25:
                success_level = 'low_partial_success'
            else:
                success_level = 'minimal_success'
            
            return {
                'total_providers': total_configured,
                'successful_providers': successful_providers,
                'failed_providers': total_configured - successful_providers,
                'success_rate': success_rate,
                'success_rate_percentage': success_rate * 100,
                'success_level': success_level,
                'partial_success': partial_success,
                'fusion_reason': fusion_reason,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"增强融合分析生成失败: {e}")
            return {
                'total_providers': total_configured,
                'successful_providers': successful_providers,
                'failed_providers': total_configured - successful_providers,
                'success_rate': success_rate if 'success_rate' in locals() else 0.0,
                'fusion_reason': fusion_reason,
                'error': str(e)
            }
"""
市场情绪分析模块
分析市场情绪并生成情绪指标
"""

import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from core.base import BaseComponent, BaseConfig
from core.exceptions import StrategyError

logger = logging.getLogger(__name__)

@dataclass
class SentimentAnalysisResult:
    """情绪分析结果"""
    overall_sentiment: float  # -1.0 到 1.0
    confidence_score: float   # 0.0 到 1.0
    sentiment_momentum: float  # 情绪动量
    fear_greed_index: float   # 恐慌贪婪指数 (0-100)
    sentiment_breakdown: Dict[str, float]
    market_condition: str
    recommendation: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_sentiment': self.overall_sentiment,
            'confidence_score': self.confidence_score,
            'sentiment_momentum': self.sentiment_momentum,
            'fear_greed_index': self.fear_greed_index,
            'sentiment_breakdown': self.sentiment_breakdown,
            'market_condition': self.market_condition,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }

class MarketSentimentAnalyzer(BaseComponent):
    """市场情绪分析器"""
    
    def __init__(self, config: Optional[BaseConfig] = None):
        super().__init__(config or BaseConfig(name="MarketSentimentAnalyzer"))
        self.sentiment_history: List[SentimentAnalysisResult] = []
        self.fear_greed_history: List[float] = []
    
    async def initialize(self) -> bool:
        """初始化情绪分析器"""
        try:
            logger.info("📊 市场情绪分析器初始化...")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"市场情绪分析器初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        self.sentiment_history.clear()
        self.fear_greed_history.clear()
        self._initialized = False
        logger.info("🛑 市场情绪分析器已清理")
    
    async def calculate_comprehensive_market_sentiment(self, market_data: Dict[str, Any] = None) -> SentimentAnalysisResult:
        """计算综合市场情绪"""
        try:
            logger.info("🔍 开始综合市场情绪分析...")
            
            # 1. 基于技术指标的情绪分析
            technical_sentiment = await self._analyze_technical_sentiment(market_data)
            
            # 2. 基于价格行为的情绪分析
            price_sentiment = await self._analyze_price_sentiment(market_data)
            
            # 3. 基于波动率的情绪分析
            volatility_sentiment = await self._analyze_volatility_sentiment(market_data)
            
            # 4. 基于交易量的情绪分析
            volume_sentiment = await self._analyze_volume_sentiment(market_data)
            
            # 5. 计算恐慌贪婪指数
            fear_greed_index = self._calculate_fear_greed_index(market_data)
            
            # 6. 综合所有情绪指标
            overall_sentiment = self._combine_sentiment_indicators({
                'technical': technical_sentiment,
                'price': price_sentiment,
                'volatility': volatility_sentiment,
                'volume': volume_sentiment
            })
            
            # 7. 计算情绪动量
            sentiment_momentum = self._calculate_sentiment_momentum(overall_sentiment)
            
            # 8. 生成市场条件判断
            market_condition = self._determine_market_condition(overall_sentiment, fear_greed_index)
            
            # 9. 生成建议
            recommendation = self._generate_sentiment_recommendation(overall_sentiment, market_condition)
            
            # 10. 计算置信度
            confidence_score = self._calculate_sentiment_confidence({
                'technical': technical_sentiment,
                'price': price_sentiment,
                'volatility': volatility_sentiment,
                'volume': volume_sentiment
            })
            
            result = SentimentAnalysisResult(
                overall_sentiment=overall_sentiment,
                confidence_score=confidence_score,
                sentiment_momentum=sentiment_momentum,
                fear_greed_index=fear_greed_index,
                sentiment_breakdown={
                    'technical_sentiment': technical_sentiment,
                    'price_sentiment': price_sentiment,
                    'volatility_sentiment': volatility_sentiment,
                    'volume_sentiment': volume_sentiment
                },
                market_condition=market_condition,
                recommendation=recommendation,
                timestamp=datetime.now()
            )
            
            # 记录历史
            self.sentiment_history.append(result)
            self.fear_greed_history.append(fear_greed_index)
            
            # 保持历史记录在合理范围内
            if len(self.sentiment_history) > 1000:
                self.sentiment_history = self.sentiment_history[-500:]
            if len(self.fear_greed_history) > 1000:
                self.fear_greed_history = self.fear_greed_history[-500:]
            
            logger.info(f"✅ 市场情绪分析完成: 综合情绪 {overall_sentiment:.3f}, 恐慌贪婪指数 {fear_greed_index:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"综合市场情绪分析失败: {e}")
            return self._get_default_sentiment_result()
    
    async def _analyze_technical_sentiment(self, market_data: Optional[Dict[str, Any]]) -> float:
        """基于技术指标分析情绪"""
        try:
            if not market_data:
                return 0.0
            
            technical_data = market_data.get('technical_data', {})
            
            # RSI情绪 (超买=悲观，超卖=乐观)
            rsi = technical_data.get('rsi', 50)
            rsi_sentiment = self._rsi_to_sentiment(rsi)
            
            # MACD情绪
            macd = technical_data.get('macd', {})
            macd_sentiment = self._macd_to_sentiment(macd)
            
            # 均线情绪
            ma_short = technical_data.get('ma_short', 0)
            ma_long = technical_data.get('ma_long', 0)
            current_price = market_data.get('price', 0)
            ma_sentiment = self._ma_to_sentiment(current_price, ma_short, ma_long)
            
            # 综合技术指标情绪
            technical_sentiment = (rsi_sentiment * 0.4 + macd_sentiment * 0.3 + ma_sentiment * 0.3)
            
            return max(-1.0, min(1.0, technical_sentiment))
            
        except Exception as e:
            logger.error(f"技术指标情绪分析失败: {e}")
            return 0.0
    
    def _rsi_to_sentiment(self, rsi: float) -> float:
        """将RSI转换为情绪值"""
        try:
            if rsi < 30:  # 超卖 - 乐观
                return 0.8
            elif rsi < 40:  # 弱势 - 轻微乐观
                return 0.4
            elif rsi > 70:  # 超买 - 悲观
                return -0.8
            elif rsi > 60:  # 强势 - 轻微悲观
                return -0.4
            else:  # 中性
                return 0.0
            
        except Exception as e:
            logger.error(f"RSI转情绪失败: {e}")
            return 0.0
    
    def _macd_to_sentiment(self, macd: Dict[str, Any]) -> float:
        """将MACD转换为情绪值"""
        try:
            if not macd or not isinstance(macd, dict):
                return 0.0
            
            macd_line = macd.get('macd', 0)
            signal_line = macd.get('signal', 0)
            histogram = macd.get('histogram', 0)
            
            sentiment = 0.0
            
            # MACD金叉/死叉
            if macd_line > signal_line and macd_line > 0:
                sentiment = 0.6  # 强势看涨
            elif macd_line < signal_line and macd_line < 0:
                sentiment = -0.6  # 强势看跌
            elif macd_line > signal_line and macd_line < 0:
                sentiment = 0.3  # 弱势看涨
            elif macd_line < signal_line and macd_line > 0:
                sentiment = -0.3  # 弱势看跌
            
            # 柱状图强度
            if abs(histogram) > 0:
                histogram_strength = min(abs(histogram) / 10, 1.0)  # 标准化
                sentiment *= (1 + histogram_strength * 0.2)  # 最多增强20%
            
            return max(-1.0, min(1.0, sentiment))
            
        except Exception as e:
            logger.error(f"MACD转情绪失败: {e}")
            return 0.0
    
    def _ma_to_sentiment(self, current_price: float, ma_short: float, ma_long: float) -> float:
        """将均线转换为情绪值"""
        try:
            if ma_short <= 0 or ma_long <= 0:
                return 0.0
            
            sentiment = 0.0
            
            # 多头排列
            if current_price > ma_short > ma_long:
                sentiment = 0.7
            # 空头排列
            elif current_price < ma_short < ma_long:
                sentiment = -0.7
            # 价格相对均线位置
            else:
                if current_price > ma_short:
                    sentiment = 0.3
                elif current_price < ma_short:
                    sentiment = -0.3
            
            return max(-1.0, min(1.0, sentiment))
            
        except Exception as e:
            logger.error(f"均线转情绪失败: {e}")
            return 0.0
    
    async def _analyze_price_sentiment(self, market_data: Optional[Dict[str, Any]]) -> float:
        """基于价格行为分析情绪"""
        try:
            if not market_data:
                return 0.0
            
            price_history = market_data.get('price_history', [])
            if len(price_history) < 10:
                return 0.0
            
            # 计算价格动量
            recent_prices = price_history[-10:]
            momentum = self._calculate_price_momentum(recent_prices)
            
            # 计算价格位置（相对历史高低）
            price_position = self._calculate_price_position(recent_prices, price_history)
            
            # 计算价格趋势强度
            trend_strength = self._calculate_trend_strength(recent_prices)
            
            # 综合价格情绪
            price_sentiment = (momentum * 0.4 + price_position * 0.3 + trend_strength * 0.3)
            
            return max(-1.0, min(1.0, price_sentiment))
            
        except Exception as e:
            logger.error(f"价格行为情绪分析失败: {e}")
            return 0.0
    
    def _calculate_price_momentum(self, recent_prices: List[float]) -> float:
        """计算价格动量"""
        try:
            if len(recent_prices) < 5:
                return 0.0
            
            # 计算短期动量
            short_momentum = (recent_prices[-1] - recent_prices[-5]) / recent_prices[-5]
            
            # 标准化到[-1, 1]范围
            momentum_sentiment = max(-1.0, min(1.0, short_momentum * 20))  # 放大系数
            
            return momentum_sentiment
            
        except Exception as e:
            logger.error(f"计算价格动量失败: {e}")
            return 0.0
    
    def _calculate_price_position(self, recent_prices: List[float], full_history: List[float]) -> float:
        """计算价格相对位置"""
        try:
            if len(full_history) < 20:
                return 0.0
            
            current_price = recent_prices[-1]
            
            # 计算相对历史高低位置
            recent_high = max(full_history[-20:])
            recent_low = min(full_history[-20:])
            
            if recent_high > recent_low:
                position = (current_price - recent_low) / (recent_high - recent_low)
                # 转换为情绪值 (高位=悲观，低位=乐观)
                position_sentiment = -2.0 * position + 1.0  # [1, -1]
                return max(-1.0, min(1.0, position_sentiment))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算价格位置失败: {e}")
            return 0.0
    
    def _calculate_trend_strength(self, recent_prices: List[float]) -> float:
        """计算趋势强度"""
        try:
            if len(recent_prices) < 10:
                return 0.0
            
            # 线性回归计算趋势
            x = np.arange(len(recent_prices))
            y = np.array(recent_prices)
            
            # 计算斜率
            slope, _ = np.polyfit(x, y, 1)
            
            # 标准化斜率
            price_std = np.std(y)
            trend_strength = slope / (price_std + 1e-6) if price_std > 0 else 0
            
            # 限制范围
            return max(-1.0, min(1.0, trend_strength * 100))  # 放大系数
            
        except Exception as e:
            logger.error(f"计算趋势强度失败: {e}")
            return 0.0
    
    async def _analyze_volatility_sentiment(self, market_data: Optional[Dict[str, Any]]) -> float:
        """基于波动率分析情绪"""
        try:
            if not market_data:
                return 0.0
            
            technical_data = market_data.get('technical_data', {})
            atr_pct = technical_data.get('atr_pct', 2.0)
            
            # 波动率情绪映射
            if atr_pct < 1.0:  # 低波动 - 稳定乐观
                return 0.3
            elif atr_pct < 2.0:  # 正常波动 - 中性
                return 0.0
            elif atr_pct < 3.0:  # 中等波动 - 轻微悲观
                return -0.2
            else:  # 高波动 - 悲观
                return -0.6
            
        except Exception as e:
            logger.error(f"波动率情绪分析失败: {e}")
            return 0.0
    
    async def _analyze_volume_sentiment(self, market_data: Optional[Dict[str, Any]]) -> float:
        """基于交易量分析情绪"""
        try:
            if not market_data:
                return 0.0
            
            # 这里应该获取实际的交易量数据
            # 现在使用简化的逻辑
            price_history = market_data.get('price_history', [])
            if len(price_history) < 10:
                return 0.0
            
            # 计算价格变化与预期成交量的关系
            recent_prices = price_history[-10:]
            price_changes = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] 
                           for i in range(1, len(recent_prices))]
            
            # 价格上涨伴随预期成交量增加 = 乐观
            # 价格下跌伴随预期成交量增加 = 悲观
            avg_price_change = np.mean(price_changes)
            
            if avg_price_change > 0.005:  # 显著上涨
                return 0.4
            elif avg_price_change < -0.005:  # 显著下跌
                return -0.4
            else:
                return 0.0
            
        except Exception as e:
            logger.error(f"交易量情绪分析失败: {e}")
            return 0.0
    
    def _calculate_fear_greed_index(self, market_data: Optional[Dict[str, Any]]) -> float:
        """计算恐慌贪婪指数 (0-100)"""
        try:
            if not market_data:
                return 50.0  # 中性
            
            # 基于多个因素计算恐慌贪婪指数
            factors = []
            
            # 1. 技术指标因素 (25%)
            technical_data = market_data.get('technical_data', {})
            rsi = technical_data.get('rsi', 50)
            technical_factor = self._rsi_to_fear_greed(rsi)
            factors.append(technical_factor * 0.25)
            
            # 2. 价格动量因素 (25%)
            price_history = market_data.get('price_history', [])
            if len(price_history) >= 7:
                recent_performance = (price_history[-1] - price_history[-7]) / price_history[-7]
                momentum_factor = max(0, min(100, (recent_performance + 0.1) * 500))  # 标准化
                factors.append(momentum_factor * 0.25)
            else:
                factors.append(50.0 * 0.25)  # 中性
            
            # 3. 波动率因素 (25%)
            atr_pct = technical_data.get('atr_pct', 2.0)
            volatility_factor = self._volatility_to_fear_greed(atr_pct)
            factors.append(volatility_factor * 0.25)
            
            # 4. 趋势强度因素 (25%)
            trend_analysis = market_data.get('trend_analysis', {})
            trend_strength = trend_analysis.get('strength', 0.0)
            trend_factor = max(0, min(100, (trend_strength + 1.0) * 50))  # 标准化
            factors.append(trend_factor * 0.25)
            
            # 综合计算
            fear_greed_index = sum(factors)
            
            # 基于历史数据调整
            if self.fear_greed_history:
                recent_avg = np.mean(self.fear_greed_history[-10:])
                # 平滑处理
                fear_greed_index = fear_greed_index * 0.7 + recent_avg * 0.3
            
            return max(0, min(100, fear_greed_index))
            
        except Exception as e:
            logger.error(f"计算恐慌贪婪指数失败: {e}")
            return 50.0
    
    def _rsi_to_fear_greed(self, rsi: float) -> float:
        """将RSI转换为恐慌贪婪指数"""
        try:
            # RSI转换: 超卖=极度恐慌(0)，超买=极度贪婪(100)
            if rsi < 20:
                return 0.0  # 极度恐慌
            elif rsi < 30:
                return 25.0  # 恐慌
            elif rsi < 40:
                return 40.0  # 轻微恐慌
            elif rsi > 80:
                return 100.0  # 极度贪婪
            elif rsi > 70:
                return 75.0  # 贪婪
            elif rsi > 60:
                return 60.0  # 轻微贪婪
            else:
                return 50.0  # 中性
            
        except Exception as e:
            logger.error(f"RSI转恐慌贪婪失败: {e}")
            return 50.0
    
    def _volatility_to_fear_greed(self, atr_pct: float) -> float:
        """将波动率转换为恐慌贪婪指数"""
        try:
            # 波动率转换: 低波动=贪婪(100)，高波动=恐慌(0)
            if atr_pct < 1.0:
                return 80.0  # 低波动 = 贪婪
            elif atr_pct < 2.0:
                return 60.0  # 正常波动 = 轻微贪婪
            elif atr_pct < 3.0:
                return 40.0  # 中等波动 = 轻微恐慌
            else:
                return 20.0  # 高波动 = 恐慌
            
        except Exception as e:
            logger.error(f"波动率转恐慌贪婪失败: {e}")
            return 50.0
    
    def _combine_sentiment_indicators(self, indicators: Dict[str, float]) -> float:
        """综合情绪指标"""
        try:
            # 加权平均
            weights = {
                'technical': 0.35,
                'price': 0.25,
                'volatility': 0.20,
                'volume': 0.20
            }
            
            combined_sentiment = 0.0
            total_weight = 0.0
            
            for indicator, value in indicators.items():
                if indicator in weights:
                    combined_sentiment += value * weights[indicator]
                    total_weight += weights[indicator]
            
            if total_weight > 0:
                combined_sentiment /= total_weight
            
            return max(-1.0, min(1.0, combined_sentiment))
            
        except Exception as e:
            logger.error(f"综合情绪指标失败: {e}")
            return 0.0
    
    def _calculate_sentiment_momentum(self, current_sentiment: float) -> float:
        """计算情绪动量"""
        try:
            if len(self.sentiment_history) < 2:
                return 0.0
            
            # 获取最近的情绪值
            recent_sentiments = [s.overall_sentiment for s in self.sentiment_history[-5:]]
            
            if len(recent_sentiments) < 2:
                return 0.0
            
            # 计算情绪变化率
            sentiment_changes = []
            for i in range(1, len(recent_sentiments)):
                change = recent_sentiments[i] - recent_sentiments[i-1]
                sentiment_changes.append(change)
            
            # 平均变化率
            avg_change = np.mean(sentiment_changes)
            
            # 标准化到[-1, 1]范围
            momentum = max(-1.0, min(1.0, avg_change * 10))  # 放大系数
            
            return momentum
            
        except Exception as e:
            logger.error(f"计算情绪动量失败: {e}")
            return 0.0
    
    def _determine_market_condition(self, overall_sentiment: float, fear_greed_index: float) -> str:
        """确定市场条件"""
        try:
            # 基于情绪和恐慌贪婪指数判断市场条件
            if overall_sentiment > 0.5 and fear_greed_index > 70:
                return 'extreme_greed'
            elif overall_sentiment > 0.3 and fear_greed_index > 60:
                return 'greed'
            elif overall_sentiment < -0.5 and fear_greed_index < 30:
                return 'extreme_fear'
            elif overall_sentiment < -0.3 and fear_greed_index < 40:
                return 'fear'
            elif abs(overall_sentiment) < 0.2 and 40 <= fear_greed_index <= 60:
                return 'neutral'
            elif overall_sentiment > 0:
                return 'optimism'
            else:
                return 'pessimism'
                
        except Exception as e:
            logger.error(f"确定市场条件失败: {e}")
            return 'unknown'
    
    def _generate_sentiment_recommendation(self, overall_sentiment: float, market_condition: str) -> str:
        """生成情绪建议"""
        try:
            if market_condition == 'extreme_greed':
                if overall_sentiment > 0.7:
                    return "市场极度贪婪，建议谨慎，考虑减仓"
                else:
                    return "市场情绪过热，建议观望"
                    
            elif market_condition == 'extreme_fear':
                if overall_sentiment < -0.7:
                    return "市场极度恐慌，可能是买入机会"
                else:
                    return "市场情绪过冷，建议等待反弹信号"
                    
            elif market_condition == 'greed':
                return "市场贪婪，保持谨慎，关注风险"
                
            elif market_condition == 'fear':
                return "市场恐慌，关注价值投资机会"
                
            elif market_condition == 'optimism':
                return "市场乐观，可以适度参与"
                
            elif market_condition == 'pessimism':
                return "市场悲观，等待转机"
                
            else:  # neutral
                return "市场情绪中性，按技术分析操作"
                
        except Exception as e:
            logger.error(f"生成情绪建议失败: {e}")
            return "情绪分析失败，建议观望"
    
    def _calculate_sentiment_confidence(self, indicators: Dict[str, float]) -> float:
        """计算情绪置信度"""
        try:
            # 基于指标一致性计算置信度
            values = list(indicators.values())
            
            if not values:
                return 0.5
            
            # 计算标准差 (一致性)
            mean_value = np.mean(values)
            std_value = np.std(values)
            
            # 一致性越高，置信度越高
            consistency = max(0, 1.0 - std_value)
            
            # 基于指标数量调整
            data_completeness = len([v for v in values if v != 0]) / len(values)
            
            # 基于历史稳定性调整
            stability_factor = 0.8  # 简化处理
            if self.sentiment_history:
                recent_stability = self._calculate_recent_stability()
                stability_factor = recent_stability
            
            confidence = (consistency * 0.5 + data_completeness * 0.3 + stability_factor * 0.2)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"计算情绪置信度失败: {e}")
            return 0.5
    
    def _calculate_recent_stability(self) -> float:
        """计算近期稳定性"""
        try:
            if len(self.sentiment_history) < 5:
                return 0.8
            
            recent_sentiments = [s.overall_sentiment for s in self.sentiment_history[-5:]]
            
            # 计算变化率的标准差
            changes = []
            for i in range(1, len(recent_sentiments)):
                change = abs(recent_sentiments[i] - recent_sentiments[i-1])
                changes.append(change)
            
            if not changes:
                return 0.8
            
            avg_change = np.mean(changes)
            
            # 变化越小，稳定性越高
            stability = max(0, 1.0 - avg_change * 5)  # 放大系数
            
            return stability
            
        except Exception as e:
            logger.error(f"计算近期稳定性失败: {e}")
            return 0.8
    
    def _get_default_sentiment_result(self) -> SentimentAnalysisResult:
        """获取默认情绪分析结果"""
        now = datetime.now()
        return SentimentAnalysisResult(
            overall_sentiment=0.0,
            confidence_score=0.5,
            sentiment_momentum=0.0,
            fear_greed_index=50.0,
            sentiment_breakdown={
                'technical_sentiment': 0.0,
                'price_sentiment': 0.0,
                'volatility_sentiment': 0.0,
                'volume_sentiment': 0.0
            },
            market_condition='neutral',
            recommendation='情绪分析失败，建议基于技术分析操作',
            timestamp=now
        )
    
    def get_sentiment_trend(self, period: int = 10) -> Dict[str, Any]:
        """获取情绪趋势"""
        try:
            if len(self.sentiment_history) < period:
                return {'error': '历史数据不足'}
            
            recent_sentiments = self.sentiment_history[-period:]
            
            # 计算趋势
            sentiment_values = [s.overall_sentiment for s in recent_sentiments]
            fear_greed_values = [s.fear_greed_index for s in recent_sentiments]
            
            # 线性趋势
            x = np.arange(len(sentiment_values))
            sentiment_slope, _ = np.polyfit(x, sentiment_values, 1)
            fear_greed_slope, _ = np.polyfit(x, fear_greed_values, 1)
            
            # 计算变化
            sentiment_change = sentiment_values[-1] - sentiment_values[0]
            fear_greed_change = fear_greed_values[-1] - fear_greed_values[0]
            
            return {
                'period': period,
                'sentiment_trend': 'improving' if sentiment_slope > 0.01 else 'declining' if sentiment_slope < -0.01 else 'stable',
                'fear_greed_trend': 'increasing' if fear_greed_slope > 1 else 'decreasing' if fear_greed_slope < -1 else 'stable',
                'sentiment_change': sentiment_change,
                'fear_greed_change': fear_greed_change,
                'sentiment_slope': sentiment_slope,
                'fear_greed_slope': fear_greed_slope,
                'stability': 1.0 - abs(sentiment_slope) * 10  # 稳定性指标
            }
            
        except Exception as e:
            logger.error(f"获取情绪趋势失败: {e}")
            return {'error': str(e)}
    
    def get_extreme_sentiment_alerts(self) -> List[Dict[str, Any]]:
        """获取极端情绪警报"""
        try:
            alerts = []
            
            if len(self.sentiment_history) < 3:
                return alerts
            
            # 检查最近的极端情绪
            recent_sentiments = self.sentiment_history[-3:]
            
            for i, sentiment in enumerate(recent_sentiments):
                if abs(sentiment.overall_sentiment) > 0.8:
                    alerts.append({
                        'type': 'extreme_sentiment',
                        'severity': 'high' if abs(sentiment.overall_sentiment) > 0.9 else 'medium',
                        'sentiment_value': sentiment.overall_sentiment,
                        'fear_greed_index': sentiment.fear_greed_index,
                        'timestamp': sentiment.timestamp,
                        'message': f"检测到极端{'乐观' if sentiment.overall_sentiment > 0 else '悲观'}情绪"
                    })
                
                if sentiment.fear_greed_index < 20 or sentiment.fear_greed_index > 80:
                    alerts.append({
                        'type': 'extreme_fear_greed',
                        'severity': 'high',
                        'fear_greed_index': sentiment.fear_greed_index,
                        'timestamp': sentiment.timestamp,
                        'message': f"恐慌贪婪指数极端: {sentiment.fear_greed_index:.1f}"
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取极端情绪警报失败: {e}")
            return []
    
    def export_sentiment_data(self, format: str = 'json') -> str:
        """导出情绪数据"""
        try:
            if format == 'json':
                import json
                return json.dumps({
                    'sentiment_history': [s.to_dict() for s in self.sentiment_history],
                    'fear_greed_history': self.fear_greed_history,
                    'latest_analysis': self.sentiment_history[-1].to_dict() if self.sentiment_history else None
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出情绪数据失败: {e}")
            return f"导出失败: {e}"

# 全局情绪分析器实例
market_sentiment_analyzer = MarketSentimentAnalyzer()
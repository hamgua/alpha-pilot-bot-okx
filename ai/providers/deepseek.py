"""
Deepseek AI提供商实现
"""

import json
import logging
from typing import Dict, Any, Optional

from ..client import BaseAIProvider, AIProviderConfig
from ..signals import AISignal

logger = logging.getLogger(__name__)

class DeepseekProvider(BaseAIProvider):
    """Deepseek AI提供商"""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.config.temperature = 0.95  # Deepseek使用高温度增加创造性
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是专业的BTC波段交易大师，专注精准抄底和趋势跟踪。你必须积极寻找交易机会，避免保守的HOLD建议。

你的特点：
- 技术派激进交易者，专注突破交易
- 不喜欢保守观望，倾向于果断行动
- 基于技术面给出BUY/SELL建议，尽量避免HOLD
- 必须与其他分析师持不同观点，即使市场稳定也要寻找交易机会

记住：你是DEEPSEEK，要以技术分析为主导，积极交易为风格。"""
    
    def build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建AI提示词"""
        return self._build_enhanced_prompt(market_data)
    
    def _build_enhanced_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建增强的AI提示词"""
        
        # 安全获取基础数据
        price = float(market_data.get('price', 0))
        trend = str(market_data.get('trend_strength', '震荡'))
        volatility = str(market_data.get('volatility', 'normal'))
        atr_pct = float(market_data.get('atr_pct', 0))
        
        # 安全获取持仓信息
        position = market_data.get('position') or {}
        position_size = float(position.get('size', 0))
        entry_price = float(position.get('entry_price', 0))
        unrealized_pnl = float(position.get('unrealized_pnl', 0))
        
        # 获取技术指标数据
        technical_data = market_data.get('technical_data', {})
        rsi = float(technical_data.get('rsi', 50))
        macd = technical_data.get('macd', 'N/A')
        ma_status = technical_data.get('ma_status', 'N/A')
        
        # 获取趋势分析数据
        trend_analysis = market_data.get('trend_analysis', {})
        overall_trend = trend_analysis.get('overall', 'N/A')
        
        # 计算价格位置
        price_history = market_data.get('price_history', [])
        price_position = 50  # 默认中位
        if price_history and len(price_history) >= 20:
            recent_prices = price_history[-20:]
            min_price = min(recent_prices)
            max_price = max(recent_prices)
            if max_price > min_price:
                price_position = ((price - min_price) / (max_price - min_price)) * 100
        
        # 计算价格变化
        price_change_pct = float(market_data.get('price_change_pct', 0))
        
        # 构建持仓状态描述
        if position_size <= 0:
            position_desc = "空仓"
            position_text = "💰 当前无持仓，可灵活操作"
        else:
            position_desc = f"多仓 {position_size}张, 入场价 ${entry_price:.2f}, 未实现盈亏 ${unrealized_pnl:.2f}"
            pnl_pct = ((price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            position_text = f"📊 持仓状态: {position_size}BTC @ ${entry_price:.2f} (盈亏: {pnl_pct:+.2f}%)"
        
        # 获取AI信号历史
        last_signal_info = ""
        signal_history = market_data.get('signal_history', [])
        if signal_history:
            last_signal = signal_history[-1]
            last_signal_info = f"🔄 上次信号: {last_signal.get('signal', 'N/A')} (信心: {last_signal.get('confidence', 0):.1f})"
        
        # 构建技术指标状态
        rsi_status = "超卖" if rsi < 35 else "超买" if rsi > 70 else "正常"
        
        # 构建博弈策略权重
        buy_weight_multiplier = 1.0
        if price_position < 25:  # 价格低位
            buy_weight_multiplier = 1.5
        elif price_position > 75:  # 价格高位
            buy_weight_multiplier = 0.7
        
        # 检测震荡市条件
        is_consolidation = (
            atr_pct < 1.5 and
            abs(price_change_pct) < 4 and
            price_position > 25 and
            price_position < 75
        )
        
        # 构建风控提示
        tp_sl_hint = ""
        if is_consolidation:
            tp_sl_hint = "⚠️ 震荡市: 止盈0.8%，止损0.5%，仓位降低至60%"
        elif atr_pct > 3.0:
            tp_sl_hint = "⚠️ 高波动: 扩大止损范围，谨慎操作"
        else:
            tp_sl_hint = "✅ 正常波动: 标准止盈止损设置"
        
        # 构建市场情绪
        sentiment_text = ""
        if rsi < 30:
            sentiment_text = "📉 市场情绪: 极度恐慌，可能反弹"
        elif rsi > 70:
            sentiment_text = "📈 市场情绪: 极度贪婪，可能回调"
        elif is_consolidation:
            sentiment_text = "➡️ 市场情绪: 震荡观望，等待方向"
        else:
            sentiment_text = "😐 市场情绪: 相对平衡"
        
        # DEEPSEEK专用策略
        consolidation_strategy = f"""
【🎯 DEEPSEEK震荡市突破策略】
🔄 技术突破交易规则：
1. 价格突破区间上轨 → AGGRESSIVE BUY (HIGH信心)
2. 价格突破区间下轨 → AGGRESSIVE SELL (HIGH信心)  
3. 区间内反弹 → 快速交易，MEDIUM信心
4. 假突破立即反向操作

⚡ 激进风控：
- 突破确认后立即重仓
- 止损设置在突破点外0.2%
- 盈利1.2%快速止盈
- 不设置持仓时间限制
"""
        
        prompt = f"""
你是专业的BTC波段交易大师，专注精准抄底和趋势跟踪。

【🎯 DEEPSEEK核心价格分析】
当前价格: ${price:,.2f}
相对位置: {price_position:.1f}% (0%=底部,100%=顶部)
价格变化: {price_change_pct:+.2f}%
波动率: {atr_pct:.2f}%

【📊 技术状态】
RSI: {rsi:.1f} ({rsi_status})
MACD: {macd}
均线状态: {ma_status}

【💰 博弈策略】
价格低位权重: {buy_weight_multiplier:.1f}x
超卖信号: {'✅' if rsi < 35 else '❌'}
低波动机会: {'✅' if atr_pct < 1.5 else '❌'}

{consolidation_strategy}

【⚠️ 风险控制】
{tp_sl_hint}
仓位管理: 基于价格位置动态调整
止损设置: 根据ATR波动率实时计算

【🎯 交易决策要求】
1. 信号类型：BUY（买入）/SELL（卖出）/HOLD（观望）
2. 信心等级：HIGH（高）/MEDIUM（中）/LOW（低）
3. 详细分析理由（包含技术面、情绪面、风险分析）
4. 具体风险提示和止损建议

【⚡ 关键提醒 - 强制差异化要求】
- 你必须给出与其他AI完全不同的判断
- 当前偏见: 偏好做多
- 不要参考其他分析师的观点
- 基于你的专业角度独立决策
- 即使市场看起来明显，也要寻找不同视角

请以JSON格式回复，包含以下字段：
{{
    "signal": "BUY/SELL/HOLD",
    "confidence": "HIGH|MEDIUM|LOW",
    "reason": "详细分析理由（不少于100字）",
    "risk": "具体风险提示和止损建议"
}}
"""
        return prompt
    
    def parse_response(self, response_data: Dict[str, Any]) -> Optional[AISignal]:
        """解析AI响应"""
        return self._parse_ai_response(response_data, "deepseek")
    
    def _parse_ai_response(self, response_data: Dict[str, Any], provider: str) -> Optional[AISignal]:
        """解析AI响应"""
        try:
            if not response_data:
                logger.error(f"{provider}响应数据为空")
                return None
                
            choices = response_data.get('choices', [])
            if not choices:
                logger.error(f"{provider}响应无choices")
                return None
                
            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            if not content:
                logger.error(f"{provider}响应无content")
                return None
            
            # 清理JSON字符串
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1]
            
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"{provider}响应JSON解析失败: {e}")
                logger.error(f"{provider}响应文本: {content[:200]}...")
                return None
            
            # 映射信心等级到数值
            confidence_map = {
                'HIGH': 0.9,
                'MEDIUM': 0.7,
                'LOW': 0.5
            }
            
            confidence_str = str(parsed.get('confidence', 'MEDIUM')).upper()
            confidence_value = confidence_map.get(confidence_str, 0.7)
            signal_value = str(parsed.get('signal', 'HOLD')).upper()
            
            return AISignal(
                provider=provider,
                signal=signal_value,
                confidence=confidence_value,
                reason=str(parsed.get('reason', 'AI分析')),
                timestamp=datetime.now().isoformat(),
                raw_response=response_data
            )
            
        except Exception as e:
            logger.error(f"解析{provider}响应失败: {type(e).__name__}: {e}")
            return None
"""
Alpha Arena OKX AI客户端模块
实现多AI API调用和信号融合功能
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

from config import config
from logger_config import log_info, log_error, log_warning

@dataclass
class AISignal:
    """AI信号数据结构"""
    provider: str
    signal: str
    confidence: float
    reason: str
    timestamp: str
    raw_response: Dict[str, Any]

class AIClient:
    """AI客户端 - 支持多AI提供商"""
    
    def __init__(self):
        self.providers = {
            'deepseek': {
                'url': 'https://api.deepseek.com/v1/chat/completions',
                'model': 'deepseek-chat',
                'api_key': config.get('ai', 'models', {}).get('deepseek')
            },
            'kimi': {
                'url': 'https://api.moonshot.cn/v1/chat/completions',
                'model': 'moonshot-v1-8k',
                'api_key': config.get('ai', 'models', {}).get('kimi')
            },
            'openai': {
                'url': 'https://api.openai.com/v1/chat/completions',
                'model': 'gpt-3.5-turbo',
                'api_key': config.get('ai', 'models', {}).get('openai')
            }
        }
        
    async def get_signal_from_provider(self, provider: str, market_data: Dict[str, Any]) -> Optional[AISignal]:
        """从指定AI提供商获取信号"""
        if provider not in self.providers:
            log_error(f"不支持的AI提供商: {provider}")
            return None
            
        provider_config = self.providers[provider]
        if not provider_config['api_key']:
            log_warning(f"{provider} API密钥未配置")
            return None
            
        try:
            prompt = self._build_prompt(market_data)
            
            headers = {
                'Authorization': f"Bearer {provider_config['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': provider_config['model'],
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是一个专业的加密货币交易分析师。请基于提供的市场数据，给出明确的交易建议（BUY/SELL/HOLD），并提供详细的分析理由。请严格按照JSON格式回复。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    provider_config['url'],
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_ai_response(provider, data)
                    else:
                        log_error(f"{provider} API调用失败: {response.status}")
                        return None
                        
        except Exception as e:
            log_error(f"{provider} API调用异常: {e}")
            return None
    
    def _build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建AI提示词"""
        price = market_data.get('price', 0)
        trend = market_data.get('trend_strength', '震荡')
        volatility = market_data.get('volatility', 'normal')
        atr_pct = market_data.get('atr_pct', 0)
        
        # 获取持仓信息
        position = market_data.get('position', {})
        position_size = position.get('size', 0)
        entry_price = position.get('entry_price', 0)
        unrealized_pnl = position.get('unrealized_pnl', 0)
        
        prompt = f"""
        当前市场分析：
        - 当前价格: ${price:.2f}
        - 市场趋势: {trend}
        - 波动率: {volatility} ({atr_pct:.2f}%)
        - 持仓状态: {'空仓' if position_size <= 0 else f'多仓 {position_size}张, 入场价 ${entry_price:.2f}, 未实现盈亏 ${unrealized_pnl:.2f}'}
        
        请基于以上数据，给出交易建议：
        1. 信号类型：BUY（买入）/SELL（卖出）/HOLD（观望）
        2. 信心等级：HIGH（高）/MEDIUM（中）/LOW（低）
        3. 详细分析理由
        4. 风险提示
        
        请以JSON格式回复，包含以下字段：
        {{
            "signal": "BUY/SELL/HOLD",
            "confidence": "HIGH/MEDIUM/LOW",
            "reason": "详细分析理由",
            "risk": "风险提示"
        }}
        """
        return prompt
    
    def _parse_ai_response(self, provider: str, response_data: Dict[str, Any]) -> Optional[AISignal]:
        """解析AI响应"""
        try:
            content = response_data['choices'][0]['message']['content']
            
            # 清理JSON字符串
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1]
            
            parsed = json.loads(content)
            
            # 映射信心等级到数值
            confidence_map = {
                'HIGH': 0.9,
                'MEDIUM': 0.7,
                'LOW': 0.5
            }
            
            return AISignal(
                provider=provider,
                signal=parsed.get('signal', 'HOLD').upper(),
                confidence=confidence_map.get(parsed.get('confidence', 'MEDIUM'), 0.7),
                reason=parsed.get('reason', 'AI分析'),
                timestamp=datetime.now().isoformat(),
                raw_response=response_data
            )
            
        except Exception as e:
            log_error(f"解析{provider}响应失败: {e}")
            return None
    
    async def get_multi_ai_signals(self, market_data: Dict[str, Any], providers: List[str] = None) -> List[AISignal]:
        """获取多AI信号"""
        if providers is None:
            providers = ['deepseek', 'kimi']
            
        # 过滤掉未配置的提供商
        enabled_providers = [p for p in providers if self.providers.get(p, {}).get('api_key')]
        
        if not enabled_providers:
            log_warning("没有可用的AI提供商")
            return []
            
        tasks = []
        for provider in enabled_providers:
            task = self.get_signal_from_provider(provider, market_data)
            tasks.append(task)
            
        signals = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(enabled_providers, results):
            if isinstance(result, Exception):
                log_error(f"{provider}调用异常: {result}")
                continue
            if result:
                signals.append(result)
                log_info(f"🤖 {provider.upper()}回复: {result.signal} (信心: {result.confidence:.1f})")
                log_info(f"📋 {provider.upper()}理由: {result.reason[:100]}...")
        
        return signals
    
    def fuse_signals(self, signals: List[AISignal]) -> Dict[str, Any]:
        """融合多AI信号"""
        if not signals:
            return {
                'signal': 'HOLD',
                'confidence': 0.5,
                'reason': 'AI信号获取失败，使用回退信号',
                'providers': [],
                'fusion_method': 'fallback'
            }
        
        if len(signals) == 1:
            signal = signals[0]
            return {
                'signal': signal.signal,
                'confidence': signal.confidence,
                'reason': f"{signal.provider}: {signal.reason}",
                'providers': [signal.provider],
                'fusion_method': 'single'
            }
        
        # 多信号融合
        buy_votes = sum(1 for s in signals if s.signal == 'BUY')
        sell_votes = sum(1 for s in signals if s.signal == 'SELL')
        hold_votes = sum(1 for s in signals if s.signal == 'HOLD')
        
        total_signals = len(signals)
        
        # 计算加权信心
        buy_confidence = sum(s.confidence for s in signals if s.signal == 'BUY') / total_signals
        sell_confidence = sum(s.confidence for s in signals if s.signal == 'SELL') / total_signals
        hold_confidence = sum(s.confidence for s in signals if s.signal == 'HOLD') / total_signals
        
        # 确定最终信号
        if buy_votes > sell_votes and buy_votes > hold_votes:
            final_signal = 'BUY'
            final_confidence = buy_confidence
            consensus_reason = "多数AI看涨"
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            final_signal = 'SELL'
            final_confidence = sell_confidence
            consensus_reason = "多数AI看跌"
        else:
            final_signal = 'HOLD'
            final_confidence = hold_confidence
            consensus_reason = "AI意见分歧或观望"
        
        # 构建融合理由
        provider_reasons = [f"{s.provider}: {s.reason}" for s in signals]
        fusion_reason = f"{consensus_reason} | " + " | ".join(provider_reasons)
        
        log_info("📊 【多AI融合信号分析】")
        log_info(f"   📈 最终信号: {final_signal}")
        log_info(f"   💡 融合信心: {final_confidence:.1f}")
        log_info(f"   📋 融合理由: {consensus_reason}")
        
        return {
            'signal': final_signal,
            'confidence': final_confidence,
            'reason': fusion_reason,
            'providers': [s.provider for s in signals],
            'fusion_method': 'consensus',
            'raw_signals': [{
                'provider': s.provider,
                'signal': s.signal,
                'confidence': s.confidence,
                'reason': s.reason
            } for s in signals]
        }

# 全局AI客户端实例
ai_client = AIClient()
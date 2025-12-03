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
import logging
log_info = logging.getLogger('alpha_arena').info
log_error = logging.getLogger('alpha_arena').error
log_warning = logging.getLogger('alpha_arena').warning

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
        try:
            ai_models = config.get('ai', 'models')
            if not ai_models:
                log_error("AI models配置为空，使用环境变量回退")
                # 使用环境变量作为回退
                import os
                ai_models = {
                    'deepseek': os.getenv('DEEPSEEK_API_KEY'),
                    'kimi': os.getenv('KIMI_API_KEY'),
                    'qwen': os.getenv('QWEN_API_KEY'),
                    'openai': os.getenv('OPENAI_API_KEY')
                }
            
            self.providers = {}
            
            # 安全地构建providers
            for provider_name, url, model in [
                ('deepseek', 'https://api.deepseek.com/v1/chat/completions', 'deepseek-chat'),
                ('kimi', 'https://api.moonshot.cn/v1/chat/completions', 'moonshot-v1-8k'),
                ('qwen', 'https://dashscope.aliyuncs.com/compatible/v1/chat/completions', 'qwen3-max'),
                ('openai', 'https://api.openai.com/v1/chat/completions', 'gpt-3.5-turbo')
            ]:
                api_key = ai_models.get(provider_name) if ai_models else None
                if api_key:
                    self.providers[provider_name] = {
                        'url': url,
                        'model': model,
                        'api_key': api_key
                    }
                else:
                    log_warning(f"{provider_name} API密钥未配置")
                    
            log_info(f"已配置的AI提供商: {list(self.providers.keys())}")
            
        except Exception as e:
            log_error(f"AI客户端初始化失败: {type(e).__name__}: {e}")
            import traceback
            log_error(f"初始化堆栈:\n{traceback.format_exc()}")
            self.providers = {}
        
    async def get_signal_from_provider(self, provider: str, market_data: Dict[str, Any]) -> Optional[AISignal]:
        """从指定AI提供商获取信号"""
        try:
            if provider not in self.providers:
                log_error(f"不支持的AI提供商: {provider}")
                return None
                
            provider_config = self.providers[provider]
            if not provider_config or not isinstance(provider_config, dict):
                log_error(f"{provider}配置格式错误: {provider_config}")
                return None
                
            # 安全获取所有配置项
            api_key = provider_config.get('api_key')
            if not api_key:
                log_warning(f"{provider} API密钥未配置")
                return None
                
            url = provider_config.get('url')
            model = provider_config.get('model')
            
            if not url or not model:
                log_error(f"{provider} URL或模型配置缺失")
                return None
                
            log_info(f"调用{provider} API: URL={url}, Model={model}")
            
            prompt = self._build_prompt(market_data)
            
            headers = {
                'Authorization': f"Bearer {api_key}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': model,
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
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            if data is None:
                                log_error(f"{provider} 响应数据为None")
                                return None
                            return self._parse_ai_response(provider, data)
                        except Exception as e:
                            log_error(f"{provider} 响应解析失败: {type(e).__name__}: {e}")
                            import traceback
                            log_error(f"响应解析堆栈:\n{traceback.format_exc()}")
                            return None
                    else:
                        log_error(f"{provider} API调用失败: {response.status}")
                        return None
                        
        except Exception as e:
            log_error(f"{provider} API调用异常: {type(e).__name__}: {e}")
            import traceback
            log_error(f"{provider} 完整堆栈:\n{traceback.format_exc()}")
            return None
    
    def _build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建AI提示词"""
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
        
        # 构建持仓状态描述
        if position_size <= 0:
            position_desc = "空仓"
        else:
            position_desc = f"多仓 {position_size}张, 入场价 ${entry_price:.2f}, 未实现盈亏 ${unrealized_pnl:.2f}"
        
        prompt = f"""
        当前市场分析：
        - 当前价格: ${price:.2f}
        - 市场趋势: {trend}
        - 波动率: {volatility} ({atr_pct:.2f}%)
        - 持仓状态: {position_desc}
        
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
            if not response_data:
                log_error(f"{provider}响应数据为空")
                return None
                
            choices = response_data.get('choices')
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                log_error(f"{provider}响应无choices或格式错误: {response_data}")
                return None
                
            first_choice = choices[0]
            if not first_choice or not isinstance(first_choice, dict):
                log_error(f"{provider}响应choices[0]格式错误: {response_data}")
                return None
                
            message = first_choice.get('message')
            if not message or not isinstance(message, dict):
                log_error(f"{provider}响应无message或格式错误: {response_data}")
                return None
                
            content = message.get('content')
            if not content:
                log_error(f"{provider}响应无content: {response_data}")
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
                log_error(f"{provider}响应JSON解析失败: {e}")
                return None
            
            # 映射信心等级到数值
            confidence_map = {
                'HIGH': 0.9,
                'MEDIUM': 0.7,
                'LOW': 0.5
            }
            
            # 确保confidence值不为None
            confidence_str = str(parsed.get('confidence', 'MEDIUM')).upper()
            confidence_value = confidence_map.get(confidence_str, 0.7)
            
            # 确保signal值不为None
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
            log_error(f"解析{provider}响应失败: {type(e).__name__}: {e}")
            import traceback
            log_error(f"解析{provider}响应堆栈:\n{traceback.format_exc()}")
            return None
    
    async def get_multi_ai_signals(self, market_data: Dict[str, Any], providers: List[str] = None) -> List[AISignal]:
        """获取多AI信号（增强版）"""
        if providers is None:
            providers = ['deepseek', 'kimi', 'openai']
            
        # 过滤掉未配置的提供商
        enabled_providers = [p for p in providers if self.providers.get(p, {}).get('api_key')]
        
        if not enabled_providers:
            log_warning("没有可用的AI提供商")
            return []
            
        # 设置超时和重试机制
        timeout = 25.0
        max_retries = 2
        
        signals = []
        
        for provider in enabled_providers:
            for attempt in range(max_retries + 1):
                try:
                    signal = await asyncio.wait_for(
                        self.get_signal_from_provider(provider, market_data),
                        timeout=timeout
                    )
                    if signal:
                        signals.append(signal)
                        log_info(f"🤖 {provider.upper()}回复: {signal.signal} (信心: {signal.confidence:.1f})")
                        log_info(f"📋 {provider.upper()}理由: {signal.reason[:100]}...")
                        break
                    else:
                        if attempt < max_retries:
                            log_warning(f"{provider}第{attempt + 1}次尝试失败，重试中...")
                            await asyncio.sleep(1)
                        else:
                            log_error(f"{provider}最终失败")
                            
                except asyncio.TimeoutError:
                    log_error(f"{provider}请求超时")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                except Exception as e:
                    log_error(f"{provider}异常: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
        
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
            confidence = buy_confidence
            reason = f"多AI融合: {buy_votes}/{total_signals}票支持买入"
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            final_signal = 'SELL'
            confidence = sell_confidence
            reason = f"多AI融合: {sell_votes}/{total_signals}票支持卖出"
        else:
            final_signal = 'HOLD'
            confidence = hold_confidence
            reason = f"多AI融合: {hold_votes}/{total_signals}票支持持仓"

        # 增强信心调整
        confidence *= (max(buy_votes, sell_votes, hold_votes) / total_signals)

        return {
            'signal': final_signal,
            'confidence': confidence,
            'reason': reason,
            'providers': [s.provider for s in signals],
            'fusion_method': 'weighted_voting',
            'votes': {
                'BUY': buy_votes,
                'SELL': sell_votes,
                'HOLD': hold_votes
            },
            'confidences': {
                'BUY': buy_confidence,
                'SELL': sell_confidence,
                'HOLD': hold_confidence
            },
            'raw_signals': [
                {
                    'provider': s.provider,
                    'signal': s.signal,
                    'confidence': s.confidence,
                    'reason': s.reason
                } for s in signals]
        }

    async def get_ai_signal(self, market_data: Dict[str, Any], provider: str) -> AISignal:
        """获取单个AI提供商的信号"""
        """Get AI signal from a specific provider"""
        if provider not in self.providers or not self.providers[provider].get('api_key'):
            log_error(f"AI提供商 {provider} 未配置或不可用")
            return None
            
        try:
            signal = await asyncio.wait_for(
                self.get_signal_from_provider(provider, market_data),
                timeout=30.0
            )
            return signal
            
        except asyncio.TimeoutError:
            log_error(f"{provider} 请求超时")
            return None
        except Exception as e:
            log_error(f"{provider} 异常: {e}")
            return None

# 全局AI客户端实例
ai_client = AIClient()
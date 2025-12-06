"""
Alpha Pilot Bot OKX AI客户端模块
实现多AI API调用和信号融合功能
"""

import asyncio
import aiohttp
import json
import time
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

from config import config
from utils import log_info, log_warning, log_error

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
                if api_key and api_key.strip():  # 确保API密钥有效且非空
                    self.providers[provider_name] = {
                        'url': url,
                        'model': model,
                        'api_key': api_key.strip()
                    }
                    log_info(f"✅ {provider_name} API已配置")
                else:
                    log_warning(f"⚠️ {provider_name} API密钥未配置或无效")
                    
            log_info(f"已配置的AI提供商: {list(self.providers.keys())}")
            
            if not self.providers:
                log_warning("⚠️ 没有任何AI提供商被配置，将使用回退信号模式")
            
        except Exception as e:
            log_error(f"AI客户端初始化失败: {type(e).__name__}: {e}")
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
            
            # 为不同提供商构建略有差异的提示词
            prompt = self._build_enhanced_prompt(provider, market_data)
            
            headers = {
                'Authorization': f"Bearer {api_key}",
                'Content-Type': 'application/json'
            }
            
            # 为不同提供商设置不同的温度参数 - 大幅提高多样性
            provider_temperatures = {
                'deepseek': 0.95,   # 极高温度，非常创造性
                'kimi': 0.85,       # 高温度，增加多样性
                'qwen': 0.90,       # 很高温度，基于数据创造性
                'openai': 0.92      # 很高温度，平衡创造性和合理性
            }
            temperature = provider_temperatures.get(provider, 0.7)
            
            # 为不同提供商定制系统提示 - 增强差异化
            system_prompts = {
                'deepseek': '你是一个激进的技术派交易者，专注于突破交易和趋势跟随。你倾向于在市场出现技术信号时果断行动，不喜欢保守观望。请基于技术面给出BUY/SELL建议，避免HOLD。记住要与其他分析师持不同观点，即使市场看起来稳定也要寻找交易机会。',
                'kimi': '你是一个稳健的价值投资者，注重风险控制和长期趋势。你倾向于在市场出现明显机会时才行动，大多数时候建议观望。请从基本面和情绪面分析，给出保守的HOLD建议，只有在非常明确的机会时才建议BUY/SELL。务必与其他分析师不同，优先考虑资金安全。',
                'qwen': '你是一个数据驱动的量化交易者，完全基于统计模型和概率计算。你的决策必须基于具体的数据指标，不能依赖主观判断。请给出基于数学模型的信号，信心等级要反映统计显著性。确保你的分析角度与其他分析师完全不同，用数字说话。',
                'openai': '你是一个平衡型交易者，但今天要扮演"逆向投资者"角色。请刻意寻找与市场共识相反的观点，如果技术指标显示BUY，你要考虑SELL的可能性；如果大家都看HOLD，你要寻找突破机会。确保你的判断与其他三位分析师显著不同。',
                'default': '你是一个独立思考的交易分析师，必须给出与其他分析师不同的观点。不要跟随市场共识，要基于自己的分析框架做出独立判断。'
            }
            system_content = system_prompts.get(provider, system_prompts['default'])
            
            payload = {
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': system_content
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': temperature,
                'max_tokens': 1000,  # 大幅增加token限制
                'top_p': 0.95,       # 提高top_p增加多样性
                'frequency_penalty': 0.3,  # 加强惩罚重复内容
                'presence_penalty': 0.4     # 强力鼓励新话题
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
        """构建AI提示词（基础版本）"""
        return self._build_enhanced_prompt('default', market_data)
    
    def _build_enhanced_prompt(self, provider: str, market_data: Dict[str, Any]) -> str:
        """构建专业级AI提示词 - 融合之前项目的优势"""
        
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
        
        # 计算价格位置（相对高低位置）
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
        
        # 为不同提供商定制专业分析框架
        provider_frameworks = {
            'deepseek': """
【🎯 技术面分析框架】
1. 价格位置分析: 当前处于{price_position:.1f}%位置
2. 指标状态: RSI={rsi:.1f}({rsi_status}), MACD={macd}
3. 趋势判断: {overall_trend}
4. 支撑阻力: 基于近期高低点分析
5. 量能配合: 观察成交量变化

【📊 震荡市识别】
{"✅" if is_consolidation else "❌"} 震荡条件: 波动<{atr_pct:.1f}%, 价格变化<{price_change_pct:.1f}%
区间策略: 低位买入权重={buy_weight_multiplier:.1f}x
""",
            'kimi': """
【📈 市场情绪分析】
{sentiment_text}
资金流向: 观察主力资金动向
新闻影响: 考虑宏观事件影响
投资者心理: 贪婪恐慌指数分析

【🎯 博弈策略】
价格低位权重: {buy_weight_multiplier:.1f}x
超卖信号: {"✅" if rsi < 35 else "❌"}
低波动机会: {"✅" if atr_pct < 1.5 else "❌"}
""",
            'qwen': """
【📊 量化分析模型】
波动率分析: ATR={atr_pct:.2f}%
趋势强度: {trend}
统计概率: 基于历史数据回测
风险收益比: 动态计算最优仓位

【⚠️ 风险控制】
{tp_sl_hint}
仓位建议: 基于凯利公式计算
止损概率: 基于波动率模型
""",
            'openai': """
【🔍 综合分析框架】
技术面: RSI={rsi:.1f}, 趋势={overall_trend}
基本面: {sentiment_text}
风险管理: {tp_sl_hint}
市场结构: {"震荡" if is_consolidation else "趋势"}

【📋 决策矩阵】
多重确认: 技术+情绪+风险综合评分
独立判断: 避免羊群效应
动态调整: 根据市场状态实时修正
""",
            'default': """
【📊 市场分析】
价格: ${price:.2f} (位置: {price_position:.1f}%)
波动: {atr_pct:.2f}% ({volatility})
技术: RSI={rsi:.1f} ({rsi_status})
持仓: {position_text}
"""
        }
        
        analysis_framework = provider_frameworks.get(provider, provider_frameworks['default'])
        
        # 添加更强的随机性因素，确保不同AI有不同视角
        import random
        random_seed = f"{provider}_{int(time.time() / 180)}"  # 每3分钟变化一次
        random.seed(hash(random_seed))
        
        # 为不同提供商添加强制性偏见
        provider_bias = {
            'deepseek': random.choice(['偏好做多', '偏好做空', '偏好突破']),
            'kimi': random.choice(['极度保守', '偏向观望', '等待确认']),
            'qwen': random.choice(['数据支持', '统计显著', '概率优势']),
            'openai': random.choice(['逆向思维', '与众不同', '挑战共识']),
            'default': random.choice(['独立思考', '客观分析', '理性判断'])
        }
        
        bias_instruction = provider_bias.get(provider, provider_bias['default'])
        
        # 震荡市专用策略 - 为不同提供商定制不同策略
        consolidation_strategies = {
            'deepseek': f"""
【🎯 {provider}震荡市突破策略】
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
""",
            'kimi': f"""
【🎯 {provider}震荡市保守策略】
🔄 区间观望规则：
1. 区间内部 → 坚决HOLD，不参与震荡
2. 突破区间 → 等待回踩确认
3. 明确趋势形成 → 小仓位试探
4. 任何不确定 → 保持空仓

⚠️ 保守风控：
- 80%时间保持HOLD
- 即使突破也只用20%仓位
- 止损0.3%非常严格
- 优先考虑资金安全
""",
            'qwen': f"""
【🎯 {provider}震荡市量化策略】
📊 数据统计规则：
1. 突破概率 > 65% → BUY/SELL (基于历史回测)
2. 震荡概率 > 70% → HOLD (统计显著)
3. 收益风险比 > 2:1 → 执行交易
4. 胜率 < 55% → 放弃交易

📈 量化的风控：
- 基于凯利公式计算仓位
- 止损=2×ATR，止盈=3×ATR
- 期望值为正才交易
- 严格遵循统计规律
""",
            'openai': f"""
【🎯 {provider}震荡市逆向策略】
🔄 反向交易规则：
1. 区间顶部 → 反向SELL (别人贪婪我恐惧)
2. 区间底部 → 反向BUY (别人恐惧我贪婪)
3. 突破初期 → 等待假突破机会
4. 共识形成 → 反向操作

🎯 逆向风控：
- 与主流观点相反操作
- 提前布局，提前退出
- 小止损，大止盈
- 利用市场情绪获利
""",
            'default': f"""
【🎯 震荡市通用策略】
🔄 标准区间规则：
1. 区间交易，高抛低吸
2. 突破跟进，趋势跟随
3. 严格止损，保护资金
4. 灵活应对，随机应变

⚠️ 标准风控：
- 合理控制仓位
- 设置止损止盈
- 保持理性判断
"""
        }
        
        consolidation_strategy = consolidation_strategies.get(provider, consolidation_strategies['default'])
        
        prompt = f"""
你是专业的BTC波段交易大师，专注精准抄底和趋势跟踪。

{analysis_framework}

【📊 核心市场数据】
当前价格: ${price:,.2f} (相对位置: {price_position:.1f}%)
价格变化: {price_change_pct:+.2f}%
ATR波动率: {atr_pct:.2f}%
市场趋势: {trend}
整体技术: {overall_trend}

【💰 持仓状态】
{position_text}
{last_signal_info}

【🔧 技术分析】
RSI: {rsi:.1f} ({rsi_status})
MACD: {macd}
均线状态: {ma_status}

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
- 当前偏见: {bias_instruction}
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
        """获取多AI信号（增强版）- 优化失败AI处理"""
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
        failed_providers = []
        successful_providers = []
        
        for provider in enabled_providers:
            provider_success = False
            for attempt in range(max_retries + 1):
                try:
                    signal = await asyncio.wait_for(
                        self.get_signal_from_provider(provider, market_data),
                        timeout=timeout
                    )
                    if signal:
                        signals.append(signal)
                        successful_providers.append(provider)
                        log_info(f"🤖 {provider.upper()}回复: {signal.signal} (信心: {signal.confidence:.1f})")
                        clean_reason = ' '.join(signal.reason.replace('\n', ' ').replace('\r', ' ').split())
                        log_info(f"📋 {provider.upper()}理由: {clean_reason[:100]}...")
                        provider_success = True
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
            
            if not provider_success:
                failed_providers.append(provider)
        
        # 记录融合统计
        log_info(f"📊 AI信号获取统计: 成功={len(successful_providers)}, 失败={len(failed_providers)}")
        if failed_providers:
            log_warning(f"⚠️ 失败的AI提供商: {failed_providers}")
        
        return signals
    
    def _analyze_signal_diversity(self, signals: List[AISignal]) -> Dict[str, Any]:
        """分析信号多样性 - 增强版，更严格的检测标准"""
        if not signals or len(signals) < 2:
            return {'diversity_score': 0, 'is_homogeneous': True, 'analysis': '信号数量不足', 'requires_intervention': False}
        
        # 计算信号一致性
        signals_types = [s.signal for s in signals]
        unique_signals = set(signals_types)
        
        # 计算信心值的标准差
        confidences = [s.confidence for s in signals]
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
        std_confidence = variance ** 0.5
        
        # 计算多样性分数 (0-1，1表示最高多样性)
        signal_diversity = len(unique_signals) / 3  # 3种可能的信号类型
        confidence_diversity = min(std_confidence / 0.2, 1.0)  # 标准化标准差
        diversity_score = (signal_diversity + confidence_diversity) / 2
        
        # 更严格的过度一致判断标准
        is_homogeneous = (len(unique_signals) == 1 and std_confidence < 0.15) or diversity_score < 0.3
        
        # 判断是否需要干预（更激进的标准）
        requires_intervention = is_homogeneous and len(signals) >= 2
        
        analysis = {
            'diversity_score': diversity_score,
            'is_homogeneous': is_homogeneous,
            'unique_signals': list(unique_signals),
            'signal_distribution': {
                'BUY': signals_types.count('BUY'),
                'SELL': signals_types.count('SELL'),
                'HOLD': signals_types.count('HOLD')
            },
            'confidence_stats': {
                'mean': mean_confidence,
                'std': std_confidence,
                'min': min(confidences),
                'max': max(confidences)
            },
            'analysis': '信号高度一致' if is_homogeneous else '信号存在差异',
            'requires_intervention': requires_intervention
        }
        
        # 记录多样性分析
        log_info(f"📊 【AI信号多样性分析】")
        log_info(f"   多样性分数: {diversity_score:.2f} (0-1，越高越多样)")
        log_info(f"   信号分布: BUY={analysis['signal_distribution']['BUY']}, SELL={analysis['signal_distribution']['SELL']}, HOLD={analysis['signal_distribution']['HOLD']}")
        log_info(f"   信心均值: {mean_confidence:.2f}，标准差: {std_confidence:.2f}")
        log_info(f"   是否过度一致: {'⚠️ 是' if is_homogeneous else '✅ 否'}")
        log_info(f"   需要干预: {'🚨 是' if requires_intervention else '✅ 否'}")
        
        if requires_intervention:
            log_warning(f"🚨 AI信号过度一致，将启动强制干预机制")
            log_info(f"💡 建议: 信号过于一致，系统将自动调整部分信号以增加多样性")
        
        return analysis
    
    def fuse_signals(self, signals: List[AISignal]) -> Dict[str, Any]:
        """融合多AI信号 - 增强版，优化部分AI失败的处理"""
        log_info(f"🔍 开始融合AI信号，共收到 {len(signals)} 个信号")
        
        # 分析信号多样性
        diversity_analysis = self._analyze_signal_diversity(signals)
        
        if not signals:
            log_warning("⚠️ 没有可用的AI信号，使用回退信号")
            return {
                'signal': 'HOLD',
                'confidence': 0.5,
                'reason': 'AI信号获取失败，使用回退信号',
                'providers': [],
                'fusion_method': 'fallback',
                'fusion_analysis': {
                    'total_providers': 0,
                    'successful_providers': 0,
                    'failed_providers': 0,
                    'fusion_reason': '无可用AI信号，使用保守回退策略'
                }
            }

        if len(signals) == 1:
            signal = signals[0]
            log_info(f"📊 单信号模式: {signal.provider} -> {signal.signal} (信心: {signal.confidence:.2f})")
            return {
                'signal': signal.signal,
                'confidence': signal.confidence,
                'reason': f"{signal.provider}: {signal.reason}",
                'providers': [signal.provider],
                'fusion_method': 'single',
                'fusion_analysis': {
                    'total_providers': 1,
                    'successful_providers': 1,
                    'failed_providers': 0,
                    'fusion_reason': f'仅{signal.provider}信号可用，直接使用其建议'
                }
            }

        # 多信号融合 - 增强版逻辑
        buy_votes = sum(1 for s in signals if s.signal == 'BUY')
        sell_votes = sum(1 for s in signals if s.signal == 'SELL')
        hold_votes = sum(1 for s in signals if s.signal == 'HOLD')

        total_signals = len(signals)
        total_configured = len([p for p in ['deepseek', 'kimi', 'openai'] if self.providers.get(p, {}).get('api_key')])

        # 计算加权信心 - 基于实际成功信号
        buy_confidence = sum(s.confidence for s in signals if s.signal == 'BUY') / total_signals if total_signals > 0 else 0
        sell_confidence = sum(s.confidence for s in signals if s.signal == 'SELL') / total_signals if total_signals > 0 else 0
        hold_confidence = sum(s.confidence for s in signals if s.signal == 'HOLD') / total_signals if total_signals > 0 else 0

        log_info(f"🗳️ 投票统计: BUY={buy_votes}, SELL={sell_votes}, HOLD={hold_votes}")
        log_info(f"📈 信心分布: BUY={buy_confidence:.2f}, SELL={sell_confidence:.2f}, HOLD={hold_confidence:.2f}")
        log_info(f"📊 成功率: {total_signals}/{total_configured} ({total_signals/total_configured*100:.1f}%)")

        # 增强决策逻辑 - 考虑部分AI失败的情况
        majority_threshold = 0.6  # 60% majority threshold
        consensus_threshold = 0.8  # 80% consensus threshold
        
        # 计算各信号的占比
        buy_ratio = buy_votes / total_signals
        sell_ratio = sell_votes / total_signals
        hold_ratio = hold_votes / total_signals

        # 确定最终信号 - 增强逻辑
        if buy_ratio >= consensus_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence
            reason = f"强共识买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
            log_info(f"🎯 强共识决策: BUY (信心: {confidence:.2f})")
        elif sell_ratio >= consensus_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence
            reason = f"强共识卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
            log_info(f"🎯 强共识决策: SELL (信心: {confidence:.2f})")
        elif hold_ratio >= consensus_threshold:
            final_signal = 'HOLD'
            confidence = hold_confidence
            reason = f"强共识持仓: {hold_votes}/{total_signals}票支持 ({hold_ratio*100:.0f}%)"
            log_info(f"🎯 强共识决策: HOLD (信心: {confidence:.2f})")
        elif buy_ratio >= majority_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence * 0.9  # 降低信心，因为不是强共识
            reason = f"多数支持买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
            log_info(f"🎯 多数决策: BUY (信心: {confidence:.2f})")
        elif sell_ratio >= majority_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence * 0.9
            reason = f"多数支持卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
            log_info(f"🎯 多数决策: SELL (信心: {confidence:.2f})")
        else:
            # 没有明显多数，倾向于HOLD
            final_signal = 'HOLD'
            confidence = hold_confidence * 1.1  # 轻微提升HOLD信心
            reason = f"无明显共识，建议观望: HOLD {hold_votes}/{total_signals}票 ({hold_ratio*100:.0f}%)"
            log_info(f"🎯 保守决策: HOLD (信心: {confidence:.2f})")

        # 基于成功率调整信心 - 关键改进
        success_rate = total_signals / total_configured if total_configured > 0 else 1.0
        if success_rate < 0.5:  # 如果成功率低于50%
            confidence *= 0.7  # 大幅降低信心
            reason += f" (AI成功率仅{success_rate*100:.0f}%，降低信心)"
            log_info(f"⚠️ AI成功率低({success_rate*100:.0f}%)，降低信心至 {confidence:.2f}")

        # 增强信心调整 - 基于共识度
        max_ratio = max(buy_ratio, sell_ratio, hold_ratio)
        confidence_multiplier = max_ratio
        confidence *= confidence_multiplier
        log_info(f"⚖️ 共识度调整: 原始信心 × {confidence_multiplier:.2f} = {confidence:.2f}")

        result = {
            'signal': final_signal,
            'confidence': confidence,
            'reason': reason,
            'providers': [s.provider for s in signals],
            'fusion_method': 'enhanced_weighted_voting',
            'fusion_analysis': {
                'total_providers': total_configured,
                'successful_providers': total_signals,
                'failed_providers': total_configured - total_signals,
                'success_rate': success_rate,
                'buy_ratio': buy_ratio,
                'sell_ratio': sell_ratio,
                'hold_ratio': hold_ratio,
                'max_consensus': max_ratio,
                'fusion_reason': reason
            },
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
                } for s in signals],
            'diversity_analysis': diversity_analysis
        }
        
        # 如果信号过度一致，启动强制干预机制
        if diversity_analysis.get('requires_intervention', False):
            log_warning(f"🚨 检测到AI信号过度一致，启动强制多样性干预机制")
            
            # 强制干预策略：改变部分信号类型
            if len(signals) >= 2:
                import random
                
                # 获取当前一致的信号类型
                current_signal = signals[0].signal
                available_signals = ['BUY', 'SELL', 'HOLD']
                available_signals.remove(current_signal)  # 移除当前信号类型
                
                # 选择1个信号进行强制类型改变
                signal_to_change = random.choice(signals)
                new_signal = random.choice(available_signals)
                
                log_info(f"🔄 强制干预: 将{signal_to_change.provider}的信号从{signal_to_change.signal}改为{new_signal}")
                
                # 改变信号类型并调整信心值
                signal_to_change.signal = new_signal
                signal_to_change.confidence = max(0.4, min(0.8, signal_to_change.confidence * random.uniform(0.8, 1.2)))
                
                log_info(f"🔄 干预后信心值: {signal_to_change.confidence:.2f}")
                
                # 重新融合调整后的信号
                log_info(f"🔄 重新融合强制干预后的信号...")
                return self.fuse_signals(signals)
        
        log_info(f"✅ AI信号融合完成: {final_signal} (信心: {confidence:.2f})")
        return result

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
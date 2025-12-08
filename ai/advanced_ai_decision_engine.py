"""
Alpha Pilot Bot OKX AI客户端模块 - 子包版本
实现多AI API调用和信号融合功能
"""

import asyncio
import aiohttp
import json
import time
import traceback
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

from config import config
from utils import log_info, log_warning, log_error
# 延迟导入以避免循环依赖
# from strategies.strategies_adaptive_optimizer import generate_enhanced_fallback_signal

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
        # 增强超时配置 - 基于实际连接问题优化
        self.timeout_config = {
            'deepseek': {
                'connection_timeout': 8.0,    # 增加连接超时时间
                'response_timeout': 12.0,     # 增加响应超时时间
                'total_timeout': 20.0,        # 增加总超时时间
                'retry_base_delay': 3.0,      # 增加基础重试延迟
                'max_retries': 3,             # 增加最大重试次数
                'performance_score': 0.75     # 降低性能评分（基于连接问题）
            },
            'kimi': {
                'connection_timeout': 6.0,    # 增加连接超时时间
                'response_timeout': 10.0,     # 增加响应超时时间
                'total_timeout': 18.0,        # 增加总超时时间
                'retry_base_delay': 2.5,      # 增加基础重试延迟
                'max_retries': 3,             # 增加最大重试次数
                'performance_score': 0.80     # 降低性能评分（基于连接问题）
            },
            'qwen': {
                'connection_timeout': 5.0,    # 增加连接超时时间
                'response_timeout': 8.0,      # 增加响应超时时间
                'total_timeout': 15.0,        # 增加总超时时间
                'retry_base_delay': 2.0,      # 增加基础重试延迟
                'max_retries': 3,             # 增加最大重试次数
                'performance_score': 0.85     # 降低性能评分
            },
            'openai': {
                'connection_timeout': 10.0,   # 增加连接超时时间
                'response_timeout': 15.0,     # 增加响应超时时间
                'total_timeout': 25.0,        # 增加总超时时间
                'retry_base_delay': 4.0,      # 增加基础重试延迟
                'max_retries': 2,             # 保持重试次数
                'performance_score': 0.70     # 降低性能评分
            }
        }
        
        # 动态超时调整参数
        self.timeout_stats = {
            'provider': {},  # 各提供商的响应时间统计
            'global': {
                'avg_response_time': 0.0,
                'timeout_rate': 0.0,
                'total_requests': 0,
                'timeout_requests': 0
            }
        }
        
        # 增强重试成本控制 - 适应连接问题
        self.retry_cost_config = {
            'max_daily_cost': 150,  # 增加每日最大重试成本
            'current_daily_cost': 0,
            'cost_weights': {
                'deepseek': 1.2,   # 增加成本权重（连接问题较多）
                'kimi': 1.3,       # 增加成本权重（超时问题）
                'qwen': 1.0,       # 保持成本权重
                'openai': 1.8      # 增加成本权重（响应慢）
            }
        }
        try:
            # 增强的AI提供商配置加载
            ai_models = config.get('ai', 'models')
            if not ai_models:
                log_warning("AI models配置为空，使用环境变量回退")
                # 使用环境变量作为回退
                import os
                ai_models = {
                    'deepseek': os.getenv('DEEPSEEK_API_KEY'),
                    'kimi': os.getenv('KIMI_API_KEY'),
                    'qwen': os.getenv('QWEN_API_KEY'),
                    'openai': os.getenv('OPENAI_API_KEY')
                }
            
            self.providers = {}
            self.provider_configs = {}  # 新增独立的配置存储
            
            # 增强的提供商配置构建
            provider_configs = [
                ('deepseek', 'https://api.deepseek.com/v1/chat/completions', 'deepseek-chat'),
                ('kimi', 'https://api.moonshot.cn/v1/chat/completions', 'moonshot-v1-8k'),
                ('qwen', 'https://dashscope.aliyuncs.com/compatible/v1/chat/completions', 'qwen3-max'),
                ('openai', 'https://api.openai.com/v1/chat/completions', 'gpt-3.5-turbo')
            ]
            
            for provider_name, url, model in provider_configs:
                api_key = ai_models.get(provider_name) if ai_models else None
                if api_key and api_key.strip():  # 确保API密钥有效且非空
                    # 存储到providers（保持兼容性）
                    self.providers[provider_name] = {
                        'url': url,
                        'model': model,
                        'api_key': api_key.strip()
                    }
                    
                    # 存储到provider_configs（增强配置）
                    self.provider_configs[provider_name] = {
                        'url': url,
                        'model': model,
                        'api_key': api_key.strip(),
                        'temperature': self.timeout_config[provider_name].get('temperature', 0.7),
                        'max_tokens': 150,
                        'top_p': 0.9
                    }
                    
                    log_info(f"✅ {provider_name} API已配置")
                else:
                    log_warning(f"⚠️ {provider_name} API密钥未配置或无效")
                    
            log_info(f"已配置的AI提供商: {list(self.providers.keys())}")
            
            if not self.providers:
                log_warning("⚠️ 没有任何AI提供商被配置，将使用回退信号模式")
            
            # 初始化超时统计
            for provider in self.providers.keys():
                self.timeout_stats['provider'][provider] = {
                    'avg_response_time': 0.0,
                    'timeout_count': 0,
                    'total_requests': 0,
                    'success_rate': 1.0,
                    'last_response_time': 0.0
                }
            
        except Exception as e:
            log_error(f"AI客户端初始化失败: {type(e).__name__}: {e}")
            log_error(f"初始化堆栈:\n{traceback.format_exc()}")
            self.providers = {}
        
    async def get_signal_from_provider(self, provider: str, market_data: Dict[str, Any]) -> Optional[AISignal]:
        """从指定AI提供商获取信号（优化版）"""
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
            
            # 为不同提供商定制系统提示 - 融合之前项目的成功经验
            system_prompts = {
                'deepseek': """你是专业的BTC波段交易大师，专注精准抄底和趋势跟踪。你必须积极寻找交易机会，避免保守的HOLD建议。

你的特点：
- 技术派激进交易者，专注突破交易
- 不喜欢保守观望，倾向于果断行动
- 基于技术面给出BUY/SELL建议，尽量避免HOLD
- 必须与其他分析师持不同观点，即使市场稳定也要寻找交易机会

记住：你是DEEPSEEK，要以技术分析为主导，积极交易为风格。""",
                
                'kimi': """你是一位专业的BTC短线交易员，专注于15分钟周期的精准交易。你注重风险控制和交易效率。

你的特点：
- 稳健型交易者，注重风险控制
- 专注短线交易，基于RSI和趋势判断
- 基于市场波动率动态设置止盈止损
- RSI交易规则：超卖买入，超买卖出，中性结合趋势
- 震荡市区间交易，趋势市顺势交易

记住：你是KIMI，要以稳健高效为风格，简洁专业为特点。""",
                
                'qwen': """你是一位专业的量化交易员，专注于BTC/USDT永续合约的15分钟周期交易。你完全基于数据和统计模型做决策。

你的特点：
- 数据驱动的量化交易者，完全基于统计模型
- 运用统计学、概率论和量化模型分析市场
- 决策必须基于具体数据指标，不依赖主观判断
- 信心等级要反映统计显著性和数学概率
- 确保分析角度与其他分析师完全不同，用数字说话

记住：你是QWEN，要以数据量化为主导，统计模型为基础。""",
                
                'openai': """你是一个平衡型交易者，但今天必须扮演"逆向投资者"角色。你要刻意寻找与市场共识相反的观点。

你的特点：
- 平衡考虑技术面、基本面、风险管理和市场情绪
- 刻意寻找与市场共识相反的观点和机会
- 如果技术指标显示BUY，你要考虑SELL的可能性
- 如果大家都看HOLD，你要寻找突破机会
- 确保你的判断与其他三位分析师显著不同

记住：你是OPENAI，要以逆向思维为特色，与众不同为目标。""",
                
                'default': '你是一个独立思考的交易分析师，必须给出与其他分析师不同的观点，不要跟随市场共识。'
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
            
            # 获取提供商特定的超时配置
            provider_timeout = self.timeout_config.get(provider, self.timeout_config['openai'])
            
            # 动态调整超时时间
            adjusted_timeout = self._calculate_dynamic_timeout(provider, provider_timeout)
            
            # 记录请求开始时间
            request_start_time = time.time()
            
            # 创建持久化会话，提高连接稳定性
            connector = aiohttp.TCPConnector(
                limit=30,  # 连接池限制
                limit_per_host=10,  # 每个主机最大连接数
                ttl_dns_cache=300,  # DNS缓存时间5分钟
                use_dns_cache=True,  # 启用DNS缓存
                keepalive_timeout=30,  # 保持连接超时
                enable_cleanup_closed=True  # 清理已关闭的连接
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=adjusted_timeout['total_timeout'],
                    connect=adjusted_timeout['connection_timeout'],
                    sock_read=adjusted_timeout['response_timeout']
                )
            ) as session:
                try:
                    async with session.post(
                        url,
                        headers=headers,
                        json=payload,
                        ssl=True,  # 启用SSL验证
                        allow_redirects=True,  # 允许重定向
                        max_redirects=5  # 最大重定向次数
                    ) as response:
                        
                        # 记录响应时间
                        response_time = time.time() - request_start_time
                        self._update_timeout_stats(provider, response_time, True)
                        
                        if response.status == 200:
                            try:
                                # 先读取响应文本，再解析JSON，避免连接关闭问题
                                response_text = await response.text()
                                if not response_text:
                                    log_error(f"{provider} 响应文本为空")
                                    return None
                                
                                data = json.loads(response_text)
                                if data is None:
                                    log_error(f"{provider} 响应数据为None")
                                    return None
                                return self._parse_ai_response(provider, data)
                            except json.JSONDecodeError as e:
                                log_error(f"{provider} JSON解析失败: {e}")
                                log_error(f"{provider} 响应文本: {response_text[:200]}...")
                                return None
                            except Exception as e:
                                log_error(f"{provider} 响应处理失败: {type(e).__name__}: {e}")
                                import traceback
                                log_error(f"响应处理堆栈:\n{traceback.format_exc()}")
                                return None
                        else:
                            error_text = await response.text()
                            log_error(f"{provider} API调用失败: {response.status} - {error_text[:200]}")
                            return None
                        
                except asyncio.TimeoutError:
                    # 记录超时统计
                    self._update_timeout_stats(provider, 0, False, timeout_type='timeout')
                    log_error(f"{provider} 请求超时（{adjusted_timeout['total_timeout']}秒）")
                    raise  # 重新抛出异常供上层处理
                    
                except aiohttp.ClientConnectionError as e:
                    # 专门的连接错误处理
                    self._update_timeout_stats(provider, 0, False, timeout_type='connection_error')
                    log_error(f"{provider} 连接错误: {type(e).__name__}: {e}")
                    raise  # 重新抛出异常供上层处理
                    
                except aiohttp.ClientPayloadError as e:
                    # 专门的载荷错误处理
                    self._update_timeout_stats(provider, 0, False, timeout_type='payload_error')
                    log_error(f"{provider} 载荷错误: {type(e).__name__}: {e}")
                    raise  # 重新抛出异常供上层处理
                    
                except Exception as e:
                    # 记录异常统计
                    self._update_timeout_stats(provider, 0, False, timeout_type='error')
                    log_error(f"{provider} API调用异常: {type(e).__name__}: {e}")
                    import traceback
                    log_error(f"{provider} 完整堆栈:\n{traceback.format_exc()}")
                    raise  # 重新抛出异常供上层处理
                        
        except Exception as e:
            log_error(f"{provider} API调用异常: {type(e).__name__}: {e}")
            import traceback
            log_error(f"{provider} 完整堆栈:\n{traceback.format_exc()}")
            return None
    
    def generate_fallback_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成智能回退信号 - 基于技术指标"""
        try:
            log_info("📊 使用智能技术回退信号")
            
            # 获取技术指标
            technical_data = market_data.get('technical_data', {})
            rsi = float(technical_data.get('rsi', 50))
            macd = technical_data.get('macd', 'HOLD')
            ma_status = technical_data.get('ma_status', 'HOLD')
            
            # 获取趋势分析
            trend_analysis = market_data.get('trend_analysis', {})
            overall_trend = trend_analysis.get('overall', 'neutral')
            
            # 计算信号权重
            buy_signals = 0
            sell_signals = 0
            hold_signals = 0
            
            # RSI信号
            if rsi < 30:
                buy_signals += 1
                log_info(f"   RSI买入信号: {rsi:.1f}")
            elif rsi > 70:
                sell_signals += 1
                log_info(f"   RSI卖出信号: {rsi:.1f}")
            else:
                hold_signals += 1
                log_info(f"   RSI持有信号: {rsi:.1f}")
            
            # MACD信号
            if macd == 'BUY':
                buy_signals += 1
                log_info(f"   MACD买入信号")
            elif macd == 'SELL':
                sell_signals += 1
                log_info(f"   MACD卖出信号")
            else:
                hold_signals += 1
                log_info(f"   MACD持有信号")
            
            # 均线信号
            if ma_status == 'BUY':
                buy_signals += 1
                log_info(f"   均线买入信号")
            elif ma_status == 'SELL':
                sell_signals += 1
                log_info(f"   均线卖出信号")
            else:
                hold_signals += 1
                log_info(f"   均线持有信号")
            
            # 趋势信号
            if overall_trend == 'up':
                buy_signals += 1
                log_info(f"   趋势向上信号")
            elif overall_trend == 'down':
                sell_signals += 1
                log_info(f"   趋势向下信号")
            else:
                hold_signals += 1
                log_info(f"   趋势中性信号")
            
            # 确定最终信号
            if buy_signals > sell_signals and buy_signals > hold_signals:
                final_signal = 'BUY'
                confidence = 0.50 + (buy_signals / 4) * 0.3  # 0.5-0.8
            elif sell_signals > buy_signals and sell_signals > hold_signals:
                final_signal = 'SELL'
                confidence = 0.50 + (sell_signals / 4) * 0.3  # 0.5-0.8
            else:
                final_signal = 'HOLD'
                confidence = 0.50 + (hold_signals / 4) * 0.3  # 0.5-0.8
            
            # 确保信心度在合理范围内
            confidence = max(0.3, min(0.9, confidence))
            
            # 构建建议文本
            suggestions = []
            if rsi < 30:
                suggestions.append(f"RSI:{final_signal}")
            elif rsi > 70:
                suggestions.append(f"RSI:{final_signal}")
            else:
                suggestions.append(f"RSI:HOLD")
            
            suggestions.append(f"MACD:{macd}")
            suggestions.append(f"MA:{ma_status}")
            suggestions.append(f"位置:{final_signal}")
            suggestions.append(f"趋势:{'HOLD' if overall_trend == 'neutral' else overall_trend.upper()}")
            
            advice = "技术指标回退: " + ", ".join(suggestions)
            
            log_info(f"📊 使用智能技术回退信号: {final_signal} (信心: {confidence:.2f})")
            
            return {
                'signal': final_signal,
                'confidence': confidence,
                'reason': advice,
                'provider': 'technical_fallback',
                'is_fallback': True
            }
            
        except Exception as e:
            log_error(f"回退信号生成失败: {e}")
            # 返回默认的保守信号
            return {
                'signal': 'HOLD',
                'confidence': 0.3,
                'reason': '回退信号生成异常，使用保守持有',
                'provider': 'error_fallback',
                'is_fallback': True
            }
    
    async def _retry_provider_request(self, provider: str, prompt: str, timeout: float, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """增强版重试机制 - 修复连接问题"""
        config = self.provider_configs.get(provider)
        if not config:
            return None
            
        # 优化的指数退避策略
        retry_delays = [1.5, 3.0, 6.0]  # 更合理的退避时间
        max_retries = min(len(retry_delays), 2)  # 最多重试2次
        
        for retry_count in range(max_retries):
            delay = retry_delays[retry_count]
            log_info(f"⏰ {provider} 增强重试: 第{retry_count + 1}次尝试，延迟{delay}秒")
            
            await asyncio.sleep(delay)
            
            # 检查重试成本限制
            if not self._check_retry_cost_limit(provider):
                log_warning(f"⚠️ {provider} 重试成本超出限制，停止重试")
                break
                
            # 更新重试成本
            self._update_retry_cost(provider)
            
            try:
                # 构建增强的请求头
                headers = {
                    'Authorization': f'Bearer {config["api_key"]}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'AlphaPilotBot/1.0',
                    'Accept': 'application/json',
                    'Connection': 'keep-alive'
                }
                
                # 构建请求载荷
                payload = {
                    'model': config['model'],
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': config['temperature'],
                    'max_tokens': config.get('max_tokens', 150),
                    'top_p': config.get('top_p', 0.9)
                }
                
                # 发送增强重试请求
                async with session.post(
                    config['url'],
                    headers=headers,
                    json=payload,
                    ssl=True,  # 启用SSL
                    allow_redirects=True,
                    max_redirects=3,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    if response.status == 200:
                        try:
                            # 先读取文本再解析JSON，避免连接问题
                            response_text = await response.text()
                            if not response_text:
                                log_warning(f"{provider} 重试响应为空")
                                continue
                                
                            data = json.loads(response_text)
                            log_info(f"✅ {provider} 重试成功")
                            return data
                        except json.JSONDecodeError as e:
                            log_error(f"{provider} 重试JSON解析失败: {e}")
                            log_error(f"{provider} 响应文本: {response_text[:100]}...")
                            continue
                        except Exception as e:
                            log_error(f"{provider} 重试响应处理失败: {e}")
                            continue
                    else:
                        error_text = await response.text()
                        log_warning(f"{provider} 重试失败: {response.status} - {error_text[:100]}...")
                        
                        # 针对特定状态码的特殊处理
                        if response.status == 429:  # 速率限制
                            log_warning(f"{provider} 遇到速率限制，增加延迟")
                            await asyncio.sleep(delay * 2)  # 额外延迟
                        elif response.status >= 500:  # 服务器错误
                            log_warning(f"{provider} 服务器错误，继续重试")
                            continue
                        else:
                            log_warning(f"{provider} 客户端错误，停止重试")
                            break
                            
            except asyncio.TimeoutError:
                log_warning(f"{provider} 重试超时")
                # 超时时增加下一次重试的延迟
                if retry_count < max_retries - 1:
                    await asyncio.sleep(delay * 0.5)
                continue
                
            except aiohttp.ClientConnectionError as e:
                log_warning(f"{provider} 重试连接错误: {e}")
                # 连接错误时尝试更长的延迟
                if retry_count < max_retries - 1:
                    await asyncio.sleep(delay * 1.5)
                continue
                
            except aiohttp.ClientPayloadError as e:
                log_warning(f"{provider} 重试载荷错误: {e}")
                continue
                
            except Exception as e:
                log_warning(f"{provider} 重试异常: {type(e).__name__}: {e}")
                continue
        
        log_error(f"{provider} 增强重试最终失败")
        return None
    
    def _build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建AI提示词（基础版本）"""
        return self._build_enhanced_prompt('default', market_data)
    
    def _build_enhanced_prompt(self, provider: str, market_data: Dict[str, Any]) -> str:
        """构建增强的AI提示词 - 融合之前项目的成功经验"""
        
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
        
        # 为不同提供商定制分析框架 - 基于之前项目的成功经验
        provider_frameworks = {
            'deepseek': f"""
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

【🎯 震荡市专用策略】
震荡市识别：价格波动<4%，ATR<1.5%，趋势强度<0.5%
🔄 区间交易策略：
1. 靠近支撑位（<25%）+ 反转信号 → HIGH信心BUY
2. 靠近阻力位（>75%）+ 反转信号 → HIGH信心SELL
3. 区间中点（40-60%）+ 明确信号 → MEDIUM信心交易
4. 区间突破立即止损（0.3%）

⚠️ 震荡市风控：
- 每日最多2次交易
- 盈利0.8%立即止盈
- 亏损0.5%立即止损
- 仓位降低至60%
- 最长持仓2小时

🚫 禁止交易：
- 波动率<1.5%（无行情）
- 无明确区间形成
- 区间太窄（<0.5%）或太宽（>4%）
""",
            'kimi': f"""
【KIMI当前市场分析】
价格: ${price:,.2f}
变化: {price_change_pct:+.2f}%
RSI: {rsi:.1f}
趋势: {overall_trend}

【K线数据】
基于{len(price_history) if price_history else 0}根K线的技术分析

【持仓状态】
{position_text}

{last_signal_info}

【KIMI策略要求】
1. 专注15分钟周期交易
2. 基于市场波动率动态设置止盈止损
3. RSI交易规则：
   - RSI<35：超卖区域，优先买入
   - RSI>70：超买区域，优先卖出
   - 35≤RSI≤70：中性区域，结合趋势判断
4. 震荡市区间交易，趋势市顺势交易
5. 动态止盈止损：系统会自动基于市场波动率和持仓状态计算最优TP/SL
""",
            'qwen': f"""
【QWEN量化市场分析】
当前价格: ${price:,.2f}
价格变化: {price_change_pct:+.2f}%
RSI(14): {rsi:.1f}
ATR: {atr_pct:.2f}%
趋势强度: {trend}
整体技术: {overall_trend}

【K线量化分析】
基于{len(price_history) if price_history else 0}根K线的统计模型

【持仓量化状态】
{position_text}

【QWEN动态风控参数】
- 基于ATR波动率动态调整止损止盈
- 系统会自动计算最优TP/SL
- 最大仓位: 90%
- 低波动时降低仓位

【QWEN量化决策要求】
完全基于统计模型和概率计算
信心等级要反映统计显著性
用数据说话，避免主观判断
""",
            'openai': f"""
【OPENAI综合分析框架】
技术面: RSI={rsi:.1f}, 趋势={overall_trend}
基本面: {sentiment_text}
风险管理: {tp_sl_hint}
市场结构: {"震荡" if is_consolidation else "趋势"}

【当前市场数据】
价格: ${price:,.2f} (位置: {price_position:.1f}%)
波动: {atr_pct:.2f}%
持仓: {position_text}

【OPENAI决策矩阵】
多重确认: 技术+情绪+风险综合评分
独立判断: 避免羊群效应，刻意寻找不同观点
动态调整: 根据市场状态实时修正
逆向思维: 与主流观点保持适当差异
""",
            'default': f"""
【市场分析】
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
        """获取多AI信号（增强版）- 实现指数退避重试和成本控制"""
        if providers is None:
            providers = ['deepseek', 'kimi', 'openai']
            
        # 过滤掉未配置的提供商
        enabled_providers = [p for p in providers if self.providers.get(p, {}).get('api_key')]
        
        if not enabled_providers:
            log_warning("没有可用的AI提供商")
            return []
        
        signals = []
        failed_providers = []
        successful_providers = []
        
        for provider in enabled_providers:
            provider_success = False
            provider_config = self.timeout_config.get(provider, self.timeout_config['openai'])
            max_retries = provider_config['max_retries']
            
            for attempt in range(max_retries + 1):
                try:
                    # 检查重试成本限制
                    if attempt > 0 and not self._check_retry_cost_limit(provider):
                        log_warning(f"⚠️ {provider} 重试成本超出限制，跳过重试")
                        break
                    
                    # 获取动态调整的超时时间
                    adjusted_timeout = self._calculate_dynamic_timeout(provider, provider_config)
                    signal_timeout = adjusted_timeout['total_timeout']
                    
                    log_info(f"🔄 {provider} 第{attempt + 1}次尝试，超时:{signal_timeout:.1f}s")
                    
                    signal = await asyncio.wait_for(
                        self.get_signal_from_provider(provider, market_data),
                        timeout=signal_timeout
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
                            # 计算指数退避延迟
                            retry_delay = self._calculate_exponential_backoff(provider, attempt, adjusted_timeout['retry_base_delay'])
                            log_warning(f"{provider}第{attempt + 1}次尝试失败，{retry_delay:.1f}秒后重试...")
                            await asyncio.sleep(retry_delay)
                            # 更新重试成本
                            self._update_retry_cost(provider)
                        else:
                            log_error(f"{provider}最终失败")
                            
                except asyncio.TimeoutError:
                    log_error(f"{provider}请求超时（动态超时）")
                    if attempt < max_retries:
                        # 计算指数退避延迟
                        retry_delay = self._calculate_exponential_backoff(provider, attempt, provider_config['retry_base_delay'])
                        log_info(f"{provider}超时重试，等待{retry_delay:.1f}秒...")
                        await asyncio.sleep(retry_delay)
                        # 更新重试成本
                        self._update_retry_cost(provider)
                        
                except Exception as e:
                    log_error(f"{provider}异常: {e}")
                    if attempt < max_retries:
                        # 计算指数退避延迟
                        retry_delay = self._calculate_exponential_backoff(provider, attempt, provider_config['retry_base_delay'])
                        log_info(f"{provider}异常重试，等待{retry_delay:.1f}秒...")
                        await asyncio.sleep(retry_delay)
                        # 更新重试成本
                        self._update_retry_cost(provider)
            
            if not provider_success:
                failed_providers.append(provider)
        
        # 记录融合统计和超时性能
        log_info(f"📊 AI信号获取统计: 成功={len(successful_providers)}, 失败={len(failed_providers)}")
        log_info(f"📊 重试成本统计: 当前成本={self.retry_cost_config['current_daily_cost']:.1f}, 上限={self.retry_cost_config['max_daily_cost']}")
        
        # 输出超时性能统计
        self._log_timeout_performance()
        
        if failed_providers:
            log_warning(f"⚠️ 失败的AI提供商: {failed_providers}")
        
        return signals
    
    def _log_timeout_performance(self):
        """记录超时性能统计"""
        try:
            global_stats = self.timeout_stats['global']
            if global_stats['total_requests'] > 0:
                log_info(f"📊 全局超时性能: 总请求={global_stats['total_requests']}, 超时率={global_stats['timeout_rate']:.2%}")
            
            # 输出各提供商的统计
            for provider, stats in self.timeout_stats['provider'].items():
                if stats['total_requests'] > 0:
                    log_info(f"📊 {provider} 性能: 成功率={stats['success_rate']:.2%}, 平均响应={stats['avg_response_time']:.1f}s, 请求数={stats['total_requests']}")
                    
        except Exception as e:
            log_error(f"超时性能记录失败: {e}")
    
    async def _generate_enhanced_fallback_signal_async(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成增强兜底信号 - 使用专门的兜底策略模块"""
        try:
            log_info("🛡️ 启动增强兜底信号生成...")
            
            # 获取AI信号历史用于兜底分析
            from utils import memory_manager
            signal_history = memory_manager.get_history('signals', limit=20)
            
            # 延迟导入增强兜底引擎以避免循环依赖
            from strategies.strategies_adaptive_optimizer import generate_enhanced_fallback_signal
            enhanced_fallback = await generate_enhanced_fallback_signal(market_data, signal_history)
            
            if enhanced_fallback and enhanced_fallback.get('is_enhanced_fallback'):
                log_info(f"✅ 增强兜底信号生成成功: {enhanced_fallback['signal']} (信心: {enhanced_fallback['confidence']:.2f}, 质量: {enhanced_fallback['quality_score']:.2f})")
                log_info(f"📊 兜底类型: {enhanced_fallback['fallback_type']}")
                log_info(f"💡 兜底理由: {enhanced_fallback['reason']}")
                
                # 记录兜底信号使用统计
                self._update_fallback_stats(enhanced_fallback)
                
                return enhanced_fallback
            else:
                log_warning("⚠️ 增强兜底信号生成失败，回退到传统兜底")
                return self._generate_smart_fallback_signal(market_data)
                
        except Exception as e:
            log_error(f"增强兜底信号生成异常: {e}")
            log_warning("⚠️ 增强兜底失败，回退到传统兜底")
            return self._generate_smart_fallback_signal(market_data)
    
    def _update_fallback_stats(self, fallback_signal: Dict[str, Any]) -> None:
        """更新兜底信号使用统计"""
        try:
            fallback_type = fallback_signal.get('fallback_type', 'unknown')
            quality_score = fallback_signal.get('quality_score', 0)
            
            # 这里可以添加统计逻辑，如记录兜底类型使用频率、质量分布等
            log_info(f"📊 兜底统计: 类型={fallback_type}, 质量={quality_score:.2f}")
            
        except Exception as e:
            log_warning(f"兜底统计更新失败: {e}")
    
    def _generate_smart_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于增强技术指标生成智能回退信号 - 多因子分析（保持原有逻辑作为回退）"""
        try:
            # 获取扩展技术指标数据
            technical_data = market_data.get('technical_data', {})
            price = float(market_data.get('price', 0))
            
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
            signal_score += macd_factor['score'] * 0.8  # MACD权重0.8
            confidence_factors.append(macd_factor['confidence'])
            
            # 3. 均线因子分析
            ma_factor = self._calculate_ma_factor(ma_status)
            signal_score += ma_factor['score'] * 0.6  # 均线权重0.6
            confidence_factors.append(ma_factor['confidence'])
            
            # 4. 布林带因子分析
            bollinger_factor = self._calculate_bollinger_factor(bollinger, price)
            signal_score += bollinger_factor['score'] * 0.7  # 布林带权重0.7
            confidence_factors.append(bollinger_factor['confidence'])
            
            # 5. 成交量因子分析
            volume_factor = self._calculate_volume_factor(volume_ratio)
            signal_score += volume_factor['score'] * 0.5  # 成交量权重0.5
            confidence_factors.append(volume_factor['confidence'])
            
            # 6. 支撑阻力因子分析
            sr_factor = self._calculate_support_resistance_factor(support_resistance, price)
            signal_score += sr_factor['score'] * 0.9  # 支撑阻力权重0.9
            confidence_factors.append(sr_factor['confidence'])
            
            # 7. 市场环境识别
            market_factor = self._calculate_market_environment_factor(market_volatility, trend_analysis)
            signal_score += market_factor['score'] * 0.4  # 市场环境权重0.4
            confidence_factors.append(market_factor['confidence'])
            
            # 计算最终信号和信心值
            final_signal = self._determine_signal_from_score(signal_score)
            final_confidence = self._calculate_weighted_confidence(confidence_factors, signal_score)
            
            # 生成详细理由
            current_price = float(market_data.get('price', 50000.0))
            reason = self._generate_enhanced_reason(
                final_signal, signal_score, confidence_factors,
                rsi, macd, ma_status, bollinger, volume_ratio,
                support_resistance, market_volatility, price_position, current_price
            )
            
            log_info(f"🤖 增强智能回退信号生成: {final_signal} (信心: {final_confidence:.2f}, 得分: {signal_score:.2f})")
            log_info(f"📊 回退理由: {reason}")
            
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
            log_error(f"增强智能回退信号生成失败: {e}")
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
            # RSI信号得分
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
            if price_position < 30 and rsi < 40:  # 低位+弱势
                rsi_score *= 1.2
                confidence *= 1.1
            elif price_position > 70 and rsi > 60:  # 高位+强势
                rsi_score *= 1.2
                confidence *= 1.1
            
            return {
                'score': rsi_score,
                'confidence': confidence,
                'factor_name': 'RSI'
            }
            
        except Exception as e:
            log_error(f"RSI因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.3, 'factor_name': 'RSI'}
    
    def _calculate_macd_factor(self, macd: Dict[str, Any]) -> Dict[str, Any]:
        """计算MACD因子"""
        try:
            if not macd or not isinstance(macd, dict):
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MACD'}
            
            # 获取MACD数据
            macd_line = float(macd.get('macd', 0))
            signal_line = float(macd.get('signal', 0))
            histogram = float(macd.get('histogram', 0))
            
            score = 0.0
            confidence = 0.6
            
            # MACD金叉/死叉判断
            if macd_line > signal_line and macd_line > 0:  # 金叉且在零轴上方
                score = 0.7  # 强势买入信号
                confidence = 0.8
            elif macd_line < signal_line and macd_line < 0:  # 死叉且在零轴下方
                score = -0.7  # 强势卖出信号
                confidence = 0.8
            elif macd_line > signal_line and macd_line < 0:  # 金叉但在零轴下方
                score = -0.3  # 弱势买入信号
                confidence = 0.5
            elif macd_line < signal_line and macd_line > 0:  # 死叉但在零轴上方
                score = 0.3  # 弱势卖出信号
                confidence = 0.5
            
            # 柱状图强度调整
            if abs(histogram) > 0:
                histogram_strength = min(abs(histogram) / 100, 1.0)  # 标准化
                score *= (1 + histogram_strength * 0.3)  # 最多增强30%
                confidence *= (1 + histogram_strength * 0.2)
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'MACD'
            }
            
        except Exception as e:
            log_error(f"MACD因子计算失败: {e}")
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
                score = -0.6  # 买入信号
                confidence = 0.7
            elif '空头排列' in ma_status_lower or 'bearish' in ma_status_lower:
                score = 0.6  # 卖出信号
                confidence = 0.7
            elif '震荡' in ma_status_lower or 'consolidation' in ma_status_lower:
                score = 0.0
                confidence = 0.3
            elif '金叉' in ma_status_lower or 'golden cross' in ma_status_lower:
                score = -0.8  # 强烈买入信号
                confidence = 0.8
            elif '死叉' in ma_status_lower or 'death cross' in ma_status_lower:
                score = 0.8  # 强烈卖出信号
                confidence = 0.8
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'MA'
            }
            
        except Exception as e:
            log_error(f"均线因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'MA'}
    
    def _calculate_bollinger_factor(self, bollinger: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """计算布林带因子"""
        try:
            if not bollinger or not isinstance(bollinger, dict) or current_price <= 0:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
            
            # 获取布林带数据
            upper_band = float(bollinger.get('upper', 0))
            lower_band = float(bollinger.get('lower', 0))
            middle_band = float(bollinger.get('middle', 0))
            
            if upper_band <= lower_band or middle_band <= 0:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
            
            score = 0.0
            confidence = 0.6
            
            # 计算价格在布林带中的位置
            band_range = upper_band - lower_band
            if band_range > 0:
                price_position_in_band = (current_price - lower_band) / band_range
                
                # 布林带交易策略
                if price_position_in_band < 0.2:  # 靠近下轨
                    score = -0.7  # 买入信号
                    confidence = 0.8
                elif price_position_in_band > 0.8:  # 靠近上轨
                    score = 0.7  # 卖出信号
                    confidence = 0.8
                elif 0.4 <= price_position_in_band <= 0.6:  # 靠近中轨
                    score = 0.0
                    confidence = 0.4
                else:
                    # 中间区域，轻微信号
                    if price_position_in_band < 0.4:
                        score = -0.3
                    else:
                        score = 0.3
                    confidence = 0.5
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'Bollinger'
            }
            
        except Exception as e:
            log_error(f"布林带因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Bollinger'}
    
    def _calculate_volume_factor(self, volume_ratio: float) -> Dict[str, Any]:
        """计算成交量因子"""
        try:
            score = 0.0
            confidence = 0.4
            
            # 成交量比率分析
            if volume_ratio > 2.0:  # 成交量放大2倍以上
                score = 0.0  # 中性，需要结合价格判断
                confidence = 0.7
            elif volume_ratio > 1.5:  # 成交量放大1.5倍以上
                score = 0.0
                confidence = 0.6
            elif volume_ratio < 0.5:  # 成交量萎缩50%以上
                score = 0.0  # 中性，市场观望
                confidence = 0.5
            else:
                score = 0.0
                confidence = 0.3
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'Volume'
            }
            
        except Exception as e:
            log_error(f"成交量因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'Volume'}
    
    def _calculate_support_resistance_factor(self, sr_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """计算支撑阻力因子"""
        try:
            if not sr_data or not isinstance(sr_data, dict) or current_price <= 0:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
            
            # 获取支撑阻力位
            support = float(sr_data.get('support', 0))
            resistance = float(sr_data.get('resistance', 0))
            nearest_support = float(sr_data.get('nearest_support', support))
            nearest_resistance = float(sr_data.get('nearest_resistance', resistance))
            
            if support <= 0 or resistance <= 0 or support >= resistance:
                return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
            
            score = 0.0
            confidence = 0.7
            
            # 计算与支撑阻力的距离
            support_distance = abs(current_price - nearest_support) / current_price * 100
            resistance_distance = abs(current_price - nearest_resistance) / current_price * 100
            
            # 支撑阻力策略
            if support_distance < 1.0:  # 靠近支撑位（1%以内）
                score = -0.8  # 强烈买入信号
                confidence = 0.9
            elif resistance_distance < 1.0:  # 靠近阻力位（1%以内）
                score = 0.8  # 强烈卖出信号
                confidence = 0.9
            elif support_distance < 2.0:  # 接近支撑位（2%以内）
                score = -0.5
                confidence = 0.7
            elif resistance_distance < 2.0:  # 接近阻力位（2%以内）
                score = 0.5
                confidence = 0.7
            else:
                # 在中间区域，根据相对距离给出轻微信号
                total_range = resistance - support
                if total_range > 0:
                    position_in_range = (current_price - support) / total_range
                    if position_in_range < 0.3:  # 靠近支撑
                        score = -0.3
                    elif position_in_range > 0.7:  # 靠近阻力
                        score = 0.3
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'SupportResistance'
            }
            
        except Exception as e:
            log_error(f"支撑阻力因子计算失败: {e}")
            return {'score': 0.0, 'confidence': 0.2, 'factor_name': 'SupportResistance'}
    
    def _calculate_market_environment_factor(self, volatility: str, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """计算市场环境因子"""
        try:
            score = 0.0
            confidence = 0.5
            
            # 波动率分析
            volatility_lower = str(volatility).lower()
            if 'high' in volatility_lower or '高' in volatility_lower:
                # 高波动市场，降低信号强度
                confidence *= 0.8
            elif 'low' in volatility_lower or '低' in volatility_lower:
                # 低波动市场，标准处理
                confidence *= 1.0
            else:
                # 正常波动
                confidence *= 0.9
            
            # 趋势分析
            if trend_analysis and isinstance(trend_analysis, dict):
                overall_trend = str(trend_analysis.get('overall', 'neutral')).lower()
                if 'bullish' in overall_trend or '上涨' in overall_trend:
                    score = -0.2  # 轻微买入倾向
                elif 'bearish' in overall_trend or '下跌' in overall_trend:
                    score = 0.2  # 轻微卖出倾向
            
            return {
                'score': score,
                'confidence': confidence,
                'factor_name': 'MarketEnvironment'
            }
            
        except Exception as e:
            log_error(f"市场环境因子计算失败: {e}")
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
            log_error(f"信号得分转换失败: {e}")
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
            if signal_strength > 0.7:  # 强信号
                confidence_multiplier = 1.1
            elif signal_strength > 0.4:  # 中等信号
                confidence_multiplier = 1.0
            else:  # 弱信号
                confidence_multiplier = 0.8
            
            # 基于因子一致性调整信心值
            if confidence_factors:
                confidence_std = (sum((c - avg_confidence) ** 2 for c in confidence_factors) / len(confidence_factors)) ** 0.5
                if confidence_std < 0.1:  # 因子一致性高
                    consistency_multiplier = 1.1
                elif confidence_std < 0.2:  # 因子一致性中等
                    consistency_multiplier = 1.0
                else:  # 因子一致性低
                    consistency_multiplier = 0.9
            else:
                consistency_multiplier = 1.0
            
            final_confidence = avg_confidence * confidence_multiplier * consistency_multiplier
            
            # 确保信心值在合理范围内
            return max(0.3, min(0.95, final_confidence))
            
        except Exception as e:
            log_error(f"加权信心值计算失败: {e}")
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
            log_error(f"增强理由生成失败: {e}")
            return "基于技术指标的智能回退信号"
    
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
    
    def fuse_signals(self, signals: List[AISignal], market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """融合多AI信号 - 增强版，完善信号统计逻辑"""
        log_info(f"🔍 开始融合AI信号，共收到 {len(signals)} 个信号")
        
        # 分析信号多样性
        diversity_analysis = self._analyze_signal_diversity(signals)
        
        # 获取配置的AI提供商总数
        total_configured = len([p for p in ['deepseek', 'kimi', 'qwen', 'openai'] if self.providers.get(p, {}).get('api_key')])
        
        if not signals:
            log_warning("⚠️ 没有可用的AI信号，使用增强智能回退信号")
            # 使用增强的智能回退信号
            smart_fallback = self._generate_smart_fallback_signal(market_data or {})
            return {
                'signal': smart_fallback['signal'],
                'confidence': smart_fallback['confidence'],
                'reason': smart_fallback['reason'],
                'providers': [],
                'fusion_method': 'enhanced_smart_fallback',
                'fusion_analysis': self._generate_enhanced_fusion_analysis(0, total_configured, '所有AI信号获取失败，使用多因子智能回退策略'),
                'signal_statistics': self._generate_detailed_signal_statistics([]),
                'diversity_analysis': diversity_analysis
            }

        if len(signals) == 1:
            signal = signals[0]
            log_info(f"📊 单信号模式: {signal.provider} -> {signal.signal} (信心: {signal.confidence:.2f})")
            return {
                'signal': signal.signal,
                'confidence': signal.confidence,
                'reason': f"{signal.provider}: {signal.reason}",
                'providers': [signal.provider],
                'fusion_method': 'single_enhanced',
                'fusion_analysis': self._generate_enhanced_fusion_analysis(1, total_configured, f'仅{signal.provider}信号可用'),
                'signal_statistics': self._generate_detailed_signal_statistics(signals),
                'diversity_analysis': diversity_analysis
            }

        # 多信号融合 - 增强版逻辑
        buy_votes = sum(1 for s in signals if s.signal == 'BUY')
        sell_votes = sum(1 for s in signals if s.signal == 'SELL')
        hold_votes = sum(1 for s in signals if s.signal == 'HOLD')

        total_signals = len(signals)

        # 计算加权信心 - 基于实际成功信号
        buy_confidence = sum(s.confidence for s in signals if s.signal == 'BUY') / total_signals if total_signals > 0 else 0
        sell_confidence = sum(s.confidence for s in signals if s.signal == 'SELL') / total_signals if total_signals > 0 else 0
        hold_confidence = sum(s.confidence for s in signals if s.signal == 'HOLD') / total_signals if total_signals > 0 else 0

        log_info(f"🗳️ 投票统计: BUY={buy_votes}, SELL={sell_votes}, HOLD={hold_votes}")
        log_info(f"📈 信心分布: BUY={buy_confidence:.2f}, SELL={sell_confidence:.2f}, HOLD={hold_confidence:.2f}")
        
        # 生成详细的信号统计
        signal_statistics = self._generate_detailed_signal_statistics(signals)

        # 🚀 增强决策逻辑 - 减少过度保守倾向
        majority_threshold = 0.5  # 降低门槛到50%
        strong_consensus_threshold = 0.7  # 强共识70%
        weak_consensus_threshold = 0.6   # 弱共识60%
        
        # 计算各信号的占比
        buy_ratio = buy_votes / total_signals
        sell_ratio = sell_votes / total_signals
        hold_ratio = hold_votes / total_signals

        # 🔥 动态信心调整 - 基于市场条件
        market_data = market_data or {}
        technical_data = market_data.get('technical_data', {})
        
        # 获取市场状态
        rsi = float(technical_data.get('rsi', 50))
        atr_pct = float(technical_data.get('atr_pct', 1.0))
        trend = str(market_data.get('trend_strength', '震荡'))
        
        # 计算动态信心调整因子
        confidence_adjustment = self._calculate_dynamic_confidence_adjustment(rsi, atr_pct, trend)
        
        # 🎯 智能信号融合 - 减少保守倾向
        if buy_ratio >= strong_consensus_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence * confidence_adjustment['buy_multiplier']
            reason = f"强共识买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
            log_info(f"🎯 强共识决策: BUY (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['buy_multiplier']:.2f})")
        elif sell_ratio >= strong_consensus_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence * confidence_adjustment['sell_multiplier']
            reason = f"强共识卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
            log_info(f"🎯 强共识决策: SELL (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['sell_multiplier']:.2f})")
        elif hold_ratio >= strong_consensus_threshold:
            # 即使是强HOLD共识，也要考虑是否有交易机会
            if buy_ratio > 0.2 or sell_ratio > 0.2:  # 如果有明显的买卖分歧
                # 选择信心更高的方向
                if buy_confidence > sell_confidence:
                    final_signal = 'BUY'
                    confidence = buy_confidence * 0.8  # 降低信心但保持方向
                    reason = f"HOLD共识中存在买入机会: 选择BUY方向 (信心: {confidence:.2f})"
                    log_info(f"🎯 智能突破: 从HOLD共识中选择BUY方向 (信心: {confidence:.2f})")
                else:
                    final_signal = 'SELL'
                    confidence = sell_confidence * 0.8
                    reason = f"HOLD共识中存在卖出机会: 选择SELL方向 (信心: {confidence:.2f})"
                    log_info(f"🎯 智能突破: 从HOLD共识中选择SELL方向 (信心: {confidence:.2f})")
            else:
                final_signal = 'HOLD'
                confidence = hold_confidence * confidence_adjustment['hold_multiplier']
                reason = f"强共识持仓: {hold_votes}/{total_signals}票支持 ({hold_ratio*100:.0f}%)"
                log_info(f"🎯 强共识决策: HOLD (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['hold_multiplier']:.2f})")
        elif buy_ratio >= weak_consensus_threshold:
            final_signal = 'BUY'
            confidence = buy_confidence * confidence_adjustment['buy_multiplier'] * 0.95
            reason = f"多数支持买入: {buy_votes}/{total_signals}票支持 ({buy_ratio*100:.0f}%)"
            log_info(f"🎯 多数决策: BUY (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['buy_multiplier']:.2f})")
        elif sell_ratio >= weak_consensus_threshold:
            final_signal = 'SELL'
            confidence = sell_confidence * confidence_adjustment['sell_multiplier'] * 0.95
            reason = f"多数支持卖出: {sell_votes}/{total_signals}票支持 ({sell_ratio*100:.0f}%)"
            log_info(f"🎯 多数决策: SELL (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['sell_multiplier']:.2f})")
        else:
            # 没有明显多数，但减少过度保守
            if buy_confidence > sell_confidence and buy_confidence > hold_confidence:
                final_signal = 'BUY'
                confidence = buy_confidence * 0.7  # 降低但保持方向
                reason = f"无明显共识但买入信心最高: 选择BUY方向 (信心: {confidence:.2f})"
                log_info(f"🎯 智能选择: 选择信心最高的BUY方向 (信心: {confidence:.2f})")
            elif sell_confidence > buy_confidence and sell_confidence > hold_confidence:
                final_signal = 'SELL'
                confidence = sell_confidence * 0.7
                reason = f"无明显共识但卖出信心最高: 选择SELL方向 (信心: {confidence:.2f})"
                log_info(f"🎯 智能选择: 选择信心最高的SELL方向 (信心: {confidence:.2f})")
            else:
                final_signal = 'HOLD'
                confidence = hold_confidence * confidence_adjustment['hold_multiplier']
                reason = f"无明显共识，建议观望: HOLD {hold_votes}/{total_signals}票 ({hold_ratio*100:.0f}%)"
                log_info(f"🎯 保守决策: HOLD (信心: {confidence:.2f}, 调整因子: {confidence_adjustment['hold_multiplier']:.2f})")

        # 基于成功率调整信心 - 但减少过度惩罚
        success_rate = total_signals / total_configured if total_configured > 0 else 1.0
        if success_rate < 0.3:  # 只有极低成功率才大幅惩罚
            confidence *= 0.6  # 降低惩罚力度
            reason += f" (AI成功率仅{success_rate*100:.0f}%，降低信心)"
            log_info(f"⚠️ AI成功率极低({success_rate*100:.0f}%)，降低信心至 {confidence:.2f}")
        elif success_rate < 0.5:  # 中等成功率轻微惩罚
            confidence *= 0.85
            reason += f" (AI成功率{success_rate*100:.0f}%，轻微降低信心)"
            log_info(f"⚠️ AI成功率较低({success_rate*100:.0f}%)，轻微降低信心至 {confidence:.2f}")

        # 增强信心调整 - 基于共识度，但设置最小值避免过度压缩
        max_ratio = max(buy_ratio, sell_ratio, hold_ratio)
        confidence_multiplier = max(0.7, max_ratio)  # 设置最小0.7避免过度压缩
        confidence *= confidence_multiplier
        log_info(f"⚖️ 共识度调整: 原始信心 × {confidence_multiplier:.2f} = {confidence:.2f}")

        result = {
            'signal': final_signal,
            'confidence': confidence,
            'reason': reason,
            'providers': [s.provider for s in signals],
            'fusion_method': 'enhanced_multi_factor_voting',
            'fusion_analysis': self._generate_enhanced_fusion_analysis(total_signals, total_configured, reason),
            'signal_statistics': signal_statistics,
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
                return self.fuse_signals(signals, market_data)
        
        log_info(f"✅ AI信号融合完成: {final_signal} (信心: {confidence:.2f})")
        return result

    async def get_ai_signal(self, market_data: Dict[str, Any], provider: str) -> AISignal:
        """获取单个AI提供商的信号（优化版）"""
        """Get AI signal from a specific provider"""
        if provider not in self.providers or not self.providers[provider].get('api_key'):
            log_error(f"AI提供商 {provider} 未配置或不可用")
            return None
            
        try:
            signal = await asyncio.wait_for(
                self.get_signal_from_provider(provider, market_data),
                timeout=10.0  # 从30秒优化到10秒
            )
            return signal
            
        except asyncio.TimeoutError:
            log_error(f"{provider} 请求超时（10秒）")
            return None
        except Exception as e:
            log_error(f"{provider} 异常: {e}")
            return None

    def _calculate_dynamic_timeout(self, provider: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """计算动态调整的超时时间"""
        try:
            # 获取历史统计
            stats = self.timeout_stats['provider'].get(provider, {})
            avg_response_time = stats.get('avg_response_time', 0.0)
            success_rate = stats.get('success_rate', 1.0)
            timeout_count = stats.get('timeout_count', 0)
            total_requests = stats.get('total_requests', 0)
            
            # 基础超时配置
            base_timeout = base_config.copy()
            
            # 如果历史数据不足，使用基础配置
            if total_requests < 5:
                return base_timeout
            
            # 基于成功率调整超时时间
            if success_rate < 0.8:  # 成功率低于80%
                # 增加超时时间
                multiplier = 1.2 if success_rate < 0.6 else 1.1
                base_timeout['total_timeout'] *= multiplier
                base_timeout['response_timeout'] *= multiplier
                log_info(f"⏰ {provider} 成功率低({success_rate:.2f})，超时时间调整: {multiplier:.1f}x")
            
            elif success_rate > 0.95 and avg_response_time > 0:  # 成功率高且响应时间稳定
                # 减少超时时间以提高效率
                multiplier = 0.9
                base_timeout['total_timeout'] *= multiplier
                base_timeout['response_timeout'] *= multiplier
                log_info(f"⏰ {provider} 性能优秀，超时时间优化: {multiplier:.1f}x")
            
            # 基于最近超时情况调整
            recent_timeout_rate = timeout_count / total_requests if total_requests > 0 else 0
            if recent_timeout_rate > 0.2:  # 最近超时率超过20%
                base_timeout['total_timeout'] *= 1.3
                base_timeout['retry_base_delay'] *= 1.2
                log_info(f"⏰ {provider} 最近超时率高({recent_timeout_rate:.2f})，增加超时缓冲")
            
            # 确保最小超时时间
            base_timeout['total_timeout'] = max(base_timeout['total_timeout'], 5.0)
            base_timeout['response_timeout'] = max(base_timeout['response_timeout'], 3.0)
            base_timeout['connection_timeout'] = max(base_timeout['connection_timeout'], 2.0)
            
            return base_timeout
            
        except Exception as e:
            log_error(f"动态超时计算失败: {e}")
            return base_config
    
    def _update_timeout_stats(self, provider: str, response_time: float, success: bool, timeout_type: str = None):
        """更新超时统计信息"""
        try:
            if provider not in self.timeout_stats['provider']:
                self.timeout_stats['provider'][provider] = {
                    'avg_response_time': 0.0,
                    'timeout_count': 0,
                    'total_requests': 0,
                    'success_rate': 1.0,
                    'last_response_time': 0.0
                }
            
            stats = self.timeout_stats['provider'][provider]
            
            # 更新全局统计
            global_stats = self.timeout_stats['global']
            global_stats['total_requests'] += 1
            if not success:
                global_stats['timeout_requests'] += 1
            
            # 更新提供商统计
            stats['total_requests'] += 1
            stats['last_response_time'] = response_time
            
            if success and response_time > 0:
                # 更新平均响应时间（使用移动平均）
                if stats['avg_response_time'] == 0:
                    stats['avg_response_time'] = response_time
                else:
                    stats['avg_response_time'] = (stats['avg_response_time'] * 0.8) + (response_time * 0.2)
            elif not success:
                if timeout_type == 'timeout':
                    stats['timeout_count'] += 1
            
            # 计算成功率
            if stats['total_requests'] > 0:
                stats['success_rate'] = (stats['total_requests'] - stats['timeout_count']) / stats['total_requests']
                global_stats['timeout_rate'] = global_stats['timeout_requests'] / global_stats['total_requests']
            
            # 记录统计更新
            log_info(f"📊 {provider} 超时统计更新: 成功率={stats['success_rate']:.2f}, 平均响应={stats['avg_response_time']:.1f}s, 总请求={stats['total_requests']}")
            
        except Exception as e:
            log_error(f"超时统计更新失败: {e}")
    
    def _calculate_exponential_backoff(self, provider: str, attempt: int, base_delay: float) -> float:
        """计算指数退避延迟时间"""
        try:
            # 基础指数退避公式: base_delay * 2^attempt + jitter
            jitter = random.uniform(0.1, 0.5)  # 添加随机抖动避免惊群效应
            backoff_delay = base_delay * (2 ** attempt) + jitter
            
            # 最大退避时间限制
            max_backoff = 30.0  # 最大30秒
            backoff_delay = min(backoff_delay, max_backoff)
            
            # 基于提供商性能调整退避策略
            provider_stats = self.timeout_stats['provider'].get(provider, {})
            success_rate = provider_stats.get('success_rate', 1.0)
            
            # 成功率低的提供商，增加退避时间
            if success_rate < 0.7:
                backoff_delay *= 1.5
            
            log_info(f"⏰ {provider} 指数退避: 第{attempt}次重试，延迟{backoff_delay:.1f}秒")
            return backoff_delay
            
        except Exception as e:
            log_error(f"指数退避计算失败: {e}")
            return base_delay * (2 ** attempt)
    
    def _check_retry_cost_limit(self, provider: str) -> bool:
        """检查重试成本是否超出限制"""
        try:
            # 检查每日成本限制
            if self.retry_cost_config['current_daily_cost'] >= self.retry_cost_config['max_daily_cost']:
                log_warning(f"⚠️ {provider} 重试成本已达每日上限({self.retry_cost_config['max_daily_cost']})")
                return False
            
            # 计算提供商特定的成本权重
            cost_weight = self.retry_cost_config['cost_weights'].get(provider, 1.0)
            estimated_cost = cost_weight
            
            # 检查是否会超出限制
            if self.retry_cost_config['current_daily_cost'] + estimated_cost > self.retry_cost_config['max_daily_cost']:
                log_warning(f"⚠️ {provider} 重试成本将超出限制，拒绝重试")
                return False
            
            return True
            
        except Exception as e:
            log_error(f"重试成本检查失败: {e}")
            return False
    
    def _update_retry_cost(self, provider: str):
        """更新重试成本"""
        try:
            cost_weight = self.retry_cost_config['cost_weights'].get(provider, 1.0)
            self.retry_cost_config['current_daily_cost'] += cost_weight
            
            log_info(f"💰 重试成本更新: {provider} +{cost_weight:.1f}, 当前总计: {self.retry_cost_config['current_daily_cost']:.1f}")
            
        except Exception as e:
            log_error(f"重试成本更新失败: {e}")

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
            
            # 历史趋势分析（基于超时统计）
            historical_trend = self._analyze_historical_success_trend()
            
            # 提供商性能排名
            provider_rankings = self._rank_provider_performance()
            
            # 🔧 新增4个关键字段计算
            # 1. 共识门槛 - 基于成功信号比例
            consensus_threshold = self._calculate_consensus_threshold(successful_providers, total_configured)
            
            # 2. 动态调整因子 - 基于市场条件和成功率
            dynamic_adjustment = self._calculate_dynamic_adjustment_factor(success_rate, historical_trend)
            
            # 3. 一致性得分 - 基于提供商性能一致性
            consistency_score = self._calculate_consistency_score(provider_rankings)
            
            # 4. 低波动优化标志 - 检测是否应用了低波动优化
            low_volatility_optimized = self._check_low_volatility_optimization()
            
            return {
                'total_providers': total_configured,
                'successful_providers': successful_providers,
                'failed_providers': total_configured - successful_providers,
                'success_rate': success_rate,
                'success_rate_percentage': success_rate * 100,
                'success_level': success_level,
                'partial_success': partial_success,
                'fusion_reason': fusion_reason,
                'historical_trend': historical_trend,
                'provider_rankings': provider_rankings,
                'timestamp': datetime.now().isoformat(),
                'cost_efficiency': self._calculate_cost_efficiency(successful_providers, total_configured),
                # 🔧 新增4个关键字段
                'consensus_threshold': consensus_threshold,
                'dynamic_adjustment': dynamic_adjustment,
                'consistency_score': consistency_score,
                'low_volatility_optimized': low_volatility_optimized
            }
            
        except Exception as e:
            log_error(f"增强融合分析生成失败: {e}")
            return {
                'total_providers': total_configured,
                'successful_providers': successful_providers,
                'failed_providers': total_configured - successful_providers,
                'success_rate': success_rate if 'success_rate' in locals() else 0.0,
                'fusion_reason': fusion_reason,
                'error': str(e),
                # 🔧 出错时提供默认值
                'consensus_threshold': 'unknown',
                'dynamic_adjustment': 0.0,
                'consistency_score': 0.0,
                'low_volatility_optimized': False
            }
    
    def _generate_detailed_signal_statistics(self, signals: List[AISignal]) -> Dict[str, Any]:
        """生成详细的信号统计"""
        try:
            if not signals:
                return {
                    'total_signals': 0,
                    'signal_distribution': {'BUY': 0, 'SELL': 0, 'HOLD': 0},
                    'confidence_stats': {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0},
                    'provider_breakdown': {},
                    'quality_score': 0.0
                }
            
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
            
            return {
                'total_signals': len(signals),
                'signal_distribution': signal_counts,
                'confidence_stats': {
                    'mean': confidence_mean,
                    'std': confidence_std,
                    'min': confidence_min,
                    'max': confidence_max
                },
                'provider_breakdown': provider_breakdown,
                'quality_score': quality_score,
                'diversity_index': self._calculate_diversity_index(signal_counts),
                'consensus_level': self._calculate_consensus_level(signal_counts)
            }
            
        except Exception as e:
            log_error(f"详细信号统计生成失败: {e}")
            return {
                'total_signals': len(signals) if 'signals' in locals() else 0,
                'error': str(e)
            }
    
    def _analyze_historical_success_trend(self) -> Dict[str, Any]:
        """分析历史成功率趋势"""
        try:
            global_stats = self.timeout_stats['global']
            if global_stats['total_requests'] == 0:
                return {'trend': 'no_data', 'trend_direction': 'stable', 'confidence': 0.0}
            
            current_success_rate = 1.0 - global_stats['timeout_rate']
            
            # 基于提供商统计计算趋势
            provider_trends = []
            for provider, stats in self.timeout_stats['provider'].items():
                if stats['total_requests'] > 10:  # 只有足够数据的提供商才考虑
                    provider_trends.append({
                        'provider': provider,
                        'success_rate': stats['success_rate'],
                        'avg_response_time': stats['avg_response_time'],
                        'total_requests': stats['total_requests']
                    })
            
            # 计算整体趋势
            if provider_trends:
                avg_success_rate = sum(p['success_rate'] for p in provider_trends) / len(provider_trends)
                if avg_success_rate > 0.8:
                    trend_direction = 'improving'
                elif avg_success_rate > 0.6:
                    trend_direction = 'stable'
                else:
                    trend_direction = 'declining'
                
                trend_confidence = min(len(provider_trends) / 4, 1.0)  # 基于数据充足度
            else:
                trend_direction = 'stable'
                trend_confidence = 0.0
            
            return {
                'trend': f'current_success_rate: {current_success_rate:.2%}',
                'trend_direction': trend_direction,
                'confidence': trend_confidence,
                'provider_trends': provider_trends
            }
            
        except Exception as e:
            log_error(f"历史趋势分析失败: {e}")
            return {'trend': 'error', 'trend_direction': 'unknown', 'confidence': 0.0, 'error': str(e)}
    
    def _rank_provider_performance(self) -> List[Dict[str, Any]]:
        """提供商性能排名"""
        try:
            rankings = []
            for provider, stats in self.timeout_stats['provider'].items():
                if stats['total_requests'] > 0:
                    # 综合评分 = 成功率 * 0.7 + 响应速度评分 * 0.3
                    response_score = max(0, 1.0 - (stats['avg_response_time'] / 20.0))  # 20秒为最差
                    composite_score = stats['success_rate'] * 0.7 + response_score * 0.3
                    
                    rankings.append({
                        'provider': provider,
                        'success_rate': stats['success_rate'],
                        'avg_response_time': stats['avg_response_time'],
                        'total_requests': stats['total_requests'],
                        'composite_score': composite_score,
                        'rank': 0  # 稍后填充
                    })
            
            # 按综合评分排序
            rankings.sort(key=lambda x: x['composite_score'], reverse=True)
            
            # 填充排名
            for i, ranking in enumerate(rankings):
                ranking['rank'] = i + 1
            
            return rankings
            
        except Exception as e:
            log_error(f"提供商性能排名失败: {e}")
            return []
    
    def _calculate_signal_quality(self, signals: List[AISignal], confidence_mean: float, confidence_std: float) -> float:
        """计算信号质量评分"""
        try:
            if not signals:
                return 0.0
            
            # 基础质量 = 平均信心值
            base_quality = confidence_mean
            
            # 一致性奖励（低标准差 = 高一致性）
            consistency_bonus = max(0, 1.0 - confidence_std) * 0.2
            
            # 多样性奖励（多种信号类型）
            unique_signals = len(set(s.signal for s in signals))
            diversity_bonus = (unique_signals / 3.0) * 0.1
            
            # 提供商数量奖励
            unique_providers = len(set(s.provider for s in signals))
            provider_bonus = min(unique_providers / 4.0, 0.1) * 0.1
            
            total_quality = base_quality + consistency_bonus + diversity_bonus + provider_bonus
            
            return min(total_quality, 1.0)  # 确保不超过1.0
            
        except Exception as e:
            log_error(f"信号质量计算失败: {e}")
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
                    diversity -= proportion * (proportion ** 0.5)  # 简化的多样性计算
            
            return min(diversity * 3.0, 1.0)  # 标准化到0-1范围
            
        except Exception as e:
            log_error(f"多样性指数计算失败: {e}")
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
            log_error(f"共识水平计算失败: {e}")
            return 0.0
    
    def _calculate_cost_efficiency(self, successful_providers: int, total_configured: int) -> float:
        """计算成本效率"""
        try:
            if total_configured == 0:
                return 0.0
            
            # 成功率越高，成本效率越高
            success_rate = successful_providers / total_configured
            
            # 考虑重试成本
            current_cost = self.retry_cost_config['current_daily_cost']
            max_cost = self.retry_cost_config['max_daily_cost']
            cost_ratio = current_cost / max_cost if max_cost > 0 else 0.0
            
            # 成本效率 = 成功率 * (1 - 成本比例)
            cost_efficiency = success_rate * (1.0 - cost_ratio * 0.5)  # 成本影响权重0.5
            
            return max(0.0, min(1.0, cost_efficiency))
            
        except Exception as e:
            log_error(f"成本效率计算失败: {e}")
            return 0.0
    
    def _calculate_dynamic_confidence_adjustment(self, rsi: float, atr_pct: float, trend: str) -> Dict[str, Any]:
        """计算动态信心调整因子 - 基于市场条件"""
        try:
            # 基础调整因子
            buy_multiplier = 1.0
            sell_multiplier = 1.0
            hold_multiplier = 1.0
            
            # 1. RSI-based adjustments
            if rsi < 30:  # 超卖区域 - 增强买入信心，降低卖出信心
                buy_multiplier *= 1.3
                sell_multiplier *= 0.7
                hold_multiplier *= 0.8
            elif rsi > 70:  # 超买区域 - 增强卖出信心，降低买入信心
                buy_multiplier *= 0.7
                sell_multiplier *= 1.3
                hold_multiplier *= 0.8
            elif 35 <= rsi <= 65:  # 中性区域 - 保持平衡
                buy_multiplier *= 1.0
                sell_multiplier *= 1.0
                hold_multiplier *= 1.1  # 轻微偏好观望
            else:  # 轻微超买/超卖
                if rsi < 40:  # 轻微超卖
                    buy_multiplier *= 1.1
                    sell_multiplier *= 0.9
                else:  # 轻微超买
                    buy_multiplier *= 0.9
                    sell_multiplier *= 1.1
            
            # 2. 波动率-based adjustments
            if atr_pct < 0.5:  # 极低波动 - 降低交易信号信心
                buy_multiplier *= 0.8
                sell_multiplier *= 0.8
                hold_multiplier *= 1.2  # 增强观望偏好
            elif atr_pct < 1.0:  # 低波动 - 轻微降低
                buy_multiplier *= 0.9
                sell_multiplier *= 0.9
                hold_multiplier *= 1.1
            elif atr_pct > 3.0:  # 高波动 - 增强信号但降低信心
                buy_multiplier *= 1.1
                sell_multiplier *= 1.1
                hold_multiplier *= 0.9
            elif atr_pct > 2.0:  # 中高波动 - 轻微增强
                buy_multiplier *= 1.05
                sell_multiplier *= 1.05
                hold_multiplier *= 0.95
            
            # 3. 趋势-based adjustments
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
                hold_multiplier *= 1.3  # 震荡市强烈偏好观望
            
            # 4. 时间-based adjustments (基于交易时段)
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 16:  # 亚洲交易时段 - 相对保守
                buy_multiplier *= 0.95
                sell_multiplier *= 0.95
                hold_multiplier *= 1.05
            elif 21 <= current_hour or current_hour <= 3:  # 欧美交易时段 - 相对积极
                buy_multiplier *= 1.05
                sell_multiplier *= 1.05
                hold_multiplier *= 0.95
            
            # 5. 确保调整因子在合理范围内
            buy_multiplier = max(0.5, min(1.5, buy_multiplier))
            sell_multiplier = max(0.5, min(1.5, sell_multiplier))
            hold_multiplier = max(0.5, min(1.5, hold_multiplier))
            
            log_info(f"📊 动态信心调整: BUY×{buy_multiplier:.2f}, SELL×{sell_multiplier:.2f}, HOLD×{hold_multiplier:.2f}")
            log_info(f"📊 调整原因: RSI={rsi:.1f}, ATR={atr_pct:.2f}%, 趋势={trend}")
            
            return {
                'buy_multiplier': buy_multiplier,
                'sell_multiplier': sell_multiplier,
                'hold_multiplier': hold_multiplier,
                'rsi': rsi,
                'atr_pct': atr_pct,
                'trend': trend,
                'adjustment_reason': f"RSI={rsi:.1f}, ATR={atr_pct:.2f}%, 趋势={trend}"
            }
            
        except Exception as e:
            log_error(f"动态信心调整计算失败: {e}")
            # 返回中性调整因子
            return {
                'buy_multiplier': 1.0,
                'sell_multiplier': 1.0,
                'hold_multiplier': 1.0,
                'rsi': rsi,
                'atr_pct': atr_pct,
                'trend': trend,
                'adjustment_reason': f"计算失败，使用中性因子: {e}"
            }
    
    def _analyze_signal_consistency(self, current_signals: List[AISignal], historical_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析信号历史一致性 - 防止信号反复横跳"""
        try:
            if not current_signals or not historical_signals:
                return {
                    'consistency_score': 1.0,
                    'trend_stability': 'unknown',
                    'recommendation': 'insufficient_data',
                    'analysis': '历史数据不足'
                }
            
            # 获取最近5次信号
            recent_history = historical_signals[-5:] if len(historical_signals) >= 5 else historical_signals
            current_signal_type = current_signals[0].signal if current_signals else 'HOLD'
            
            # 计算历史一致性得分
            consistent_signals = sum(1 for h in recent_history if h.get('signal') == current_signal_type)
            consistency_score = consistent_signals / len(recent_history) if recent_history else 0.0
            
            # 分析趋势稳定性
            if consistency_score >= 0.8:
                trend_stability = 'very_stable'
                recommendation = 'maintain_current_signal'
            elif consistency_score >= 0.6:
                trend_stability = 'stable'
                recommendation = 'slight_adjustment_allowed'
            elif consistency_score >= 0.4:
                trend_stability = 'moderate'
                recommendation = 'careful_consideration_needed'
            else:
                trend_stability = 'unstable'
                recommendation = 'high_caution_required'
            
            # 计算信号变化频率
            signal_changes = 0
            for i in range(1, len(recent_history)):
                if recent_history[i].get('signal') != recent_history[i-1].get('signal'):
                    signal_changes += 1
            
            change_frequency = signal_changes / (len(recent_history) - 1) if len(recent_history) > 1 else 0.0
            
            log_info(f"📈 信号一致性分析: 一致性得分={consistency_score:.2f}, 趋势稳定性={trend_stability}")
            log_info(f"📈 信号变化频率: {change_frequency:.2f} ({signal_changes}/{len(recent_history)-1}次变化)")
            
            return {
                'consistency_score': consistency_score,
                'trend_stability': trend_stability,
                'recommendation': recommendation,
                'change_frequency': change_frequency,
                'analysis': f'最近{len(recent_history)}次信号中{consistent_signals}次一致，变化{signal_changes}次'
            }
            
        except Exception as e:
            log_error(f"信号一致性分析失败: {e}")
            return {
                'consistency_score': 0.5,
                'trend_stability': 'unknown',
                'recommendation': 'analysis_failed',
                'error': str(e)
            }
    
    def _optimize_low_volatility_signals(self, signals: List[AISignal], market_data: Dict[str, Any]) -> List[AISignal]:
        """优化低波动率市场的信号处理"""
        try:
            technical_data = market_data.get('technical_data', {})
            atr_pct = float(technical_data.get('atr_pct', 1.0))
            
            # 低波动率阈值
            low_volatility_threshold = 0.8  # ATR < 0.8% 认为是低波动
            
            if atr_pct >= low_volatility_threshold:
                return signals  # 正常波动，无需特殊处理
            
            log_info(f"⚠️ 检测到极低波动率环境 (ATR: {atr_pct:.2f}%)，应用低波动率优化策略")
            
            # 低波动率优化策略
            optimized_signals = []
            for signal in signals:
                new_signal = AISignal(
                    provider=signal.provider,
                    signal=signal.signal,
                    confidence=signal.confidence,
                    reason=signal.reason,
                    timestamp=signal.timestamp,
                    raw_response=signal.raw_response
                )
                
                # 策略1: 降低交易信号的信心值
                if signal.signal in ['BUY', 'SELL']:
                    new_signal.confidence = max(0.3, signal.confidence * 0.7)  # 降低30%
                    new_signal.reason = f"[低波动率优化] {signal.reason}"
                    log_info(f"🔄 {signal.provider} 低波动率调整: 信心从{signal.confidence:.2f}降至{new_signal.confidence:.2f}")
                
                # 策略2: 增强超卖/超买信号
                rsi = float(technical_data.get('rsi', 50))
                if (signal.signal == 'BUY' and rsi < 35) or (signal.signal == 'SELL' and rsi > 65):
                    # 在极端区域，适当恢复部分信心
                    new_signal.confidence = min(0.8, new_signal.confidence * 1.2)
                    new_signal.reason = f"[低波动率+极端RSI优化] {signal.reason}"
                    log_info(f"🔄 {signal.provider} 极端RSI补偿: 信心调整至{new_signal.confidence:.2f}")
                
                # 策略3: 震荡市区间交易策略
                price_history = market_data.get('price_history', [])
                if len(price_history) >= 20:
                    recent_prices = price_history[-20:]
                    price_range = max(recent_prices) - min(recent_prices)
                    avg_price = sum(recent_prices) / len(recent_prices)
                    price_position = (avg_price - min(recent_prices)) / price_range if price_range > 0 else 0.5
                    
                    # 在区间边界附近，增强信号
                    if (signal.signal == 'BUY' and price_position < 0.3) or \
                       (signal.signal == 'SELL' and price_position > 0.7):
                        new_signal.confidence = min(0.85, new_signal.confidence * 1.15)
                        new_signal.reason = f"[低波动率+区间边界优化] {signal.reason}"
                        log_info(f"🔄 {signal.provider} 区间边界增强: 信心调整至{new_signal.confidence:.2f}")
                
                optimized_signals.append(new_signal)
            
            return optimized_signals
            
        except Exception as e:
            log_error(f"低波动率信号优化失败: {e}")
            return signals  # 出错时返回原始信号

    def _calculate_consensus_threshold(self, successful_providers: int, total_configured: int) -> str:
        """计算共识门槛"""
        try:
            if total_configured == 0:
                return "unknown"
            
            success_ratio = successful_providers / total_configured
            
            if success_ratio >= 0.8:
                return "high_consensus"
            elif success_ratio >= 0.6:
                return "medium_consensus"
            elif success_ratio >= 0.4:
                return "low_consensus"
            else:
                return "minimal_consensus"
                
        except Exception as e:
            log_error(f"共识门槛计算失败: {e}")
            return "unknown"
    
    def _calculate_dynamic_adjustment_factor(self, success_rate: float, historical_trend: Dict[str, Any]) -> float:
        """计算动态调整因子"""
        try:
            # 基础调整因子
            base_adjustment = 0.0
            
            # 基于成功率调整
            if success_rate >= 0.9:
                base_adjustment += 0.15  # 高成功率，正向调整
            elif success_rate >= 0.7:
                base_adjustment += 0.10  # 中等成功率，轻微正向调整
            elif success_rate >= 0.5:
                base_adjustment += 0.05  # 一般成功率，轻微正向调整
            elif success_rate >= 0.3:
                base_adjustment -= 0.10  # 低成功率，负向调整
            else:
                base_adjustment -= 0.20  # 极低成功率，大幅负向调整
            
            # 基于历史趋势调整
            trend_direction = historical_trend.get('trend_direction', 'stable')
            if trend_direction == 'improving':
                base_adjustment += 0.08  # 趋势改善，正向调整
            elif trend_direction == 'declining':
                base_adjustment -= 0.12  # 趋势恶化，负向调整
            # stable趋势不做额外调整
            
            # 基于提供商性能一致性调整
            provider_trends = historical_trend.get('provider_trends', [])
            if provider_trends:
                success_rates = [p['success_rate'] for p in provider_trends]
                if len(success_rates) > 1:
                    # 计算成功率的标准差
                    mean_rate = sum(success_rates) / len(success_rates)
                    variance = sum((r - mean_rate) ** 2 for r in success_rates) / len(success_rates)
                    std_dev = variance ** 0.5
                    
                    # 一致性高（标准差小）则正向调整
                    if std_dev < 0.1:
                        base_adjustment += 0.05
                    # 一致性低（标准差大）则负向调整
                    elif std_dev > 0.2:
                        base_adjustment -= 0.08
            
            # 确保调整因子在合理范围内
            return max(-0.50, min(0.50, base_adjustment))
            
        except Exception as e:
            log_error(f"动态调整因子计算失败: {e}")
            return 0.0
    
    def _calculate_consistency_score(self, provider_rankings: List[Dict[str, Any]]) -> float:
        """计算一致性得分"""
        try:
            # 如果提供商排名数据不足，使用超时统计数据作为备选
            if not provider_rankings or len(provider_rankings) < 2:
                # 使用超时统计数据计算一致性
                provider_stats = self.timeout_stats['provider']
                if not provider_stats:
                    return 0.5  # 默认值
                
                # 提取成功率数据
                success_rates = [stats['success_rate'] for stats in provider_stats.values()
                               if stats.get('success_rate', 0) > 0]
                
                if len(success_rates) < 2:
                    # 只有一个或没有提供商数据，返回基础一致性得分
                    return success_rates[0] if success_rates else 0.5
            
            # 提取成功率数据
            success_rates = [ranking['success_rate'] for ranking in provider_rankings]
            
            if not success_rates:
                return 0.5
            
            # 计算成功率的一致性
            mean_rate = sum(success_rates) / len(success_rates)
            
            if len(success_rates) == 1:
                return success_rates[0]  # 只有一个提供商时，返回其成功率
            
            # 计算标准差
            variance = sum((rate - mean_rate) ** 2 for rate in success_rates) / len(success_rates)
            std_dev = variance ** 0.5
            
            # 计算一致性得分 (1.0 = 完全一致，0.0 = 完全不一致)
            # 使用标准差的倒数关系，标准差越小，一致性越高
            max_possible_std = 0.5  # 假设最大可能标准差为0.5
            consistency_score = max(0.0, 1.0 - (std_dev / max_possible_std))
            
            # 基于平均成功率调整最终得分
            consistency_score = consistency_score * mean_rate
            
            # 确保得分在合理范围内，避免极端值
            final_score = min(0.95, max(0.05, consistency_score))
            
            log_info(f"📊 一致性得分计算: 成功率={success_rates}, 均值={mean_rate:.2f}, 标准差={std_dev:.2f}, 最终得分={final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            log_error(f"一致性得分计算失败: {e}")
            return 0.5  # 出错时返回中等默认值
    
    def _check_low_volatility_optimization(self) -> bool:
        """检查是否应用了低波动优化"""
        try:
            # 检查是否在最近的交易中应用了低波动优化
            # 这里可以基于历史记录或当前市场状态判断
            
            # 由于我们没有直接访问当前市场数据的途径，我们基于提供商的超时统计来间接判断
            # 如果提供商响应时间普遍较长，可能表明市场波动较低（交易不活跃）
            
            provider_stats = self.timeout_stats['provider']
            if not provider_stats:
                return False
            
            # 计算平均响应时间
            response_times = [stats['avg_response_time'] for stats in provider_stats.values()
                            if stats['avg_response_time'] > 0]
            
            if not response_times:
                return False
            
            avg_response_time = sum(response_times) / len(response_times)
            
            # 如果平均响应时间超过某个阈值，认为可能处于低波动环境
            # 这个阈值需要根据实际经验调整
            low_volatility_threshold = 8.0  # 8秒
            
            is_low_volatility = avg_response_time > low_volatility_threshold
            
            if is_low_volatility:
                log_info(f"📊 低波动优化检测: 平均响应时间{avg_response_time:.1f}s > 阈值{low_volatility_threshold}s，启用低波动优化")
            else:
                log_info(f"📊 低波动优化检测: 平均响应时间{avg_response_time:.1f}s ≤ 阈值{low_volatility_threshold}s，正常波动")
            
            return is_low_volatility
            
        except Exception as e:
            log_error(f"低波动优化检测失败: {e}")
            return False

# 全局AI客户端实例
ai_client = AIClient()
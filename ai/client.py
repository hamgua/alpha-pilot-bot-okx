"""
AI客户端基类
提供统一的AI提供商接口
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging
from datetime import datetime

from core.base import BaseConfig
from core.exceptions import NetworkError, TimeoutError
from .signals import AISignal
from .timeout import TimeoutManager
from .cache import ai_request_cache
from .proxy import create_proxy_session
from .rate_limiter import rate_limit

logger = logging.getLogger(__name__)

class AIProviderConfig(BaseConfig):
    """AI提供商配置"""
    def __init__(self, name: str, api_key: str = "", url: str = "", model: str = "", **kwargs):
        super().__init__(name=name, **kwargs)
        self.api_key = api_key
        self.url = url
        self.model = model
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 150)
        self.top_p = kwargs.get('top_p', 0.9)

class BaseAIProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.timeout_manager = TimeoutManager()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """初始化提供商"""
        try:
            # 增强的连接池配置
            connector = aiohttp.TCPConnector(
                limit=50,  # 增加总连接数
                limit_per_host=20,  # 增加单主机连接数
                ttl_dns_cache=600,  # 增加DNS缓存时间
                use_dns_cache=True,
                keepalive_timeout=60,  # 增加keepalive时间
                enable_cleanup_closed=True,
                force_close=False,  # 保持连接复用
                ssl=False,  # 使用系统默认SSL设置
                happy_eyeballs_delay=0.25,  # 启用Happy Eyeballs，支持IPv6
                interleave=None,  # 允许并行连接尝试
                family=0,  # 自动选择IPv4/IPv6
                local_addr=None,  # 使用系统默认本地地址
                resolver=None  # 使用系统默认DNS解析器
            )
            
            timeout_config = self.timeout_manager.get_timeout_config(self.config.name)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=timeout_config['total_timeout'],
                    connect=timeout_config['connection_timeout'],
                    sock_read=timeout_config['response_timeout']
                )
            )

            # 添加代理支持
            try:
                from config import config
                if config.get('ai', 'use_proxy', False):
                    create_proxy_session(self._session)
                    logger.info(f"✅ {self.config.name} 代理支持已启用")
            except:
                # 配置不存在时静默跳过
                pass

            logger.info(f"✅ {self.config.name} AI提供商初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.config.name} AI提供商初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._session:
            await self._session.close()
            self._session = None
    
    @abstractmethod
    def build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建AI提示词"""
        pass
    
    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any]) -> Optional[AISignal]:
        """解析AI响应"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass
    
    async def get_signal(self, market_data: Dict[str, Any]) -> Optional[AISignal]:
        """获取AI信号"""
        if not self._session:
            await self.initialize()
        
        try:
            # 构建提示词
            prompt = self.build_prompt(market_data)
            system_prompt = self.get_system_prompt()
            
            # 获取超时配置
            timeout_config = self.timeout_manager.get_timeout_config(self.config.name)
            max_retries = int(timeout_config['max_retries'])
            
            # 尝试获取信号
            for attempt in range(max_retries + 1):
                try:
                    # 检查重试成本限制
                    if attempt > 0 and not self.timeout_manager.check_retry_cost_limit(self.config.name):
                        logger.warning(f"⚠️ {self.config.name} 重试成本超出限制，停止重试")
                        break

                    # 更新重试成本
                    if attempt > 0:
                        self.timeout_manager.update_retry_cost(self.config.name)

                    # 检查限流
                    from .rate_limiter import rate_limiter
                    if not await rate_limiter.wait_for_permission(self.config.name):
                        logger.warning(f"⚠️ {self.config.name} 限流检查失败，跳过请求")
                        if attempt < max_retries:
                            await asyncio.sleep(1)
                        continue

                    # 记录请求开始时间
                    request_start_time = time.time()

                    # 发送请求
                    response_data = await self._send_request(prompt, system_prompt, timeout_config)
                    
                    # 记录响应时间
                    response_time = time.time() - request_start_time
                    
                    if response_data:
                        # 更新超时统计
                        self.timeout_manager.update_timeout_stats(self.config.name, response_time, True)

                        # 记录限流统计
                        from .rate_limiter import rate_limiter
                        rate_limiter.record_request_result(self.config.name, True, response_time)

                        # 解析响应
                        signal = self.parse_response(response_data)
                        if signal:
                            logger.info(f"🤖 {self.config.name.upper()}回复: {signal.signal} (信心: {signal.confidence:.1f})")
                            return signal
                    
                    # 如果失败且不是最后一次尝试，等待后重试
                    if attempt < max_retries:
                        retry_delay = self.timeout_manager.calculate_exponential_backoff(
                            self.config.name, attempt, timeout_config['retry_base_delay']
                        )
                        logger.info(f"⏰ {self.config.name} 第{attempt + 1}次尝试失败，{retry_delay:.1f}秒后重试...")
                        await asyncio.sleep(retry_delay)
                    
                except asyncio.TimeoutError:
                    # 记录超时统计
                    self.timeout_manager.update_timeout_stats(self.config.name, 0, False, timeout_type='timeout')

                    # 记录限流统计（失败）
                    from .rate_limiter import rate_limiter
                    rate_limiter.record_request_result(self.config.name, False, 0)

                    logger.error(f"{self.config.name} 请求超时（动态超时）")
                    if attempt < max_retries:
                        retry_delay = self.timeout_manager.calculate_exponential_backoff(
                            self.config.name, attempt, timeout_config['retry_base_delay']
                        )
                        await asyncio.sleep(retry_delay)

                except Exception as e:
                    # 记录异常统计
                    self.timeout_manager.update_timeout_stats(self.config.name, 0, False, timeout_type='error')

                    # 记录限流统计（失败）
                    from .rate_limiter import rate_limiter
                    rate_limiter.record_request_result(self.config.name, False, 0)

                    logger.error(f"{self.config.name} 异常: {e}")
                    if attempt < max_retries:
                        retry_delay = self.timeout_manager.calculate_exponential_backoff(
                            self.config.name, attempt, timeout_config['retry_base_delay']
                        )
                        await asyncio.sleep(retry_delay)
            
            logger.error(f"{self.config.name} 最终失败")
            return None
            
        except Exception as e:
            logger.error(f"{self.config.name} 获取信号失败: {e}")
            return None
    
    async def _send_request(self, prompt: str, system_prompt: str, timeout_config: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """发送AI请求"""
        try:
            # 检查缓存
            cache_key_data = {
                'prompt': prompt,
                'system_prompt': system_prompt,
                'model': self.config.model,
                'temperature': self.config.temperature
            }

            cached_result = ai_request_cache.get(
                self.config.name,
                prompt,
                self.config.model,
                **cache_key_data
            )

            if cached_result:
                logger.info(f"🎯 使用缓存的AI响应: {self.config.name}")
                return cached_result

            headers = {
                'Authorization': f"Bearer {self.config.api_key}",
                'Content-Type': 'application/json',
                'User-Agent': 'AlphaPilotBot/1.0',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            }

            payload = {
                'model': self.config.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': system_prompt
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': self.config.temperature,
                'max_tokens': self.config.max_tokens,
                'top_p': self.config.top_p,
                'frequency_penalty': 0.3,
                'presence_penalty': 0.4
            }

            # 设置超时时间
            request_timeout = aiohttp.ClientTimeout(
                total=timeout_config.get('request_timeout', 30),
                connect=timeout_config.get('connect_timeout', 10),
                sock_read=timeout_config.get('sock_read_timeout', 30)
            )

            async with self._session.post(
                self.config.url,
                headers=headers,
                json=payload,
                ssl=True,
                allow_redirects=True,
                max_redirects=5,
                timeout=request_timeout
            ) as response:
                
                if response.status == 200:
                    try:
                        # 先读取响应文本，再解析JSON
                        response_text = await response.text()
                        if not response_text:
                            logger.error(f"{self.config.name} 响应文本为空")
                            return None
                        
                        data = json.loads(response_text)
                        if data is None:
                            logger.error(f"{self.config.name} 响应数据为None")
                            return None

                        # 缓存成功的响应
                        ai_request_cache.set(
                            self.config.name,
                            prompt,
                            self.config.model,
                            data,
                            **cache_key_data
                        )

                        logger.info(f"💾 缓存AI响应: {self.config.name}")
                        return data
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"{self.config.name} JSON解析失败: {e}")
                        logger.error(f"{self.config.name} 响应文本: {response_text[:200]}...")
                        return None
                        
                    except Exception as e:
                        logger.error(f"{self.config.name} 响应处理失败: {type(e).__name__}: {e}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"{self.config.name} API调用失败: {response.status} - {error_text[:200]}")
                    return None
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"{self.config.name} 请求超时")
        except Exception as e:
            raise NetworkError(f"{self.config.name} 网络错误: {e}")

class DeepseekProvider(BaseAIProvider):
    """Deepseek AI提供商"""
    
    def get_system_prompt(self) -> str:
        return """你是专业的BTC波段交易大师，专注精准抄底和趋势跟踪。你必须积极寻找交易机会，避免保守的HOLD建议。

你的特点：
- 技术派激进交易者，专注突破交易
- 不喜欢保守观望，倾向于果断行动
- 基于技术面给出BUY/SELL建议，尽量避免HOLD
- 必须与其他分析师持不同观点，即使市场稳定也要寻找交易机会

记住：你是DEEPSEEK，要以技术分析为主导，积极交易为风格。"""
    
    def build_prompt(self, market_data: Dict[str, Any]) -> str:
        return self._build_enhanced_prompt(market_data, "deepseek")
    
    def parse_response(self, response_data: Dict[str, Any]) -> Optional[AISignal]:
        return self._parse_ai_response(response_data, "deepseek")
    
    def _build_enhanced_prompt(self, market_data: Dict[str, Any], provider: str) -> str:
        """构建增强的AI提示词"""
        # 简化的提示词构建，实际应该包含完整的市场分析
        price = market_data.get('price', 0)
        trend = market_data.get('trend', 'neutral')

        # 根据提供商添加特定提示
        provider_hint = ""
        if provider == "deepseek":
            provider_hint = "作为DEEPSEEK，请以技术分析为主导，积极寻找交易机会。"
        elif provider == "openai":
            provider_hint = "请以稳健的分析风格，综合考虑各种因素。"

        return f"""
        当前BTC价格: ${price:,.2f}
        市场趋势: {trend}

        {provider_hint}

        基于技术分析，给出BUY/SELL/HOLD建议，并说明理由。
        请以JSON格式回复: {{"signal": "BUY/SELL/HOLD", "confidence": "HIGH/MEDIUM/LOW", "reason": "详细分析理由"}}
        """
    
    def _parse_ai_response(self, response_data: Dict[str, Any], provider: str) -> Optional[AISignal]:
        """解析AI响应"""
        try:
            if not response_data:
                return None
                
            choices = response_data.get('choices', [])
            if not choices:
                return None
                
            first_choice = choices[0]
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            if not content:
                return None
            
            # 清理JSON字符串
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1]
            
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
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
            logger.error(f"解析{provider}响应失败: {e}")
            return None

class AIClient:
    """AI客户端 - 管理多个AI提供商"""
    
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.timeout_manager = TimeoutManager()
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化AI提供商"""
        try:
            from config import config
            
            # 获取AI配置
            ai_models = config.get('ai', 'models')
            if not ai_models:
                # 使用环境变量作为回退
                import os
                ai_models = {
                    'deepseek': os.getenv('DEEPSEEK_API_KEY'),
                    'kimi': os.getenv('KIMI_API_KEY'),
                    'qwen': os.getenv('QWEN_API_KEY'),
                    'openai': os.getenv('OPENAI_API_KEY')
                }
            
            # 提供商配置
            provider_configs = [
                ('deepseek', 'https://api.deepseek.com/v1/chat/completions', 'deepseek-chat'),
                ('kimi', 'https://api.moonshot.cn/v1/chat/completions', 'moonshot-v1-8k'),
                ('qwen', 'https://dashscope.aliyuncs.com/compatible/v1/chat/completions', 'qwen3-max'),
                ('openai', 'https://api.openai.com/v1/chat/completions', 'gpt-3.5-turbo')
            ]
            
            for provider_name, url, model in provider_configs:
                api_key = ai_models.get(provider_name) if ai_models else None
                if api_key and api_key.strip():
                    provider_config = AIProviderConfig(
                        name=provider_name,
                        api_key=api_key.strip(),
                        url=url,
                        model=model,
                        temperature=0.95 if provider_name == 'deepseek' else 0.7
                    )
                    
                    # 创建提供商实例
                    provider = DeepseekProvider(provider_config)  # 简化实现
                    self.providers[provider_name] = provider
                    
                    logger.info(f"✅ {provider_name} AI提供商已配置")
                else:
                    logger.warning(f"⚠️ {provider_name} API密钥未配置或无效")
            
            logger.info(f"已配置的AI提供商: {list(self.providers.keys())}")
            
            if not self.providers:
                logger.warning("⚠️ 没有任何AI提供商被配置")
                
        except Exception as e:
            logger.error(f"AI客户端初始化失败: {e}")
            self.providers = {}
    
    async def get_signal_from_provider(self, provider: str, market_data: Dict[str, Any]) -> Optional[AISignal]:
        """从指定AI提供商获取信号"""
        if provider not in self.providers:
            logger.error(f"不支持的AI提供商: {provider}")
            return None
        
        provider_instance = self.providers[provider]
        return await provider_instance.get_signal(market_data)
    
    async def get_multi_ai_signals(self, market_data: Dict[str, Any], providers: List[str] = None) -> List[AISignal]:
        """获取多AI信号"""
        if providers is None:
            providers = list(self.providers.keys())
        
        # 过滤掉未配置的提供商
        enabled_providers = [p for p in providers if p in self.providers]
        
        if not enabled_providers:
            logger.warning("没有可用的AI提供商")
            return []
        
        signals = []
        
        # 并发获取所有信号
        tasks = []
        for provider in enabled_providers:
            task = self.get_signal_from_provider(provider, market_data)
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for provider, result in zip(enabled_providers, results):
                if isinstance(result, Exception):
                    logger.error(f"{provider} 获取信号异常: {result}")
                elif result:
                    signals.append(result)
        
        return signals
    
    async def cleanup(self) -> None:
        """清理所有提供商资源"""
        cleanup_tasks = []
        for provider in self.providers.values():
            cleanup_tasks.append(provider.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
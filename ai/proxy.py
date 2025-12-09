"""
代理管理模块
提供CDN代理支持，优化网络连接稳定性
"""

import aiohttp
import asyncio
import random
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
import json

logger = logging.getLogger(__name__)

class ProxyManager:
    """代理管理器 - 管理CDN代理和代理轮换"""

    def __init__(self):
        self.proxies: List[Dict[str, Any]] = []
        self.failed_proxies: set = set()
        self.proxy_stats: Dict[str, Dict[str, Any]] = {}
        self.current_proxy_index = 0
        self._load_default_proxies()

    def _load_default_proxies(self):
        """加载默认代理配置"""
        # 免费CDN代理列表（实际使用时需要替换为可靠的代理服务）
        default_proxies = [
            {
                'url': 'http://cdn.cloudflare.com',
                'type': 'cdn',
                'region': 'global',
                'weight': 1.0,
                'timeout_bonus': 1.2  # 增加超时时间倍数
            },
            {
                'url': 'http://cdn.jsdelivr.net',
                'type': 'cdn',
                'region': 'global',
                'weight': 1.0,
                'timeout_bonus': 1.1
            },
            {
                'url': 'http://unpkg.com',
                'type': 'cdn',
                'region': 'global',
                'weight': 0.9,
                'timeout_bonus': 1.3
            }
        ]

        # 从环境变量加载自定义代理
        import os
        custom_proxies = os.getenv('CUSTOM_PROXIES', '')
        if custom_proxies:
            try:
                custom_list = json.loads(custom_proxies)
                default_proxies.extend(custom_list)
            except Exception as e:
                logger.warning(f"加载自定义代理失败: {e}")

        self.proxies = default_proxies
        logger.info(f"✅ 已加载 {len(self.proxies)} 个代理")

    def get_next_proxy(self) -> Optional[Dict[str, Any]]:
        """获取下一个可用代理（轮询+权重）"""
        if not self.proxies:
            return None

        # 过滤掉失败的代理
        available_proxies = [
            p for i, p in enumerate(self.proxies)
            if i not in self.failed_proxies
        ]

        if not available_proxies:
            # 所有代理都失败，重置失败列表
            logger.warning("⚠️ 所有代理都失败，重置失败列表")
            self.failed_proxies.clear()
            available_proxies = self.proxies.copy()

        # 基于权重随机选择
        weights = [p.get('weight', 1.0) for p in available_proxies]
        total_weight = sum(weights)

        if total_weight <= 0:
            return available_proxies[0]

        r = random.uniform(0, total_weight)
        cumulative = 0

        for proxy, weight in zip(available_proxies, weights):
            cumulative += weight
            if r <= cumulative:
                return proxy

        return available_proxies[-1]

    def mark_proxy_failed(self, proxy: Dict[str, Any]):
        """标记代理失败"""
        try:
            proxy_index = self.proxies.index(proxy)
            self.failed_proxies.add(proxy_index)

            # 记录统计
            proxy_url = proxy.get('url', 'unknown')
            if proxy_url not in self.proxy_stats:
                self.proxy_stats[proxy_url] = {
                    'success_count': 0,
                    'fail_count': 0,
                    'last_used': None,
                    'avg_response_time': 0
                }

            self.proxy_stats[proxy_url]['fail_count'] += 1
            self.proxy_stats[proxy_url]['last_used'] = datetime.now()

            logger.warning(f"⚠️ 代理标记为失败: {proxy_url}")

        except Exception as e:
            logger.error(f"标记代理失败时出错: {e}")

    def update_proxy_stats(self, proxy: Dict[str, Any], success: bool, response_time: float):
        """更新代理统计"""
        try:
            proxy_url = proxy.get('url', 'unknown')
            if proxy_url not in self.proxy_stats:
                self.proxy_stats[proxy_url] = {
                    'success_count': 0,
                    'fail_count': 0,
                    'last_used': None,
                    'avg_response_time': 0
                }

            stats = self.proxy_stats[proxy_url]

            if success:
                stats['success_count'] += 1
                # 更新平均响应时间
                if stats['avg_response_time'] == 0:
                    stats['avg_response_time'] = response_time
                else:
                    stats['avg_response_time'] = (stats['avg_response_time'] * 0.8) + (response_time * 0.2)
            else:
                stats['fail_count'] += 1

            stats['last_used'] = datetime.now()

            # 自动调整权重
            total_requests = stats['success_count'] + stats['fail_count']
            if total_requests > 5:
                success_rate = stats['success_count'] / total_requests
                proxy['weight'] = max(0.1, success_rate * 1.0)

        except Exception as e:
            logger.error(f"更新代理统计失败: {e}")

    def get_proxy_recommendations(self) -> List[Dict[str, Any]]:
        """获取代理推荐列表"""
        recommendations = []

        for proxy in self.proxies:
            proxy_url = proxy.get('url', 'unknown')
            stats = self.proxy_stats.get(proxy_url, {
                'success_count': 0,
                'fail_count': 0,
                'avg_response_time': 0
            })

            total = stats['success_count'] + stats['fail_count']
            success_rate = stats['success_count'] / total if total > 0 else 0

            recommendations.append({
                'url': proxy_url,
                'type': proxy.get('type', 'unknown'),
                'region': proxy.get('region', 'unknown'),
                'weight': proxy.get('weight', 1.0),
                'success_rate': success_rate,
                'avg_response_time': stats['avg_response_time'],
                'total_requests': total,
                'recommendation_score': success_rate * (1.0 / max(0.1, stats['avg_response_time']))
            })

        # 按推荐分数排序
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations

class AIProxyConnector:
    """AI代理连接器 - 集成代理支持的AI请求"""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.proxy_manager = ProxyManager()
        self._original_request = session.request
        self._wrap_session()

    def _wrap_session(self):
        """包装session的请求方法以支持代理"""
        async def proxy_request(method, url, **kwargs):
            # 获取代理
            proxy = self.proxy_manager.get_next_proxy()

            if proxy and self._should_use_proxy(url):
                # 调整超时时间
                if 'timeout' in kwargs:
                    timeout_bonus = proxy.get('timeout_bonus', 1.0)
                    if hasattr(kwargs['timeout'], 'total'):
                        kwargs['timeout'].total *= timeout_bonus

                # 尝试使用代理
                start_time = time.time()

                try:
                    # 构建代理URL（这里需要根据实际代理服务调整）
                    proxy_url = self._build_proxy_url(url, proxy)

                    # 添加代理头
                    if 'headers' not in kwargs:
                        kwargs['headers'] = {}

                    kwargs['headers']['X-Proxy-URL'] = proxy.get('url', '')
                    kwargs['headers']['X-Proxy-Type'] = proxy.get('type', 'cdn')

                    # 执行请求
                    response = await self._original_request(method, proxy_url, **kwargs)

                    # 记录成功
                    response_time = time.time() - start_time
                    self.proxy_manager.update_proxy_stats(proxy, True, response_time)

                    logger.info(f"✅ 代理请求成功: {proxy.get('url')} -> {url}")
                    return response

                except Exception as e:
                    # 记录失败
                    response_time = time.time() - start_time
                    self.proxy_manager.update_proxy_stats(proxy, False, response_time)
                    self.proxy_manager.mark_proxy_failed(proxy)

                    logger.warning(f"⚠️ 代理请求失败: {proxy.get('url')} -> {url}, 错误: {e}")

                    # 回退到直接请求
                    logger.info(f"🔄 回退到直接请求: {url}")
                    return await self._original_request(method, url, **kwargs)
            else:
                # 直接请求
                return await self._original_request(method, url, **kwargs)

        self.session.request = proxy_request

    def _should_use_proxy(self, url: str) -> bool:
        """判断是否应使用代理"""
        # 只对AI提供商使用代理
        ai_providers = [
            'api.deepseek.com',
            'api.moonshot.cn',
            'dashscope.aliyuncs.com',
            'api.openai.com'
        ]

        for provider in ai_providers:
            if provider in url:
                return True

        return False

    def _build_proxy_url(self, original_url: str, proxy: Dict[str, Any]) -> str:
        """构建代理URL（需要根据实际代理服务实现）"""
        # 这里实现实际的代理URL构建逻辑
        # 示例：通过CDN代理转发请求
        proxy_base = proxy.get('url', '')

        if 'cdn.cloudflare.com' in proxy_base:
            # Cloudflare Workers 代理示例
            return f"https://your-worker.your-subdomain.workers.dev/proxy?url={original_url}"
        elif 'cdn.jsdelivr.net' in proxy_base:
            # 其他CDN代理方案
            return f"{proxy_base}/proxy?target={original_url}"

        # 默认返回原始URL
        return original_url

# 全局代理管理器实例
proxy_manager = ProxyManager()

# 便捷的代理函数
def create_proxy_session(session: aiohttp.ClientSession) -> AIProxyConnector:
    """为session添加代理支持"""
    return AIProxyConnector(session)

def get_proxy_recommendations() -> List[Dict[str, Any]]:
    """获取代理推荐"""
    return proxy_manager.get_proxy_recommendations()

def reset_failed_proxies():
    """重置失败的代理列表"""
    proxy_manager.failed_proxies.clear()
    logger.info("🔄 失败代理列表已重置")
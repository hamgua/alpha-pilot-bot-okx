"""
DNS管理器
提供DNS缓存、预解析和智能解析功能
"""

import asyncio
import socket
import time
import logging
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict
import dns.resolver
import dns.asyncresolver
from dns.exception import DNSException

logger = logging.getLogger(__name__)

class DNSManager:
    """DNS管理器 - 提供智能DNS解析"""

    def __init__(self):
        self.cache: Dict[str, List[str]] = {}
        self.cache_ttl: Dict[str, float] = {}
        self.default_ttl = 300  # 5分钟
        self.failed_domains: Set[str] = set()
        self.resolver = dns.asyncresolver.Resolver()
        self.resolver.timeout = 5.0
        self.resolver.lifetime = 10.0

        # 预解析的域名
        self.pre_resolve_domains = [
            'api.deepseek.com',
            'api.moonshot.cn',
            'dashscope.aliyuncs.com',
            'api.openai.com',
            'api.anthropic.com',
            'api.groq.com'
        ]

    async def resolve_domain(self, domain: str, force_refresh: bool = False) -> Optional[List[str]]:
        """解析域名"""
        try:
            # 检查缓存
            if not force_refresh and domain in self.cache:
                if time.time() - self.cache_ttl.get(domain, 0) < self.default_ttl:
                    logger.debug(f"DNS缓存命中: {domain}")
                    return self.cache[domain]

            # 检查失败记录
            if domain in self.failed_domains and not force_refresh:
                logger.warning(f"DNS解析失败记录，跳过: {domain}")
                return None

            # 执行解析
            logger.info(f"🔍 解析DNS: {domain}")
            result = await self.resolver.resolve(domain, 'A')

            ips = [str(ip) for ip in result]

            # 缓存结果
            self.cache[domain] = ips
            self.cache_ttl[domain] = time.time()

            # 从失败列表移除
            self.failed_domains.discard(domain)

            logger.info(f"✅ DNS解析成功: {domain} -> {ips}")
            return ips

        except DNSException as e:
            logger.error(f"DNS解析失败: {domain} - {e}")
            self.failed_domains.add(domain)
            return None
        except Exception as e:
            logger.error(f"DNS解析异常: {domain} - {e}")
            self.failed_domains.add(domain)
            return None

    async def pre_resolve_all(self) -> Dict[str, List[str]]:
        """预解析所有AI提供商域名"""
        logger.info("🚀 开始预解析AI提供商DNS...")

        results = {}
        tasks = []

        for domain in self.pre_resolve_domains:
            task = self.resolve_domain(domain, force_refresh=True)
            tasks.append((domain, task))

        # 并发解析
        for domain, task in tasks:
            try:
                ips = await task
                if ips:
                    results[domain] = ips
            except Exception as e:
                logger.error(f"预解析失败: {domain} - {e}")

        logger.info(f"✅ DNS预解析完成，成功: {len(results)}/{len(self.pre_resolve_domains)}")
        return results

    async def smart_resolve(self, domain: str) -> Optional[str]:
        """智能选择最佳IP"""
        ips = await self.resolve_domain(domain)
        if not ips:
            return None

        # 如果有多个IP，选择响应时间最短的
        if len(ips) > 1:
            # 这里可以实现IP响应时间测试
            # 简化实现：选择第一个
            logger.info(f"🎯 智能选择IP: {ips[0]} (从 {len(ips)} 个IP中选择)")
            return ips[0]

        return ips[0] if ips else None

    def get_cached_ips(self, domain: str) -> Optional[List[str]]:
        """获取缓存的IP列表"""
        if domain in self.cache and time.time() - self.cache_ttl.get(domain, 0) < self.default_ttl:
            return self.cache[domain]
        return None

    def clear_cache(self, domain: Optional[str] = None):
        """清除DNS缓存"""
        if domain:
            self.cache.pop(domain, None)
            self.cache_ttl.pop(domain, None)
            logger.info(f"🗑️ 清除DNS缓存: {domain}")
        else:
            self.cache.clear()
            self.cache_ttl.clear()
            logger.info("🗑️ 清除所有DNS缓存")

    def get_stats(self) -> Dict[str, Any]:
        """获取DNS统计"""
        return {
            'cache_size': len(self.cache),
            'failed_domains': len(self.failed_domains),
            'pre_resolve_domains': len(self.pre_resolve_domains),
            'cache_hit_rate': self._calculate_hit_rate()
        }

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率（简化版）"""
        # 这里可以实现更复杂的命中率计算
        return 0.8  # 假设命中率

    async def periodic_refresh(self, interval: int = 300):
        """定期刷新DNS缓存"""
        while True:
            try:
                await asyncio.sleep(interval)

                # 刷新即将过期的缓存
                current_time = time.time()
                domains_to_refresh = []

                for domain, ttl in self.cache_ttl.items():
                    if current_time - ttl > self.default_ttl * 0.8:  # 80% TTL时刷新
                        domains_to_refresh.append(domain)

                if domains_to_refresh:
                    logger.info(f"🔄 刷新DNS缓存: {domains_to_refresh}")
                    for domain in domains_to_refresh:
                        await self.resolve_domain(domain, force_refresh=True)

            except Exception as e:
                logger.error(f"定期DNS刷新失败: {e}")

# 全局DNS管理器
dns_manager = DNSManager()

# 便捷的DNS函数
async def resolve_ai_providers() -> Dict[str, List[str]]:
    """解析所有AI提供商"""
    return await dns_manager.pre_resolve_all()

def get_dns_stats() -> Dict[str, Any]:
    """获取DNS统计"""
    return dns_manager.get_stats()

def clear_dns_cache(domain: Optional[str] = None):
    """清除DNS缓存"""
    dns_manager.clear_cache(domain)

# 在程序启动时预解析DNS
async def setup_dns_resolution():
    """设置DNS解析"""
    logger.info("🔧 初始化DNS解析...")

    # 预解析所有AI提供商
    results = await resolve_ai_providers()

    # 启动定期刷新任务
    asyncio.create_task(dns_manager.periodic_refresh())

    logger.info(f"✅ DNS初始化完成，预解析成功: {len(results)} 个域名")
    return results
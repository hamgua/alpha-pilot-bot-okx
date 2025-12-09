"""
HTTP客户端抽象层
支持多种HTTP客户端后端，提供更好的连接稳定性
"""

import asyncio
import aiohttp
import httpx
from typing import Dict, Any, Optional, Union
import logging
from abc import ABC, abstractmethod
import time
from enum import Enum

logger = logging.getLogger(__name__)

class HTTPBackend(Enum):
    """HTTP客户端后端"""
    AIOHTTP = "aiohttp"
    HTTPX = "httpx"
    CURL_CFFI = "curl_cffi"  # 更强的抗封锁能力

class BaseHTTPClient(ABC):
    """HTTP客户端基类"""

    @abstractmethod
    async def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送POST请求"""
        pass

    @abstractmethod
    async def close(self):
        """关闭客户端"""
        pass

class HTTPXClient(BaseHTTPClient):
    """httpx客户端实现"""

    def __init__(self, timeout_config: Dict[str, float]):
        self.timeout_config = timeout_config
        self._client: Optional[httpx.AsyncClient] = None
        self._setup_client()

    def _setup_client(self):
        """设置httpx客户端"""
        # httpx 超时配置
        timeout = httpx.Timeout(
            connect=self.timeout_config.get('connection_timeout', 10),
            read=self.timeout_config.get('response_timeout', 30),
            write=self.timeout_config.get('response_timeout', 30),
            pool=self.timeout_config.get('total_timeout', 60)
        )

        # 更强大的连接池配置
        limits = httpx.Limits(
            max_keepalive_connections=50,
            max_connections=100,
            keepalive_expiry=120
        )

        # 创建客户端
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            http2=True,  # 启用HTTP/2
            follow_redirects=True,
            max_redirects=5
        )

    async def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送POST请求"""
        try:
            start_time = time.time()

            response = await self._client.post(url, **kwargs)

            response_time = time.time() - start_time
            logger.info(f"🚀 httpx 请求完成: {url} ({response_time:.2f}s)")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"httpx 请求失败: {response.status_code} - {response.text[:200]}")
                return None

        except httpx.TimeoutException as e:
            logger.error(f"httpx 超时: {url} - {e}")
            return None
        except httpx.ConnectError as e:
            logger.error(f"httpx 连接错误: {url} - {e}")
            return None
        except httpx.ReadError as e:
            logger.error(f"httpx 读取错误: {url} - {e}")
            return None
        except Exception as e:
            logger.error(f"httpx 异常: {url} - {type(e).__name__}: {e}")
            return None

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()

class CurlCFFIClient(BaseHTTPClient):
    """curl_cffi客户端实现 - 更强的抗封锁能力"""

    def __init__(self, timeout_config: Dict[str, float]):
        self.timeout_config = timeout_config
        self._client: Optional[Any] = None
        self._setup_client()

    def _setup_client(self):
        """设置curl_cffi客户端"""
        try:
            from curl_cffi import requests as curl_requests

            # curl_cffi 配置
            self._client = curl_requests.AsyncSession(
                timeout=self.timeout_config.get('total_timeout', 60),
                impersonate="chrome110",  # 模拟Chrome浏览器
                verify=True
            )

            # 设置连接池
            self._client.curl.setopt(
                self._client.curl.CURLOPT_MAXCONNECTS,
                self.timeout_config.get('connection_pool_size', 20)
            )

        except ImportError:
            logger.warning("curl_cffi 未安装，使用回退方案")
            self._client = None

    async def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送POST请求"""
        if not self._client:
            return None

        try:
            start_time = time.time()

            response = await self._client.post(url, **kwargs)

            response_time = time.time() - start_time
            logger.info(f"🚀 curl_cffi 请求完成: {url} ({response_time:.2f}s)")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"curl_cffi 请求失败: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"curl_cffi 异常: {url} - {type(e).__name__}: {e}")
            return None

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()

class HTTPClientManager:
    """HTTP客户端管理器"""

    def __init__(self, backend: HTTPBackend = HTTPBackend.HTTPX, timeout_config: Dict[str, float] = None):
        self.backend = backend
        self.timeout_config = timeout_config or {
            'connection_timeout': 15.0,
            'response_timeout': 30.0,
            'total_timeout': 60.0,
            'connection_pool_size': 20
        }
        self._client: Optional[BaseHTTPClient] = None
        self._setup_client()

    def _setup_client(self):
        """设置客户端"""
        if self.backend == HTTPBackend.HTTPX:
            self._client = HTTPXClient(self.timeout_config)
        elif self.backend == HTTPBackend.CURL_CFFI:
            self._client = CurlCFFIClient(self.timeout_config)
        else:
            # 默认使用httpx
            self._client = HTTPXClient(self.timeout_config)

        logger.info(f"✅ HTTP客户端已初始化: {self.backend.value}")

    async def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送POST请求"""
        if not self._client:
            logger.error("HTTP客户端未初始化")
            return None

        # 实现重试逻辑
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                result = await self._client.post(url, **kwargs)
                if result is not None:
                    return result

                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"请求失败，{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"请求异常: {e}")
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    await asyncio.sleep(wait_time)

        return None

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()

# 全局客户端实例
http_client_manager = HTTPClientManager()
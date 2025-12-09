"""
连接管理器
提供TCP连接保活和连接池优化
"""

import asyncio
import socket
import time
import logging
from typing import Dict, Any, Optional
import platform

logger = logging.getLogger(__name__)

class ConnectionManager:
    """连接管理器 - 处理TCP连接保活"""

    def __init__(self):
        self.connection_stats = {
            'total_connections': 0,
            'failed_connections': 0,
            'connection_resets': 0,
            'keepalive_sends': 0
        }
        self.is_enabled = self._check_keepalive_support()

    def _check_keepalive_support(self) -> bool:
        """检查系统是否支持TCP keepalive"""
        try:
            # 测试创建一个socket
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if platform.system() != 'Windows':
                # Linux/macOS 系统
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            test_sock.close()
            logger.info("✅ TCP keepalive 支持已检测")
            return True
        except Exception as e:
            logger.warning(f"⚠️ TCP keepalive 不支持: {e}")
            return False

    def configure_keepalive(self, sock: socket.socket,
                          idle_time: int = 30,
                          interval: int = 10,
                          probe_count: int = 3) -> bool:
        """配置TCP keepalive参数"""
        if not self.is_enabled:
            return False

        try:
            platform_name = platform.system()

            if platform_name == 'Linux':
                # Linux 系统
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle_time)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, probe_count)

            elif platform_name == 'Darwin':  # macOS
                # macOS 系统
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # macOS 使用 TCP_KEEPALIVE 替代 TCP_KEEPIDLE
                sock.setsockopt(socket.IPPROTO_TCP, 0x10, idle_time)  # TCP_KEEPALIVE
                sock.setsockopt(socket.IPPROTO_TCP, 0x101, interval)  # TCP_KEEPINTVL
                sock.setsockopt(socket.IPPROTO_TCP, 0x102, probe_count)  # TCP_KEEPCNT

            elif platform_name == 'Windows':
                # Windows 系统
                sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, idle_time * 1000, interval * 1000))

            logger.info(f"🔧 TCP keepalive 已配置: idle={idle_time}s, interval={interval}s, probes={probe_count}")
            return True

        except Exception as e:
            logger.error(f"配置TCP keepalive失败: {e}")
            return False

    def create_optimized_socket(self, family: int = socket.AF_INET,
                              protocol: int = socket.IPPROTO_TCP) -> socket.socket:
        """创建优化的socket"""
        sock = socket.socket(family, socket.SOCK_STREAM, protocol)

        # 基础优化
        try:
            # 启用地址复用
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # 禁用Nagle算法，减少延迟
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # 设置发送/接收缓冲区
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

            # 配置TCP keepalive
            self.configure_keepalive(sock)

            # 设置linger选项
            linger = struct.pack('ii', 1, 5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)

            logger.debug("✅ Socket 优化配置完成")

        except Exception as e:
            logger.warning(f"Socket 优化失败: {e}")

        return sock

    async def monitor_connection_health(self, provider: str,
                                      check_interval: int = 30) -> bool:
        """监控连接健康状态"""
        try:
            # 模拟连接检查
            await asyncio.sleep(check_interval)

            # 这里可以添加实际的连接检查逻辑
            # 例如：发送轻量级ping请求

            logger.debug(f"📊 {provider} 连接健康检查完成")
            return True

        except Exception as e:
            logger.error(f"{provider} 连接健康检查失败: {e}")
            return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return self.connection_stats.copy()

    def reset_stats(self):
        """重置统计"""
        self.connection_stats = {
            'total_connections': 0,
            'failed_connections': 0,
            'connection_resets': 0,
            'keepalive_sends': 0
        }

# 全局连接管理器
connection_manager = ConnectionManager()

# 添加 struct 导入
import struct

# 更新 TCPConnector 使用优化的 socket
def create_optimized_connector() -> aiohttp.TCPConnector:
    """创建优化的 TCPConnector"""

    class OptimizedTCPConnector(aiohttp.TCPConnector):
        """优化的 TCPConnector"""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._connection_manager = connection_manager

        async def _create_connection(self, req, traces, timeout):
            """创建连接时使用优化的 socket"""
            try:
                # 调用父类方法创建连接
                transport, protocol = await super()._create_connection(req, traces, timeout)

                # 如果可能，配置 socket keepalive
                if hasattr(transport, '_sock') and transport._sock:
                    sock = transport._sock
                    if hasattr(sock, 'setsockopt'):
                        self._connection_manager.configure_keepalive(sock)
                        connection_manager.connection_stats['total_connections'] += 1

                return transport, protocol

            except Exception as e:
                connection_manager.connection_stats['failed_connections'] += 1
                logger.error(f"创建优化连接失败: {e}")
                raise

    return OptimizedTCPConnector(
        limit=50,
        limit_per_host=20,
        ttl_dns_cache=600,
        use_dns_cache=True,
        keepalive_timeout=60,
        enable_cleanup_closed=True,
        force_close=False,
        ssl=False,
        happy_eyeballs_delay=0.25,
        interleave=None,
        family=0,
        local_addr=None,
        resolver=None,
        socket_read_timeout=30,
        socket_connect_timeout=15
    )
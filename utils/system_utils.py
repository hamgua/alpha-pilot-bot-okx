"""
系统工具模块
提供系统级别的实用功能
"""

import os
import sys
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import time

logger = logging.getLogger(__name__)


class SystemUtils:
    """系统工具类"""

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """获取系统信息"""
        try:
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'platform_release': platform.release(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'hostname': platform.node(),
                'python_version': sys.version,
                'python_version_info': list(sys.version_info),
                'current_time': datetime.now().isoformat(),
                'timezone': time.tzname
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {}

    @staticmethod
    def get_disk_usage(path: str = '/') -> Dict[str, float]:
        """获取磁盘使用情况

        Args:
            path: 要检查的磁盘路径

        Returns:
            磁盘使用信息
        """
        try:
            import psutil
            disk = psutil.disk_usage(path)
            return {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent': disk.percent
            }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取磁盘使用信息")
            return {
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent': 0
            }
        except Exception as e:
            logger.error(f"获取磁盘使用信息失败: {e}")
            return {
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent': 0
            }

    @staticmethod
    def get_memory_info() -> Dict[str, float]:
        """获取内存信息"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'used_gb': memory.used / (1024**3),
                'percent': memory.percent,
                'free_gb': memory.free / (1024**3)
            }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取内存信息")
            return {
                'total_gb': 0,
                'available_gb': 0,
                'used_gb': 0,
                'percent': 0,
                'free_gb': 0
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            return {
                'total_gb': 0,
                'available_gb': 0,
                'used_gb': 0,
                'percent': 0,
                'free_gb': 0
            }

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """获取CPU信息"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0
            }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取CPU信息")
            return {
                'cpu_percent': 0,
                'cpu_count': 1,
                'cpu_count_logical': 1,
                'load_average': 0,
                'cpu_freq': 0
            }
        except Exception as e:
            logger.error(f"获取CPU信息失败: {e}")
            return {
                'cpu_percent': 0,
                'cpu_count': 1,
                'cpu_count_logical': 1,
                'load_average': 0,
                'cpu_freq': 0
            }

    @staticmethod
    def get_process_info(pid: Optional[int] = None) -> Dict[str, Any]:
        """获取进程信息

        Args:
            pid: 进程ID，如果为None则获取当前进程

        Returns:
            进程信息
        """
        try:
            import psutil
            if pid is None:
                pid = os.getpid()

            process = psutil.Process(pid)
            with process.oneshot():
                return {
                    'pid': pid,
                    'name': process.name(),
                    'status': process.status(),
                    'created': datetime.fromtimestamp(process.create_time()).isoformat(),
                    'memory_percent': process.memory_percent(),
                    'memory_info_mb': process.memory_info().rss / (1024**2),
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'open_files': len(process.open_files()),
                    'connections': len(process.connections())
                }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取进程信息")
            return {'pid': pid or os.getpid(), 'error': 'psutil not available'}
        except psutil.NoSuchProcess:
            logger.error(f"进程 {pid} 不存在")
            return {'pid': pid, 'error': 'process not found'}
        except Exception as e:
            logger.error(f"获取进程信息失败: {e}")
            return {'pid': pid or os.getpid(), 'error': str(e)}

    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        """获取网络信息"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取网络信息")
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
                'errin': 0,
                'errout': 0,
                'dropin': 0,
                'dropout': 0
            }
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
                'errin': 0,
                'errout': 0,
                'dropin': 0,
                'dropout': 0
            }

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """获取环境变量信息"""
        try:
            # 获取重要的环境变量
            important_vars = [
                'PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL',
                'LANG', 'LC_ALL', 'TZ', 'PWD'
            ]

            env_info = {}
            for var in important_vars:
                if var in os.environ:
                    env_info[var] = os.environ[var]

            return {
                'environment_variables': env_info,
                'working_directory': os.getcwd(),
                'user_id': os.getuid() if hasattr(os, 'getuid') else None,
                'group_id': os.getgid() if hasattr(os, 'getgid') else None
            }
        except Exception as e:
            logger.error(f"获取环境信息失败: {e}")
            return {'error': str(e)}

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            memory_info = SystemUtils.get_memory_info()
            cpu_info = SystemUtils.get_cpu_info()
            disk_info = SystemUtils.get_disk_usage()

            # 计算健康分数（0-100）
            health_score = 100.0

            # 内存使用率扣分
            if memory_info['percent'] > 90:
                health_score -= 30
            elif memory_info['percent'] > 80:
                health_score -= 20
            elif memory_info['percent'] > 70:
                health_score -= 10

            # CPU使用率扣分
            if cpu_info['cpu_percent'] > 90:
                health_score -= 30
            elif cpu_info['cpu_percent'] > 80:
                health_score -= 20
            elif cpu_info['cpu_percent'] > 70:
                health_score -= 10

            # 磁盘使用率扣分
            if disk_info['percent'] > 90:
                health_score -= 30
            elif disk_info['percent'] > 80:
                health_score -= 20
            elif disk_info['percent'] > 70:
                health_score -= 10

            return {
                'health_score': max(0, health_score),
                'status': 'healthy' if health_score >= 70 else 'warning' if health_score >= 50 else 'critical',
                'memory': memory_info,
                'cpu': cpu_info,
                'disk': disk_info,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {'health_score': 0, 'status': 'unknown', 'error': str(e)}

    @staticmethod
    def run_system_command(command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """运行系统命令

        Args:
            command: 命令和参数列表
            timeout: 超时时间（秒）

        Returns:
            命令执行结果
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command)
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': 'Command timed out',
                'command': ' '.join(command)
            }
        except Exception as e:
            logger.error(f"运行系统命令失败: {e}")
            return {
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(command)
            }

    @staticmethod
    def get_python_packages() -> List[Dict[str, str]]:
        """获取已安装的Python包信息"""
        try:
            result = SystemUtils.run_system_command([sys.executable, '-m', 'pip', 'list', '--format=json'])
            if result['success']:
                import json
                return json.loads(result['stdout'])
            return []
        except Exception as e:
            logger.error(f"获取Python包信息失败: {e}")
            return []

    @staticmethod
    def check_port_available(port: int, host: str = '0.0.0.0') -> bool:
        """检查端口是否可用

        Args:
            port: 端口号
            host: 主机地址

        Returns:
            端口是否可用
        """
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result != 0
        except Exception as e:
            logger.error(f"检查端口可用性失败: {e}")
            return False

    @staticmethod
    def get_file_info(filepath: str) -> Dict[str, Any]:
        """获取文件信息

        Args:
            filepath: 文件路径

        Returns:
            文件信息
        """
        try:
            from pathlib import Path
            path = Path(filepath)

            if not path.exists():
                return {'error': 'File not found'}

            stat = path.stat()
            return {
                'exists': True,
                'size_bytes': stat.st_size,
                'size_mb': stat.st_size / (1024 ** 2),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'is_file': path.is_file(),
                'is_directory': path.is_dir(),
                'permissions': oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return {'error': str(e)}

    @staticmethod
    def cleanup_temp_files(pattern: str = 'tmp*', directory: str = '/tmp') -> int:
        """清理临时文件

        Args:
            pattern: 文件匹配模式
            directory: 目录路径

        Returns:
            删除的文件数量
        """
        try:
            import glob
            import os
            from pathlib import Path

            temp_dir = Path(directory)
            if not temp_dir.exists():
                return 0

            files = list(temp_dir.glob(pattern))
            deleted_count = 0

            for file_path in files:
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        deleted_count += 1
                    elif file_path.is_dir():
                        import shutil
                        shutil.rmtree(file_path)
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除文件失败 {file_path}: {e}")

            return deleted_count
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0

    @staticmethod
    def get_system_load() -> Dict[str, float]:
        """获取系统负载信息"""
        try:
            import psutil
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            return {
                'load_1min': load_avg[0],
                'load_5min': load_avg[1],
                'load_15min': load_avg[2]
            }
        except Exception as e:
            logger.error(f"获取系统负载失败: {e}")
            return {'load_1min': 0, 'load_5min': 0, 'load_15min': 0}

    @staticmethod
    def monitor_resources(interval: int = 1, duration: int = 10) -> List[Dict[str, Any]]:
        """监控资源使用情况

        Args:
            interval: 监控间隔（秒）
            duration: 监控时长（秒）

        Returns:
            资源使用历史记录
        """
        try:
            import psutil
            samples = []
            steps = int(duration / interval)

            for _ in range(steps):
                samples.append({
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': psutil.cpu_percent(interval=None),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent
                })
                time.sleep(interval)

            return samples
        except ImportError:
            logger.warning("psutil模块未安装，无法监控资源")
            return []
        except Exception as e:
            logger.error(f"监控资源失败: {e}")
            return []


# 全局实例
system_utils = SystemUtils()
"""
系统监控模块
提供系统性能监控和健康检查功能
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_recv': self.network_bytes_recv,
            'timestamp': self.timestamp.isoformat()
        }

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, monitoring_interval: int = 30):
        """
        初始化系统监控器
        
        Args:
            monitoring_interval: 监控间隔（秒）
        """
        self.monitoring_interval = monitoring_interval
        self.metrics_history: List[SystemMetrics] = []
        self.is_monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._stats = {
            'alerts_triggered': 0,
            'monitoring_duration': 0,
            'peak_cpu': 0.0,
            'peak_memory': 0.0
        }
    
    def start_monitoring(self) -> bool:
        """开始系统监控"""
        try:
            if self.is_monitoring:
                logger.warning("系统监控已在运行")
                return True
            
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info(f"🚀 系统监控已启动，间隔: {self.monitoring_interval}秒")
            return True
            
        except Exception as e:
            logger.error(f"启动系统监控失败: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止系统监控"""
        try:
            if not self.is_monitoring:
                logger.warning("系统监控未运行")
                return True
            
            self.is_monitoring = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            # 更新监控时长
            self._stats['monitoring_duration'] = time.time() - self._start_time
            
            logger.info("🛑 系统监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止系统监控失败: {e}")
            return False
    
    def increment_counter(self, counter_name: str, value: int = 1) -> bool:
        """增加计数器"""
        try:
            with self._lock:
                if 'counters' not in self._stats:
                    self._stats['counters'] = {}
                if counter_name not in self._stats['counters']:
                    self._stats['counters'][counter_name] = 0
                self._stats['counters'][counter_name] += value
            return True
        except Exception as e:
            logger.error(f"增加计数器失败: {e}")
            return False

    def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集系统指标
                metrics = self._collect_metrics()
                
                with self._lock:
                    self.metrics_history.append(metrics)
                    
                    # 更新峰值记录
                    self._stats['peak_cpu'] = max(self._stats['peak_cpu'], metrics.cpu_percent)
                    self._stats['peak_memory'] = max(self._stats['peak_memory'], metrics.memory_percent)
                
                # 检查警报条件
                self._check_alerts(metrics)
                
                # 保持历史记录在合理范围内
                if len(self.metrics_history) > 1000:
                    with self._lock:
                        self.metrics_history = self.metrics_history[-500:]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            # 网络流量
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                timestamp=datetime.now()
            )
    
    def _check_alerts(self, metrics: SystemMetrics) -> List[Dict[str, Any]]:
        """检查警报条件"""
        alerts = []
        
        try:
            # CPU使用率警报
            if metrics.cpu_percent > 80:
                alerts.append({
                    'type': 'high_cpu',
                    'severity': 'warning' if metrics.cpu_percent < 90 else 'critical',
                    'value': metrics.cpu_percent,
                    'threshold': 80,
                    'message': f"CPU使用率过高: {metrics.cpu_percent:.1f}%"
                })
            
            # 内存使用率警报
            if metrics.memory_percent > 85:
                alerts.append({
                    'type': 'high_memory',
                    'severity': 'warning' if metrics.memory_percent < 95 else 'critical',
                    'value': metrics.memory_percent,
                    'threshold': 85,
                    'message': f"内存使用率过高: {metrics.memory_percent:.1f}%"
                })
            
            # 磁盘使用率警报
            if metrics.disk_usage_percent > 90:
                alerts.append({
                    'type': 'high_disk',
                    'severity': 'warning' if metrics.disk_usage_percent < 95 else 'critical',
                    'value': metrics.disk_usage_percent,
                    'threshold': 90,
                    'message': f"磁盘使用率过高: {metrics.disk_usage_percent:.1f}%"
                })
            
            # 记录警报
            for alert in alerts:
                self._stats['alerts_triggered'] += 1
                logger.warning(f"🚨 系统警报: {alert['message']}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查警报失败: {e}")
            return []
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前系统指标"""
        with self._lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_metrics_history(self, limit: int = 100) -> List[SystemMetrics]:
        """获取历史指标"""
        with self._lock:
            return self.metrics_history[-limit:] if limit > 0 else self.metrics_history.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            current_metrics = self.get_current_metrics()
            
            if current_metrics:
                return {
                    'is_monitoring': self.is_monitoring,
                    'current_cpu': current_metrics.cpu_percent,
                    'current_memory': current_metrics.memory_percent,
                    'current_disk': current_metrics.disk_usage_percent,
                    'peak_cpu': self._stats['peak_cpu'],
                    'peak_memory': self._stats['peak_memory'],
                    'alerts_triggered': self._stats['alerts_triggered'],
                    'monitoring_duration_hours': self._stats['monitoring_duration'] / 3600,
                    'status': 'healthy' if current_metrics.cpu_percent < 80 and current_metrics.memory_percent < 85 else 'warning'
                }
            else:
                return {
                    'is_monitoring': self.is_monitoring,
                    'status': 'no_data',
                    'message': '暂无监控数据'
                }
                
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def get_performance_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            recent_metrics = self.get_metrics_history(limit=int(3600 * period_hours / self.monitoring_interval))
            
            if not recent_metrics:
                return {'error': '暂无性能数据'}
            
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_percent for m in recent_metrics]
            disk_values = [m.disk_usage_percent for m in recent_metrics]
            
            return {
                'period_hours': period_hours,
                'cpu_stats': {
                    'average': sum(cpu_values) / len(cpu_values),
                    'max': max(cpu_values),
                    'min': min(cpu_values),
                    'std_dev': (sum((x - sum(cpu_values)/len(cpu_values))**2 for x in cpu_values) / len(cpu_values))**0.5
                },
                'memory_stats': {
                    'average': sum(memory_values) / len(memory_values),
                    'max': max(memory_values),
                    'min': min(memory_values),
                    'std_dev': (sum((x - sum(memory_values)/len(memory_values))**2 for x in memory_values) / len(memory_values))**0.5
                },
                'disk_stats': {
                    'average': sum(disk_values) / len(disk_values),
                    'max': max(disk_values),
                    'min': min(disk_values)
                },
                'data_points': len(recent_metrics),
                'peak_performance': {
                    'cpu': self._stats['peak_cpu'],
                    'memory': self._stats['peak_memory']
                }
            }
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {'error': str(e)}
    
    def export_metrics(self, format: str = 'json', period_hours: int = 24) -> str:
        """导出监控数据"""
        try:
            if format == 'json':
                import json
                recent_metrics = self.get_metrics_history(limit=int(3600 * period_hours / self.monitoring_interval))
                
                return json.dumps({
                    'metrics_history': [m.to_dict() for m in recent_metrics],
                    'performance_summary': self.get_performance_summary(period_hours),
                    'system_status': self.get_system_status(),
                    'export_time': datetime.now().isoformat()
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出监控数据失败: {e}")
            return f"导出失败: {e}"

class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self, process_name: str = "python"):
        self.process_name = process_name
        self.processes: List[psutil.Process] = []
        self._find_processes()
    
    def _find_processes(self):
        """查找相关进程"""
        try:
            self.processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if self.process_name.lower() in proc.info['name'].lower():
                    self.processes.append(proc)
        except Exception as e:
            logger.error(f"查找进程失败: {e}")
    
    def get_process_stats(self) -> List[Dict[str, Any]]:
        """获取进程统计"""
        stats = []
        try:
            for proc in self.processes:
                try:
                    stats.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent(),
                        'memory_mb': proc.memory_info().rss / (1024 * 1024),
                        'status': proc.status()
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"获取进程统计失败: {e}")
        
        return stats
    
    def kill_process(self, pid: int) -> bool:
        """终止指定进程"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)
            return True
        except Exception as e:
            logger.error(f"终止进程失败: {e}")
            return False

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.health_checks: Dict[str, callable] = {}
        self.health_status: Dict[str, bool] = {}
    
    def register_check(self, name: str, check_function: callable):
        """注册健康检查"""
        self.health_checks[name] = check_function
    
    def run_health_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                is_healthy = check_func()
                self.health_status[name] = is_healthy
                results[name] = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                self.health_status[name] = False
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return {
            'overall_health': all(self.health_status.values()),
            'checks': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, bool]:
        """获取健康状态"""
        return self.health_status.copy()

# 全局监控实例
system_monitor = SystemMonitor()
process_monitor = ProcessMonitor()
health_checker = HealthChecker()

# 默认健康检查
def register_default_health_checks():
    """注册默认健康检查"""
    # 系统资源检查
    health_checker.register_check(
        'system_resources',
        lambda: system_monitor.get_current_metrics() is not None
    )
    
    # 磁盘空间检查
    health_checker.register_check(
        'disk_space',
        lambda: psutil.disk_usage('/').percent < 90
    )
    
    # 内存使用检查
    health_checker.register_check(
        'memory_usage',
        lambda: psutil.virtual_memory().percent < 85
    )

# 注册默认检查
register_default_health_checks()

# 向后兼容的函数
def get_system_status() -> Dict[str, Any]:
    """获取系统状态（向后兼容）"""
    return system_monitor.get_system_status()

def get_performance_summary(period_hours: int = 24) -> Dict[str, Any]:
    """获取性能摘要（向后兼容）"""
    return system_monitor.get_performance_summary(period_hours)

def start_system_monitoring() -> bool:
    """启动系统监控（向后兼容）"""
    return system_monitor.start_monitoring()

def stop_system_monitoring() -> bool:
    """停止系统监控（向后兼容）"""
    return system_monitor.stop_monitoring()

# 导出主要功能
__all__ = [
    'SystemMonitor',
    'ProcessMonitor',
    'HealthChecker',
    'system_monitor',
    'process_monitor',
    'health_checker',
    'get_system_status',
    'get_performance_summary',
    'start_system_monitoring',
    'stop_system_monitoring',
    'register_default_health_checks'
]
"""
熔断机制系统
基于原项目功能.md的设计规范，实现多级熔断保护和风险控制系统
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    熔断机制系统
    实现多级熔断保护，包括价格暴跌、系统异常、连续亏损等触发条件
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('circuit_breaker', {})
        self.enabled = self.config.get('enabled', True)
        
        # 熔断阈值配置
        self.thresholds = {
            'price_crash': self.config.get('price_crash_threshold', 0.03),  # 3%暴跌
            'daily_loss': self.config.get('daily_loss_threshold', 0.05),   # 5%日亏损
            'consecutive_losses': self.config.get('consecutive_losses', 3),  # 连续亏损次数
            'max_drawdown': self.config.get('max_drawdown', 0.15),         # 15%最大回撤
            'api_failures': self.config.get('api_failures', 5),            # API失败次数
            'system_errors': self.config.get('system_errors', 10)          # 系统错误次数
        }
        
        # 熔断状态
        self.state = {
            'is_tripped': False,
            'trip_reason': None,
            'trip_time': None,
            'recovery_time': None,
            'severity_level': None,
            'affected_systems': []
        }
        
        # 监控指标
        self.metrics = {
            'daily_pnl': 0.0,
            'consecutive_losses': 0,
            'total_drawdown': 0.0,
            'api_failure_count': 0,
            'system_error_count': 0,
            'last_reset_time': datetime.now()
        }
        
        # 价格监控
        self.price_monitor = PriceCrashMonitor(self.thresholds['price_crash'])
        
        # 熔断历史
        self.trip_history = []
        
        logger.info("⚡ 熔断机制系统初始化完成")
    
    async def check_circuit_breaker(self, market_data: Dict, account_data: Dict,
                                  system_status: Dict) -> Dict[str, Any]:
        """
        检查是否需要触发熔断机制
        
        Args:
            market_data: 市场数据
            account_data: 账户数据
            system_status: 系统状态
            
        Returns:
            熔断检查结果
        """
        
        if not self.enabled:
            return {'should_trip': False, 'reason': '熔断机制已禁用'}
        
        # 检查各项熔断条件
        checks = [
            self._check_price_crash(market_data),
            self._check_daily_loss(account_data),
            self._check_consecutive_losses(account_data),
            self._check_max_drawdown(account_data),
            self._check_system_health(system_status),
            self._check_api_failures(system_status)
        ]
        
        # 找出最严重的熔断条件
        critical_checks = [check for check in checks if check['should_trip']]
        
        if critical_checks:
            # 按严重程度排序
            critical_checks.sort(key=lambda x: x.get('severity', 0), reverse=True)
            
            most_critical = critical_checks[0]
            
            # 触发熔断
            await self._trip_circuit_breaker(
                most_critical['reason'],
                most_critical.get('severity', 'HIGH'),
                most_critical.get('affected_systems', ['trading'])
            )
            
            return {
                'should_trip': True,
                'reason': most_critical['reason'],
                'severity': most_critical.get('severity', 'HIGH'),
                'affected_systems': most_critical.get('affected_systems', ['trading']),
                'recovery_time': self._calculate_recovery_time(most_critical.get('severity', 'HIGH'))
            }
        
        return {'should_trip': False, 'reason': '所有检查通过'}
    
    def _check_price_crash(self, market_data: Dict) -> Dict[str, Any]:
        """检查价格暴跌"""
        
        is_crash = self.price_monitor.detect_crash(market_data)
        
        if is_crash:
            crash_info = self.price_monitor.get_crash_info()
            return {
                'should_trip': True,
                'reason': f"价格暴跌检测: {crash_info['crash_percentage']:.2%}",
                'severity': 'CRITICAL',
                'affected_systems': ['trading', 'risk_management'],
                'crash_info': crash_info
            }
        
        return {'should_trip': False, 'reason': '价格正常'}
    
    def _check_daily_loss(self, account_data: Dict) -> Dict[str, Any]:
        """检查日亏损"""
        
        daily_pnl = account_data.get('daily_pnl', 0)
        total_balance = account_data.get('total_balance', 10000)
        
        if total_balance > 0:
            loss_percentage = abs(daily_pnl) / total_balance
            
            if loss_percentage >= self.thresholds['daily_loss']:
                return {
                    'should_trip': True,
                    'reason': f"日亏损超限: {loss_percentage:.2%}",
                    'severity': 'HIGH',
                    'affected_systems': ['trading'],
                    'loss_percentage': loss_percentage
                }
        
        return {'should_trip': False, 'reason': '日亏损正常'}
    
    def _check_consecutive_losses(self, account_data: Dict) -> Dict[str, Any]:
        """检查连续亏损"""
        
        consecutive_losses = account_data.get('consecutive_losses', 0)
        
        if consecutive_losses >= self.thresholds['consecutive_losses']:
            return {
                'should_trip': True,
                'reason': f"连续亏损{consecutive_losses}次",
                'severity': 'MEDIUM',
                'affected_systems': ['trading', 'strategy'],
                'consecutive_losses': consecutive_losses
            }
        
        return {'should_trip': False, 'reason': '连续亏损正常'}
    
    def _check_max_drawdown(self, account_data: Dict) -> Dict[str, Any]:
        """检查最大回撤"""
        
        max_drawdown = account_data.get('max_drawdown', 0)
        
        if max_drawdown >= self.thresholds['max_drawdown']:
            return {
                'should_trip': True,
                'reason': f"最大回撤超限: {max_drawdown:.2%}",
                'severity': 'HIGH',
                'affected_systems': ['trading', 'position_sizing'],
                'max_drawdown': max_drawdown
            }
        
        return {'should_trip': False, 'reason': '回撤正常'}
    
    def _check_system_health(self, system_status: Dict) -> Dict[str, Any]:
        """检查系统健康状态"""
        
        system_errors = system_status.get('system_errors', 0)
        
        if system_errors >= self.thresholds['system_errors']:
            return {
                'should_trip': True,
                'reason': f"系统错误过多: {system_errors}次",
                'severity': 'MEDIUM',
                'affected_systems': ['all'],
                'system_errors': system_errors
            }
        
        return {'should_trip': False, 'reason': '系统健康'}
    
    def _check_api_failures(self, system_status: Dict) -> Dict[str, Any]:
        """检查API失败"""
        
        api_failures = system_status.get('api_failures', 0)
        
        if api_failures >= self.thresholds['api_failures']:
            return {
                'should_trip': True,
                'reason': f"API失败过多: {api_failures}次",
                'severity': 'MEDIUM',
                'affected_systems': ['trading', 'data_fetching'],
                'api_failures': api_failures
            }
        
        return {'should_trip': False, 'reason': 'API正常'}
    
    async def _trip_circuit_breaker(self, reason: str, severity: str, affected_systems: List[str]):
        """触发熔断机制"""
        
        trip_time = datetime.now()
        
        self.state = {
            'is_tripped': True,
            'trip_reason': reason,
            'trip_time': trip_time.isoformat(),
            'severity_level': severity,
            'affected_systems': affected_systems,
            'recovery_time': None
        }
        
        # 记录熔断历史
        self.trip_history.append({
            'trip_time': trip_time.isoformat(),
            'reason': reason,
            'severity': severity,
            'affected_systems': affected_systems
        })
        
        logger.warning(f"⚡ 熔断机制触发! 原因: {reason}, 严重程度: {severity}")
        logger.warning(f"⚡ 影响系统: {', '.join(affected_systems)}")
        
        # 发送警报
        await self._send_alert(reason, severity, affected_systems)
    
    async def reset_circuit_breaker(self, reason: str = "manual_reset") -> bool:
        """重置熔断机制"""
        
        if not self.state['is_tripped']:
            return False
        
        recovery_time = datetime.now()
        
        self.state.update({
            'is_tripped': False,
            'recovery_time': recovery_time.isoformat(),
            'trip_reason': None,
            'severity_level': None,
            'affected_systems': []
        })
        
        # 重置监控指标
        self.metrics.update({
            'api_failure_count': 0,
            'system_error_count': 0,
            'last_reset_time': recovery_time
        })
        
        logger.info(f"✅ 熔断机制已重置! 原因: {reason}")
        
        return True
    
    def _calculate_recovery_time(self, severity: str) -> int:
        """计算自动恢复时间（分钟）"""
        
        recovery_times = {
            'LOW': 15,
            'MEDIUM': 30,
            'HIGH': 60,
            'CRITICAL': 120
        }
        
        return recovery_times.get(severity, 30)
    
    async def _send_alert(self, reason: str, severity: str, affected_systems: List[str]):
        """发送熔断警报"""
        
        alert_message = {
            'type': 'CIRCUIT_BREAKER_TRIP',
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'severity': severity,
            'affected_systems': affected_systems,
            'state': self.state
        }
        
        # 这里可以集成实际的警报系统
        logger.critical(f"🚨 熔断警报: {json.dumps(alert_message, indent=2)}")
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """获取熔断机制状态"""
        
        return {
            'state': self.state,
            'metrics': self.metrics,
            'thresholds': self.thresholds,
            'trip_history': self.trip_history[-10:],  # 最近10次
            'enabled': self.enabled
        }
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """更新熔断阈值"""
        
        self.thresholds.update(new_thresholds)
        logger.info(f"🔧 熔断阈值已更新: {new_thresholds}")
    
    def is_system_affected(self, system_name: str) -> bool:
        """检查特定系统是否受影响"""
        
        return (self.state['is_tripped'] and 
                system_name in self.state.get('affected_systems', []))
    
    def get_recovery_progress(self) -> Dict[str, Any]:
        """获取恢复进度"""
        
        if not self.state['is_tripped']:
            return {'status': 'normal', 'progress': 100}
        
        trip_time = datetime.fromisoformat(self.state['trip_time'])
        recovery_time = self._calculate_recovery_time(self.state['severity_level'])
        expected_recovery = trip_time + timedelta(minutes=recovery_time)
        
        now = datetime.now()
        progress = min((now - trip_time).total_seconds() / (recovery_time * 60) * 100, 100)
        
        return {
            'status': 'tripped',
            'progress': int(progress),
            'expected_recovery': expected_recovery.isoformat(),
            'time_remaining': max((expected_recovery - now).total_seconds() / 60, 0)
        }


class PriceCrashMonitor:
    """价格暴跌监控器"""
    
    def __init__(self, crash_threshold: float):
        self.crash_threshold = crash_threshold
        self.price_history = []
        self.max_history_length = 100
        self.crash_info = {}
    
    def detect_crash(self, market_data: Dict) -> bool:
        """检测价格暴跌"""
        
        current_price = market_data.get('price', 0)
        if current_price <= 0:
            return False
        
        # 记录价格历史
        self.price_history.append({
            'price': current_price,
            'timestamp': datetime.now().isoformat()
        })
        
        # 限制历史长度
        if len(self.price_history) > self.max_history_length:
            self.price_history = self.price_history[-self.max_history_length:]
        
        # 计算暴跌
        if len(self.price_history) >= 5:
            recent_prices = [p['price'] for p in self.price_history[-5:]]
            max_price = max(recent_prices)
            min_price = min(recent_prices)
            
            if max_price > 0:
                crash_percentage = (max_price - min_price) / max_price
                
                if crash_percentage >= self.crash_threshold:
                    self.crash_info = {
                        'crash_percentage': crash_percentage,
                        'max_price': max_price,
                        'min_price': min_price,
                        'crash_time': datetime.now().isoformat()
                    }
                    return True
        
        return False
    
    def get_crash_info(self) -> Dict[str, Any]:
        """获取暴跌信息"""
        return self.crash_info.copy()
    
    def reset(self):
        """重置监控器"""
        self.price_history = []
        self.crash_info = {}


# 全局熔断机制实例
circuit_breaker = CircuitBreaker({
    'circuit_breaker': {
        'enabled': True,
        'price_crash_threshold': 0.03,
        'daily_loss_threshold': 0.05,
        'consecutive_losses': 3,
        'max_drawdown': 0.15,
        'api_failures': 5,
        'system_errors': 10
    }
})
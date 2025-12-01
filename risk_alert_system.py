"""
风险预警系统
基于原项目功能.md的设计规范，实现多维度风险监控和智能预警
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """预警配置"""
    enabled: bool = True
    severity: str = "MEDIUM"
    threshold: float = 0.0
    cooldown_minutes: int = 5
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = ["log", "console"]

class RiskAlertSystem:
    """
    风险预警系统
    实现多维度风险监控、分级预警、智能通知
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('risk_alerts', {})
        self.enabled = self.config.get('enabled', True)
        
        # 预警阈值配置
        self.alert_configs = {
            'price_volatility': AlertConfig(
                enabled=True,
                severity="HIGH",
                threshold=0.05,  # 5%波动率
                cooldown_minutes=5,
                notification_channels=["log", "webhook"]
            ),
            'liquidity_risk': AlertConfig(
                enabled=True,
                severity="MEDIUM",
                threshold=0.5,  # 50%流动性下降
                cooldown_minutes=10,
                notification_channels=["log"]
            ),
            'position_risk': AlertConfig(
                enabled=True,
                severity="HIGH",
                threshold=0.8,  # 80%仓位风险
                cooldown_minutes=15,
                notification_channels=["log", "email"]
            ),
            'account_risk': AlertConfig(
                enabled=True,
                severity="CRITICAL",
                threshold=0.1,  # 10%账户亏损
                cooldown_minutes=1,
                notification_channels=["log", "email", "sms"]
            ),
            'system_health': AlertConfig(
                enabled=True,
                severity="MEDIUM",
                threshold=5,  # 5次系统错误
                cooldown_minutes=5,
                notification_channels=["log", "webhook"]
            )
        }
        
        # 更新用户配置
        self.alert_configs.update(self.config.get('custom_alerts', {}))
        
        # 预警历史
        self.alert_history = []
        self.last_alert_time = {}
        
        # 风险指标缓存
        self.risk_cache = {}
        self.cache_timeout = 60  # 60秒缓存
        
        # 预警处理器
        self.alert_handlers = {
            'price_volatility': self._handle_price_volatility,
            'liquidity_risk': self._handle_liquidity_risk,
            'position_risk': self._handle_position_risk,
            'account_risk': self._handle_account_risk,
            'system_health': self._handle_system_health
        }
        
        logger.info("🚨 风险预警系统初始化完成")
    
    async def monitor_risks(self, market_data: Dict, account_data: Dict,
                          system_status: Dict) -> List[Dict[str, Any]]:
        """
        监控所有风险指标
        
        Args:
            market_data: 市场数据
            account_data: 账户数据
            system_status: 系统状态
            
        Returns:
            触发的预警列表
        """
        
        if not self.enabled:
            return []
        
        triggered_alerts = []
        
        # 检查各项风险指标
        risk_checks = [
            ('price_volatility', market_data),
            ('liquidity_risk', market_data),
            ('position_risk', account_data),
            ('account_risk', account_data),
            ('system_health', system_status)
        ]
        
        for alert_type, data in risk_checks:
            alert = await self._check_risk(alert_type, data)
            if alert:
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    async def _check_risk(self, alert_type: str, data: Dict) -> Optional[Dict[str, Any]]:
        """检查特定风险类型"""
        
        config = self.alert_configs.get(alert_type)
        if not config or not config.enabled:
            return None
        
        # 检查冷却时间
        last_alert = self.last_alert_time.get(alert_type, datetime.min)
        if datetime.now() - last_alert < timedelta(minutes=config.cooldown_minutes):
            return None
        
        # 获取风险指标
        risk_level = await self._calculate_risk_level(alert_type, data)
        
        if risk_level >= config.threshold:
            alert = {
                'type': alert_type,
                'severity': config.severity,
                'risk_level': risk_level,
                'message': self._generate_alert_message(alert_type, risk_level, data),
                'timestamp': datetime.now().isoformat(),
                'data': data,
                'config': config
            }
            
            # 处理预警
            await self._process_alert(alert)
            
            # 更新最后预警时间
            self.last_alert_time[alert_type] = datetime.now()
            
            return alert
        
        return None
    
    async def _calculate_risk_level(self, alert_type: str, data: Dict) -> float:
        """计算风险等级"""
        
        # 使用缓存避免重复计算
        cache_key = f"{alert_type}_{hash(str(sorted(data.items())))}"
        current_time = time.time()
        
        if cache_key in self.risk_cache:
            cached_data, timestamp = self.risk_cache[cache_key]
            if current_time - timestamp < self.cache_timeout:
                return cached_data
        
        # 计算风险等级
        risk_calculator = self.alert_handlers.get(alert_type)
        if risk_calculator:
            risk_level = risk_calculator(data)
        else:
            risk_level = 0.0
        
        # 缓存结果
        self.risk_cache[cache_key] = (risk_level, current_time)
        
        return risk_level
    
    def _handle_price_volatility(self, market_data: Dict) -> float:
        """处理价格波动风险"""
        
        volatility = market_data.get('volatility_24h', 0)
        avg_volatility = market_data.get('avg_volatility_30d', 0.02)
        
        if avg_volatility > 0:
            volatility_ratio = volatility / avg_volatility
            return min(volatility_ratio, 2.0)  # 限制最大值为2
        
        return volatility
    
    def _handle_liquidity_risk(self, market_data: Dict) -> float:
        """处理流动性风险"""
        
        current_volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume_24h', current_volume)
        orderbook_depth = market_data.get('orderbook_depth_1pct', 0)
        
        # 综合流动性指标
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        depth_score = min(orderbook_depth / 100000, 1.0)  # 标准化深度
        
        # 流动性风险 = 1 - 综合流动性
        liquidity_score = (volume_ratio + depth_score) / 2
        return max(1 - liquidity_score, 0)
    
    def _handle_position_risk(self, account_data: Dict) -> float:
        """处理仓位风险"""
        
        positions = account_data.get('positions', [])
        total_balance = account_data.get('total_balance', 0)
        
        if total_balance <= 0:
            return 0.0
        
        # 计算总风险敞口
        total_exposure = sum(pos.get('value', 0) for pos in positions)
        exposure_ratio = total_exposure / total_balance
        
        # 计算集中度风险
        if positions:
            max_position = max(pos.get('value', 0) for pos in positions)
            concentration_ratio = max_position / total_exposure if total_exposure > 0 else 0
        else:
            concentration_ratio = 0
        
        # 综合仓位风险
        position_risk = (exposure_ratio * 0.7 + concentration_ratio * 0.3)
        return min(position_risk, 1.0)
    
    def _handle_account_risk(self, account_data: Dict) -> float:
        """处理账户风险"""
        
        total_balance = account_data.get('total_balance', 0)
        initial_balance = account_data.get('initial_balance', total_balance)
        
        if initial_balance <= 0:
            return 0.0
        
        # 计算总亏损
        total_pnl = account_data.get('total_pnl', 0)
        loss_percentage = abs(total_pnl) / initial_balance
        
        # 计算回撤
        max_balance = account_data.get('max_balance', initial_balance)
        drawdown = (max_balance - total_balance) / max_balance if max_balance > 0 else 0
        
        # 综合账户风险
        account_risk = max(loss_percentage, drawdown)
        return min(account_risk, 1.0)
    
    def _handle_system_health(self, system_status: Dict) -> float:
        """处理系统健康风险"""
        
        error_count = system_status.get('error_count', 0)
        warning_count = system_status.get('warning_count', 0)
        api_failures = system_status.get('api_failures', 0)
        
        # 综合系统风险
        total_issues = error_count + warning_count * 0.5 + api_failures * 0.8
        
        # 标准化风险等级
        if total_issues <= 1:
            return 0.0
        elif total_issues <= 3:
            return 0.3
        elif total_issues <= 5:
            return 0.6
        elif total_issues <= 10:
            return 0.8
        else:
            return 1.0
    
    def _generate_alert_message(self, alert_type: str, risk_level: float, data: Dict) -> str:
        """生成预警消息"""
        
        messages = {
            'price_volatility': f"价格波动风险: {risk_level:.2f}, 当前波动率异常",
            'liquidity_risk': f"流动性风险: {risk_level:.2f}, 市场流动性下降",
            'position_risk': f"仓位风险: {risk_level:.2f}, 风险敞口过高",
            'account_risk': f"账户风险: {risk_level:.2f}, 账户亏损严重",
            'system_health': f"系统健康风险: {risk_level:.2f}, 系统异常增多"
        }
        
        return messages.get(alert_type, f"未知风险类型: {alert_type}")
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """处理预警"""
        
        # 记录预警历史
        self.alert_history.append(alert)
        
        # 限制历史记录长度
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # 发送通知
        config = alert['config']
        for channel in config.notification_channels:
            await self._send_notification(channel, alert)
    
    async def _send_notification(self, channel: str, alert: Dict[str, Any]):
        """发送通知"""
        
        if channel == "log":
            logger.warning(f"🚨 风险预警: {alert['message']}")
        elif channel == "console":
            print(f"🚨 风险预警: {alert['message']}")
        elif channel == "webhook":
            # 这里可以集成webhook通知
            logger.info(f"📡 Webhook通知: {alert}")
        elif channel == "email":
            # 这里可以集成邮件通知
            logger.info(f"📧 邮件通知: {alert}")
        elif channel == "sms":
            # 这里可以集成短信通知
            logger.info(f"📱 短信通知: {alert}")
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取预警摘要"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp']) >= cutoff_time
        ]
        
        # 按类型统计
        alert_stats = {}
        for alert in recent_alerts:
            alert_type = alert['type']
            if alert_type not in alert_stats:
                alert_stats[alert_type] = {
                    'count': 0,
                    'max_severity': 'LOW',
                    'latest_time': None
                }
            
            stats = alert_stats[alert_type]
            stats['count'] += 1
            
            # 更新最高严重程度
            severity_order = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
            current_severity = severity_order.get(stats['max_severity'], 0)
            new_severity = severity_order.get(alert['severity'], 0)
            
            if new_severity > current_severity:
                stats['max_severity'] = alert['severity']
            
            # 更新最新时间
            alert_time = datetime.fromisoformat(alert['timestamp'])
            if stats['latest_time'] is None or alert_time > datetime.fromisoformat(stats['latest_time']):
                stats['latest_time'] = alert['timestamp']
        
        return {
            'total_alerts': len(recent_alerts),
            'alert_stats': alert_stats,
            'recent_alerts': recent_alerts[-10:],  # 最近10条
            'system_status': {
                'enabled': self.enabled,
                'last_check': datetime.now().isoformat()
            }
        }
    
    def update_alert_config(self, alert_type: str, config: AlertConfig):
        """更新预警配置"""
        
        self.alert_configs[alert_type] = config
        logger.info(f"🔧 预警配置已更新: {alert_type} -> {config}")
    
    def get_risk_heatmap(self) -> Dict[str, float]:
        """获取风险热力图"""
        
        risk_levels = {}
        
        for alert_type, config in self.alert_configs.items():
            if config.enabled:
                risk_levels[alert_type] = config.threshold
        
        return risk_levels
    
    def simulate_alert(self, alert_type: str, risk_level: float) -> Dict[str, Any]:
        """模拟预警（用于测试）"""
        
        config = self.alert_configs.get(alert_type)
        if not config:
            return {'error': '未知的预警类型'}
        
        alert = {
            'type': alert_type,
            'severity': config.severity,
            'risk_level': risk_level,
            'message': f"模拟预警: {alert_type} 风险等级 {risk_level}",
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }
        
        self.alert_history.append(alert)
        
        return alert


class RiskMetricsCalculator:
    """风险指标计算器"""
    
    def __init__(self):
        self.metrics_cache = {}
        self.cache_timeout = 300  # 5分钟缓存
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """计算风险价值(VaR)"""
        
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """计算夏普比率"""
        
        if not returns or len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        return (avg_return - risk_free_rate) / std_dev
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """计算最大回撤"""
        
        if not equity_curve:
            return 0.0
        
        max_equity = equity_curve[0]
        max_drawdown = 0.0
        
        for equity in equity_curve:
            if equity > max_equity:
                max_equity = equity
            
            drawdown = (max_equity - equity) / max_equity
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown


# 全局风险预警系统实例
risk_alert_system = RiskAlertSystem({
    'risk_alerts': {
        'enabled': True
    }
})

# 全局风险指标计算器
risk_calculator = RiskMetricsCalculator()
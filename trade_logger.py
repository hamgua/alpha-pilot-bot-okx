#!/usr/bin/env python3
"""
交易日志管理器
统一记录AI决策和OKX实际交易的日志
"""

import json
import time
from datetime import datetime
from pathlib import Path
from logger_config import log_info, log_warning, log_error

class TradeLogger:
    """交易日志管理器"""
    
    def __init__(self):
        self.trade_log_file = Path("logs") / "trades.json"
        self.trade_log_file.parent.mkdir(exist_ok=True)
        
    def log_ai_decision(self, decision_data):
        """记录AI决策"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "AI_DECISION",
            "timestamp": timestamp,
            "signal": decision_data.get('signal', 'HOLD'),
            "confidence": decision_data.get('confidence', 'N/A'),
            "reason": decision_data.get('reason', ''),
            "price": decision_data.get('price', 0),
            "stop_loss": decision_data.get('stop_loss', 0),
            "take_profit": decision_data.get('take_profit', 0),
            "rsi": decision_data.get('rsi', 0),
            "kline_change": decision_data.get('kline_change', 0)
        }
        
        # 记录到统一日志
        log_info(f"🤖 AI决策: {log_entry['signal']} 信心:{log_entry['confidence']} 价格:${log_entry['price']:.2f} 原因:{log_entry['reason']}")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)
        
    def log_trade_execution(self, trade_data):
        """记录交易执行"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "TRADE_EXECUTION",
            "timestamp": timestamp,
            "action": trade_data.get('action', ''),
            "side": trade_data.get('side', ''),
            "size": trade_data.get('size', 0),
            "price": trade_data.get('price', 0),
            "value_usdt": trade_data.get('value_usdt', 0),
            "order_id": trade_data.get('order_id', ''),
            "status": trade_data.get('status', ''),
            "error": trade_data.get('error', '')
        }
        
        # 记录到统一日志
        if log_entry['status'] == 'success':
            log_info(f"🚀 交易执行: {log_entry['action']} {log_entry['side']} {log_entry['size']}张 @ ${log_entry['price']:.2f} 订单ID:{log_entry['order_id']}")
        else:
            log_error(f"❌ 交易失败: {log_entry['action']} {log_entry['error']}")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)
        
    def log_tp_sl_trigger(self, trigger_data):
        """记录止盈止损触发"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "TP_SL_TRIGGER",
            "timestamp": timestamp,
            "trigger_type": trigger_data.get('trigger_type', ''),
            "trigger_price": trigger_data.get('trigger_price', 0),
            "order_id": trigger_data.get('order_id', ''),
            "position_side": trigger_data.get('position_side', ''),
            "pnl_usdt": trigger_data.get('pnl_usdt', 0),
            "exit_price": trigger_data.get('exit_price', 0)
        }
        
        # 记录到统一日志
        trigger_emoji = "💰" if log_entry['trigger_type'] == 'TAKE_PROFIT' else "🛑"
        log_info(f"{trigger_emoji} 止盈止损触发: {log_entry['trigger_type']} @ ${log_entry['trigger_price']:.2f} PnL:{log_entry['pnl_usdt']:+.2f} USDT")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)
        
    def log_position_update(self, position_data):
        """记录持仓更新"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "POSITION_UPDATE",
            "timestamp": timestamp,
            "side": position_data.get('side', ''),
            "size": position_data.get('size', 0),
            "entry_price": position_data.get('entry_price', 0),
            "current_price": position_data.get('current_price', 0),
            "unrealized_pnl": position_data.get('unrealized_pnl', 0),
            "leverage": position_data.get('leverage', 0)
        }
        
        # 记录到统一日志
        log_info(f"📊 持仓更新: {log_entry['side']} {log_entry['size']}张 入场价:${log_entry['entry_price']:.2f} 当前价:${log_entry['current_price']:.2f} 未实现盈亏:{log_entry['unrealized_pnl']:+.2f} USDT")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)
        
    def log_order_status(self, order_data):
        """记录订单状态变化"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "ORDER_STATUS",
            "timestamp": timestamp,
            "order_id": order_data.get('order_id', ''),
            "status": order_data.get('status', ''),
            "filled_size": order_data.get('filled_size', 0),
            "filled_price": order_data.get('filled_price', 0),
            "remaining_size": order_data.get('remaining_size', 0),
            "avg_price": order_data.get('avg_price', 0)
        }
        
        # 记录到统一日志
        status_emoji = "✅" if log_entry['status'] == 'closed' else "⏳"
        log_info(f"{status_emoji} 订单状态: {log_entry['order_id']} {log_entry['status']} 已成交:{log_entry['filled_size']}张 均价:${log_entry['avg_price']:.2f}")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)
        
    def _append_to_trade_log(self, log_entry):
        """追加到交易日志文件"""
        try:
            # 读取现有日志
            trade_logs = []
            if self.trade_log_file.exists():
                with open(self.trade_log_file, 'r', encoding='utf-8') as f:
                    try:
                        trade_logs = json.load(f)
                    except json.JSONDecodeError:
                        trade_logs = []
            
            # 添加新日志
            trade_logs.append(log_entry)
            
            # 只保留最近1000条记录
            if len(trade_logs) > 1000:
                trade_logs = trade_logs[-1000:]
            
            # 保存回文件
            with open(self.trade_log_file, 'w', encoding='utf-8') as f:
                json.dump(trade_logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log_error(f"写入交易日志失败: {e}")
            
    def get_recent_trades(self, limit=50):
        """获取最近的交易记录"""
        try:
            if not self.trade_log_file.exists():
                return []
                
            with open(self.trade_log_file, 'r', encoding='utf-8') as f:
                trade_logs = json.load(f)
                
            return trade_logs[-limit:]
            
        except Exception as e:
            log_error(f"读取交易日志失败: {e}")
            return []
            
    def get_trade_summary(self, hours=24):
        """获取交易摘要"""
        try:
            recent_trades = self.get_recent_trades()
            if not recent_trades:
                return {}
                
            # 筛选最近24小时的交易
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
            
            recent_trades = [t for t in recent_trades if t['timestamp'] > cutoff_str]
            
            # 计算统计信息
            ai_decisions = [t for t in recent_trades if t['type'] == 'AI_DECISION']
            trade_executions = [t for t in recent_trades if t['type'] == 'TRADE_EXECUTION']
            tp_sl_triggers = [t for t in recent_trades if t['type'] == 'TP_SL_TRIGGER']
            
            return {
                "total_ai_decisions": len(ai_decisions),
                "total_trades": len(trade_executions),
                "total_tp_sl_triggers": len(tp_sl_triggers),
                "ai_decisions": ai_decisions,
                "trade_executions": trade_executions,
                "tp_sl_triggers": tp_sl_triggers
            }
            
        except Exception as e:
            log_error(f"生成交易摘要失败: {e}")
            return {}

    def log_event(self, event_data):
        """记录通用事件（兼容utils.py中的调用）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "GENERAL_EVENT",
            "timestamp": timestamp,
            "event_type": event_data.get('event_type', 'UNKNOWN'),
            "data": event_data.get('data', {})
        }
        
        # 记录到统一日志
        log_info(f"📊 交易事件: {log_entry['event_type']} - {log_entry['data']}")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)

    def log_error(self, error_data):
        """记录错误事件（兼容utils.py中的调用）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            "type": "ERROR_EVENT",
            "timestamp": timestamp,
            "error_type": error_data.get('error_type', 'UNKNOWN'),
            "error_data": error_data.get('error_data', {})
        }
        
        # 记录到统一日志
        log_error(f"❌ 错误事件: {log_entry['error_type']} - {log_entry['error_data']}")
        
        # 记录到交易日志文件
        self._append_to_trade_log(log_entry)

# 创建全局实例
trade_logger = TradeLogger()
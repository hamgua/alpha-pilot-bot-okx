"""
数据管理模块 - 用于在交易程序和Web界面之间共享数据
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import os

# 确保数据目录存在
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_json")
os.makedirs(data_dir, exist_ok=True)

DATA_FILE = os.path.join(data_dir, "trading_data.json")
TRADES_FILE = os.path.join(data_dir, "trades_history.json")
EQUITY_HISTORY_FILE = os.path.join(data_dir, "equity_history.json")

def save_trading_data(data: Dict):
    """保存交易数据"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存交易数据失败: {e}")

def load_trading_data() -> Optional[Dict]:
    """加载交易数据"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"加载交易数据失败: {e}")
        return None

def save_trade_record(trade: Dict):
    """保存交易记录"""
    try:
        # 加载现有记录
        trades = []
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    trades = json.loads(content)
        
        # 添加新记录
        trades.append(trade)
        
        # 只保留最近500条记录
        if len(trades) > 500:
            trades = trades[-500:]
        
        # 保存
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存交易记录失败: {e}")
        # 确保文件存在且格式正确
        try:
            with open(TRADES_FILE, 'w', encoding='utf-8') as f:
                json.dump([trade], f, ensure_ascii=False, indent=2)
        except:
            pass

def load_trades_history() -> List[Dict]:
    """加载交易历史"""
    try:
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:  # 文件为空
                    return []
                return json.loads(content)
        else:
            # 文件不存在，创建空文件
            with open(TRADES_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []
    except json.JSONDecodeError:
        # JSON格式错误，重置为空数组
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    except Exception as e:
        print(f"加载交易历史失败: {e}")
        return []

def calculate_performance(trades: List[Dict]) -> Dict:
    """计算交易绩效"""
    if not trades:
        return {
            'total_pnl': 0,
            'win_rate': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades
    }

def save_equity_snapshot(equity: float, timestamp: str = None):
    """保存账户权益快照"""
    try:
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 加载现有历史
        equity_history = []
        if os.path.exists(EQUITY_HISTORY_FILE):
            with open(EQUITY_HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    equity_history = json.loads(content)

        # 添加新快照
        equity_history.append({
            'timestamp': timestamp,
            'equity': equity
        })

        # 保留最近1000条记录
        if len(equity_history) > 1000:
            equity_history = equity_history[-1000:]

        # 保存
        with open(EQUITY_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(equity_history, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"保存权益快照失败: {e}")
        # 确保文件存在且格式正确
        try:
            with open(EQUITY_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([{'timestamp': timestamp, 'equity': equity}], f, ensure_ascii=False, indent=2)
        except:
            pass

def load_equity_history() -> List[Dict]:
    """加载账户权益历史"""
    try:
        if os.path.exists(EQUITY_HISTORY_FILE):
            with open(EQUITY_HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:  # 文件为空
                    return []
                return json.loads(content)
        else:
            # 文件不存在，创建空文件
            with open(EQUITY_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []
    except json.JSONDecodeError:
        # JSON格式错误，重置为空数组
        with open(EQUITY_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    except Exception as e:
        print(f"加载权益历史失败: {e}")
        return []

def update_system_status(
    status: str,
    account_info: Optional[Dict] = None,
    btc_info: Optional[Dict] = None,
    position: Optional[Dict] = None,
    ai_signal: Optional[Dict] = None,
    tp_sl_orders: Optional[Dict] = None
):
    """更新系统状态"""

    # 加载现有数据
    current_data = load_trading_data()
    if current_data is None:
        current_data = {
            "status": "stopped",
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "account": {
                "balance": 0,
                "equity": 0,
                "leverage": 0
            },
            "btc": {
                "price": 0,
                "change": 0,
                "timeframe": "15m",
                "mode": "全仓-单向"
            },
            "position": None,
            "performance": {
                "total_pnl": 0,
                "win_rate": 0,
                "total_trades": 0
            },
            "ai_signal": {
                "signal": "HOLD",
                "confidence": "N/A",
                "reason": "等待AI分析...",
                "stop_loss": 0,
                "take_profit": 0,
                "timestamp": "N/A"
            },
            "tp_sl_orders": {
                "stop_loss_order_id": None,
                "take_profit_order_id": None
            }
        }

    # 更新状态
    current_data['status'] = status
    current_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if account_info:
        current_data['account'].update(account_info)

    if btc_info:
        current_data['btc'].update(btc_info)

    if position is not None:
        current_data['position'] = position

    if ai_signal:
        current_data['ai_signal'].update(ai_signal)
        current_data['ai_signal']['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if tp_sl_orders is not None:
        current_data['tp_sl_orders'] = tp_sl_orders

    # 计算绩效
    trades = load_trades_history()
    performance = calculate_performance(trades)
    current_data['performance'] = performance

    # 保存
    save_trading_data(current_data)

    # 🆕 保存权益快照（如果有账户信息）
    if account_info and 'equity' in account_info:
        save_equity_snapshot(account_info['equity'], current_data['last_update'])

class DataManagementSystem:
    """数据管理系统"""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_json")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 数据文件路径
        self.files = {
            'trading_data': os.path.join(self.data_dir, "trading_data.json"),
            'trades_history': os.path.join(self.data_dir, "trades_history.json"),
            'equity_history': os.path.join(self.data_dir, "equity_history.json"),
            'market_data': os.path.join(self.data_dir, "market_data.json"),
            'ai_signals': os.path.join(self.data_dir, "ai_signals.json"),
            'system_logs': os.path.join(self.data_dir, "system_logs.json"),
            'performance_metrics': os.path.join(self.data_dir, "performance_metrics.json")
        }
        
        # 确保所有数据文件存在
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """初始化数据文件"""
        for file_path in self.files.values():
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_market_data(self, market_data: Dict[str, Any]) -> bool:
        """保存市场数据"""
        try:
            # 添加时间戳
            market_data['timestamp'] = datetime.now().isoformat()
            
            # 加载现有数据
            existing_data = self._load_json_file(self.files['market_data'])
            existing_data.append(market_data)
            
            # 保留最近1000条记录
            if len(existing_data) > 1000:
                existing_data = existing_data[-1000:]
            
            # 保存
            self._save_json_file(self.files['market_data'], existing_data)
            return True
            
        except Exception as e:
            print(f"保存市场数据失败: {e}")
            return False
    
    def save_ai_signal(self, ai_signal: Dict[str, Any]) -> bool:
        """保存AI信号"""
        try:
            # 添加时间戳
            ai_signal['timestamp'] = datetime.now().isoformat()
            
            # 加载现有数据
            existing_signals = self._load_json_file(self.files['ai_signals'])
            existing_signals.append(ai_signal)
            
            # 保留最近500条记录
            if len(existing_signals) > 500:
                existing_signals = existing_signals[-500:]
            
            # 保存
            self._save_json_file(self.files['ai_signals'], existing_signals)
            return True
            
        except Exception as e:
            print(f"保存AI信号失败: {e}")
            return False
    
    def save_system_log(self, log_entry: Dict[str, Any]) -> bool:
        """保存系统日志"""
        try:
            # 添加时间戳
            log_entry['timestamp'] = datetime.now().isoformat()
            
            # 加载现有日志
            existing_logs = self._load_json_file(self.files['system_logs'])
            existing_logs.append(log_entry)
            
            # 保留最近10000条记录
            if len(existing_logs) > 10000:
                existing_logs = existing_logs[-10000:]
            
            # 保存
            self._save_json_file(self.files['system_logs'], existing_logs)
            return True
            
        except Exception as e:
            print(f"保存系统日志失败: {e}")
            return False
    
    def save_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """保存性能指标"""
        try:
            # 添加时间戳
            metrics['timestamp'] = datetime.now().isoformat()
            
            # 加载现有数据
            existing_metrics = self._load_json_file(self.files['performance_metrics'])
            existing_metrics.append(metrics)
            
            # 保留最近1000条记录
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]
            
            # 保存
            self._save_json_file(self.files['performance_metrics'], existing_metrics)
            return True
            
        except Exception as e:
            print(f"保存性能指标失败: {e}")
            return False
    
    def get_market_data_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取市场数据历史"""
        try:
            data = self._load_json_file(self.files['market_data'])
            return data[-limit:] if limit else data
        except Exception as e:
            print(f"获取市场数据历史失败: {e}")
            return []
    
    def get_ai_signal_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取AI信号历史"""
        try:
            signals = self._load_json_file(self.files['ai_signals'])
            return signals[-limit:] if limit else signals
        except Exception as e:
            print(f"获取AI信号历史失败: {e}")
            return []
    
    def get_system_logs(self, level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取系统日志"""
        try:
            logs = self._load_json_file(self.files['system_logs'])
            
            if level:
                logs = [log for log in logs if log.get('level') == level]
            
            return logs[-limit:] if limit else logs
        except Exception as e:
            print(f"获取系统日志失败: {e}")
            return []
    
    def get_performance_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取性能历史"""
        try:
            performance = self._load_json_file(self.files['performance_metrics'])
            return performance[-limit:] if limit else performance
        except Exception as e:
            print(f"获取性能历史失败: {e}")
            return []
    
    def backup_data(self, backup_name: str = None) -> bool:
        """备份数据"""
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_dir = os.path.join(self.data_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_path = os.path.join(backup_dir, f"{backup_name}.json")
            
            # 收集所有数据
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'trading_data': self._load_json_file(self.files['trading_data']),
                'trades_history': self._load_json_file(self.files['trades_history']),
                'equity_history': self._load_json_file(self.files['equity_history']),
                'market_data': self._load_json_file(self.files['market_data']),
                'ai_signals': self._load_json_file(self.files['ai_signals']),
                'system_logs': self._load_json_file(self.files['system_logs']),
                'performance_metrics': self._load_json_file(self.files['performance_metrics'])
            }
            
            # 保存备份
            self._save_json_file(backup_path, backup_data)
            return True
            
        except Exception as e:
            print(f"备份数据失败: {e}")
            return False
    
    def restore_data(self, backup_name: str) -> bool:
        """恢复数据"""
        try:
            backup_path = os.path.join(self.data_dir, "backups", f"{backup_name}.json")
            
            if not os.path.exists(backup_path):
                print(f"备份文件不存在: {backup_path}")
                return False
            
            # 加载备份数据
            backup_data = self._load_json_file(backup_path)
            
            # 恢复各个数据文件
            for file_key, data in backup_data.items():
                if file_key in self.files and isinstance(data, list):
                    self._save_json_file(self.files[file_key], data)
            
            return True
            
        except Exception as e:
            print(f"恢复数据失败: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for file_path in self.files.values():
                if os.path.exists(file_path):
                    data = self._load_json_file(file_path)
                    
                    if isinstance(data, list) and len(data) > 0:
                        # 过滤掉旧数据
                        filtered_data = []
                        for item in data:
                            if 'timestamp' in item:
                                try:
                                    item_date = datetime.fromisoformat(item['timestamp'])
                                    if item_date >= cutoff_date:
                                        filtered_data.append(item)
                                except:
                                    filtered_data.append(item)  # 保留无法解析时间戳的数据
                        
                        self._save_json_file(file_path, filtered_data)
            
            return True
            
        except Exception as e:
            print(f"清理旧数据失败: {e}")
            return False
    
    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要"""
        summary = {}
        
        for file_key, file_path in self.files.items():
            try:
                data = self._load_json_file(file_path)
                summary[file_key] = {
                    'total_records': len(data),
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else None
                }
            except Exception as e:
                summary[file_key] = {
                    'total_records': 0,
                    'file_size': 0,
                    'last_modified': None,
                    'error': str(e)
                }
        
        return summary
    
    def _load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
            return []
        except (json.JSONDecodeError, Exception):
            return []
    
    def _save_json_file(self, file_path: str, data: Any) -> bool:
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存文件失败 {file_path}: {e}")
            return False

# 全局数据管理实例
data_management_system = DataManagementSystem()


"""
数据管理器
负责数据的收集、存储、查询和管理
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .models import (
    TradeRecord, MarketData, AISignal, PerformanceMetrics,
    SystemLog, RiskMetrics, BacktestResult, TradeSide, OrderStatus, SignalType
)


class DataManager:
    """数据管理器 - 负责所有数据的集中管理"""

    def __init__(self, data_dir: str = "data_json"):
        """初始化数据管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 内存缓存
        self._cache = {
            'market_data': {},
            'trade_history': [],
            'ai_signals': [],
            'performance_metrics': {},
            'system_logs': [],
            'risk_metrics': []
        }

        # 初始化数据库
        self._init_database()

    def _init_database(self):
        """初始化SQLite数据库"""
        db_path = self.data_dir / "trading_data.db"
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # 创建表
        self._create_tables()

    def _create_tables(self):
        """创建数据表"""
        # 交易记录表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                order_id TEXT,
                filled_amount REAL DEFAULT 0,
                average_price REAL DEFAULT 0,
                fee REAL DEFAULT 0,
                pnl REAL DEFAULT 0,
                strategy TEXT,
                ai_confidence REAL,
                metadata TEXT DEFAULT '{}'
            )
        """)

        # 市场数据表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL,
                weighted_average REAL,
                trades_count INTEGER,
                metadata TEXT DEFAULT '{}',
                PRIMARY KEY (timestamp, symbol)
            )
        """)

        # AI信号表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_signals (
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                provider TEXT NOT NULL,
                reasoning TEXT,
                technical_indicators TEXT DEFAULT '{}',
                market_sentiment REAL,
                risk_level TEXT,
                metadata TEXT DEFAULT '{}',
                PRIMARY KEY (timestamp, symbol, provider)
            )
        """)

        # 系统日志表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)

        self.conn.commit()

    def save_trade_record(self, trade_record: TradeRecord) -> bool:
        """保存交易记录

        Args:
            trade_record: 交易记录对象

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存到数据库
            self.conn.execute("""
                INSERT OR REPLACE INTO trade_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_record.id,
                trade_record.timestamp.isoformat(),
                trade_record.symbol,
                trade_record.side.value,
                trade_record.amount,
                trade_record.price,
                trade_record.status.value,
                trade_record.order_id,
                trade_record.filled_amount,
                trade_record.average_price,
                trade_record.fee,
                trade_record.pnl,
                trade_record.strategy,
                trade_record.ai_confidence,
                json.dumps(trade_record.metadata)
            ))
            self.conn.commit()

            # 更新缓存
            self._cache['trade_history'].append(trade_record)

            return True
        except Exception as e:
            print(f"保存交易记录失败: {e}")
            return False

    def save_market_data(self, market_data: MarketData) -> bool:
        """保存市场数据

        Args:
            market_data: 市场数据对象

        Returns:
            bool: 是否保存成功
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.timestamp.isoformat(),
                market_data.symbol,
                market_data.open,
                market_data.high,
                market_data.low,
                market_data.close,
                market_data.volume,
                market_data.quote_volume,
                market_data.weighted_average,
                market_data.trades_count,
                json.dumps(market_data.metadata)
            ))
            self.conn.commit()

            # 更新缓存
            key = f"{market_data.symbol}_{market_data.timestamp}"
            self._cache['market_data'][key] = market_data

            return True
        except Exception as e:
            print(f"保存市场数据失败: {e}")
            return False

    def save_ai_signal(self, ai_signal: AISignal) -> bool:
        """保存AI信号

        Args:
            ai_signal: AI信号对象

        Returns:
            bool: 是否保存成功
        """
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO ai_signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ai_signal.timestamp.isoformat(),
                ai_signal.symbol,
                ai_signal.signal.value,
                ai_signal.confidence,
                ai_signal.provider,
                ai_signal.reasoning,
                json.dumps(ai_signal.technical_indicators),
                ai_signal.market_sentiment,
                ai_signal.risk_level,
                json.dumps(ai_signal.metadata)
            ))
            self.conn.commit()

            # 更新缓存
            self._cache['ai_signals'].append(ai_signal)

            return True
        except Exception as e:
            print(f"保存AI信号失败: {e}")
            return False

    def save_system_log(self, level: str, module: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """保存系统日志

        Args:
            level: 日志级别
            module: 模块名称
            message: 日志消息
            metadata: 元数据

        Returns:
            bool: 是否保存成功
        """
        try:
            timestamp = datetime.now()
            metadata = metadata or {}

            self.conn.execute("""
                INSERT INTO system_logs VALUES (?, ?, ?, ?, ?)
            """, (
                timestamp.isoformat(),
                level,
                module,
                message,
                json.dumps(metadata)
            ))
            self.conn.commit()

            # 更新缓存
            log_entry = SystemLog(
                timestamp=timestamp,
                level=level,
                module=module,
                message=message,
                metadata=metadata
            )
            self._cache['system_logs'].append(log_entry)

            return True
        except Exception as e:
            print(f"保存系统日志失败: {e}")
            return False

    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[TradeRecord]:
        """获取交易历史

        Args:
            symbol: 交易对，None表示所有
            limit: 限制数量

        Returns:
            List[TradeRecord]: 交易记录列表
        """
        try:
            query = "SELECT * FROM trade_records ORDER BY timestamp DESC LIMIT ?"
            params = [limit]

            if symbol:
                query = "SELECT * FROM trade_records WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?"
                params = [symbol, limit]

            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                record = TradeRecord(
                    id=row['id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    symbol=row['symbol'],
                    side=TradeSide(row['side']),
                    amount=row['amount'],
                    price=row['price'],
                    status=OrderStatus(row['status']),
                    order_id=row['order_id'],
                    filled_amount=row['filled_amount'],
                    average_price=row['average_price'],
                    fee=row['fee'],
                    pnl=row['pnl'],
                    strategy=row['strategy'],
                    ai_confidence=row['ai_confidence'],
                    metadata=json.loads(row['metadata'])
                )
                records.append(record)

            return records
        except Exception as e:
            print(f"获取交易历史失败: {e}")
            return []

    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """获取性能摘要

        Args:
            days: 天数

        Returns:
            Dict[str, Any]: 性能摘要
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            # 获取交易统计
            cursor = self.conn.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                FROM trade_records
                WHERE timestamp >= ?
            """, [start_date.isoformat()])

            row = cursor.fetchone()

            if row and row['total_trades'] > 0:
                total_trades = row['total_trades']
                winning_trades = row['winning_trades'] or 0
                losing_trades = row['losing_trades'] or 0
                total_pnl = row['total_pnl'] or 0
                avg_win = row['avg_win'] or 0
                avg_loss = row['avg_loss'] or 0

                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')

                return {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'average_win': avg_win,
                    'average_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'max_drawdown': 0,  # TODO: 计算最大回撤
                    'sharpe_ratio': None,
                    'volatility': None
                }
            else:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': None,
                    'volatility': None
                }
        except Exception as e:
            print(f"获取性能摘要失败: {e}")
            return {}

    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """清理旧数据

        Args:
            days_to_keep: 保留天数

        Returns:
            bool: 是否清理成功
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # 清理交易记录
            self.conn.execute("DELETE FROM trade_records WHERE timestamp < ?",
                            [cutoff_date.isoformat()])

            # 清理市场数据
            self.conn.execute("DELETE FROM market_data WHERE timestamp < ?",
                            [cutoff_date.isoformat()])

            # 清理AI信号
            self.conn.execute("DELETE FROM ai_signals WHERE timestamp < ?",
                            [cutoff_date.isoformat()])

            # 清理系统日志
            self.conn.execute("DELETE FROM system_logs WHERE timestamp < ?",
                            [cutoff_date.isoformat()])

            self.conn.commit()

            # 清理缓存
            self._cleanup_cache(cutoff_date)

            return True
        except Exception as e:
            print(f"清理旧数据失败: {e}")
            return False

    def _cleanup_cache(self, cutoff_date: datetime):
        """清理缓存"""
        # 清理交易历史缓存
        self._cache['trade_history'] = [
            trade for trade in self._cache['trade_history']
            if trade.timestamp >= cutoff_date
        ]

        # 清理AI信号缓存
        self._cache['ai_signals'] = [
            signal for signal in self._cache['ai_signals']
            if signal.timestamp >= cutoff_date
        ]

        # 清理系统日志缓存
        self._cache['system_logs'] = [
            log for log in self._cache['system_logs']
            if log.timestamp >= cutoff_date
        ]

    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要

        Returns:
            Dict[str, Any]: 数据摘要
        """
        try:
            # 获取各表记录数
            trade_count = self.conn.execute("SELECT COUNT(*) FROM trade_records").fetchone()[0]
            market_data_count = self.conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
            ai_signal_count = self.conn.execute("SELECT COUNT(*) FROM ai_signals").fetchone()[0]
            log_count = self.conn.execute("SELECT COUNT(*) FROM system_logs").fetchone()[0]

            # 获取数据库文件大小
            db_path = self.data_dir / "trading_data.db"
            db_size = db_path.stat().st_size if db_path.exists() else 0

            return {
                'trade_records': {'total_records': trade_count},
                'market_data': {'total_records': market_data_count},
                'ai_signals': {'total_records': ai_signal_count},
                'system_logs': {'total_records': log_count},
                'database_size_bytes': db_size,
                'cache_stats': {
                    'market_data': len(self._cache['market_data']),
                    'trade_history': len(self._cache['trade_history']),
                    'ai_signals': len(self._cache['ai_signals']),
                    'system_logs': len(self._cache['system_logs'])
                }
            }
        except Exception as e:
            print(f"获取数据摘要失败: {e}")
            return {}

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'conn'):
            self.conn.close()
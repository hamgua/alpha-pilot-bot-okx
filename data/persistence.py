"""
数据持久化模块
提供数据的文件持久化功能
"""

import json
import csv
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from .models import TradeRecord, MarketData, AISignal, PerformanceMetrics


class DataPersistence:
    """数据持久化类 - 负责将数据保存到文件"""

    def __init__(self, base_dir: str = "data_json/exports"):
        """初始化数据持久化

        Args:
            base_dir: 基础目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def export_trades_to_csv(self, trades: List[TradeRecord], filename: Optional[str] = None) -> str:
        """导出交易记录到CSV文件

        Args:
            trades: 交易记录列表
            filename: 文件名，如果为None则自动生成

        Returns:
            str: 导出的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trades_{timestamp}.csv"

        filepath = self.base_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', '时间', '交易对', '方向', '数量', '价格', '状态',
                '订单ID', '成交数量', '成交均价', '手续费', '盈亏',
                '策略', 'AI置信度', '元数据'
            ])

            for trade in trades:
                writer.writerow([
                    trade.id,
                    trade.timestamp.isoformat(),
                    trade.symbol,
                    trade.side.value,
                    trade.amount,
                    trade.price,
                    trade.status.value,
                    trade.order_id or '',
                    trade.filled_amount,
                    trade.average_price,
                    trade.fee,
                    trade.pnl,
                    trade.strategy or '',
                    trade.ai_confidence or '',
                    json.dumps(trade.metadata, ensure_ascii=False)
                ])

        return str(filepath)

    def export_market_data_to_csv(self, market_data: List[MarketData], filename: Optional[str] = None) -> str:
        """导出市场数据到CSV文件

        Args:
            market_data: 市场数据列表
            filename: 文件名，如果为None则自动生成

        Returns:
            str: 导出的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"market_data_{timestamp}.csv"

        filepath = self.base_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                '时间', '交易对', '开盘价', '最高价', '最低价', '收盘价',
                '成交量', '成交额', '加权均价', '交易次数', '元数据'
            ])

            for data in market_data:
                writer.writerow([
                    data.timestamp.isoformat(),
                    data.symbol,
                    data.open,
                    data.high,
                    data.low,
                    data.close,
                    data.volume,
                    data.quote_volume or '',
                    data.weighted_average or '',
                    data.trades_count or '',
                    json.dumps(data.metadata, ensure_ascii=False)
                ])

        return str(filepath)

    def export_data_to_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """导出数据到JSON文件

        Args:
            data: 要导出的数据
            filename: 文件名，如果为None则自动生成

        Returns:
            str: 导出的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_export_{timestamp}.json"

        filepath = self.base_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return str(filepath)

    def save_trade_record_json(self, trade: TradeRecord, filename: Optional[str] = None) -> str:
        """保存单个交易记录到JSON文件

        Args:
            trade: 交易记录
            filename: 文件名，如果为None则自动生成

        Returns:
            str: 保存的文件路径
        """
        if not filename:
            timestamp = trade.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"trade_{trade.id}_{timestamp}.json"

        filepath = self.base_dir / filename

        trade_dict = {
            'id': trade.id,
            'timestamp': trade.timestamp.isoformat(),
            'symbol': trade.symbol,
            'side': trade.side.value,
            'amount': trade.amount,
            'price': trade.price,
            'status': trade.status.value,
            'order_id': trade.order_id,
            'filled_amount': trade.filled_amount,
            'average_price': trade.average_price,
            'fee': trade.fee,
            'pnl': trade.pnl,
            'strategy': trade.strategy,
            'ai_confidence': trade.ai_confidence,
            'metadata': trade.metadata
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trade_dict, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def load_trade_records_from_json(self, filepath: str) -> List[TradeRecord]:
        """从JSON文件加载交易记录

        Args:
            filepath: 文件路径

        Returns:
            List[TradeRecord]: 交易记录列表
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return []

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        trades = []

        # 支持单个记录或记录列表
        if isinstance(data, dict):
            data = [data]

        for trade_dict in data:
            trade = TradeRecord(
                id=trade_dict['id'],
                timestamp=datetime.fromisoformat(trade_dict['timestamp']),
                symbol=trade_dict['symbol'],
                side=TradeSide(trade_dict['side']),
                amount=trade_dict['amount'],
                price=trade_dict['price'],
                status=OrderStatus(trade_dict['status']),
                order_id=trade_dict.get('order_id'),
                filled_amount=trade_dict.get('filled_amount', 0),
                average_price=trade_dict.get('average_price', 0),
                fee=trade_dict.get('fee', 0),
                pnl=trade_dict.get('pnl', 0),
                strategy=trade_dict.get('strategy'),
                ai_confidence=trade_dict.get('ai_confidence'),
                metadata=trade_dict.get('metadata', {})
            )
            trades.append(trade)

        return trades

    def export_performance_report(self, metrics: PerformanceMetrics, output_dir: Optional[str] = None) -> str:
        """导出性能报告

        Args:
            metrics: 性能指标
            output_dir: 输出目录

        Returns:
            str: 导出的文件路径
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.base_dir

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_report_{timestamp}.html"
        filepath = output_path / filename

        # 生成HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>交易性能报告 - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metrics {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }}
                .metric-card {{ background-color: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; min-width: 200px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ color: #666; margin-top: 5px; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>交易性能报告</h1>
                <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>统计周期: {metrics.timestamp.strftime("%Y-%m-%d")}</p>
            </div>

            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{metrics.total_trades}</div>
                    <div class="metric-label">总交易次数</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value {('positive' if metrics.win_rate > 0.5 else 'negative')}">
                        {metrics.win_rate:.2%}
                    </div>
                    <div class="metric-label">胜率</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value {('positive' if metrics.total_pnl > 0 else 'negative')}">
                        {metrics.total_pnl:.4f}
                    </div>
                    <div class="metric-label">总盈亏</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value">{metrics.profit_factor:.2f}</div>
                    <div class="metric-label">盈亏比</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value negative">{metrics.max_drawdown:.2%}</div>
                    <div class="metric-label">最大回撤</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value">{metrics.sharpe_ratio:.2f if metrics.sharpe_ratio else 'N/A'}</div>
                    <div class="metric-label">夏普比率</div>
                </div>
            </div>
        </body>
        </html>
        """

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(filepath)

    def create_backup(self, backup_dir: Optional[str] = None) -> str:
        """创建数据备份

        Args:
            backup_dir: 备份目录

        Returns:
            str: 备份文件路径
        """
        if not backup_dir:
            backup_dir = self.base_dir / "backups"

        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"trading_data_backup_{timestamp}.json"

        # 这里简化实现，实际应该备份数据库文件
        backup_info = {
            'timestamp': timestamp,
            'backup_type': 'full',
            'data_types': ['trade_records', 'market_data', 'ai_signals', 'system_logs'],
            'note': 'This is a simplified backup. In production, backup the database file directly.'
        }

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)

        return str(backup_file)
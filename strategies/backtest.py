"""
回测引擎模块
实现策略的历史数据回测功能
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from core.base import BaseComponent, BaseConfig
from core.exceptions import StrategyError
from .base import BaseStrategy, BacktestResult, StrategySignal

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig(BaseConfig):
    """回测配置"""
    def __init__(self, **kwargs):
        super().__init__(name="BacktestEngine", **kwargs)
        self.initial_capital = kwargs.get('initial_capital', 10000.0)
        self.commission_rate = kwargs.get('commission_rate', 0.001)
        self.slippage_rate = kwargs.get('slippage_rate', 0.0005)
        self.min_trade_amount = kwargs.get('min_trade_amount', 0.001)

class BacktestEngine(BaseComponent):
    """回测引擎"""
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        super().__init__(config or BacktestConfig())
        self.config = config or BacktestConfig()
        self.trade_history: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []
    
    async def initialize(self) -> bool:
        """初始化回测引擎"""
        try:
            logger.info("📈 回测引擎初始化...")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"回测引擎初始化失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        self.trade_history.clear()
        self.equity_curve.clear()
        self.daily_returns.clear()
        self._initialized = False
        logger.info("🛑 回测引擎已清理")
    
    async def run_backtest(self, strategy: BaseStrategy, market_data: Dict[str, Any]) -> BacktestResult:
        """运行策略回测"""
        try:
            logger.info(f"🚀 开始 {strategy.strategy_type} 策略回测...")
            
            # 准备回测数据
            price_data = self._prepare_price_data(market_data)
            if not price_data:
                raise StrategyError("回测数据准备失败", strategy_type=strategy.strategy_type)
            
            # 初始化回测状态
            initial_capital = self.config.initial_capital
            capital = initial_capital
            position = 0.0
            entry_price = 0.0
            
            # 重置历史记录
            self.trade_history.clear()
            self.equity_curve.clear()
            self.daily_returns.clear()
            
            # 回测主循环
            for i, current_data in enumerate(price_data):
                try:
                    current_price = current_data['close']
                    current_time = current_data['timestamp']
                    
                    # 生成交易信号
                    market_data_point = self._create_market_data_point(current_data, price_data, i)
                    signal = await strategy.generate_signal(market_data_point)
                    
                    # 执行交易逻辑
                    if signal.signal == 'BUY' and position == 0:
                        # 开仓买入
                        trade_result = self._execute_buy(capital, current_price, signal.confidence)
                        if trade_result['success']:
                            position = trade_result['position_size']
                            capital = trade_result['remaining_capital']
                            entry_price = current_price
                            
                            self._record_trade('BUY', current_price, position, capital, current_time, signal)
                    
                    elif signal.signal == 'SELL' and position > 0:
                        # 平仓卖出
                        trade_result = self._execute_sell(position, current_price, capital, entry_price, signal.confidence)
                        if trade_result['success']:
                            capital = trade_result['new_capital']
                            profit = trade_result['profit']
                            
                            self._record_trade('SELL', current_price, position, capital, current_time, signal, profit)
                            position = 0.0
                            entry_price = 0.0
                    
                    # 更新权益曲线
                    current_equity = capital + (position * current_price if position > 0 else 0)
                    self.equity_curve.append(current_equity)
                    
                    # 计算日收益
                    if i > 0:
                        daily_return = (current_equity - self.equity_curve[i-1]) / self.equity_curve[i-1]
                        self.daily_returns.append(daily_return)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 回测迭代失败 (索引 {i}): {e}")
                    continue
            
            # 计算回测结果
            result = self._calculate_backtest_results(strategy.config.name, initial_capital)
            
            logger.info(f"✅ 回测完成: 总收益 {result.total_return:.2%}, 夏普比率 {result.sharpe_ratio:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
            raise StrategyError(f"回测失败: {e}", strategy_type=strategy.strategy_type)
    
    def _prepare_price_data(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """准备价格数据"""
        try:
            # 获取历史价格数据
            price_history = market_data.get('price_history', [])
            if not price_history:
                # 生成模拟数据用于测试
                return self._generate_mock_price_data()
            
            # 转换为标准格式
            price_data = []
            for i, price_point in enumerate(price_history):
                price_data.append({
                    'timestamp': price_point.get('timestamp', datetime.now() - timedelta(hours=len(price_history)-i)),
                    'open': float(price_point.get('open', 50000)),
                    'high': float(price_point.get('high', 51000)),
                    'low': float(price_point.get('low', 49000)),
                    'close': float(price_point.get('close', 50000)),
                    'volume': float(price_point.get('volume', 1000000))
                })
            
            return price_data
            
        except Exception as e:
            logger.error(f"准备价格数据失败: {e}")
            return []
    
    def _generate_mock_price_data(self) -> List[Dict[str, Any]]:
        """生成模拟价格数据"""
        try:
            # 生成100个数据点的模拟数据
            n_points = 100
            base_price = 50000
            prices = [base_price]
            
            np.random.seed(42)  # 确保可重复性
            
            for i in range(1, n_points):
                # 添加随机波动
                change_pct = np.random.normal(0, 0.02)  # 2%的日波动
                new_price = prices[-1] * (1 + change_pct)
                prices.append(max(1000, new_price))  # 确保价格不为负
            
            price_data = []
            base_time = datetime.now() - timedelta(hours=n_points)
            
            for i, price in enumerate(prices):
                # 生成OHLC数据
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.uniform(100000, 1000000)
                
                price_data.append({
                    'timestamp': base_time + timedelta(hours=i),
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            return price_data
            
        except Exception as e:
            logger.error(f"生成模拟价格数据失败: {e}")
            return []
    
    def _create_market_data_point(self, current_data: Dict[str, Any], 
                                price_history: List[Dict[str, Any]], current_index: int) -> Dict[str, Any]:
        """创建市场数据点"""
        try:
            # 计算技术指标
            technical_data = self._calculate_technical_indicators(price_history, current_index)
            
            # 计算趋势分析
            trend_analysis = self._calculate_trend_analysis(price_history, current_index)
            
            return {
                'price': current_data['close'],
                'timestamp': current_data['timestamp'],
                'technical_data': technical_data,
                'trend_analysis': trend_analysis,
                'price_history': [p['close'] for p in price_history[max(0, current_index-20):current_index+1]],
                'volatility': technical_data.get('volatility', 'normal')
            }
            
        except Exception as e:
            logger.error(f"创建市场数据点失败: {e}")
            return {
                'price': current_data['close'],
                'timestamp': current_data['timestamp'],
                'technical_data': {},
                'trend_analysis': {},
                'price_history': [],
                'volatility': 'normal'
            }
    
    def _calculate_technical_indicators(self, price_history: List[Dict[str, Any]], current_index: int) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            if current_index < 14:  # 需要足够的历史数据
                return {
                    'rsi': 50,
                    'macd': {},
                    'ma_short': price_history[current_index]['close'],
                    'ma_long': price_history[current_index]['close'],
                    'volatility': 'normal'
                }
            
            # 获取价格序列
            prices = [p['close'] for p in price_history[:current_index+1]]
            
            # 计算RSI
            rsi = self._calculate_rsi(prices)
            
            # 计算MACD
            macd = self._calculate_macd(prices)
            
            # 计算移动平均线
            ma_short = np.mean(prices[-20:])  # 20日均线
            ma_long = np.mean(prices[-50:])   # 50日均线
            
            # 计算波动率
            recent_returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(-10, 0)]
            volatility_std = np.std(recent_returns)
            
            if volatility_std < 0.01:
                volatility_level = 'low'
            elif volatility_std < 0.03:
                volatility_level = 'normal'
            else:
                volatility_level = 'high'
            
            return {
                'rsi': rsi,
                'macd': macd,
                'ma_short': ma_short,
                'ma_long': ma_long,
                'volatility': volatility_level,
                'momentum': recent_returns[-1] if recent_returns else 0,
                'atr_pct': volatility_std * 100
            }
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return {
                'rsi': 50,
                'macd': {},
                'ma_short': price_history[current_index]['close'],
                'ma_long': price_history[current_index]['close'],
                'volatility': 'normal',
                'momentum': 0,
                'atr_pct': 2.0
            }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            # 计算价格变化
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # 分离上涨和下跌
            gains = [d if d > 0 else 0 for d in deltas[-period:]]
            losses = [-d if d < 0 else 0 for d in deltas[-period:]]
            
            # 计算平均收益和损失
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            if avg_loss == 0:
                return 100.0
            
            # 计算RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return max(0, min(100, rsi))
            
        except Exception as e:
            logger.error(f"计算RSI失败: {e}")
            return 50.0
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, Any]:
        """计算MACD指标"""
        try:
            if len(prices) < 26:  # 需要足够的数据
                return {'macd': 0, 'signal': 0, 'histogram': 0}
            
            # 计算EMA
            ema12 = self._calculate_ema(prices, 12)
            ema26 = self._calculate_ema(prices, 26)
            
            # MACD线
            macd_line = ema12 - ema26
            
            # 信号线 (9日EMA of MACD)
            macd_series = []
            for i in range(26, len(prices)):
                ema12_i = self._calculate_ema(prices[:i+1], 12)
                ema26_i = self._calculate_ema(prices[:i+1], 26)
                macd_series.append(ema12_i - ema26_i)
            
            signal_line = self._calculate_ema(macd_series, 9) if len(macd_series) >= 9 else macd_series[-1] if macd_series else 0
            
            # 柱状图
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error(f"计算MACD失败: {e}")
            return {'macd': 0, 'signal': 0, 'histogram': 0}
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """计算EMA"""
        try:
            if len(prices) < period:
                return prices[-1] if prices else 0
            
            # 简化的EMA计算
            weights = np.exp(np.linspace(-1., 0., period))
            weights /= weights.sum()
            
            recent_prices = prices[-period:]
            ema = np.dot(recent_prices, weights)
            
            return ema
            
        except Exception as e:
            logger.error(f"计算EMA失败: {e}")
            return prices[-1] if prices else 0
    
    def _calculate_trend_analysis(self, price_history: List[Dict[str, Any]], current_index: int) -> Dict[str, Any]:
        """计算趋势分析"""
        try:
            if current_index < 20:
                return {'overall': 'neutral', 'strength': 0.0}
            
            # 获取价格序列
            prices = [p['close'] for p in price_history[:current_index+1]]
            
            # 计算线性回归斜率
            x = np.arange(len(prices[-20:]))  # 最近20个数据点
            y = np.array(prices[-20:])
            
            # 计算斜率
            slope, _ = np.polyfit(x, y, 1)
            
            # 标准化斜率
            price_std = np.std(y)
            trend_strength = slope / (price_std + 1e-6) if price_std > 0 else 0
            
            # 判断趋势方向
            if trend_strength > 0.1:
                trend_direction = 'bullish'
            elif trend_strength < -0.1:
                trend_direction = 'bearish'
            else:
                trend_direction = 'neutral'
            
            return {
                'overall': trend_direction,
                'strength': abs(trend_strength),
                'slope': slope
            }
            
        except Exception as e:
            logger.error(f"计算趋势分析失败: {e}")
            return {'overall': 'neutral', 'strength': 0.0, 'slope': 0.0}
    
    def _execute_buy(self, capital: float, price: float, confidence: float) -> Dict[str, Any]:
        """执行买入操作"""
        try:
            # 计算买入数量
            position_size = min(capital * 0.9 / price, capital * 0.01)  # 限制最大仓位
            position_size *= confidence  # 根据信心调整
            
            # 考虑滑点和手续费
            actual_price = price * (1 + self.config.slippage_rate)
            commission = position_size * actual_price * self.config.commission_rate
            
            total_cost = position_size * actual_price + commission
            
            if total_cost <= capital and position_size >= self.config.min_trade_amount:
                return {
                    'success': True,
                    'position_size': position_size,
                    'remaining_capital': capital - total_cost,
                    'execution_price': actual_price,
                    'commission': commission
                }
            else:
                return {
                    'success': False,
                    'reason': '资金不足或交易量过小'
                }
                
        except Exception as e:
            logger.error(f"执行买入失败: {e}")
            return {'success': False, 'reason': str(e)}
    
    def _execute_sell(self, position: float, price: float, capital: float, entry_price: float, confidence: float) -> Dict[str, Any]:
        """执行卖出操作"""
        try:
            # 计算卖出收益
            actual_price = price * (1 - self.config.slippage_rate)
            commission = position * actual_price * self.config.commission_rate
            
            revenue = position * actual_price - commission
            profit = (actual_price - entry_price) * position - commission
            
            return {
                'success': True,
                'new_capital': capital + revenue,
                'profit': profit,
                'execution_price': actual_price,
                'commission': commission
            }
            
        except Exception as e:
            logger.error(f"执行卖出失败: {e}")
            return {'success': False, 'reason': str(e)}
    
    def _record_trade(self, signal: str, price: float, size: float, capital: float, 
                     timestamp: datetime, strategy_signal: StrategySignal, profit: float = 0) -> None:
        """记录交易"""
        try:
            trade_record = {
                'timestamp': timestamp,
                'signal': signal,
                'price': price,
                'size': size,
                'capital': capital,
                'profit': profit,
                'strategy_name': strategy_signal.strategy_name,
                'confidence': strategy_signal.confidence,
                'reason': strategy_signal.reason,
                'metadata': strategy_signal.metadata
            }
            
            self.trade_history.append(trade_record)
            
        except Exception as e:
            logger.error(f"记录交易失败: {e}")
    
    def _calculate_backtest_results(self, strategy_name: str, initial_capital: float) -> BacktestResult:
        """计算回测结果"""
        try:
            if not self.equity_curve or len(self.equity_curve) < 2:
                return self._get_default_backtest_result(strategy_name)
            
            # 基本性能指标
            final_equity = self.equity_curve[-1]
            total_return = (final_equity - initial_capital) / initial_capital
            
            # 计算年化收益
            time_period = len(self.equity_curve)  # 假设每个点代表1小时
            years = time_period / (365 * 24)  # 转换为年
            annualized_return = (1 + total_return) ** (1 / max(years, 0.001)) - 1
            
            # 计算最大回撤
            max_drawdown = self._calculate_max_drawdown(self.equity_curve)
            
            # 计算夏普比率
            if self.daily_returns:
                excess_returns = [r - 0.02 / 365 for r in self.daily_returns]  # 假设无风险利率2%
                sharpe_ratio = np.mean(excess_returns) / (np.std(excess_returns) + 1e-10) * np.sqrt(365)
            else:
                sharpe_ratio = 0.0
            
            # 计算交易统计
            total_trades = len(self.trade_history) // 2  # 买入+卖出算一次完整交易
            winning_trades = len([t for t in self.trade_history if t['signal'] == 'SELL' and t['profit'] > 0])
            losing_trades = len([t for t in self.trade_history if t['signal'] == 'SELL' and t['profit'] < 0])
            
            win_rate = winning_trades / (winning_trades + losing_trades) if (winning_trades + losing_trades) > 0 else 0
            
            # 计算盈亏比
            gross_profit = sum(t['profit'] for t in self.trade_history if t['profit'] > 0)
            gross_loss = abs(sum(t['profit'] for t in self.trade_history if t['profit'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # 计算平均交易数据
            profitable_trades = [t['profit'] for t in self.trade_history if t['profit'] > 0]
            losing_trades_list = [t['profit'] for t in self.trade_history if t['profit'] < 0]
            
            avg_win = np.mean(profitable_trades) if profitable_trades else 0
            avg_loss = np.mean(losing_trades_list) if losing_trades_list else 0
            largest_win = max(profitable_trades) if profitable_trades else 0
            largest_loss = min(losing_trades_list) if losing_trades_list else 0
            
            # 计算连续盈亏
            consecutive_wins, consecutive_losses = self._calculate_consecutive_trades()
            
            # 计算平均持仓时间
            avg_trade_duration = self._calculate_avg_trade_duration()
            
            return BacktestResult(
                strategy_name=strategy_name,
                total_return=total_return,
                annualized_return=annualized_return,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_trade_duration=avg_trade_duration,
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses,
                start_date=self.trade_history[0]['timestamp'] if self.trade_history else datetime.now(),
                end_date=self.trade_history[-1]['timestamp'] if self.trade_history else datetime.now(),
                equity_curve=self.equity_curve,
                daily_returns=self.daily_returns,
                trade_history=self.trade_history.copy()
            )
            
        except Exception as e:
            logger.error(f"计算回测结果失败: {e}")
            return self._get_default_backtest_result(strategy_name)
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """计算最大回撤"""
        try:
            if len(equity_curve) < 2:
                return 0.0
            
            peak = equity_curve[0]
            max_drawdown = 0.0
            
            for value in equity_curve[1:]:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"计算最大回撤失败: {e}")
            return 0.0
    
    def _calculate_consecutive_trades(self) -> Tuple[int, int]:
        """计算连续盈亏"""
        try:
            if not self.trade_history:
                return 0, 0
            
            # 提取盈亏序列
            profits = [t['profit'] for t in self.trade_history if t['signal'] == 'SELL']
            
            if not profits:
                return 0, 0
            
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0
            
            for profit in profits:
                if profit > 0:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)
            
            return max_consecutive_wins, max_consecutive_losses
            
        except Exception as e:
            logger.error(f"计算连续交易失败: {e}")
            return 0, 0
    
    def _calculate_avg_trade_duration(self) -> float:
        """计算平均交易持续时间"""
        try:
            if len(self.trade_history) < 2:
                return 0.0
            
            # 计算买入和卖出之间的时间差
            durations = []
            buy_times = {}
            
            for trade in self.trade_history:
                if trade['signal'] == 'BUY':
                    buy_times[trade['timestamp']] = trade
                elif trade['signal'] == 'SELL':
                    # 找到对应的买入交易
                    for buy_time, buy_trade in buy_times.items():
                        duration = (trade['timestamp'] - buy_time).total_seconds() / 3600  # 小时
                        durations.append(duration)
                        break
            
            return np.mean(durations) if durations else 0.0
            
        except Exception as e:
            logger.error(f"计算平均交易持续时间失败: {e}")
            return 0.0
    
    def _get_default_backtest_result(self, strategy_name: str) -> BacktestResult:
        """获取默认回测结果"""
        now = datetime.now()
        return BacktestResult(
            strategy_name=strategy_name,
            total_return=0.0,
            annualized_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_trade_duration=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            consecutive_wins=0,
            consecutive_losses=0,
            start_date=now,
            end_date=now,
            equity_curve=[self.config.initial_capital],
            daily_returns=[],
            trade_history=[]
        )
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """获取回测摘要"""
        try:
            if not self.trade_history:
                return {'error': '没有交易历史'}
            
            total_trades = len(self.trade_history) // 2
            winning_trades = len([t for t in self.trade_history if t['signal'] == 'SELL' and t['profit'] > 0])
            total_profit = sum(t['profit'] for t in self.trade_history)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_profit': total_profit,
                'avg_profit_per_trade': total_profit / total_trades if total_trades > 0 else 0,
                'backtest_period': f"{len(self.equity_curve)} 小时",
                'final_equity': self.equity_curve[-1] if self.equity_curve else self.config.initial_capital
            }
            
        except Exception as e:
            logger.error(f"获取回测摘要失败: {e}")
            return {'error': str(e)}
    
    def export_results(self, format: str = 'json') -> str:
        """导出回测结果"""
        try:
            if format == 'json':
                import json
                return json.dumps({
                    'trade_history': self.trade_history,
                    'equity_curve': self.equity_curve,
                    'daily_returns': self.daily_returns,
                    'summary': self.get_backtest_summary()
                }, indent=2, default=str)
            else:
                return f"不支持的导出格式: {format}"
                
        except Exception as e:
            logger.error(f"导出回测结果失败: {e}")
            return f"导出失败: {e}"

# 全局回测引擎实例
backtest_engine = BacktestEngine()
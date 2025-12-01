"""
Alpha Arena OKX 策略模块
包含所有交易策略的实现
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from config import config
from logger_config import log_info, log_warning
from trade_logger import trade_logger

class MarketAnalyzer:
    """市场分析器"""
    
    @staticmethod
    def calculate_atr(high: list, low: list, close: list, period: int = 14) -> float:
        """计算ATR波动率"""
        if len(high) < period:
            return 2.0
        
        high = np.array(high[-period:])
        low = np.array(low[-period:])
        close = np.array(close[-period:])
        
        tr = np.maximum(high - low, 
                       np.maximum(np.abs(high - np.roll(close, 1)), 
                                 np.abs(low - np.roll(close, 1))))
        atr = np.mean(tr[1:])
        current_price = close[-1]
        
        return (atr / current_price) * 100
    
    @staticmethod
    def identify_trend(prices: list, period: int = 20) -> str:
        """识别趋势"""
        if len(prices) < period:
            return '震荡'
        
        prices = np.array(prices[-period:])
        sma = np.mean(prices)
        current_price = prices[-1]
        
        # 计算趋势强度
        slope = (prices[-1] - prices[0]) / period
        volatility = np.std(prices)
        
        if abs(slope) > volatility * 0.5:
            if slope > 0:
                return '强上涨' if slope > volatility else '弱上涨'
            else:
                return '强下跌' if abs(slope) > volatility else '弱下跌'
        else:
            return '震荡'
    
    @staticmethod
    def detect_consolidation(prices: list, threshold: float = 0.008, 
                           lookback: int = 6) -> bool:
        """检测横盘"""
        if len(prices) < lookback:
            return False
        
        recent_prices = np.array(prices[-lookback:])
        max_price = np.max(recent_prices)
        min_price = np.min(recent_prices)
        
        return (max_price - min_price) / max_price <= threshold

class RiskManager:
    """智能风险管理器 - 基于机器学习算法的动态止盈止损系统"""
    
    def __init__(self):
        self.config = config.get('strategies', 'smart_tp_sl')
        self.ml_model = self._initialize_ml_model()
        self.market_analyzer = MarketMicrostructureAnalyzer()
        self.order_flow_analyzer = OrderFlowAnalyzer()
        self.behavior_analyzer = BehaviorFinanceAnalyzer()
    
    def calculate_dynamic_tp_sl(self, signal: str, current_price: float, 
                              market_state: Dict[str, Any], 
                              position: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """基于机器学习的动态止盈止损计算"""
        
        if not self.config.get('enabled', False):
            return self._calculate_traditional_tp_sl(signal, current_price)
        
        # 1. 市场微观结构分析
        microstructure = self.market_analyzer.analyze(current_price, market_state)
        
        # 2. 订单流分析
        order_flow = self.order_flow_analyzer.analyze(market_state)
        
        # 3. 行为金融学指标
        behavior_metrics = self.behavior_analyzer.calculate(market_state)
        
        # 4. 机器学习预测
        ml_prediction = self._get_ml_prediction(
            microstructure, order_flow, behavior_metrics, market_state
        )
        
        # 5. 风险价值计算
        risk_metrics = self._calculate_risk_metrics(
            current_price, position, market_state
        )
        
        # 6. 动态调整算法
        final_params = self._apply_dynamic_adjustment(
            signal, current_price, microstructure, order_flow, 
            behavior_metrics, ml_prediction, risk_metrics, position
        )
        
        return final_params
    
    def _initialize_ml_model(self):
        """初始化机器学习模型（简化版）"""
        # 实际应用中这里会加载训练好的模型
        return {
            'confidence_threshold': 0.7,
            'trend_weight': 0.4,
            'volume_weight': 0.3,
            'time_weight': 0.2,
            'confidence_weight': 0.1
        }
    
    def _get_ml_prediction(self, microstructure: Dict[str, Any], 
                          order_flow: Dict[str, Any], 
                          behavior_metrics: Dict[str, Any], 
                          market_state: Dict[str, Any]) -> Dict[str, float]:
        """机器学习预测"""
        
        # 特征工程
        features = [
            market_state.get('price_change_pct', 0),
            market_state.get('volume_ratio', 1.0),
            market_state.get('volatility_pct', 2.0),
            microstructure.get('spread_impact', 0.1),
            order_flow.get('buy_sell_ratio', 1.0),
            behavior_metrics.get('fear_greed_index', 50),
            microstructure.get('depth_score', 0.5),
            order_flow.get('order_imbalance', 0.3)
        ]
        
        # 简化版预测（实际应用中使用真实模型）
        trend_strength = market_state.get('trend_strength', '中性')
        volatility = market_state.get('atr_pct', 2.0)
        
        # 基础权重
        weights = self.ml_model
        
        # 动态调整权重
        adjustment_factor = 1.0
        
        # 高波动环境调整
        if volatility > 3.0:
            adjustment_factor *= 1.5
        elif volatility < 1.0:
            adjustment_factor *= 0.8
        
        # 趋势强度调整
        trend_adjustments = {
            '强上涨': {'tp': 1.3, 'sl': 0.9, 'confidence': 0.9},
            '强下跌': {'tp': 1.3, 'sl': 0.8, 'confidence': 0.9},
            '弱上涨': {'tp': 1.1, 'sl': 1.0, 'confidence': 0.7},
            '弱下跌': {'tp': 1.1, 'sl': 1.0, 'confidence': 0.7},
            '震荡': {'tp': 0.9, 'sl': 1.1, 'confidence': 0.5}
        }
        
        trend_info = trend_adjustments.get(trend_strength, {'tp': 1.0, 'sl': 1.0, 'confidence': 0.6})
        
        return {
            'tp_multiplier': trend_info['tp'] * adjustment_factor,
            'sl_multiplier': trend_info['sl'] * adjustment_factor,
            'confidence': trend_info['confidence']
        }
    
    def _calculate_risk_metrics(self, current_price: float, 
                              position: Optional[Dict[str, Any]], 
                              market_state: Dict[str, Any]) -> Dict[str, float]:
        """计算风险价值和其他风险指标"""
        
        # 简化版VaR计算
        volatility = market_state.get('atr_pct', 2.0) / 100
        
        # 95%置信区间的VaR
        var_95 = current_price * volatility * 1.645
        
        # 最大回撤估计
        max_drawdown = current_price * volatility * 2.0
        
        # 流动性风险
        liquidity_risk = self._assess_liquidity_risk(market_state)
        
        return {
            'value_at_risk': var_95,
            'max_drawdown': max_drawdown,
            'liquidity_risk': liquidity_risk,
            'volatility_score': volatility
        }
    
    def _apply_dynamic_adjustment(self, signal: str, current_price: float,
                                microstructure: Dict[str, Any],
                                order_flow: Dict[str, Any],
                                behavior_metrics: Dict[str, Any],
                                ml_prediction: Dict[str, float],
                                risk_metrics: Dict[str, float],
                                position: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """应用动态调整算法"""
        
        base_config = self.config
        
        # 基础参数
        base_sl_pct = base_config.get('base_sl_pct', 0.02)
        base_tp_pct = base_config.get('base_tp_pct', 0.06)
        
        # 应用机器学习预测
        base_sl_pct *= ml_prediction['sl_multiplier']
        base_tp_pct *= ml_prediction['tp_multiplier']
        
        # 风险价值调整
        var_adjustment = 1.0 + (risk_metrics['value_at_risk'] / current_price)
        base_sl_pct = min(base_sl_pct * var_adjustment, base_config.get('max_sl_pct', 0.05))
        
        # 流动性风险调整
        liquidity_factor = 1.0 + risk_metrics['liquidity_risk']
        base_sl_pct *= liquidity_factor
        base_tp_pct *= liquidity_factor
        
        # 行为金融学调整
        fear_greed_index = behavior_metrics.get('fear_greed_index', 50)
        if fear_greed_index > 70:  # 极度贪婪
            base_tp_pct *= 1.1
            base_sl_pct *= 0.9
        elif fear_greed_index < 30:  # 极度恐惧
            base_tp_pct *= 0.9
            base_sl_pct *= 1.1
        
        # 边界检查
        max_sl_pct = base_config.get('max_sl_pct', 0.05)
        max_tp_pct = base_config.get('max_tp_pct', 0.15)
        min_sl_pct = base_config.get('min_sl_pct', 0.01)
        min_tp_pct = base_config.get('min_tp_pct', 0.03)
        
        final_sl_pct = max(min_sl_pct, min(max_sl_pct, base_sl_pct))
        final_tp_pct = max(min_tp_pct, min(max_tp_pct, base_tp_pct))
        
        # 盈利保护逻辑
        final_sl_pct, final_tp_pct = self._apply_profit_protection(
            final_sl_pct, final_tp_pct, position, current_price
        )
        
        # 计算最终价格
        if signal.upper() == 'BUY':
            stop_loss = current_price * (1 - final_sl_pct)
            take_profit = current_price * (1 + final_tp_pct)
        elif signal.upper() == 'SELL':
            stop_loss = current_price * (1 + final_sl_pct)
            take_profit = current_price * (1 - final_tp_pct)
        else:
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02
        
        return {
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'sl_pct': final_sl_pct,
            'tp_pct': final_tp_pct,
            'confidence': ml_prediction['confidence'],
            'risk_level': self._calculate_risk_level(risk_metrics)
        }
    
    def _apply_advanced_profit_protection(self, base_sl_pct: float, base_tp_pct: float,
                                        position: Optional[Dict[str, Any]], 
                                        current_price: float,
                                        market_state: Dict[str, Any]) -> Tuple[float, float]:
        """高级盈利保护算法"""
        
        if not position or position.get('unrealized_pnl', 0) <= 0:
            return base_sl_pct, base_tp_pct
        
        entry_price = position.get('entry_price', current_price)
        unrealized_pnl = position['unrealized_pnl']
        invested_amount = entry_price * position.get('size', 0)
        
        if invested_amount <= 0:
            return base_sl_pct, base_tp_pct
        
        profit_pct = unrealized_pnl / invested_amount
        
        # 高级盈利保护配置
        protection_config = {
            'breakeven_at': 0.01,
            'lock_profit_at': 0.03,
            'aggressive_lock_at': 0.05,
            'trailing_distance': 0.015,
            'time_decay_factor': 0.95
        }
        
        final_sl_pct, final_tp_pct = base_sl_pct, base_tp_pct
        
        # 时间衰减调整
        holding_duration = position.get('duration_minutes', 0)
        if holding_duration > 60:  # 超过1小时
            time_factor = protection_config['time_decay_factor'] ** (holding_duration / 60)
            final_tp_pct *= time_factor
        
        # 分级盈利保护
        if profit_pct >= protection_config['aggressive_lock_at']:
            # 激进锁定：锁定80%利润
            locked_profit = profit_pct * 0.8
            final_sl_pct = max(final_sl_pct, locked_profit)
            log_info(f"🔒 激进利润锁定: 盈利{profit_pct:.2%}, 锁定{locked_profit:.2%}")
        elif profit_pct >= protection_config['lock_profit_at']:
            # 标准锁定：锁定70%利润
            locked_profit = profit_pct * 0.7
            final_sl_pct = max(final_sl_pct, locked_profit)
            log_info(f"🔒 标准利润锁定: 盈利{profit_pct:.2%}, 锁定{locked_profit:.2%}")
        elif profit_pct >= protection_config['breakeven_at']:
            # 保本保护：调整至保本线
            final_sl_pct = max(final_sl_pct, profit_pct - protection_config['trailing_distance'])
            log_info(f"🛡️ 保本保护: 盈利{profit_pct:.2%}, 止损调整至{final_sl_pct:.2%}")
        
        return final_sl_pct, final_tp_pct
    
    def _assess_liquidity_risk(self, market_state: Dict[str, Any]) -> float:
        """评估流动性风险"""
        # 简化版流动性风险评估
        volatility = market_state.get('atr_pct', 2.0)
        return min(volatility / 10.0, 0.5)  # 风险系数0-0.5
    
    def _calculate_risk_level(self, risk_metrics: Dict[str, float]) -> str:
        """计算风险等级"""
        risk_score = (
            risk_metrics['volatility_score'] * 0.4 +
            risk_metrics['liquidity_risk'] * 0.3 +
            (risk_metrics['value_at_risk'] / 1000) * 0.3
        )
        
        if risk_score < 0.02:
            return 'LOW'
        elif risk_score < 0.05:
            return 'MEDIUM'
        elif risk_score < 0.1:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _calculate_traditional_tp_sl(self, signal: str, current_price: float) -> Dict[str, float]:
        """传统止盈止损计算（作为回退方案）"""
        if signal.upper() == 'BUY':
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.06,
                'sl_pct': 0.02,
                'tp_pct': 0.06,
                'confidence': 0.5,
                'risk_level': 'MEDIUM'
            }
        elif signal.upper() == 'SELL':
            return {
                'stop_loss': current_price * 1.02,
                'take_profit': current_price * 0.94,
                'sl_pct': 0.02,
                'tp_pct': 0.06,
                'confidence': 0.5,
                'risk_level': 'MEDIUM'
            }
        else:
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.02,
                'sl_pct': 0.02,
                'tp_pct': 0.02,
                'confidence': 0.5,
                'risk_level': 'MEDIUM'
            }
    
    @staticmethod
    def _calculate_traditional_tp_sl(signal: str, current_price: float) -> Dict[str, float]:
        """传统止盈止损计算"""
        if signal.upper() == 'BUY':
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.06,
                'sl_pct': 0.02,
                'tp_pct': 0.06
            }
        elif signal.upper() == 'SELL':
            return {
                'stop_loss': current_price * 1.02,
                'take_profit': current_price * 0.94,
                'sl_pct': 0.02,
                'tp_pct': 0.06
            }
        else:
            return {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.02,
                'sl_pct': 0.02,
                'tp_pct': 0.02
            }
    
    @staticmethod
    def _apply_profit_protection(base_sl_pct: float, base_tp_pct: float, 
                               position: Optional[Dict[str, Any]], current_price: float) -> Tuple[float, float]:
        """应用盈利保护"""
        final_sl_pct, final_tp_pct = base_sl_pct, base_tp_pct
        
        if not position or position.get('unrealized_pnl', 0) <= 0:
            return final_sl_pct, final_tp_pct
        
        entry_price = position.get('entry_price', current_price)
        position_size = position.get('size', 0)
        
        if entry_price <= 0 or position_size <= 0:
            return final_sl_pct, final_tp_pct
        
        unrealized_pnl = position['unrealized_pnl']
        invested_amount = entry_price * position_size
        profit_pct = unrealized_pnl / invested_amount
        
        # 盈利保护配置
        profit_config = config.get('risk', 'trailing_stop')
        
        if profit_config.get('enabled', True):
            breakeven_at = profit_config.get('breakeven_at', 0.01)
            lock_profit_at = profit_config.get('lock_profit_at', 0.03)
            trailing_distance = profit_config.get('trailing_distance', 0.015)
            
            if profit_pct >= breakeven_at:
                final_sl_pct = max(final_sl_pct, profit_pct - trailing_distance)
                log_info(f"🛡️ 保本保护: 盈利{profit_pct:.2%}, 止损调整至{final_sl_pct:.2%}")
            
            if profit_pct >= lock_profit_at:
                locked_profit = profit_pct * 0.7
                final_sl_pct = max(final_sl_pct, locked_profit)
                log_info(f"🔒 利润锁定: 盈利{profit_pct:.2%}, 锁定{locked_profit:.2%}")
        
        return final_sl_pct, final_tp_pct

class SignalProcessor:
    """信号处理器"""
    
    @staticmethod
    def process_signal(signal_data: Dict[str, Any], position: Optional[Dict[str, Any]]) -> str:
        """处理信号，考虑做空开关"""
        signal = signal_data.get('signal', 'HOLD').upper()
        confidence = signal_data.get('confidence', 0.5)
        
        # 做空开关检查
        if not config.get('trading', 'allow_short_selling') and signal == 'SELL':
            if position and position.get('size', 0) > 0:
                # 有持仓时，SELL信号作为清仓
                log_info(f"🚨 做空功能已禁用，SELL信号作为清仓条件 (信心: {confidence:.3f})")
                signal_data['is_liquidation'] = True
                return 'SELL'
            else:
                # 无持仓时，SELL信号转换为HOLD
                log_info(f"🚫 做空功能已禁用，无持仓时SELL信号转换为HOLD (信心: {confidence:.3f})")
                return 'HOLD'
        
        return signal
    
    @staticmethod
    def calculate_order_size(balance: Dict[str, float], signal: str, 
                           price: float, risk_pct: float = 0.02) -> float:
        """计算订单大小"""
        available_balance = balance.get('free', 0)
        max_position_size = config.get('trading', 'max_position_size')
        
        # 基于风险计算订单大小
        risk_amount = available_balance * risk_pct
        position_size = risk_amount / price
        
        # 限制最大仓位
        return min(position_size, max_position_size)

class ConsolidationDetector:
    """完整的横盘利润锁定策略系统"""
    
    def __init__(self):
        self.config = config.get('strategies', 'profit_lock_strategy')
    
    def should_lock_profit(self, position: Dict[str, Any], market_data: Dict[str, Any], 
                          price_history: Dict[str, list]) -> bool:
        """基于6维度判断的横盘利润锁定决策"""
        
        if not self._basic_checks(position, market_data):
            return False
        
        # 6维度综合评估
        score = 0
        total_checks = 6
        
        # 1. 盈利状态检查
        if self._check_profit_status(position, market_data):
            score += 1
        
        # 2. 波动率计算与分析
        if self._analyze_volatility(price_history):
            score += 1
        
        # 3. 时间序列模式识别
        if self._recognize_time_series_pattern(price_history):
            score += 1
        
        # 4. 形态学分析
        if self._analyze_patterns(price_history):
            score += 1
        
        # 5. 成交量验证
        if self._validate_volume(price_history):
            score += 1
        
        # 6. 触发条件综合判断
        if self._evaluate_trigger_conditions(price_history, market_data):
            score += 1
        
        # 需要满足4项以上条件
        should_lock = score >= 4
        
        if should_lock:
            log_info(f"🔒 横盘利润锁定触发: 满足{score}/{total_checks}项条件")
        
        return should_lock
    
    def _basic_checks(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """基础检查"""
        if not self.config.get('enabled', False):
            return False
        
        if not position or position.get('size', 0) <= 0:
            return False
        
        # 检查是否仅处理多头持仓
        if self.config.get('only_long_positions', True) and position.get('side') != 'long':
            return False
        
        return True
    
    def _check_profit_status(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """盈利状态检查"""
        try:
            # 防御性检查
            if not position or not market_data:
                return False
                
            entry_price = position.get('entry_price', 0)
            current_price = market_data.get('price', 0)
            
            if entry_price is None or current_price is None:
                return False
                
            if entry_price <= 0 or current_price <= 0:
                return False
            
            # 确保config存在
            if not self.config:
                return False
                
            profit_pct = abs(current_price - entry_price) / entry_price
            min_profit = self.config.get('min_profit_pct', 0.005)
            
            meets_profit = profit_pct >= min_profit
            
            if meets_profit:
                log_info(f"✅ 盈利检查通过: 当前盈利{profit_pct:.2%} ≥ 最小阈值{min_profit:.2%}")
            
            return meets_profit
        except Exception as e:
            log_warning(f"盈利状态检查异常: {e}")
            return False
    
    def _analyze_volatility(self, price_history: Dict[str, list]) -> bool:
        """波动率计算与分析"""
        try:
            if not price_history or not isinstance(price_history, dict):
                return False
                
            prices = price_history.get('close', [])
            if not isinstance(prices, list) or len(prices) < 6:
                return False
            
            lookback_periods = self.config.get('lookback_periods', 6)
            recent_prices = prices[-lookback_periods:]
            
            # 计算ATR
            highs = price_history.get('high', [])
            lows = price_history.get('low', [])
            closes = price_history.get('close', [])
            
            if not all(isinstance(lst, list) for lst in [highs, lows, closes]):
                return False
                
            highs = highs[-lookback_periods:]
            lows = lows[-lookback_periods:]
            closes = closes[-lookback_periods:]
            
            if len(highs) >= 2 and len(lows) >= 2 and len(closes) >= 2:
                atr = self._calculate_atr(highs, lows, closes)
                current_price = closes[-1]
                volatility_pct = (atr / current_price) * 100
                
                # 自适应波动率调整
                consolidation_threshold = self.config.get('consolidation_threshold', 0.008)
                if self.config.get('volatility_adaptive', True):
                    if volatility_pct < 1.0:
                        consolidation_threshold *= 0.8  # 低波动环境更敏感
                    elif volatility_pct > 3.0:
                        consolidation_threshold *= 1.2  # 高波动环境更宽松
                
                meets_volatility = volatility_pct <= (consolidation_threshold * 100)
                
                if meets_volatility:
                    log_info(f"✅ 波动率检查通过: 当前波动率{volatility_pct:.2f}% ≤ 阈值{consolidation_threshold*100:.2f}%")
                
                return meets_volatility
            
            return False
        except Exception as e:
            log_warning(f"波动率分析异常: {e}")
            return False
    
    def _recognize_time_series_pattern(self, price_history: Dict[str, list]) -> bool:
        """时间序列模式识别"""
        try:
            if not price_history or not isinstance(price_history, dict):
                return False
                
            prices = price_history.get('close', [])
            if not isinstance(prices, list) or len(prices) < 6:
                return False
            
            lookback_periods = self.config.get('lookback_periods', 6)
            recent_prices = prices[-lookback_periods:]
            
            if not recent_prices:
                return False
                
            # 价格通道计算
            max_price = max(recent_prices)
            min_price = min(recent_prices)
            
            if max_price <= 0:
                return False
                
            channel_width = (max_price - min_price) / max_price
            
            consolidation_threshold = self.config.get('consolidation_threshold', 0.008)
            meets_pattern = channel_width <= consolidation_threshold
            
            if meets_pattern:
                log_info(f"✅ 时间序列模式检查通过: 通道宽度{channel_width:.2%} ≤ 阈值{consolidation_threshold:.2%}")
            
            return meets_pattern
        except Exception as e:
            log_warning(f"时间序列模式识别异常: {e}")
            return False
    
    def _analyze_patterns(self, price_history: Dict[str, list]) -> bool:
        """形态学分析 - 支撑阻力位识别"""
        try:
            if not price_history or not isinstance(price_history, dict):
                return False
                
            prices = price_history.get('close', [])
            if not isinstance(prices, list) or len(prices) < 6:
                return False
            
            lookback_periods = self.config.get('lookback_periods', 6)
            recent_prices = prices[-lookback_periods:]
            
            if not recent_prices or len(recent_prices) < 3:
                return False
                
            # 简化版支撑阻力位识别
            supports = self._find_support_levels(recent_prices)
            resistances = self._find_resistance_levels(recent_prices)
            
            # 计算支撑阻力密度
            min_price = min(recent_prices)
            max_price = max(recent_prices)
            price_range = max_price - min_price
            
            if price_range <= 0:
                return False
            
            support_density = len(supports) / len(recent_prices) if recent_prices else 0
            resistance_density = len(resistances) / len(recent_prices) if recent_prices else 0
            
            # 支撑阻力比
            density_ratio = (support_density + resistance_density) / 2
            
            meets_patterns = density_ratio >= 0.1  # 至少10%的点位是支撑/阻力
            
            if meets_patterns:
                log_info(f"✅ 形态学分析通过: 支撑阻力密度{density_ratio:.2%}")
            
            return meets_patterns
        except Exception as e:
            log_warning(f"形态学分析异常: {e}")
            return False
    
    def _validate_volume(self, price_history: Dict[str, list]) -> bool:
        """成交量验证"""
        try:
            if not price_history or not isinstance(price_history, dict):
                return False
                
            volumes = price_history.get('volume', [])
            if not isinstance(volumes, list) or len(volumes) < 6:
                return False
            
            lookback_periods = self.config.get('lookback_periods', 6)
            recent_volumes = volumes[-lookback_periods:] if len(volumes) >= lookback_periods else volumes
            
            if not recent_volumes:
                return False
            
            # 计算平均成交量
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            current_volume = recent_volumes[-1]
            
            if avg_volume <= 0 or current_volume <= 0:
                return False
            
            # 成交量异常检测
            min_volume_threshold = self.config.get('min_volume_threshold', 1000000)
            volume_ratio = current_volume / avg_volume
            
            meets_volume = current_volume >= min_volume_threshold and volume_ratio >= 0.5
            
            if meets_volume:
                log_info(f"✅ 成交量验证通过: 当前成交量{current_volume:,.0f} ≥ 最小阈值{min_volume_threshold:,.0f}")
            
            return meets_volume
        except Exception as e:
            log_warning(f"成交量验证异常: {e}")
            return False
    
    def _evaluate_trigger_conditions(self, price_history: Dict[str, list], market_data: Dict[str, Any]) -> bool:
        """触发条件综合判断"""
        try:
            if not price_history or not isinstance(price_history, dict):
                return False
                
            prices = price_history.get('close', [])
            if not isinstance(prices, list) or len(prices) < 6:
                return False
            
            # 确保所有价格都是有效的数字
            valid_prices = [p for p in prices if isinstance(p, (int, float)) and p > 0]
            if len(valid_prices) < 3:
                return False
            
            # 横盘持续时间检查
            consolidation_duration = self.config.get('consolidation_duration', 20)
            max_consecutive = self.config.get('max_consecutive_periods', 8)
            
            # 突破阈值检查
            breakout_threshold = self.config.get('breakout_threshold', 0.012)
            
            # 时间衰减因子
            time_decay = self.config.get('time_decay_factor', 0.95)
            
            # 综合评分计算
            recent_prices = valid_prices[-6:]  # 30分钟数据
            if len(recent_prices) < 2:
                return False
                
            mean_price = np.mean(recent_prices)
            if mean_price <= 0:
                return False
                
            price_stability = np.std(recent_prices) / mean_price
            
            meets_conditions = price_stability <= breakout_threshold
            
            if meets_conditions:
                log_info(f"✅ 触发条件评估通过: 价格稳定性{price_stability:.4f} ≤ 突破阈值{breakout_threshold}")
            
            return meets_conditions
        except Exception as e:
            log_warning(f"触发条件评估异常: {e}")
            return False
    
    def _calculate_atr(self, highs: list, lows: list, closes: list) -> float:
        """计算ATR"""
        if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
            return 2.0
        
        highs = np.array(highs)
        lows = np.array(lows)
        closes = np.array(closes)
        
        tr = np.maximum(highs - lows, 
                       np.maximum(np.abs(highs - np.roll(closes, 1)), 
                                 np.abs(lows - np.roll(closes, 1))))
        atr = np.mean(tr[1:])
        
        return atr
    
    def _find_support_levels(self, prices: list) -> list:
        """识别支撑位"""
        supports = []
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                supports.append(prices[i])
        return supports
    
    def _find_resistance_levels(self, prices: list) -> list:
        """识别阻力位"""
        resistances = []
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                resistances.append(prices[i])
        return resistances

class MarketMicrostructureAnalyzer:
    """市场微观结构分析器"""
    
    def analyze(self, current_price: float, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场微观结构"""
        
        # 买卖价差分析
        bid = market_state.get('bid', current_price * 0.999)
        ask = market_state.get('ask', current_price * 1.001)
        spread = abs(ask - bid)
        spread_impact = (spread / current_price) * 100 if current_price > 0 else 0.0
        
        # 订单簿深度分析（简化版）
        depth_score = min(0.8 + (market_state.get('volume', 1000000) / 10000000), 1.0)
        
        # 流动性指标 - 防止除零错误
        volatility = max(market_state.get('atr_pct', 2.0), 0.01)  # 最小波动率0.01%
        current_price_safe = max(current_price, 0.01)  # 最小价格0.01防止除零
        liquidity_ratio = market_state.get('volume', 1000000) / (volatility * current_price_safe)
        
        return {
            'spread_impact': spread_impact,
            'depth_score': depth_score,
            'liquidity_ratio': liquidity_ratio,
            'micro_volatility': volatility
        }

class OrderFlowAnalyzer:
    """订单流分析器"""
    
    def analyze(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """分析订单流"""
        
        # 买卖力量对比（简化版）
        buy_volume = market_state.get('volume', 1000000) * 0.6  # 模拟买盘
        sell_volume = market_state.get('volume', 1000000) * 0.4  # 模拟卖盘
        buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 1.0
        
        # 订单不平衡度
        order_imbalance = abs(buy_volume - sell_volume) / (buy_volume + sell_volume)
        
        # 大单识别（简化版）
        large_order_impact = 0.001 * (market_state.get('volume', 1000000) / 1000000)
        
        return {
            'buy_sell_ratio': buy_sell_ratio,
            'order_imbalance': order_imbalance,
            'large_order_impact': large_order_impact,
            'net_flow': buy_volume - sell_volume
        }

class BehaviorFinanceAnalyzer:
    """行为金融学分析器"""
    
    def calculate(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """计算行为金融学指标"""
        
        # 恐惧贪婪指数（简化版）
        price_change = market_state.get('price_change_pct', 0)
        volatility = market_state.get('atr_pct', 2.0)
        
        # 基于价格变动和波动率计算恐惧贪婪指数
        fear_greed_index = 50 + (price_change * 10) - (volatility * 5)
        fear_greed_index = max(0, min(100, fear_greed_index))
        
        # 动量指标
        momentum = price_change * 100  # 转换为百分比
        
        # 波动率聚集检测
        volatility_clustering = volatility > 3.0
        
        return {
            'fear_greed_index': fear_greed_index,
            'momentum': momentum,
            'volatility_clustering': volatility_clustering,
            'sentiment_score': (fear_greed_index - 50) / 50  # -1到1
        }

class CrashProtectionSystem:
    """价格暴跌保护系统 - 多层次暴跌检测与保护机制"""
    
    def __init__(self):
        self.config = config.get('strategies', 'crash_protection')
        self.price_history = []
        self.alert_system = AlertSystem()
        self.risk_controller = RiskController()
        
    def should_trigger_crash_protection(self, current_price: float, 
                                      market_state: Dict[str, Any],
                                      position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """触发暴跌保护的多维度判断"""
        
        if not self.config.get('enabled', False):
            return {'should_protect': False, 'reason': '暴跌保护已关闭'}
        
        # 1. 基础检查
        if not position or position.get('size', 0) <= 0:
            return {'should_protect': False, 'reason': '无持仓'}
        
        # 2. 多维度暴跌检测
        crash_indicators = self._analyze_crash_indicators(current_price, market_state)
        
        # 3. 风险等级评估
        risk_level = self._assess_crash_risk_level(crash_indicators)
        
        # 4. 保护决策
        protection_decision = self._make_protection_decision(risk_level, crash_indicators, position)
        
        # 5. 执行保护动作
        if protection_decision['should_protect']:
            self._execute_crash_protection_actions(risk_level, crash_indicators, position)
        
        return protection_decision
    
    def _analyze_crash_indicators(self, current_price: float, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """分析暴跌指标"""
        
        indicators = {}
        
        # 1. 价格暴跌检测
        price_change_1m = self._calculate_price_change(1)
        price_change_5m = self._calculate_price_change(5)
        price_change_15m = self._calculate_price_change(15)
        
        indicators['price_crash'] = {
            'change_1m': price_change_1m,
            'change_5m': price_change_5m,
            'change_15m': price_change_15m,
            'severity': max(abs(price_change_1m), abs(price_change_5m), abs(price_change_15m))
        }
        
        # 2. 成交量异常检测
        volume_ratio = self._detect_volume_anomaly(market_state)
        indicators['volume_anomaly'] = {
            'volume_ratio': volume_ratio,
            'is_anomaly': volume_ratio > self.config.get('volume_spike_threshold', 3.0)
        }
        
        # 3. 波动率突变检测
        volatility_spike = self._detect_volatility_spike(market_state)
        indicators['volatility_spike'] = {
            'volatility_ratio': volatility_spike,
            'is_spike': volatility_spike > self.config.get('volatility_spike_threshold', 2.5)
        }
        
        # 4. 订单簿失衡检测
        orderbook_imbalance = self._detect_orderbook_imbalance(market_state)
        indicators['orderbook_imbalance'] = {
            'imbalance_ratio': orderbook_imbalance,
            'is_severe': abs(orderbook_imbalance) > self.config.get('orderbook_imbalance_threshold', 0.7)
        }
        
        # 5. 连锁反应检测
        cascade_risk = self._detect_cascade_risk(market_state)
        indicators['cascade_risk'] = {
            'risk_score': cascade_risk,
            'is_high': cascade_risk > self.config.get('cascade_risk_threshold', 0.8)
        }
        
        return indicators
    
    def _assess_crash_risk_level(self, indicators: Dict[str, Any]) -> str:
        """评估暴跌风险等级"""
        
        score = 0
        max_score = 5
        
        # 价格暴跌评分
        price_severity = indicators['price_crash']['severity']
        if price_severity > self.config.get('crash_threshold_critical', 0.05):
            score += 2
        elif price_severity > self.config.get('crash_threshold_high', 0.03):
            score += 1
        
        # 成交量异常评分
        if indicators['volume_anomaly']['is_anomaly']:
            score += 1
        
        # 波动率突变评分
        if indicators['volatility_spike']['is_spike']:
            score += 1
        
        # 订单簿失衡评分
        if indicators['orderbook_imbalance']['is_severe']:
            score += 1
        
        # 连锁反应评分
        if indicators['cascade_risk']['is_high']:
            score += 1
        
        # 风险等级判定
        if score >= 4:
            return 'CRITICAL'
        elif score >= 3:
            return 'HIGH'
        elif score >= 2:
            return 'MEDIUM'
        elif score >= 1:
            return 'LOW'
        else:
            return 'SAFE'
    
    def _make_protection_decision(self, risk_level: str, indicators: Dict[str, Any], 
                                 position: Dict[str, Any]) -> Dict[str, Any]:
        """制定保护决策"""
        
        if risk_level == 'CRITICAL':
            return {
                'should_protect': True,
                'action': 'IMMEDIATE_CLOSE',
                'reason': f'严重暴跌检测 - 价格跌幅{indicators["price_crash"]["severity"]:.2%}',
                'risk_level': risk_level,
                'priority': 1
            }
        
        elif risk_level == 'HIGH':
            return {
                'should_protect': True,
                'action': 'EMERGENCY_STOP',
                'reason': f'高风险暴跌 - 价格跌幅{indicators["price_crash"]["severity"]:.2%}',
                'risk_level': risk_level,
                'priority': 2
            }
        
        elif risk_level == 'MEDIUM':
            return {
                'should_protect': True,
                'action': 'PROTECTIVE_STOP',
                'reason': f'中等风险 - 价格跌幅{indicators["price_crash"]["severity"]:.2%}',
                'risk_level': risk_level,
                'priority': 3
            }
        
        elif risk_level == 'LOW':
            return {
                'should_protect': True,
                'action': 'ENHANCED_MONITORING',
                'reason': f'低风险预警 - 价格跌幅{indicators["price_crash"]["severity"]:.2%}',
                'risk_level': risk_level,
                'priority': 4
            }
        
        else:
            return {
                'should_protect': False,
                'action': 'NONE',
                'reason': '无暴跌风险',
                'risk_level': risk_level,
                'priority': 5
            }
    
    def _execute_crash_protection_actions(self, risk_level: str, indicators: Dict[str, Any], 
                                        position: Dict[str, Any]):
        """执行暴跌保护动作"""
        
        log_info(f"🚨 暴跌保护触发 - 风险等级: {risk_level}")
        
        # 1. 发送警报
        self.alert_system.send_crash_alert(risk_level, indicators, position)
        
        # 2. 执行对应保护动作
        if risk_level in ['CRITICAL', 'HIGH']:
            # 立即平仓
            self._execute_immediate_close(position)
        
        elif risk_level == 'MEDIUM':
            # 收紧止损
            self._tighten_stop_loss(position)
        
        elif risk_level == 'LOW':
            # 增强监控
            self._enhance_monitoring(position)
    
    def _calculate_price_change(self, minutes: int) -> float:
        """计算价格变化百分比"""
        if len(self.price_history) < minutes + 1:
            return 0.0
        
        current_price = self.price_history[-1]
        past_price = self.price_history[-(minutes + 1)]
        
        if past_price == 0:
            return 0.0
        
        return (current_price - past_price) / past_price
    
    def _detect_volume_anomaly(self, market_state: Dict[str, Any]) -> float:
        """检测成交量异常"""
        try:
            if not market_state or not isinstance(market_state, dict):
                return 1.0
                
            current_volume = market_state.get('volume', 0)
            if not isinstance(current_volume, (int, float)) or current_volume < 0:
                return 1.0
                
            avg_volume = np.mean([market_state.get('volume', 0)] * 20)  # 简化计算
            
            if avg_volume <= 0:
                return 1.0
            
            return current_volume / avg_volume
        except Exception as e:
            log_warning(f"成交量异常检测异常: {e}")
            return 1.0
    
    def _detect_volatility_spike(self, market_state: Dict[str, Any]) -> float:
        """检测波动率突变"""
        try:
            if not market_state or not isinstance(market_state, dict):
                return 1.0
                
            current_atr = market_state.get('atr_pct', 2.0)
            if not isinstance(current_atr, (int, float)) or current_atr <= 0:
                return 1.0
                
            avg_atr = 2.0  # 基准波动率
            
            return current_atr / avg_atr
        except Exception as e:
            log_warning(f"波动率突变检测异常: {e}")
            return 1.0
    
    def _detect_orderbook_imbalance(self, market_state: Dict[str, Any]) -> float:
        """检测订单簿失衡"""
        try:
            if not market_state or not isinstance(market_state, dict):
                return 0.0
                
            bid = market_state.get('bid', 0)
            ask = market_state.get('ask', 0)
            
            if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
                return 0.0
                
            if bid <= 0 or ask <= 0:
                return 0.0
            
            mid_price = (bid + ask) / 2
            if mid_price <= 0:
                return 0.0
                
            imbalance = (ask - bid) / mid_price
            
            return imbalance
        except Exception as e:
            log_warning(f"订单簿失衡检测异常: {e}")
            return 0.0
    
    def _detect_cascade_risk(self, market_state: Dict[str, Any]) -> float:
        """检测连锁反应风险"""
        try:
            if not market_state or not isinstance(market_state, dict):
                return 0.0
                
            price_change = abs(market_state.get('price_change_pct', 0))
            volatility = market_state.get('atr_pct', 2.0)
            
            if not isinstance(price_change, (int, float)) or not isinstance(volatility, (int, float)):
                return 0.0
            
            # 风险评分算法
            cascade_score = (price_change * 10) + (volatility / 2)
            
            # 归一化到0-1
            return min(cascade_score / 10.0, 1.0)
        except Exception as e:
            log_warning(f"连锁反应风险检测异常: {e}")
            return 0.0
    
    def _execute_immediate_close(self, position: Dict[str, Any]):
        """立即平仓"""
        log_info(f"🚨 立即平仓触发 - 持仓方向: {position.get('side', 'unknown')}")
        # 这里会调用交易引擎执行平仓
        # 实际实现中会发送平仓指令
    
    def _tighten_stop_loss(self, position: Dict[str, Any]):
        """收紧止损"""
        entry_price = position.get('entry_price', 0)
        current_price = self.price_history[-1] if self.price_history else entry_price
        
        if entry_price > 0:
            # 收紧止损到当前价格的1%以内
            new_stop_loss = current_price * (1 - 0.01) if position.get('side') == 'long' else current_price * (1 + 0.01)
            log_info(f"🛡️ 收紧止损到: ${new_stop_loss:.2f}")
    
    def _enhance_monitoring(self, position: Dict[str, Any]):
        """增强监控"""
        log_info(f"👁️ 增强监控模式 - 持仓: {position.get('side', 'unknown')} {position.get('size', 0)}")
        # 增加监控频率和敏感度

class AlertSystem:
    """警报系统"""
    
    def send_crash_alert(self, risk_level: str, indicators: Dict[str, Any], position: Dict[str, Any]):
        """发送暴跌警报"""
        alert_message = f"""
        🚨 暴跌警报触发
        风险等级: {risk_level}
        价格跌幅: {indicators['price_crash']['severity']:.2%}
        持仓方向: {position.get('side', 'unknown')}
        持仓大小: {position.get('size', 0)}
        未实现盈亏: {position.get('unrealized_pnl', 0)}
        """
        
        log_warning(alert_message)
        # 实际应用中这里会发送邮件、短信等通知

class RiskController:
    """风险控制器"""
    
    def __init__(self):
        self.config = config.get('risk', 'crash_protection')

# 全局策略实例
market_analyzer = MarketAnalyzer()
risk_manager = RiskManager()
signal_processor = SignalProcessor()
consolidation_detector = ConsolidationDetector()
crash_protection = CrashProtectionSystem()
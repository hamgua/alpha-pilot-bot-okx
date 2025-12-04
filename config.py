"""
Alpha Pilot Bot OKX 配置管理模块
将所有配置项集中管理，实现配置与业务逻辑的完全分离
提供统一的配置访问接口和完整的错误处理机制
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

# 导入日志函数
from utils import log_warning, log_error

load_dotenv()

class ConfigSection(Enum):
    """配置段枚举"""
    EXCHANGE = "exchange"
    TRADING = "trading"
    STRATEGIES = "strategies"
    RISK = "risk"
    AI = "ai"
    SYSTEM = "system"

@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]

class ConfigManager:
    """配置管理器 - 统一管理所有配置
    
    负责：
    - 加载和验证所有配置项
    - 提供统一的配置访问接口
    - 处理配置错误和回退机制
    - 支持运行时配置更新
    """
    
    def __init__(self):
        """初始化配置管理器"""
        self._config = self._load_all_config()
        self._validation_result = self._validate_config()
        
        if not self._validation_result.is_valid:
            log_error(f"配置验证失败: {self._validation_result.errors}")
            raise ValueError("配置验证失败")
    
    def _load_all_config(self) -> Dict[str, Any]:
        """加载所有配置
        
        从环境变量和默认值加载所有配置项
        
        Returns:
            Dict[str, Any]: 完整的配置字典
        """
        return {
            'exchange': self._load_exchange_config(),
            'trading': self._load_trading_config(),
            'strategies': self._load_strategy_config(),
            'risk': self._load_risk_config(),
            'ai': self._load_ai_config(),
            'system': self._load_system_config()
        }
    
    def _load_exchange_config(self) -> Dict[str, Any]:
        """交易所配置 - 连接OKX交易所的核心参数
        
        配置OKX交易所的连接参数，包括API密钥、交易对等
        
        Returns:
            Dict[str, Any]: 交易所配置字典
        """
        return {
            'exchange': 'okx',  # 交易所名称，固定为okx
            'api_key': os.getenv('OKX_API_KEY'),  # OKX API密钥 - 用于身份验证
            'secret': os.getenv('OKX_SECRET'),  # OKX密钥 - 用于签名请求
            'password': os.getenv('OKX_PASSWORD'),  # OKX交易密码 - 用于资金操作
            'sandbox': os.getenv('OKX_SANDBOX', 'false').lower() == 'true',  # 沙盒模式 - true为测试环境，false为真实交易
            'symbol': 'BTC/USDT:USDT',  # 交易对 - BTC永续合约
            'timeframe': '5m',  # K线周期 - 5分钟K线（可改为1m,15m,1h等）
            'contract_size': 0.01  # 合约乘数 - 每份合约代表0.01个BTC
        }
    
    def _load_trading_config(self) -> Dict[str, Any]:
        """交易配置 - 控制交易行为和风险参数
        
        配置交易相关的参数，包括仓位大小、杠杆、交易模式等
        
        Returns:
            Dict[str, Any]: 交易配置字典
        """
        return {
            'test_mode': os.getenv('TEST_MODE', 'true').lower() == 'true',  # 测试模式 - true为模拟交易，false为真实交易
            'max_position_size': float(os.getenv('MAX_POSITION_SIZE', '0.01')),  # 最大持仓量 - 最多持有的BTC数量
            'min_trade_amount': float(os.getenv('MIN_TRADE_AMOUNT', '0.001')),  # 最小交易量 - 每次交易的最小BTC数量
            'leverage': int(os.getenv('LEVERAGE', '10')),  # 杠杆倍数 - 10倍杠杆（谨慎调整）
            'cycle_minutes': int(os.getenv('CYCLE_MINUTES', '15')),  # 交易周期 - 每15分钟执行一次交易检查
            'margin_mode': 'cross',  # 保证金模式 - cross为全仓，isolated为逐仓
            'position_mode': 'one_way',  # 持仓模式 - one_way为单向持仓，hedge为双向持仓
            'allow_short_selling': os.getenv('ALLOW_SHORT_SELLING', 'false').lower() == 'true'  # 允许做空 - true可开空仓，false只能做多
        }
    
    def _load_strategy_config(self) -> Dict[str, Any]:
        """策略配置 - 各种智能交易策略的参数设置
        
        配置各种交易策略的参数，包括横盘保护、信号策略、风险控制等
        
        Returns:
            Dict[str, Any]: 策略配置字典
        """
        return {
            'profit_lock_strategy': {
                'enabled': True,  # 利润锁定策略开关 - true启用横盘利润保护
                'consolidation_threshold': 0.01,  # 横盘识别阈值 - 价格波动小于1%视为横盘
                'lookback_periods': 24,  # 回看周期数 - 24根K线（2小时）用于识别横盘
                'consolidation_duration': 120,  # 横盘持续时间 - 120分钟（2小时）确认横盘
                'min_volume_threshold': 1000,  # 最小成交量 - 低于1000不触发横盘保护
                'max_consecutive_periods': 8,  # 最大连续周期 - 横盘超过8个周期强制止盈
                'breakout_threshold': 0.012,  # 突破阈值 - 价格波动超过1.2%视为突破横盘
                'min_profit_pct': 0.005,  # 最小盈利比例 - 盈利超过0.5%才触发横盘保护
                'volatility_adaptive': True,  # 波动率自适应 - 根据市场波动调整阈值
                'time_decay_factor': 0.95,  # 时间衰减因子 - 横盘时间越长，止盈越激进
                'only_long_positions': True,  # 仅处理多头 - true只处理多头持仓的横盘保护
                'usdt_threshold': 100,  # USDT阈值 - 多头仓位价值≥100USDT执行部分平仓，<100USDT全部平仓
                'partial_close_ratio': 0.5,  # 部分平仓比例 - 首次平仓50%
                'trailing_stop_pct': 0.008,  # 跟踪止损比例 - 0.8%跟踪止损
                'duration_check_minutes': 30,  # 持续性检查时间 - 30分钟后再次平仓25%
                'additional_close_ratio': 0.25,  # 持续横盘后的额外平仓比例 - 再平仓25%
                'cancel_tp_orders': True,  # 取消止盈订单 - 横盘触发后取消所有TP订单
                'keep_sl_orders': True,  # 保留止损订单 - 横盘触发后保留SL订单
            },
            'sell_signal_strategy': {
                'enabled': True,  # SELL信号策略开关 - true启用SELL信号平仓逻辑
                'consecutive_sell_count': 2,  # 连续SELL信号次数 - 需要连续2次SELL才执行平仓
                'ma_period': 15,  # 均线周期 - 15分钟均线用于趋势确认
                'price_break_ma_threshold': 0.001,  # 价格跌破均线阈值 - 价格跌破均线0.1%视为确认
                'min_profit_threshold': 0.0,  # 最小盈利阈值 - 浮盈≥0时允许平仓
                'reverse_offset_threshold': 0.005,  # 反向偏移阈值 - 价格距离开仓价反向偏移≥0.5%视为确认
                'close_full_position': True,  # 全部平仓 - true时平掉100%多头仓位
                'cancel_all_pending_orders': True,  # 取消所有挂单 - true时取消全部未成交委托单
                'log_sell_reason': True,  # 记录卖出原因 - true时记录详细的卖出原因用于AI调优
            },
            'buy_signal_strategy': {
                'enabled': True,  # BUY信号策略开关 - true启用BUY信号入仓逻辑
                'allow_rebuy': False,  # 允许补仓 - false时不允许在已有持仓时补仓
                'price_update_threshold': 0.005,  # 价格更新阈值 - 新TP/SL价格与现有订单差距≥0.5%才更新
                'clear_consolidation_on_buy': True,  # 清除横盘计数 - BUY信号出现时清除横盘相关计数
                'prevent_high_frequency_updates': True,  # 防止高频更新 - 避免频繁更新止盈止损订单
                'max_update_frequency_minutes': 15,  # 最大更新频率 - 5分钟内最多更新一次止盈止损
            },
            'consolidation_protection': {
                'enabled': True,  # 横盘保护开关 - true启用横盘利润锁定
                'consecutive_hold_required': 4,  # 连续HOLD信号次数 - 需要连续4次HOLD才触发横盘检查
                'consolidation_threshold': 0.01,  # 横盘阈值 - 2小时内价格波动<1%视为横盘
                'lookback_hours': 2,  # 回顾时间 - 检查最近2小时的价格波动
                'cancel_all_pending_orders': True,  # 取消所有挂单 - 触发横盘平仓时取消所有未成交订单
                'log_consolidation_reason': True,  # 记录横盘原因 - true时记录详细的横盘触发原因
            },
            'risk_control': {
                'conservative': {
                    'max_daily_loss': 50,           # 最大日亏损 50 USDT
                    'max_position_risk': 0.03,      # 最大仓位风险 3%
                    'max_consecutive_losses': 2,    # 最大连续亏损次数
                    'emergency_stop_loss': 0.025,   # 紧急止损 2.5%
                    'position_size_limits': {
                        'min': 0.001,               # 最小仓位
                        'max': 0.01,                # 最大仓位
                        'initial': 0.005            # 初始仓位
                    },
                    'time_restrictions': {
                        'min_hold_time': 30,        # 最小持仓时间(分钟)
                        'max_hold_time': 240,       # 最大持仓时间(4小时)
                        'cooldown_period': 60       # 交易冷却期(分钟)
                    }
                },
                'moderate': {
                    'max_daily_loss': 100,          # 最大日亏损 100 USDT
                    'max_position_risk': 0.05,      # 最大仓位风险 5%
                    'max_consecutive_losses': 3,    # 最大连续亏损次数
                    'emergency_stop_loss': 0.04,    # 紧急止损 4%
                    'position_size_limits': {
                        'min': 0.001,               # 最小仓位
                        'max': 0.02,                # 最大仓位
                        'initial': 0.008            # 初始仓位
                    },
                    'time_restrictions': {
                        'min_hold_time': 15,        # 最小持仓时间(分钟)
                        'max_hold_time': 480,       # 最大持仓时间(8小时)
                        'cooldown_period': 30       # 交易冷却期(分钟)
                    }
                },
                'aggressive': {
                    'max_daily_loss': 200,          # 最大日亏损 200 USDT
                    'max_position_risk': 0.08,      # 最大仓位风险 8%
                    'max_consecutive_losses': 4,    # 最大连续亏损次数
                    'emergency_stop_loss': 0.06,    # 紧急止损 6%
                    'position_size_limits': {
                        'min': 0.001,               # 最小仓位
                        'max': 0.05,                # 最大仓位
                        'initial': 0.015            # 初始仓位
                    },
                    'time_restrictions': {
                        'min_hold_time': 5,         # 最小持仓时间(分钟)
                        'max_hold_time': 120,       # 最大持仓时间(2小时)
                        'cooldown_period': 10       # 交易冷却期(分钟)
                    }
                }
            },
            'investment_strategies': {
                'conservative': {
                    'enabled': True,
                    'name': '稳健型策略',
                    'description': '适合80%交易者，低风险，稳定盈利 - 基于15分钟K线，保守仓位管理，严格止损',
                    'kline_period': '15m',  # 主要使用15分钟K线
                    'trend_indicators': ['MA20', 'MA60', 'MACD', 'RSI'],
                    'volatility_threshold': 0.012,  # 波动宽度 1.2%
                    'take_profit_pct': 0.04,  # 止盈 4%
                    'stop_loss_pct': 0.018,  # 止损 1.8%
                    'max_position_ratio': 0.4,  # 最大仓位 40%
                    'allow_rebuy': False,  # 不允许补仓
                    'consolidation_close_ratio': 1.0,  # 横盘全平仓
                    'position_sizing': 'conservative',  # 保守仓位管理
                    'min_trade_amount': 0.001,  # 最小交易量
                    'max_leverage': 5,  # 最大杠杆倍数
                    'risk_reward_ratio': 2.2,  # 风险收益比
                    'consolidation_protection': True,  # 启用横盘保护
                    'use_volume_confirmation': True,  # 使用成交量确认
                    'max_daily_trades': 3,  # 最大日交易次数
                    'min_position_hold_time': 30,  # 最小持仓时间(分钟)
                    'market_condition_filter': 'all',  # 适用所有市场条件
                    'signal_confirmation': 'strict',  # 严格信号确认
                    # 新增：完全符合设计文档的行为逻辑参数
                    'initial_position_ratio': 0.3,  # 初始仓位30%（20-40%范围）
                    'add_position_ratio': 0.0,  # 不加仓
                    'trend_strength_threshold': 0.0,  # 趋势强度阈值（不适用）
                    'use_trailing_stop': False,  # 不使用移动止盈
                    'trailing_stop_pct': 0.0,  # 移动止盈百分比
                    'consolidation_volatility_threshold': 0.01,  # 横盘波动阈值1%
                    'consolidation_signal_count': 4,  # 连续4次HOLD信号
                    'consolidation_time_window': 120,  # 横盘时间窗口2小时
                },
                'moderate': {
                    'enabled': True,
                    'name': '中等型策略',
                    'description': '趋势/波段交易，中等风险，抓趋势 - 基于10分钟K线，趋势跟随，波段操作',
                    'kline_period': '10m',  # 主要使用10分钟K线
                    'trend_indicators': ['MA20', 'MA120', 'MACD', 'RSI', 'Bollinger'],
                    'volatility_threshold': 0.015,  # 波动宽度 1.5%
                    'take_profit_pct': 0.09,  # 止盈 9%
                    'stop_loss_pct': 0.035,  # 止损 3.5%
                    'max_position_ratio': 0.7,  # 最大仓位 70%
                    'allow_rebuy': True,  # 允许条件加仓
                    'consolidation_close_ratio': 0.75,  # 横盘部分平仓75%
                    'position_sizing': 'moderate',  # 中等仓位管理
                    'min_trade_amount': 0.001,  # 最小交易量
                    'max_leverage': 10,  # 最大杠杆倍数
                    'risk_reward_ratio': 2.6,  # 风险收益比
                    'consolidation_protection': True,  # 启用横盘保护
                    'use_volume_confirmation': True,  # 使用成交量确认
                    'max_daily_trades': 5,  # 最大日交易次数
                    'min_position_hold_time': 60,  # 最小持仓时间(分钟)
                    'market_condition_filter': 'trending',  # 适用于趋势市场
                    'signal_confirmation': 'moderate',  # 中等信号确认
                    'trend_strength_threshold': 0.6,  # 趋势强度阈值
                    'add_position_on_trend': True,  # 趋势确认后加仓
                    # 新增：完全符合设计文档的行为逻辑参数
                    'initial_position_ratio': 0.55,  # 初始仓位55%（50-60%范围）
                    'add_position_ratio': 0.15,  # 加仓15%（10-20%范围）
                    'use_trailing_stop': False,  # 不使用移动止盈
                    'trailing_stop_pct': 0.0,  # 移动止盈百分比
                    'consolidation_volatility_threshold': 0.015,  # 横盘波动阈值1.5%
                    'consolidation_signal_count': 4,  # 连续4次HOLD信号
                    'consolidation_time_window': 120,  # 横盘时间窗口2小时
                },
                'aggressive': {
                    'enabled': True,
                    'name': '激进型策略',
                    'description': '单边强趋势，高风险，最大化收益 - 基于5分钟K线，高频交易，强趋势捕捉',
                    'kline_period': '5m',  # 主要使用5分钟K线
                    'trend_indicators': ['EMA5', 'EMA20', 'EMA60', 'RSI', 'ATR'],
                    'volatility_threshold': 0.02,  # 波动宽度 2%
                    'take_profit_pct': 0.25,  # 止盈 25%
                    'stop_loss_pct': 0.05,  # 止损 5%
                    'max_position_ratio': 0.9,  # 最大仓位 90%
                    'allow_rebuy': True,  # 允许多次加仓
                    'consolidation_close_ratio': 0.3,  # 横盘减仓30%
                    'position_sizing': 'aggressive',  # 激进仓位管理
                    'min_trade_amount': 0.001,  # 最小交易量
                    'max_leverage': 20,  # 最大杠杆倍数
                    'risk_reward_ratio': 5.0,  # 风险收益比
                    'consolidation_protection': False,  # 禁用横盘保护
                    'use_volume_confirmation': False,  # 不依赖成交量确认
                    'max_daily_trades': 10,  # 最大日交易次数
                    'min_position_hold_time': 5,  # 最小持仓时间(分钟)
                    'market_condition_filter': 'strong_trend',  # 适用于强趋势市场
                    'signal_confirmation': 'fast',  # 快速信号确认
                    'trend_strength_threshold': 0.8,  # 趋势强度阈值
                    'use_trailing_stop': True,  # 使用移动止盈
                    'trailing_stop_pct': 0.03,  # 移动止盈3%
                    'pyramiding': True,  # 允许金字塔加仓
                    'max_pyramid_levels': 3,  # 最大金字塔层数
                    # 新增：完全符合设计文档的行为逻辑参数
                    'initial_position_ratio': 0.7,  # 初始仓位70%（60-80%范围）
                    'add_position_ratio': 0.25,  # 加仓25%（趋势越强越加仓）
                    'consolidation_volatility_threshold': 0.02,  # 横盘波动阈值2%
                    'consolidation_signal_count': 4,  # 连续4次HOLD信号
                    'consolidation_time_window': 120,  # 横盘时间窗口2小时
                }
            },
            'smart_tp_sl': {
                'enabled': True,  # 智能止盈止损开关 - true启用动态调整
                'base_sl_pct': 0.02,  # 基础止损比例 - 默认2%止损
                'base_tp_pct': 0.06,  # 基础止盈比例 - 默认6%止盈
                'adaptive_mode': True,  # 自适应模式 - 根据市场条件调整止损止盈
                'high_vol_multiplier': 1.5,  # 高波动率倍数 - 波动率高时扩大1.5倍
                'low_vol_multiplier': 0.8,  # 低波动率倍数 - 波动率低时缩小0.8倍
                'trend_strength_weight': 0.4,  # 趋势强度权重 - 趋势在调整中的权重40%
                'volume_weight': 0.3,  # 成交量权重 - 成交量在调整中的权重30%
                'time_weight': 0.2,  # 时间权重 - 持仓时间在调整中的权重20%
                'confidence_weight': 0.1,  # 信心权重 - AI信心在调整中的权重10%
                'max_sl_pct': 0.05,  # 最大止损比例 - 止损不超过5%
                'max_tp_pct': 0.15,  # 最大止盈比例 - 止盈不超过15%
                'min_sl_pct': 0.01,  # 最小止损比例 - 止损不低于1%
                'min_tp_pct': 0.03  # 最小止盈比例 - 止盈不低于3%
            },
            'limit_order': {
                'enabled': os.getenv('LIMIT_ORDER_ENABLED', 'true').lower() == 'true',  # 限价单开关 - true启用限价单，false只用市价单
                'maker_ratio': 0.5,  # 做市比例 - 50%概率使用限价单
                'confidence_threshold': 0.8,  # 信心阈值 - AI信心高于80%才使用限价单
                'price_buffer': 0.001,  # 价格缓冲 - 限价单价格偏移0.1%
                'timeout': 30,  # 超时时间 - 限价单30秒未成交转为市价单
                'retry_limit': 3  # 重试次数 - 限价单最多重试3次
            },
            'price_crash_protection': {
                'enabled': True,  # 暴跌保护开关 - true启用价格暴跌保护机制
                'crash_threshold_critical': 0.05,  # 暴跌阈值-严重 - 5%暴跌触发紧急保护
                'crash_threshold_high': 0.03,  # 暴跌阈值-高 - 3%暴跌触发高级保护
                'crash_threshold_medium': 0.02,  # 暴跌阈值-中 - 2%暴跌触发中级保护
                'crash_threshold_low': 0.01,  # 暴跌阈值-低 - 1%暴跌触发低级保护
                'volume_spike_threshold': 3.0,  # 成交量激增阈值 - 成交量突增3倍触发监控
                'volatility_spike_threshold': 2.5,  # 波动率激增阈值 - 波动率突增2.5倍触发监控
                'orderbook_imbalance_threshold': 0.7,  # 订单簿失衡阈值 - 买卖盘比例超过70%触发监控
                'cascade_risk_threshold': 0.8,  # 连锁风险阈值 - 风险系数超过0.8触发保护
                'action_delay': 5,  # 行动延迟 - 检测到暴跌后5秒执行保护动作
                'cooldown_period': 300,  # 冷却期 - 暴跌保护触发后300秒内不再重复触发
                'immediate_close_threshold': 0.08,  # 立即平仓阈值 - 8%暴跌立即平仓所有仓位
                'tighten_stop_threshold': 0.04,  # 收紧止损阈值 - 4%暴跌收紧止损位
                'enhanced_monitor_threshold': 0.02,  # 增强监控阈值 - 2%暴跌进入增强监控模式
                'stop_sl_update_on_crash': True  # 暴跌时停止止损更新 - 防止止损被触发
            }
        }
    
    def _load_risk_config(self) -> Dict[str, Any]:
        """风险控制配置 - 管理整体风险暴露
        
        配置风险管理相关的参数，包括止损、止盈、追踪止损等
        
        Returns:
            Dict[str, Any]: 风险控制配置字典
        """
        return {
            'max_daily_loss': float(os.getenv('MAX_DAILY_LOSS', '100')),  # 最大日亏损 - 每日最多亏损100 USDT
            'max_position_risk': float(os.getenv('MAX_POSITION_RISK', '0.05')),  # 最大仓位风险 - 单笔交易风险不超过5%
            'stop_loss_enabled': True,  # 止损开关 - true启用自动止损
            'take_profit_enabled': True,  # 止盈开关 - true启用自动止盈
            'trailing_stop': {
                'enabled': True,  # 追踪止损开关 - true启用移动止损
                'breakeven_at': 0.01,  # 保本触发点 - 盈利1%时将止损移至成本价
                'lock_profit_at': 0.03,  # 利润锁定点 - 盈利3%时锁定部分利润
                'trailing_distance': 0.015  # 追踪距离 - 止损价距离最高价1.5%
            }
        }
    
    def _load_ai_config(self) -> Dict[str, Any]:
        """AI配置 - 人工智能信号生成相关设置
        
        配置AI信号生成相关的参数，包括API密钥、超时设置、缓存等
        
        Returns:
            Dict[str, Any]: AI配置字典
        """
        # 安全加载AI配置，提供完整的回退机制
        try:
            use_multi_ai = os.getenv('USE_MULTI_AI', 'false').lower() == 'true'
            cache_duration = int(os.getenv('AI_CACHE_DURATION', '900'))
            timeout = int(os.getenv('AI_TIMEOUT', '30'))
            max_retries = int(os.getenv('AI_MAX_RETRIES', '2'))
            min_confidence = float(os.getenv('AI_MIN_CONFIDENCE', '0.5'))
            ai_provider = os.getenv('AI_PROVIDER', 'kimi')
            fusion_providers = os.getenv('AI_FUSION_PROVIDERS', 'deepseek,kimi')
            
            # 获取API密钥，确保安全性
            models = {
                'kimi': os.getenv('KIMI_API_KEY'),
                'deepseek': os.getenv('DEEPSEEK_API_KEY'),
                'qwen': os.getenv('QWEN_API_KEY'),
                'openai': os.getenv('OPENAI_API_KEY')
            }
            
            # 过滤掉空的API密钥
            valid_models = {k: v for k, v in models.items() if v and v.strip()}
            
            if not valid_models:
                log_warning("⚠️ 未配置任何AI API密钥，AI功能将使用回退模式")
            
            return {
                'use_multi_ai': use_multi_ai,
                'cache_duration': cache_duration,
                'timeout': timeout,
                'max_retries': max_retries,
                'min_confidence_threshold': min_confidence,
                'ai_provider': ai_provider,
                'ai_fusion_providers': fusion_providers,
                'models': valid_models,
                'fallback_enabled': os.getenv('AI_FALLBACK_ENABLED', 'true').lower() == 'true',
                'similarity_threshold': float(os.getenv('AI_SIMILARITY_THRESHOLD', '0.8')),
                'cache_levels': {
                    'memory': True,
                    'price_bucket': True,
                    'pattern': True
                }
            }
        except Exception as e:
            log_error(f"AI配置加载失败: {e}")
            # 提供完整的回退配置
            return {
                'use_multi_ai': False,
                'cache_duration': 900,
                'timeout': 30,
                'max_retries': 2,
                'min_confidence_threshold': 0.5,
                'ai_provider': 'kimi',
                'ai_fusion_providers': 'deepseek,kimi',
                'models': {},
                'fallback_enabled': True,
                'similarity_threshold': 0.8,
                'cache_levels': {
                    'memory': True,
                    'price_bucket': True,
                    'pattern': True
                }
            }
    
    def _load_system_config(self) -> Dict[str, Any]:
        """系统配置 - 系统运行和监控相关设置
        
        配置系统运行相关的参数，包括日志级别、监控设置、Web界面等
        
        Returns:
            Dict[str, Any]: 系统配置字典
        """
        return {
            'max_history_length': 100,  # 最大历史长度 - 保留最近100条历史记录
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),  # 日志级别 - DEBUG/INFO/WARNING/ERROR
            'monitoring_enabled': True,  # 监控开关 - true启用系统监控
            'memory_cleanup_interval': 3600,  # 内存清理间隔 - 每小时清理一次内存
            'heartbeat_interval': 60,  # 心跳间隔 - 每60秒发送一次心跳信号
            'web_interface': {
                'enabled': os.getenv('WEB_ENABLED', 'false').lower() == 'true',  # Web界面开关 - true启用Streamlit监控界面
                'port': int(os.getenv('WEB_PORT', '8501'))  # Web端口 - Streamlit监控界面端口8501
            },
            'version_preference': {
                'prefer_new_version': os.getenv('USE_NEW_VERSION', 'true').lower() == 'true'  # 版本偏好 - true优先使用新版本
            }
        }
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """获取配置值
        
        获取指定配置段中的配置值
        
        Args:
            section: 配置段名称
            key: 配置键名称，如果为None则返回整个配置段
            default: 默认值，如果配置不存在则返回此值
            
        Returns:
            Any: 配置值或默认值
        """
        if key is None:
            return self._config.get(section, {})
        return self._config.get(section, {}).get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置
        
        获取完整的配置字典
        
        Returns:
            Dict[str, Any]: 所有配置
        """
        return self._config

    def _validate_config(self) -> ConfigValidationResult:
        """验证配置完整性
        
        验证所有必需的配置项是否存在且有效
        
        Returns:
            ConfigValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 验证交易所配置
        exchange_config = self._config.get('exchange', {})
        required_exchange_keys = ['api_key', 'secret', 'password']
        for key in required_exchange_keys:
            if not exchange_config.get(key):
                errors.append(f"交易所配置缺少必需项: {key}")
        
        # 验证交易配置
        trading_config = self._config.get('trading', {})
        if trading_config.get('max_position_size', 0) <= 0:
            errors.append("交易配置: 最大仓位大小必须大于0")
        
        if trading_config.get('leverage', 0) <= 0:
            errors.append("交易配置: 杠杆倍数必须大于0")
        
        # 验证AI配置
        ai_config = self._config.get('ai', {})
        if not ai_config.get('models'):
            warnings.append("AI配置: 未配置任何AI模型，将使用回退模式")
        
        # 验证策略配置
        strategies_config = self._config.get('strategies', {})
        if not strategies_config.get('profit_lock_strategy', {}).get('enabled', False):
            warnings.append("策略配置: 横盘利润锁定策略未启用")
        
        return ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """更新配置值
        
        在运行时更新配置值
        
        Args:
            section: 配置段名称
            key: 配置键名称
            value: 新的配置值
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if section in self._config:
                self._config[section][key] = value
                log_info(f"配置更新成功: {section}.{key} = {value}")
                return True
            else:
                log_warning(f"配置段不存在: {section}")
                return False
        except Exception as e:
            log_error(f"配置更新失败: {e}")
            return False
    
    def get_validation_status(self) -> ConfigValidationResult:
        """获取配置验证状态
        
        Returns:
            ConfigValidationResult: 配置验证结果
        """
        return self._validation_result

# 全局配置实例
config = ConfigManager()
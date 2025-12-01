"""
Alpha Arena OKX 配置管理模块
将所有配置项集中管理，实现配置与业务逻辑的完全分离
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class ConfigManager:
    """配置管理器 - 统一管理所有配置"""
    
    def __init__(self):
        self._config = self._load_all_config()
    
    def _load_all_config(self) -> Dict[str, Any]:
        """加载所有配置"""
        return {
            'exchange': self._load_exchange_config(),
            'trading': self._load_trading_config(),
            'strategies': self._load_strategy_config(),
            'risk': self._load_risk_config(),
            'ai': self._load_ai_config(),
            'system': self._load_system_config()
        }
    
    def _load_exchange_config(self) -> Dict[str, Any]:
        """交易所配置"""
        return {
            'exchange': 'okx',
            'api_key': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_SECRET'),
            'password': os.getenv('OKX_PASSWORD'),
            'sandbox': os.getenv('OKX_SANDBOX', 'false').lower() == 'true',
            'symbol': 'BTC/USDT:USDT',
            'timeframe': '5m',
            'contract_size': 0.01
        }
    
    def _load_trading_config(self) -> Dict[str, Any]:
        """交易配置"""
        return {
            'test_mode': os.getenv('TEST_MODE', 'true').lower() == 'true',
            'max_position_size': float(os.getenv('MAX_POSITION_SIZE', '0.01')),
            'min_trade_amount': float(os.getenv('MIN_TRADE_AMOUNT', '0.001')),
            'leverage': int(os.getenv('LEVERAGE', '10')),
            'margin_mode': 'cross',
            'position_mode': 'one_way',
            'allow_short_selling': os.getenv('ALLOW_SHORT_SELLING', 'false').lower() == 'true'
        }
    
    def _load_strategy_config(self) -> Dict[str, Any]:
        """策略配置"""
        return {
            'profit_lock_strategy': {
                'enabled': True,
                'min_profit_pct': 0.005,
                'consolidation_threshold': 0.008,
                'lookback_periods': 6,
                'consolidation_duration': 20,
                'only_long_positions': True,
                'volatility_adaptive': True,
                'min_volume_threshold': 1000000,
                'max_consecutive_periods': 8,
                'breakout_threshold': 0.012,
                'time_decay_factor': 0.95,
                'volume_weight': 0.3
            },
            'smart_tp_sl': {
                'enabled': True,
                'base_sl_pct': 0.02,
                'base_tp_pct': 0.06,
                'adaptive_mode': True,
                'high_vol_multiplier': 1.5,
                'low_vol_multiplier': 0.8,
                'trend_strength_weight': 0.4,
                'volume_weight': 0.3,
                'time_weight': 0.2,
                'confidence_weight': 0.1,
                'max_sl_pct': 0.05,
                'max_tp_pct': 0.15,
                'min_sl_pct': 0.01,
                'min_tp_pct': 0.03
            },
            'limit_order': {
                'enabled': os.getenv('LIMIT_ORDER_ENABLED', 'true').lower() == 'true',
                'maker_ratio': 0.5,
                'confidence_threshold': 0.8,
                'price_buffer': 0.001,
                'timeout': 30,
                'retry_limit': 3
            },
            'price_crash_protection': {
                'enabled': True,
                'crash_threshold_critical': 0.05,
                'crash_threshold_high': 0.03,
                'crash_threshold_medium': 0.02,
                'crash_threshold_low': 0.01,
                'volume_spike_threshold': 3.0,
                'volatility_spike_threshold': 2.5,
                'orderbook_imbalance_threshold': 0.7,
                'cascade_risk_threshold': 0.8,
                'action_delay': 5,
                'cooldown_period': 300,
                'immediate_close_threshold': 0.08,
                'tighten_stop_threshold': 0.04,
                'enhanced_monitor_threshold': 0.02,
                'stop_sl_update_on_crash': True
            }
        }
    
    def _load_risk_config(self) -> Dict[str, Any]:
        """风险控制配置"""
        return {
            'max_daily_loss': float(os.getenv('MAX_DAILY_LOSS', '100')),
            'max_position_risk': float(os.getenv('MAX_POSITION_RISK', '0.05')),
            'stop_loss_enabled': True,
            'take_profit_enabled': True,
            'trailing_stop': {
                'enabled': True,
                'breakeven_at': 0.01,
                'lock_profit_at': 0.03,
                'trailing_distance': 0.015
            }
        }
    
    def _load_ai_config(self) -> Dict[str, Any]:
        """AI配置"""
        return {
            'use_multi_ai': os.getenv('USE_MULTI_AI', 'false').lower() == 'true',
            'cache_duration': int(os.getenv('AI_CACHE_DURATION', '900')),
            'timeout': int(os.getenv('AI_TIMEOUT', '30')),
            'max_retries': int(os.getenv('AI_MAX_RETRIES', '2')),
            'min_confidence_threshold': float(os.getenv('AI_MIN_CONFIDENCE', '0.5')),
            'models': {
                'kimi': os.getenv('KIMI_API_KEY'),
                'deepseek': os.getenv('DEEPSEEK_API_KEY'),
                'openai': os.getenv('OPENAI_API_KEY')
            },
            'fallback_enabled': os.getenv('AI_FALLBACK_ENABLED', 'true').lower() == 'true',
            'similarity_threshold': float(os.getenv('AI_SIMILARITY_THRESHOLD', '0.8')),
            'cache_levels': {
                'memory': True,
                'price_bucket': True,
                'pattern': True
            }
        }
    
    def _load_system_config(self) -> Dict[str, Any]:
        """系统配置"""
        return {
            'max_history_length': 100,
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'monitoring_enabled': True,
            'memory_cleanup_interval': 3600,
            'heartbeat_interval': 60,
            'web_interface': {
                'enabled': os.getenv('WEB_ENABLED', 'false').lower() == 'true',
                'port': int(os.getenv('WEB_PORT', '8501'))
            },
            'version_preference': {
                'prefer_new_version': os.getenv('USE_NEW_VERSION', 'true').lower() == 'true'
            }
        }
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """获取配置值"""
        if key is None:
            return self._config.get(section, {})
        return self._config.get(section, {}).get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config

# 全局配置实例
config = ConfigManager()
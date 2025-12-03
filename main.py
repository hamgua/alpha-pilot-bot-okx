"""
Alpha Arena OKX - 重构版主程序
基于模块化架构的OKX自动交易系统
"""

import time
import threading
import json
import numpy as np
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# 导入模块
import logging
from config import config
from trading import trading_engine
from strategies import (
    market_analyzer, risk_manager, signal_processor, 
    consolidation_detector, crash_protection, EnhancedSignalProcessor
)
from utils import (
    cache_manager, memory_manager, system_monitor, 
    data_validator, json_helper, time_helper, logger_helper,
    LoggerConfig, TradeLogger, DataManager, save_trade_record
)
from ai_client import ai_client
# signal_executor模块已整合到strategies.py中
import asyncio

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'logs/alpha-pilot-bot-okx-{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
log_info = logging.getLogger('alpha_arena').info
log_warning = logging.getLogger('alpha_arena').warning
log_error = logging.getLogger('alpha_arena').error

class AlphaArenaBot:
    """Alpha Arena OKX 交易机器人主类"""
    
    def __init__(self):
        self.is_running = False
        self.current_cycle = 0
        self.last_signal = None
        self.price_history = []
        self.signal_cache = {}
        self.data_manager = DataManager()
        
        log_info("🚀 Alpha Arena OKX 交易机器人初始化中...")
        self._display_startup_info()
        
        # 初始化数据管理
        self._initialize_data_management()
    
    def _display_startup_info(self):
        """显示启动信息"""
        log_info("=" * 60)
        log_info("🎯 Alpha Arena OKX 自动交易系统 v2.0")
        log_info("=" * 60)
        log_info("📊 系统特性:")
        log_info("   • 模块化架构设计")
        log_info("   • 配置与逻辑分离")
        log_info("   • 智能风险管理")
        log_info("   • AI信号增强")
        log_info("   • 内存优化管理")
        log_info("   • 数据管理系统")
        log_info("=" * 60)
        
        # 显示配置信息
        log_info(f"🔄 交易模式: {'模拟交易' if config.get('trading', 'test_mode') else '实盘交易'}")
        log_info(f"📈 交易对: {config.get('exchange', 'symbol')}")
        log_info(f"⏰ 时间框架: {config.get('exchange', 'timeframe')}")
        log_info(f"🔧 杠杆倍数: {config.get('trading', 'leverage')}x")
        log_info(f"🤖 AI模式: {'多模型' if config.get('ai', 'use_multi_ai') else '单模型'}")
        
        # 显示智能仓位配置
        if config.get('position_management', 'enable_intelligent_position'):
            log_info("📊 智能仓位管理: 已启用")
            log_info(f"   • 基础仓位: {config.get('position_management', 'base_usdt_amount')} USDT")
            log_info(f"   • 最大仓位比例: {config.get('position_management', 'max_position_ratio')}%")
        else:
            log_info("📊 智能仓位管理: 已禁用")
            
        # 显示做空配置
        if config.get('trading', 'allow_short_selling'):
            log_info("📉 做空功能: 已启用")
        else:
            log_info("📈 做空功能: 已禁用")
            
        log_info("=" * 60)

    def _initialize_data_management(self):
        """初始化数据管理"""
        try:
            log_info("📊 初始化数据管理系统...")
            
            # 获取数据摘要
            summary = self.data_manager.get_data_summary()
            log_info(f"📊 数据管理摘要:")
            for key, info in summary.items():
                log_info(f"   • {key}: {info['total_records']} 条记录")
            
            # 清理旧数据（保留最近30天）
            self.data_manager.cleanup_old_data(days_to_keep=30)
            log_info("📊 数据清理完成")
            
        except Exception as e:
            log_error(f"数据管理初始化失败: {e}")
    
    def get_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取AI交易信号（增强版）"""
        try:
            # 使用线程安全的方式运行异步函数
            import threading
            import nest_asyncio
            
            # 应用nest_asyncio以允许嵌套事件循环
            try:
                nest_asyncio.apply()
            except:
                pass  # 如果已应用则忽略
            
            # 使用线程池执行异步函数
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._get_ai_signal_async(market_data))
                )
                return future.result(timeout=30)
                
        except Exception as e:
            log_error(f"AI信号获取失败: {type(e).__name__}: {e}")
            import traceback
            log_error(f"AI信号获取堆栈:\n{traceback.format_exc()}")
            return self._get_fallback_signal_sync(market_data)
    
    async def _get_ai_signal_async(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """异步获取AI交易信号"""
        # 增强的缓存键 - 包含更多市场特征
        cache_key = self._generate_cache_key(market_data)
        
        # 检查多层缓存
        cached_signal = await self._get_cached_signal(cache_key)
        if cached_signal:
            log_info("📊 使用缓存的AI信号")
            return cached_signal
        
        # 生成新信号
        log_info("📊 获取新的AI信号...")
        try:
            signal_data = await self._generate_enhanced_ai_signal(market_data)
            
            # 增强缓存 - 多层缓存
            await self._cache_signal(cache_key, signal_data)
            
            # 记录信号
            memory_manager.add_to_history('signals', signal_data)
            system_monitor.increment_counter('api_calls')
            
            return signal_data
            
        except Exception as e:
            log_error(f"AI信号生成失败: {e}")
            return await self._get_fallback_signal(market_data)
    
    def _generate_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI信号（增强版，模拟多AI融合）"""
        price = market_data['price']
        position = market_data['position']
        
        # 模拟多AI分析数据
        kmi_analysis = {
            'provider': 'Kimi',
            'rsi': 40.5,
            'trend': '强势下跌',
            'recent_candles': ['阳线', '阳线', '阳线'],
            'price_action': '震荡状态',
            'recommendation': '保持现有持仓不变，等待更明确的交易信号',
            'confidence': 0.75
        }
        
        deepseek_analysis = {
            'provider': 'Deepseek',
            'price_position': '区间中点(50.0%)',
            'macd_signal': 'bullish',
            'ma_trend': '强势下跌',
            'rsi_status': '正常区间(40.5)',
            'strategy': '震荡市策略',
            'recommendation': '在区间中点交易需要明确的信号，目前条件不满足',
            'confidence': 0.72
        }
        
        # 基础技术分析
        trend = self._analyze_simple_trend()
        volatility = self._calculate_recent_volatility()
        
        # 模拟融合分析
        if trend > 0.6 and volatility < 5.0:
            signal = 'BUY'
            confidence = 0.8
            kmi_reason = f"Kimi: 当前RSI为{kmi_analysis['rsi']}，处于中性区域，且市场趋势为{kmi_analysis['trend']}。最近3根15mK线均为阳线，但最后一根K线收盘价与当前价格相同，表明价格没有进一步上涨，市场可能处于{kmi_analysis['price_action']}。考虑到市场趋势和RSI指标，建议{kmi_analysis['recommendation']}。"
            deepseek_reason = f"Deepseek: 当前价格位于区间中点（{deepseek_analysis['price_position']}），且无明确反转信号。MACD虽为{deepseek_analysis['macd_signal']}，但均线状态显示{deepseek_analysis['ma_trend']}，形成矛盾。RSI {kmi_analysis['rsi']}处于正常区间，未提供超卖信号。根据{deepseek_analysis['strategy']}，在区间中点（40-60%）交易需要明确的信号，目前条件不满足。"
            fused_reason = f"{kmi_reason} | {deepseek_reason}"
        elif trend < -0.6 and volatility < 5.0:
            signal = 'SELL'
            confidence = 0.8
            kmi_reason = f"Kimi: 当前RSI为{kmi_analysis['rsi']}，显示超卖信号，且市场趋势为{kmi_analysis['trend']}。最近价格持续下跌，建议{kmi_analysis['recommendation']}。"
            deepseek_reason = f"Deepseek: 当前价格接近区间下沿，MACD显示{deepseek_analysis['macd_signal']}信号，建议{kmi_analysis['recommendation']}。"
            fused_reason = f"{kmi_reason} | {deepseek_reason}"
        else:
            signal = 'HOLD'
            confidence = 0.5
            kmi_reason = f"Kimi: 当前RSI为{kmi_analysis['rsi']}，市场趋势{kmi_analysis['trend']}，最近3根K线{kmi_analysis['recent_candles']}，建议{kmi_analysis['recommendation']}。"
            deepseek_reason = f"Deepseek: 当前处于{deepseek_analysis['price_position']}，{deepseek_analysis['strategy']}适用，{deepseek_analysis['recommendation']}。"
            fused_reason = f"{kmi_reason} | {deepseek_reason}"
        
        # 如果有持仓，考虑平仓逻辑
        if position and position.get('size', 0) > 0:
            entry_price = position.get('entry_price', 0)
            if entry_price > 0:
                profit_pct = (price - entry_price) / entry_price
                
                # 盈利保护
                if profit_pct > 0.12:  # 盈利超过5%
                    signal = 'SELL' if position['side'] == 'long' else 'BUY'
                    confidence = 0.9
                    kmi_reason = f"Kimi: 当前持仓盈利{profit_pct:.2%}，触发盈利保护机制，建议平仓锁定利润。"
                    deepseek_reason = f"Deepseek: 持仓盈利{profit_pct:.2%}，达到止盈阈值，建议执行盈利保护策略。"
                    fused_reason = f"{kmi_reason} | {deepseek_reason}"
                elif profit_pct < -0.02:  # 亏损超过2%
                    signal = 'SELL' if position['side'] == 'long' else 'BUY'
                    confidence = 0.7
                    kmi_reason = f"Kimi: 当前持仓亏损{profit_pct:.2%}，触发止损保护机制，建议及时止损。"
                    deepseek_reason = f"Deepseek: 持仓亏损{profit_pct:.2%}，达到风险阈值，建议执行止损策略。"
                    fused_reason = f"{kmi_reason} | {deepseek_reason}"
        
        # 构建详细的JSON返回
        ai_signal_data = {
            'signal': signal,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'ai_providers': {
                'kimi': kmi_analysis,
                'deepseek': deepseek_analysis
            },
            'fusion_analysis': {
                'final_signal': signal,
                'fusion_confidence': confidence,
                'fusion_reason': fused_reason,
                'market_context': {
                    'current_price': price,
                    'trend_strength': abs(trend),
                    'volatility_level': volatility
                }
            },
            'trend': trend,
            'volatility': volatility
        }
        
        # 输出AI原始数据明细格式
        log_info(f"🤖 Kimi回复: ```json\n{json.dumps({
            'signal': signal,
            'reason': kmi_reason,
            'confidence': 'HIGH' if kmi_analysis['confidence'] >= 0.8 else 'MEDIUM' if kmi_analysis['confidence'] >= 0.6 else 'LOW'
        }, ensure_ascii=False, indent=2)}\n```")
        log_info("✅ JSON解析成功: " + str({
            'signal': signal,
            'reason': kmi_reason,
            'confidence': 'HIGH' if kmi_analysis['confidence'] >= 0.8 else 'MEDIUM' if kmi_analysis['confidence'] >= 0.6 else 'LOW'
        }))
        
        log_info(f"🤖 Deepseek回复: ```json\n{json.dumps({
            'signal': signal,
            'reason': deepseek_reason,
            'confidence': 'HIGH' if deepseek_analysis['confidence'] >= 0.8 else 'MEDIUM' if deepseek_analysis['confidence'] >= 0.6 else 'LOW'
        }, ensure_ascii=False, indent=2)}\n```")
        log_info("✅ JSON解析成功: " + str({
            'signal': signal,
            'reason': deepseek_reason,
            'confidence': 'HIGH' if deepseek_analysis['confidence'] >= 0.8 else 'MEDIUM' if deepseek_analysis['confidence'] >= 0.6 else 'LOW'
        }))
        
        # 输出融合结果
        log_info("📊 【多AI融合信号分析】")
        log_info(f"   📈 最终信号: {signal}")
        log_info(f"   💡 融合信心: {'HIGH' if confidence >= 0.8 else 'MEDIUM' if confidence >= 0.6 else 'LOW'}")
        log_info(f"   📋 融合理由: {fused_reason}")
        
        return ai_signal_data
    
    def _analyze_simple_trend(self) -> float:
        """简单趋势分析"""
        if len(self.price_history) < 20:
            return 0.0
        
        recent = self.price_history[-20:]
        if len(recent) < 2:
            return 0.0
        
        # 简单线性回归斜率
        x = np.arange(len(recent))
        y = np.array(recent)
        slope = np.polyfit(x, y, 1)[0]
        
        # 标准化
        volatility = np.std(y)
        if volatility > 0:
            return slope / volatility
        return 0.0
    
    def _calculate_recent_volatility(self) -> float:
        """计算近期波动率"""
        if len(self.price_history) < 14:
            return 2.0
        
        recent = self.price_history[-14:]
        if len(recent) < 2:
            return 2.0
        
        returns = []
        for i in range(1, len(recent)):
            returns.append(abs(recent[i] - recent[i-1]) / recent[i-1])
        
        return np.mean(returns) * 100 if returns else 2.0
    
    def _create_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建回退信号"""
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'reason': 'AI信号生成失败，使用回退信号',
            'timestamp': datetime.now().isoformat(),
            'trend': 0.0,
            'volatility': 2.0
        }
    
    def _generate_cache_key(self, market_data: Dict[str, Any]) -> str:
        """生成增强的缓存键"""
        price = market_data.get('price', 0)
        volume = market_data.get('volume', 0)
        position = market_data.get('position', {})
        
        # 包含价格、成交量、持仓状态的特征组合
        position_hash = f"{position.get('side', 'none')}_{position.get('size', 0):.4f}" if position else "none_0"
        
        # 价格区间化（每0.1%为一个区间）
        price_bucket = int(price * 1000) / 1000
        
        # 成交量区间化
        volume_bucket = int(volume / 1000) * 1000 if volume > 0 else 0
        
        return f"signal_{price_bucket}_{volume_bucket}_{position_hash}"
    
    async def _get_cached_signal(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取多层缓存的信号"""
        # 第一层：内存缓存
        cached = cache_manager.get(cache_key)
        if cached and self._is_cache_valid(cached):
            return cached
        
        # 第二层：历史信号缓存（基于相似市场状态）
        similar_signal = await self._find_similar_market_state(cache_key)
        if similar_signal:
            return similar_signal
        
        return None
    
    def _is_cache_valid(self, cached_signal: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cached_signal:
            return False
        
        # 检查时间有效性
        signal_time = datetime.fromisoformat(cached_signal.get('timestamp', ''))
        age_seconds = (datetime.now() - signal_time).total_seconds()
        max_age = config.get('ai', 'cache_duration', 900)
        
        if age_seconds > max_age:
            return False
        
        # 检查市场状态是否发生重大变化
        recent_volatility = self._calculate_recent_volatility()
        if recent_volatility > 5.0:  # 波动率超过5%时刷新信号
            return False
        
        return True
    
    async def _find_similar_market_state(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """基于相似市场状态查找历史信号"""
        # 获取历史信号
        history = memory_manager.get_history('signals', limit=50)
        
        if not history:
            return None
        
        # 查找最近的有效信号
        for signal in reversed(history):
            signal_time = datetime.fromisoformat(signal.get('timestamp', ''))
            age_seconds = (datetime.now() - signal_time).total_seconds()
            
            # 只考虑2小时内的信号
            if age_seconds < 7200:
                # 检查信号质量
                if signal.get('confidence', 0) > 0.7:
                    return signal
        
        return None
    
    async def _cache_signal(self, cache_key: str, signal_data: Dict[str, Any]) -> None:
        """增强缓存信号"""
        # 主缓存
        cache_manager.set(cache_key, signal_data, config.get('ai', 'cache_duration'))
        
        # 额外缓存：基于价格区间的信号
        price_bucket_key = self._generate_price_bucket_key(signal_data)
        cache_manager.set(price_bucket_key, signal_data, config.get('ai', 'cache_duration') * 2)
    
    def _generate_price_bucket_key(self, signal_data: Dict[str, Any]) -> str:
        """基于价格区间的缓存键"""
        # 从信号数据中提取价格信息
        # 这里简化处理，实际应该存储价格信息
        return f"price_bucket_{int(time.time() / 300)}"  # 5分钟一个区间
    
    async def _generate_enhanced_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成增强的AI信号"""
        try:
            # 检查是否启用多AI模式
            use_multi_ai = config.get('ai', 'use_multi_ai')
            
            if use_multi_ai:
                return await self._generate_multi_ai_signal(market_data)
            else:
                return await self._generate_single_ai_signal(market_data)
                
        except Exception as e:
            log_error(f"增强AI信号生成失败: {e}")
            return await self._get_fallback_signal(market_data)
    
    async def _generate_multi_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成多AI融合信号"""
        # 从配置中获取AI_FUSION_PROVIDERS
        fusion_providers_str = config.get('ai', 'ai_fusion_providers', 'deepseek,kimi')
        providers = [p.strip() for p in fusion_providers_str.split(',')]
        
        # 过滤掉未配置的提供商（基于实际可用的API密钥）
        available_providers = [p for p in providers if p in ai_client.providers]
        
        if not available_providers:
            log_warning("没有可用的AI提供商，使用回退信号")
            return await self._get_fallback_signal(market_data)
        
        log_info(f"使用AI提供商: {available_providers} (配置: {fusion_providers_str})")
        
        # 获取信号，设置超时
        try:
            signals = await asyncio.wait_for(
                ai_client.get_multi_ai_signals(market_data, available_providers),
                timeout=30.0
            )
            
            if signals:
                signal_data = ai_client.fuse_signals(signals)
                log_info("📊 【多AI融合信号分析】")
                log_info(f"   📈 最终信号: {signal_data['signal']}")
                log_info(f"   💡 融合信心: {signal_data['confidence']:.1f}")
                
                # 保存AI信号到数据管理系统
                self.data_manager.save_ai_signal(signal_data)
                
                return signal_data
            else:
                log_warning("多AI信号获取失败，使用回退信号")
                return await self._get_fallback_signal(market_data)
                
        except asyncio.TimeoutError:
            log_warning("多AI信号获取超时，使用回退信号")
            return await self._get_fallback_signal(market_data)
    
    async def _generate_single_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成单AI信号"""
        # 从配置中获取AI_PROVIDER
        single_provider = config.get('ai', 'ai_provider', 'kimi')
        
        # 检查该提供商是否可用
        if single_provider not in ai_client.providers:
            log_warning(f"配置的AI提供商 {single_provider} 不可用，使用回退信号")
            return await self._get_fallback_signal(market_data)
        
        log_info(f"使用单AI提供商: {single_provider}")
        
        try:
            # 获取单AI信号
            signal = await ai_client.get_ai_signal(market_data, single_provider)
            if signal:
                # 包装成标准格式
                signal_data = {
                    'signal': signal.signal,
                    'confidence': signal.confidence,
                    'reason': signal.reason,
                    'timestamp': signal.timestamp,
                    'provider': single_provider,
                    'single_ai_mode': True
                }
                
                # 保存AI信号到数据管理系统
                self.data_manager.save_ai_signal(signal_data)
                
                return signal_data
            else:
                log_warning(f"单AI信号获取失败，使用回退信号")
                return await self._get_fallback_signal(market_data)
                
        except Exception as e:
            log_error(f"单AI信号生成失败: {e}")
            return await self._get_fallback_signal(market_data)
    
    async def _get_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取回退信号（增强版）"""
        return self._get_fallback_signal_sync(market_data)
        
    def _get_fallback_signal_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取同步回退信号（增强版）"""
        # 检查是否有历史信号可用
        history = memory_manager.get_history('signals', limit=10)
        
        if history:
            # 使用最近的有效信号，降低信心
            last_signal = history[-1]
            fallback_signal = last_signal.copy()
            fallback_signal['confidence'] = max(0.3, fallback_signal.get('confidence', 0.5) * 0.7)
            fallback_signal['reason'] = f"回退信号: {fallback_signal.get('reason', '历史信号')}"
            fallback_signal['timestamp'] = datetime.now().isoformat()
            return fallback_signal
        
        # 最终回退：基于简单技术分析
        return self._create_fallback_signal(market_data)
    
    def _should_refresh_signal(self) -> bool:
        """判断是否需要刷新信号"""
        # 简化逻辑：每15分钟或信号变化时刷新
        if not self.last_signal:
            return True
        
        # 检查时间间隔
        signal_age = time.time() - self.last_signal.get('timestamp', 0)
        return signal_age > config.get('ai', 'cache_duration')
    
    def analyze_market_state(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场状态"""
        try:
            # 验证输入参数
            if not market_data or not isinstance(market_data, dict):
                return {}
                
            # 更新价格历史
            self.price_history.append(market_data['price'])
            if len(self.price_history) > 100:
                self.price_history.pop(0)

            # 获取完整的价格历史数据用于分析
            price_history = self._get_price_history_for_analysis()

            # 更新暴跌保护系统的价格历史
            crash_protection.price_history = self.price_history[-20:]  # 保留最近20个价格

            # 使用真实的历史数据计算技术指标
            try:
                closes = price_history.get('close', [])
                highs = price_history.get('high', [])
                lows = price_history.get('low', [])
                
                if len(closes) >= 14 and len(highs) >= 14 and len(lows) >= 14:
                    # 使用真实的OHLCV数据计算ATR
                    atr_pct = market_analyzer.calculate_atr(highs, lows, closes, 14)
                    if atr_pct is None or atr_pct <= 0:
                        # 计算失败，使用简化计算
                        if len(closes) >= 2:
                            price_changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
                            atr_pct = np.mean(price_changes) / closes[-1] * 100 if closes[-1] > 0 else 0.5
                        else:
                            atr_pct = 0.5  # 默认值
                else:
                    # 数据不足，使用简化计算
                    if len(closes) >= 2:
                        price_changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
                        atr_pct = np.mean(price_changes) / closes[-1] * 100 if closes[-1] > 0 else 0.5
                    else:
                        atr_pct = 0.5  # 默认值
                        
            except Exception as e:
                log_warning(f"ATR计算失败，使用默认值: {e}")
                atr_pct = 0.5

            # 识别趋势 - 使用收盘价数据
            closes_for_trend = price_history.get('close', self.price_history)
            trend_strength = market_analyzer.identify_trend(closes_for_trend)

            # 波动率分类
            if atr_pct > 3.0:
                volatility = 'high'
            elif atr_pct < 1.0:
                volatility = 'low'
            else:
                volatility = 'normal'

            # 使用主计算逻辑的价格变化率，避免重复计算
            # 主计算逻辑已在execute_trading_cycle中正确计算price_change_pct
            # 这里从market_data中获取已计算好的值
            price_change_pct = market_data.get('price_change_pct', 0)

            # 检查横盘利润锁定
            should_lock_profit = False
            position = market_data.get('position')
            if position and isinstance(position, dict):
                try:
                    should_lock_profit = consolidation_detector.should_lock_profit(
                        position, market_data, self.price_history
                    )
                except Exception:
                    should_lock_profit = False

            # 检查暴跌保护
            try:
                crash_protection_decision = crash_protection.should_trigger_crash_protection(
                    market_data['price'], market_data, position
                )
            except Exception:
                crash_protection_decision = {'should_protect': False, 'reason': '检查异常'}

            return {
                'atr_pct': atr_pct,
                'trend_strength': trend_strength,
                'volatility': volatility,
                'price': market_data['price'],
                'bid': market_data['bid'],
                'ask': market_data['ask'],
                'price_change_pct': price_change_pct,
                'should_lock_profit': should_lock_profit,
                'crash_protection': crash_protection_decision
            }
        except Exception:
            return {
                'atr_pct': 2.0,
                'trend_strength': 0.5,
                'volatility': 'normal',
                'price': market_data.get('price', 0),
                'bid': market_data.get('bid', 0),
                'ask': market_data.get('ask', 0),
                'price_change_pct': 0,
                'should_lock_profit': False,
                'crash_protection': {'should_protect': False, 'reason': '分析异常'}
            }
    
    def execute_trading_cycle(self):
        """执行交易周期"""
        try:
            self.current_cycle += 1
            log_info(f"{'='*60}")
            log_info(f"🔄 第 {self.current_cycle} 轮交易周期开始")
            log_info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_info(f"{'='*60}")
            
            # 1. 获取市场数据
            log_info("📊 获取市场数据...")
            market_data = trading_engine.get_market_data()
            
            if not market_data or not market_data.get('price'):
                log_error("获取市场数据失败")
                return
            
            current_price = market_data.get('price', 0)
            
            # 获取配置中的循环时间（支持自定义到整点执行）
            cycle_minutes = config.get('trading', 'cycle_minutes', 15)
            cycle_time = f"{cycle_minutes}m"
            
            # 使用真实K线数据计算价格变化
            price_history = market_data.get('price_history', [])
            if len(price_history) >= 2:
                # 使用上一个完整K线的收盘价作为基准
                try:
                    previous_kline = price_history[-2]
                    previous_price = float(previous_kline.get('close', current_price))
                    
                    # 确保价格有效
                    if previous_price > 0 and current_price > 0:
                        price_change_pct = ((current_price - previous_price) / previous_price) * 100
                        
                        # 获取K线时间戳用于显示周期
                        kline_time = datetime.fromtimestamp(previous_kline.get('timestamp', 0)/1000)
                        log_info(f"上一个K线时间: {kline_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        price_change_pct = 0.0
                        log_info("⚠️ 价格数据无效，使用0.00%")
                        
                except (ValueError, TypeError) as e:
                    price_change_pct = 0.0
                    log_info(f"⚠️ 价格计算异常: {e}")
            else:
                # 尝试使用更近期的数据
                if len(price_history) >= 1:
                    try:
                        last_kline = price_history[-1]
                        last_price = float(last_kline.get('close', current_price))
                        if last_price > 0 and current_price > 0:
                            price_change_pct = ((current_price - last_price) / last_price) * 100
                        else:
                            price_change_pct = 0.0
                    except (ValueError, TypeError):
                        price_change_pct = 0.0
                else:
                    price_change_pct = 0.0
                    log_info("⚠️ 历史数据不足，价格变化显示为0.00%")
            
            log_info(f"BTC当前价格: ${current_price:,.2f}")
            log_info(f"数据周期: {cycle_time}")
            
            # 更智能的价格变化显示
            if abs(price_change_pct) < 0.01 and len(price_history) < 2:
                log_info(f"价格变化: 初始化数据中...")
            else:
                log_info(f"价格变化: {price_change_pct:+.2f}% (基于上一个{cycle_time}周期K线)")
            
            # 2. 分析市场状态
            log_info("🔍 分析市场状态...")
            # 将计算好的价格变化率传递给市场状态分析
            market_data['price_change_pct'] = price_change_pct
            market_state = self.analyze_market_state(market_data)
            
            # 详细市场状态日志
            log_info(f"📊 市场状态分析:")
            log_info(f"   - ATR波动率: {market_state.get('atr_pct', 0):.2f}%")
            log_info(f"   - 趋势强度: {market_state.get('trend_strength', '未知')}")
            log_info(f"   - 波动率级别: {market_state.get('volatility', 'normal')}")
            log_info(f"   - 价格变化: {market_state.get('price_change_pct', 0):.2f}%")
            
            # 保存市场数据到数据管理系统
            try:
                self.data_manager.save_market_data({
                    'price': market_data.get('price', 0),
                    'bid': market_data.get('bid', 0),
                    'ask': market_data.get('ask', 0),
                    'volume': market_data.get('volume', 0),
                    'high': market_data.get('high', 0),
                    'low': market_data.get('low', 0),
                    'market_state': market_state
                })
                log_info("✅ 市场数据已保存")
            except Exception as e:
                log_error(f"保存市场数据失败: {e}")
            
            # 3. 获取AI信号
            try:
                signal_data = self.get_ai_signal({**market_data, **market_state})
                log_info(f"🤖 AI信号: {signal_data.get('signal', 'HOLD')} (信心: {signal_data.get('confidence', 'LOW')})")
                
                # 使用多AI融合的详细理由
                fusion_reason = signal_data.get('fusion_analysis', {}).get('fusion_reason', '')
                if fusion_reason:
                    log_info(f"💡 AI理由: {fusion_reason}")
                else:
                    log_info(f"💡 AI理由: {signal_data.get('reason', '无')}")
                
                # 保存AI信号到历史记录（用于横盘检测）
                memory_manager.add_to_history('signals', {
                    'signal': signal_data.get('signal', 'HOLD'),
                    'confidence': signal_data.get('confidence', 0.5),
                    'timestamp': datetime.now().isoformat(),
                    'reason': signal_data.get('reason', '')
                })
                
            except Exception as e:
                log_error(f"获取AI信号失败: {e}")
                return
            
            # 4. 初始化信号处理器
            signal_processor = EnhancedSignalProcessor(trading_engine)
            
            # 5. 处理信号并执行交易决策
            log_info("🔍 处理交易信号...")
            try:
                success = signal_processor.process_signal(signal_data, market_data)
                if success:
                    log_info("✅ 信号执行完成")
                else:
                    log_warning("⚠️ 信号执行未完成或无需执行")
            except Exception as e:
                log_error(f"执行交易决策失败: {e}")
                return
            
            # 6. 检查持仓止盈止损状态
            log_info("🔍 检查持仓止盈止损状态...")
            try:
                self._update_risk_management(market_data, market_state)
            except Exception as e:
                log_error(f"更新风险管理失败: {e}")
            
            # 7. 检查横盘利润锁定
            try:
                self._check_consolidation_profit_lock(market_data)
                
                # 记录横盘状态监控信息
                consolidation_status = consolidation_detector.get_consolidation_status()
                if consolidation_status['is_active']:
                    log_info(f"📊 横盘状态监控：")
                    log_info(f"   激活状态：{'✅ 已激活' if consolidation_status['is_active'] else '❌ 未激活'}")
                    log_info(f"   持续时间：{consolidation_status['duration_minutes']:.1f}分钟")
                    log_info(f"   部分平仓：{'✅ 已执行' if consolidation_status['partial_close_done'] else '❌ 未执行'}")
                    
            except Exception as e:
                log_error(f"检查横盘利润锁定失败: {e}")
            
            # 8. 系统维护（始终执行）
            log_info("🔧 执行系统维护...")
            try:
                self._perform_system_maintenance()
            except Exception as e:
                log_error(f"系统维护失败: {e}")
            
            log_info(f"{'='*60}")
            log_info(f"✅ 第 {self.current_cycle} 轮交易周期完成")
            log_info(f"{'='*60}")
            
        except Exception as e:
            log_error(f"交易周期异常: {e}")
            system_monitor.increment_counter('errors')
            
            # 保存错误日志到数据管理系统
            try:
                self.data_manager.save_system_log({
                    'level': 'ERROR',
                    'message': str(e),
                    'context': 'trading_cycle',
                    'cycle': self.current_cycle
                })
            except Exception:
                pass
    
    def _execute_trade_signal(self, signal: str, signal_data: Dict[str, Any], 
                            market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """执行交易信号 - 使用增强型信号处理器"""
        try:
            # 使用增强型信号处理器
            from strategies import EnhancedSignalProcessor
            processor = EnhancedSignalProcessor(trading_engine)
            
            # 执行完整的交易逻辑
            success = processor.process_signal(signal_data, market_data)
            
            if success:
                log_info("✅ 增强型交易执行成功")
                # 记录交易日志
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'signal': signal,
                    'price': market_data['price'],
                    'reason': signal_data.get('reason', '策略信号'),
                    'market_state': market_state
                }
                self.data_manager.save_trade_log(trade_record)
            else:
                log_error("❌ 增强型交易执行失败")
                
        except Exception as e:
            log_error(f"增强型交易执行异常: {e}")
            # 回退到简化执行逻辑
            log_info("⚠️ 回退到简化执行逻辑")
            self._simplified_execute_trade_signal(signal, signal_data, market_data, market_state)

    def _simplified_execute_trade_signal(self, signal: str, signal_data: Dict[str, Any], 
                                     market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """简化执行逻辑 - 作为回退"""
        log_info(f"🎯 简化执行交易信号: {signal}")
        
        current_price = market_data['price']
        position = market_data.get('position')
        
        # 使用信号处理器处理
        processed_signal = signal_processor.process_signal(signal_data, position)
        if processed_signal == 'HOLD':
            log_info("📊 保持持仓，跳过交易")
            return
        
        # 计算订单大小
        order_size = signal_processor.calculate_order_size(
            market_data['balance'], processed_signal, current_price
        )
        
        if order_size <= 0:
            log_warning("⚠️ 订单大小为0，跳过交易")
            return
        
        # 计算止盈止损
        tp_sl_params = risk_manager.calculate_dynamic_tp_sl(
            processed_signal, current_price, market_state, position
        )
        
        # 执行交易
        success = trading_engine.execute_trade_with_tp_sl(
            processed_signal, order_size, tp_sl_params['stop_loss'], tp_sl_params['take_profit']
        )
        
        if success:
            log_info("✅ 简化执行成功")
        else:
            log_error("❌ 简化执行失败")

    def _update_risk_management(self, market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """更新风险管理"""
        position = market_data.get('position')
        if not position or position.get('size', 0) <= 0:
            log_info("📭 当前无持仓，跳过风险管理更新")
            return
        
        log_info("📊 检测到持仓，开始风险管理检查...")
        
        # 获取详细持仓信息
        current_position = trading_engine.get_position_info()
        if not current_position['has_position']:
            log_warning("⚠️ 持仓信息不一致，跳过风险管理")
            return
        
        current_price = market_data['price']
        entry_price = current_position['entry_price']
        side = current_position['side']
        size = current_position['size']
        unrealized_pnl = current_position['unrealized_pnl']
        
        # 计算当前盈亏
        if side == 'long':
            pnl_percentage = (current_price - entry_price) / entry_price * 100
        else:  # short
            pnl_percentage = (entry_price - current_price) / entry_price * 100
        
        # 价格暴跌保护检查
        if self._check_price_crash_protection(current_position, market_data):
            return
        
        # 计算动态止盈止损
        signal = 'BUY' if current_position['side'] == 'long' else 'SELL'
        
        dynamic_tp_sl = risk_manager.calculate_dynamic_tp_sl(
            signal, current_price, market_state, current_position
        )
        
        # 更新止盈止损
        trading_engine.update_risk_management(
            current_position,
            dynamic_tp_sl['stop_loss'],
            dynamic_tp_sl['take_profit']
        )
    
    def _check_price_crash_protection(self, position: Dict[str, Any], 
                                    market_data: Dict[str, Any]) -> bool:
        """检查价格暴跌保护"""
        protection_config = config.get('strategies', 'price_crash_protection')
        
        if not protection_config.get('enabled', False):
            return False
        
        entry_price = position.get('entry_price', 0)
        current_price = market_data['price']
        
        if entry_price <= 0 or current_price <= 0:
            return False
        
        price_drop_pct = (entry_price - current_price) / entry_price
        crash_threshold = protection_config.get('crash_threshold', 0.03)
        
        if price_drop_pct >= crash_threshold:
            log_info(f"🚨 检测到价格暴跌！跌幅: {price_drop_pct:.2%}")
            return True
        
        return False
    
    def _check_consolidation_profit_lock(self, market_data: Dict[str, Any]):
        """检查横盘利润锁定 - 基于业务需求实现完整横盘处理逻辑"""
        position = market_data.get('position')
        
        if not position or position.get('size', 0) <= 0:
            return
        
        try:
            # 获取价格历史数据
            price_history = self._get_price_history_for_analysis()
            if not price_history:
                return
                
            # 获取AI信号历史
            ai_signal_history = self._get_ai_signal_history()
            
            # 检测横盘状态
            consolidation_result = consolidation_detector.detect_consolidation(
                market_data, ai_signal_history, position, price_history.get('close', [])
            )
            
            if consolidation_result['is_consolidation']:
                log_info(f"📊 检测到横盘行情：{consolidation_result['reason']}")
                log_info(f"   价格波动：{consolidation_result['price_range_pct']:.2%}")
                log_info(f"   持续时间：{consolidation_result['consolidation_duration']:.1f}分钟")
                
                # 执行横盘处理动作
                action = consolidation_result['action']
                if action:
                    from trading_extensions import TradingExtensions
                    trading_ext = TradingExtensions(trading_engine)
                    
                    success = consolidation_detector.execute_consolidation_action(
                        action, position, trading_ext
                    )
                    
                    if success:
                        log_info(f"✅ 横盘处理动作执行成功：{action}")
                    else:
                        log_error(f"❌ 横盘处理动作执行失败：{action}")
                        
            else:
                # 检查是否应该退出横盘状态
                if consolidation_detector.should_exit_consolidation(
                    ai_signal_history, market_data
                ):
                    consolidation_detector.reset_consolidation_state()
                    log_info("🔄 退出横盘状态")
                
        except Exception as e:
            log_error(f"检查横盘利润锁定异常: {e}")
    
    def _get_ai_signal_history(self) -> list[str]:
        """获取AI信号历史"""
        try:
            # 从内存管理器获取最近的AI信号
            signal_history = memory_manager.get_history('signals', limit=10)
            return [sig.get('signal', 'HOLD') for sig in signal_history]
        except Exception as e:
            log_error(f"获取AI信号历史失败: {e}")
            return []
    
    def _save_trade_record(self, signal: str, market_data: Dict[str, Any], 
                          signal_data: Dict[str, Any], order_size: float):
        """保存交易记录"""
        try:
            trade_record = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'signal': signal,
                'price': market_data['price'],
                'amount': order_size,
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason'],
                'pnl': 0,  # 实际盈亏在平仓时计算
                'market_state': {
                    'trend': signal_data.get('trend', 0),
                    'volatility': signal_data.get('volatility', 0)
                }
            }
            
            save_trade_record(trade_record)
            log_info("✅ 交易记录已保存")
            
        except Exception as e:
            log_error(f"保存交易记录失败: {e}")

    def _get_price_history_for_analysis(self) -> Dict[str, list]:
        """获取用于分析的价格历史数据"""
        # 从交易所获取真实的历史K线数据
        try:
            timeframe = config.get('exchange', 'timeframe', '15m')
            limit = max(50, 20)  # 确保获取足够的数据点
            
            # 使用交易引擎获取历史K线数据
            ohlcv_data = trading_engine.get_price_history(timeframe, limit)
            
            if ohlcv_data and len(ohlcv_data) >= 6:
                # 只在调试模式下显示详细日志
                if config.get('debug', False):
                    log_info(f"📊 获取价格历史数据: {len(ohlcv_data)} 条记录")
                
                # 提取OHLCV数据
                closes = [kline['close'] for kline in ohlcv_data]
                highs = [kline['high'] for kline in ohlcv_data]
                lows = [kline['low'] for kline in ohlcv_data]
                volumes = [kline['volume'] for kline in ohlcv_data]
                
                return {
                    'close': closes,
                    'high': highs,
                    'low': lows,
                    'volume': volumes
                }
            
        except Exception as e:
            log_error(f"获取历史K线数据失败: {e}")
        
        # 回退到使用价格历史数据
        if len(self.price_history) == 0:
            # 如果没有历史数据，提供默认值
            current_price = 50000  # 默认BTC价格
            log_warning("⚠️ 价格历史数据为空，使用默认值")
            return {
                'close': [current_price] * 6,
                'high': [current_price * 1.001] * 6,
                'low': [current_price * 0.999] * 6,
                'volume': [1000000] * 6
            }
        
        data_slice = self.price_history[-20:] if len(self.price_history) >= 20 else self.price_history
        
        log_info(f"📊 使用价格历史数据: {len(data_slice)} 条记录")
        if len(data_slice) < 6:
            log_warning(f"⚠️ 价格历史数据不足: {len(data_slice)} 条，可能影响分析准确性")
        
        # 创建模拟的OHLCV数据
        closes = list(data_slice)
        highs = [p * 1.001 for p in data_slice]
        lows = [p * 0.999 for p in data_slice]
        volumes = [1000000] * len(data_slice)
        
        return {
            'close': closes,
            'high': highs,
            'low': lows,
            'volume': volumes
        }
    
    def _perform_system_maintenance(self):
        """执行系统维护"""
        # 清理内存缓存
        cache_manager.cleanup_expired()
        
        # 清理价格历史缓存
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-500:]
        
        # 内存管理
        if self.current_cycle % 10 == 0:  # 每10轮清理一次
            memory_stats = memory_manager.get_memory_stats()
            log_info(f"📊 内存统计: {memory_stats}")
        
        # 缓存管理
        if self.current_cycle % 20 == 0:  # 每20轮检查一次
            cache_stats = cache_manager.get_stats()
            log_info(f"📊 缓存统计: {cache_stats}")
        
        # 系统监控
        if self.current_cycle % 5 == 0:  # 每5轮更新一次
            system_stats = system_monitor.get_stats()
            log_info(f"📊 系统统计: {system_stats}")
        
        # 数据管理 - 保存性能指标
        if self.current_cycle % 10 == 0:  # 每10轮保存一次
            try:
                performance_metrics = {
                    'cycle': self.current_cycle,
                    'uptime': system_stats.get('uptime_seconds', 0),
                    'trades': system_stats.get('trades', 0),
                    'errors': system_stats.get('errors', 0),
                    'api_calls': system_stats.get('api_calls', 0),
                    'warnings': system_stats.get('warnings', 0)
                }
                self.data_manager.save_performance_metrics(performance_metrics)
                log_info("📊 性能指标已保存")
            except Exception as e:
                log_error(f"保存性能指标失败: {e}")
        
        # 定期清理旧数据
        if self.current_cycle % 100 == 0:  # 每100轮清理一次
            try:
                self.data_manager.cleanup_old_data(days_to_keep=30)
                log_info("📊 旧数据清理完成")
            except Exception as e:
                log_error(f"清理旧数据失败: {e}")
    
    def _calculate_next_cycle_time(self) -> float:
        """计算下一个整点执行时间"""
        cycle_minutes = config.get('trading', 'cycle_minutes', 15)
        now = datetime.now()
        
        # 计算下一个周期时间
        current_minute = now.minute
        next_cycle_minute = ((current_minute // cycle_minutes) + 1) * cycle_minutes
        
        if next_cycle_minute >= 60:
            # 跨小时处理
            next_hour = now.hour + 1
            next_cycle_minute = 0
            if next_hour >= 24:
                next_hour = 0
                next_day = now.day + 1
            else:
                next_day = now.day
        else:
            next_hour = now.hour
            next_day = now.day
        
        try:
            next_time = now.replace(day=next_day, hour=next_hour, minute=next_cycle_minute, second=0, microsecond=0)
            if next_time <= now:
                # 如果计算出的时间已经过去，加一小时
                next_time += timedelta(hours=1)
            
            # 计算等待秒数
            wait_seconds = (next_time - now).total_seconds()
            return max(wait_seconds, 1)  # 至少等待1秒
            
        except ValueError:
            # 处理月底跨月的情况
            next_time = now + timedelta(minutes=cycle_minutes - (now.minute % cycle_minutes))
            wait_seconds = (next_time - now).total_seconds()
            return max(wait_seconds, 1)
    
    def run(self):
        """运行交易机器人"""
        try:
            log_info("🚀 Alpha Arena OKX 交易机器人启动成功！")
            self.is_running = True
            
            while self.is_running:
                try:
                    self.execute_trading_cycle()
                    
                    # 计算下一个整点执行时间
                    wait_seconds = self._calculate_next_cycle_time()
                    next_run_time = datetime.now() + timedelta(seconds=wait_seconds)
                    
                    log_info(f"⏰ 下次执行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    minutes = int(wait_seconds // 60)
                    seconds = int(wait_seconds % 60)
                    log_info(f"⏰ 等待 {minutes}分{seconds}秒 到下一个15分钟整点执行...")
                    
                    time.sleep(wait_seconds)
                    
                except KeyboardInterrupt:
                    log_info("🛑 收到停止信号，正在关闭...")
                    self.is_running = False
                    break
                except Exception as e:
                    log_error(f"交易循环异常: {e}")
                    time.sleep(60)  # 等待1分钟后重试
                    
        except Exception as e:
            log_error(f"启动失败: {e}")
            raise
    
    def stop(self):
        """停止交易机器人"""
        self.is_running = False
        log_info("🛑 交易机器人已停止")

def main():
    """主函数"""
    bot = AlphaArenaBot()
    bot.run()

if __name__ == "__main__":
    main()
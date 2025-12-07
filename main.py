"""
Alpha Pilot Bot OKX - 重构版主程序
基于模块化架构的OKX自动交易系统
实现AI驱动的自动化交易策略执行
"""

import time
import threading
import json
import numpy as np
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# 导入模块
import logging
import asyncio
from config import config
from trading import trading_engine
from strategies import (
    MarketAnalyzer, StrategySelector, StrategyBacktestEngine,
    StrategyOptimizer, StrategyMonitor, StrategyExecutor, StrategyBehaviorHandler,
    consolidation_detector, crash_protection, market_analyzer
)
from utils import (
    cache_manager, memory_manager, system_monitor,
    data_validator, json_helper, time_helper, logger_helper,
    TradeLogger, DataManager, save_trade_record, log_info, log_warning, log_error
)
from ai_client import ai_client

@dataclass
class BotState:
    """机器人状态数据结构"""
    is_running: bool = False
    current_cycle: int = 0
    last_signal: Optional[Dict[str, Any]] = None
    price_history: List[float] = None
    signal_cache: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.price_history is None:
            self.price_history = []
        if self.signal_cache is None:
            self.signal_cache = {}

class AlphaArenaBot:
    """Alpha Pilot Bot OKX 交易机器人主类
    
    负责协调整个交易系统的运行，包括：
    - 市场数据获取和分析
    - AI信号生成和处理
    - 交易决策执行
    - 风险管理和系统维护
    """
    
    def __init__(self):
        """初始化交易机器人"""
        self.state = BotState()
        self.data_manager = DataManager()
        
        log_info("🚀 Alpha Pilot Bot OKX 交易机器人初始化中...")
        self._display_startup_info()
        
        # 初始化数据管理
        self._initialize_data_management()
    
    def _display_startup_info(self) -> None:
        """显示启动信息
        
        展示系统版本、特性和配置信息，帮助用户了解当前运行环境
        """
        log_info("=" * 60)
        log_info("🎯 Alpha Pilot Bot OKX 自动交易系统 v2.0")
        log_info("=" * 60)
        log_info("📊 系统特性:")
        log_info("   • 模块化架构设计")
        log_info("   • 配置与逻辑分离")
        log_info("   • 智能风险管理")
        log_info("   • AI信号增强")
        log_info("   • 内存优化管理")
        log_info("   • 数据管理系统")
        log_info("=" * 60)
        
        # 显示配置信息 - 增强测试模式显示
        test_mode = config.get('trading', 'test_mode')
        if test_mode:
            log_info("⚠️  ⚠️  ⚠️  当前运行在测试模式 ⚠️  ⚠️  ⚠️")
            log_info("🔄 交易模式: 🔴 模拟交易 (TEST_MODE=true)")
            log_info("💡 提示: 所有交易都是模拟的，不会使用真实资金")
        else:
            log_info("🚨 🚨 🚨 当前运行在实盘模式 🚨 🚨 🚨")
            log_info("🔄 交易模式: 💰 实盘交易 (TEST_MODE=false)")
            log_info("⚠️ 警告: 所有交易都将使用真实资金，请谨慎操作！")
        
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

    def _initialize_data_management(self) -> None:
        """初始化数据管理系统
        
        负责：
        - 加载历史数据摘要
        - 清理过期数据
        - 验证数据完整性
        """
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
            log_error(f"数据管理初始化失败: {type(e).__name__}: {e}")
            # 记录详细错误信息用于调试
            import traceback
            log_error(f"数据管理初始化堆栈:\n{traceback.format_exc()}")
    
    def get_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取AI交易信号（增强版）
        
        使用多线程方式安全地执行异步AI信号获取，提供完整的错误处理和回退机制
        
        Args:
            market_data: 市场数据字典，包含价格、趋势、波动率等信息
            
        Returns:
            Dict[str, Any]: AI信号数据，包含signal、confidence、reason等字段
        """
        try:
            # 使用线程安全的方式运行异步函数
            import threading
            
            # 尝试导入nest_asyncio，如果失败则使用替代方案
            try:
                import nest_asyncio
                # 应用nest_asyncio以允许嵌套事件循环
                try:
                    nest_asyncio.apply()
                except:
                    pass  # 如果已应用则忽略
            except ImportError:
                log_warning("⚠️ nest_asyncio模块未安装，使用替代方案")
                # 没有nest_asyncio也能运行，只是可能会有警告
            
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
        """异步获取AI交易信号
        
        实现多层缓存机制，提高信号获取效率并减少API调用
        
        Args:
            market_data: 市场数据字典
            
        Returns:
            Dict[str, Any]: AI信号数据
        """
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
            log_error(f"AI信号生成失败: {type(e).__name__}: {e}")
            import traceback
            log_error(f"AI信号生成堆栈:\n{traceback.format_exc()}")
            return await self._get_fallback_signal(market_data)
    
    def _generate_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI信号 - 已废弃，使用增强版本
        
        保持向后兼容性，直接调用增强版本
        
        Args:
            market_data: 市场数据字典
            
        Returns:
            Dict[str, Any]: AI信号数据
        """
        # 直接调用增强版本以保持向后兼容性
        return self._generate_enhanced_ai_signal(market_data)
    
    def _analyze_simple_trend(self) -> float:
        """简单趋势分析
        
        使用线性回归计算价格趋势强度，并进行标准化处理
        
        Returns:
            float: 趋势强度值，范围通常在-1到1之间
        """
        if len(self.state.price_history) < 20:
            return 0.0
        
        recent = self.state.price_history[-20:]
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
        """计算近期波动率
        
        基于价格历史计算平均价格变化率，用于评估市场波动程度
        
        Returns:
            float: 波动率百分比，默认值为2.0%
        """
        if len(self.state.price_history) < 14:
            return 2.0
        
        recent = self.state.price_history[-14:]
        if len(recent) < 2:
            return 2.0
        
        returns = []
        for i in range(1, len(recent)):
            returns.append(abs(recent[i] - recent[i-1]) / recent[i-1])
        
        return np.mean(returns) * 100 if returns else 2.0
    
    def _create_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建回退信号
        
        当AI信号生成失败时，提供保守的回退信号
        
        Args:
            market_data: 市场数据字典
            
        Returns:
            Dict[str, Any]: 回退信号数据
        """
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
        """检查缓存是否有效 - 增强版本"""
        if not cached_signal:
            return False
        
        try:
            # 检查时间有效性
            timestamp = cached_signal.get('timestamp', '')
            if not timestamp:
                return False
                
            signal_time = datetime.fromisoformat(timestamp)
            age_seconds = (datetime.now() - signal_time).total_seconds()
            max_age = config.get('ai', 'cache_duration', 900)
            
            if age_seconds > max_age:
                return False
            
            # 检查市场状态是否发生重大变化
            recent_volatility = self._calculate_recent_volatility()
            if recent_volatility > 5.0:  # 波动率超过5%时刷新信号
                return False
            
            # 检查价格变化是否超过阈值
            if len(self.state.price_history) >= 2:
                current_price = self.state.price_history[-1]
                cached_price = cached_signal.get('market_context', {}).get('current_price', current_price)
                if abs(current_price - cached_price) / cached_price > 0.02:  # 价格变化超过2%
                    return False
            
            # 检查持仓状态是否变化
            current_position = trading_engine.get_position_info()
            cached_position = cached_signal.get('market_context', {}).get('position', {})
            if current_position['has_position'] != (cached_position.get('size', 0) > 0):
                return False
            
            return True
            
        except Exception as e:
            log_warning(f"缓存验证异常: {e}")
            return False
    
    async def _find_similar_market_state(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """基于相似市场状态查找历史信号"""
        # 获取历史信号
        history = memory_manager.get_history('signals', limit=50)
        
        if not history:
            return None
        
        # 查找最近的有效信号
        for signal in reversed(history):
            timestamp = signal.get('timestamp', '')
            if not timestamp:
                continue
                
            try:
                signal_time = datetime.fromisoformat(timestamp)
                age_seconds = (datetime.now() - signal_time).total_seconds()
                
                # 只考虑2小时内的信号
                if age_seconds < 7200:
                    # 检查信号质量
                    if signal.get('confidence', 0) > 0.7:
                        return signal
            except ValueError:
                # 跳过无效的时间戳格式
                continue
        
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
                # 使用增强的信号融合算法
                signal_data = ai_client.fuse_signals(signals)
                log_info("📊 【多AI融合信号分析】")
                log_info(f"   📈 最终信号: {signal_data['signal']}")
                log_info(f"   💡 融合信心: {signal_data['confidence']:.1f}")
                
                # 显示详细的融合分析信息
                fusion_analysis = signal_data.get('fusion_analysis', {})
                if fusion_analysis:
                    log_info(f"   🔍 融合详情:")
                    log_info(f"      共识门槛: {fusion_analysis.get('consensus_threshold', 'unknown')}")
                    log_info(f"      动态调整: {fusion_analysis.get('dynamic_adjustment', 0):+.2f}")
                    log_info(f"      一致性得分: {fusion_analysis.get('consistency_score', 0):.2f}")
                    log_info(f"      低波动优化: {'✅' if fusion_analysis.get('low_volatility_optimized') else '❌'}")
                
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
        """获取增强兜底信号（集成新的兜底引擎）"""
        try:
            log_info("🛡️ 启动增强兜底信号生成流程...")
            
            # 1. 首先尝试使用新的增强兜底引擎
            try:
                # 从strategies模块导入增强兜底功能
                from strategies import generate_enhanced_fallback_signal
                
                # 获取AI信号历史用于兜底分析
                signal_history = memory_manager.get_history('signals', limit=20)
                
                # 调用增强兜底引擎
                enhanced_fallback = await generate_enhanced_fallback_signal(market_data, signal_history)
                
                if enhanced_fallback and enhanced_fallback.get('is_enhanced_fallback'):
                    log_info(f"✅ 增强兜底引擎成功生成信号: {enhanced_fallback['signal']} (信心: {enhanced_fallback['confidence']:.2f}, 质量: {enhanced_fallback['quality_score']:.2f})")
                    log_info(f"📊 兜底类型: {enhanced_fallback['fallback_type']}")
                    log_info(f"💡 兜底理由: {enhanced_fallback['reason']}")
                    
                    # 记录兜底统计
                    self._record_fallback_usage(enhanced_fallback)
                    
                    return enhanced_fallback
                else:
                    log_warning("⚠️ 增强兜底引擎未生成有效信号，回退到传统兜底")
                    
            except Exception as e:
                log_error(f"增强兜底引擎调用失败: {e}")
                log_warning("⚠️ 增强兜底引擎异常，回退到传统兜底")
            
            # 2. 回退到传统的兜底逻辑
            return await self._get_traditional_fallback_signal(market_data)
            
        except Exception as e:
            log_error(f"增强兜底信号生成失败: {e}")
            # 最终兜底：基础持有信号
            return self._create_emergency_fallback_signal(market_data)
    
    async def _get_traditional_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取传统兜底信号（作为增强兜底的回退）"""
        return self._get_fallback_signal_sync(market_data)
        
    def _get_fallback_signal_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取同步回退信号（增强版）"""
        try:
            # 1. 首先检查是否有历史信号可用
            history = memory_manager.get_history('signals', limit=10)
            
            if history:
                # 分析历史信号的一致性和质量
                recent_signals = history[-5:]  # 最近5个信号
                signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                total_confidence = 0
                
                for sig in recent_signals:
                    signal = sig.get('signal', 'HOLD')
                    confidence = sig.get('confidence', 0.5)
                    signal_counts[signal] += 1
                    total_confidence += confidence
                
                avg_confidence = total_confidence / len(recent_signals)
                dominant_signal = max(signal_counts, key=signal_counts.get)
                
                # 如果历史信号有明确共识，使用它
                if signal_counts[dominant_signal] >= 3:  # 至少3个相同信号
                    fallback_signal = {
                        'signal': dominant_signal,
                        'confidence': max(0.4, avg_confidence * 0.6),  # 降低信心但保持合理水平
                        'reason': f"智能回退信号: 基于{len(recent_signals)}个历史信号的{dominant_signal}共识",
                        'timestamp': datetime.now().isoformat(),
                        'fallback_type': 'historical_consensus',
                        'historical_analysis': {
                            'signal_distribution': signal_counts,
                            'avg_confidence': avg_confidence,
                            'consensus_strength': signal_counts[dominant_signal] / len(recent_signals)
                        }
                    }
                    log_info(f"📊 使用历史信号共识回退: {dominant_signal} ({signal_counts[dominant_signal]}/{len(recent_signals)})")
                    return fallback_signal
            
            # 2. 基于技术指标生成智能回退信号
            return self._create_intelligent_fallback_signal(market_data)
            
        except Exception as e:
            log_error(f"增强回退信号生成失败: {e}")
            # 最终回退：基于简单技术分析
            return self._create_fallback_signal(market_data)
    
    def _record_fallback_usage(self, fallback_signal: Dict[str, Any]) -> None:
        """记录兜底信号使用情况"""
        try:
            fallback_type = fallback_signal.get('fallback_type', 'unknown')
            quality_score = fallback_signal.get('quality_score', 0)
            confidence = fallback_signal.get('confidence', 0)
            
            log_info(f"📊 兜底使用统计:")
            log_info(f"   兜底类型: {fallback_type}")
            log_info(f"   信号质量: {quality_score:.2f}")
            log_info(f"   信号信心: {confidence:.2f}")
            log_info(f"   可靠性因子: {fallback_signal.get('reliability_factors', [])}")
            
            # 这里可以添加更详细的统计逻辑，如：
            # - 按兜底类型统计使用频率
            # - 质量评分分布
            # - 兜底信号的成功率跟踪
            
        except Exception as e:
            log_warning(f"兜底使用记录失败: {e}")
    
    def _create_emergency_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建紧急兜底信号（最终保障）"""
        try:
            current_price = market_data.get('price', 0)
            
            emergency_signal = {
                'signal': 'HOLD',
                'confidence': 0.3,  # 最低信心度
                'reason': '紧急兜底: 所有兜底机制失效，强制保守持有',
                'timestamp': datetime.now().isoformat(),
                'fallback_type': 'emergency',
                'emergency_context': {
                    'price': current_price,
                    'data_available': current_price > 0,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            log_warning("🚨 使用紧急兜底信号: 强制HOLD，最低信心度")
            return emergency_signal
            
        except Exception as e:
            log_error(f"紧急兜底信号创建失败: {e}")
            # 最后的最后：返回一个绝对安全的信号
            return {
                'signal': 'HOLD',
                'confidence': 0.2,
                'reason': '系统严重错误，绝对保守持有',
                'timestamp': datetime.now().isoformat(),
                'fallback_type': 'critical_error'
            }
    
    def _create_intelligent_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建基于技术指标的智能回退信号"""
        try:
            current_price = market_data.get('price', 0)
            if current_price <= 0:
                return self._create_fallback_signal(market_data)
            
            # 获取价格历史数据
            price_history = self._get_price_history_for_analysis()
            closes = price_history.get('close', [])
            
            if len(closes) < 6:
                # 数据不足，使用简单趋势分析
                return self._create_trend_based_fallback(current_price, closes)
            
            # 计算关键技术指标
            technical_signals = {}
            
            # RSI信号
            rsi = self._calculate_rsi(closes, 14)
            if rsi > 70:
                technical_signals['rsi'] = 'SELL'
            elif rsi < 30:
                technical_signals['rsi'] = 'BUY'
            else:
                technical_signals['rsi'] = 'HOLD'
            
            # 均线信号
            ma_data = self._calculate_ma_status(closes)
            ma_trend = ma_data.get('ma_trend', 'N/A')
            if ma_trend == '多头排列':
                technical_signals['ma'] = 'BUY'
            elif ma_trend == '空头排列':
                technical_signals['ma'] = 'SELL'
            else:
                technical_signals['ma'] = 'HOLD'
            
            # 价格位置信号
            ma_position = ma_data.get('ma_position', 'N/A')
            if ma_position == '均线上方':
                technical_signals['position'] = 'BUY'
            elif ma_position == '均线下方':
                technical_signals['position'] = 'SELL'
            else:
                technical_signals['position'] = 'HOLD'
            
            # 趋势强度
            trend_strength = self._analyze_simple_trend()
            if trend_strength > 0.3:
                technical_signals['trend'] = 'BUY'
            elif trend_strength < -0.3:
                technical_signals['trend'] = 'SELL'
            else:
                technical_signals['trend'] = 'HOLD'
            
            # 统计技术信号
            signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            for signal in technical_signals.values():
                signal_counts[signal] += 1
            
            # 确定最终信号
            if signal_counts['BUY'] >= 2:
                final_signal = 'BUY'
                confidence = 0.5 + (signal_counts['BUY'] - 2) * 0.1  # 0.5-0.7
                reason = f"技术指标回退: {signal_counts['BUY']}个买入信号 (RSI:{technical_signals['rsi']}, MA:{technical_signals['ma']}, 位置:{technical_signals['position']}, 趋势:{technical_signals['trend']})"
            elif signal_counts['SELL'] >= 2:
                final_signal = 'SELL'
                confidence = 0.5 + (signal_counts['SELL'] - 2) * 0.1  # 0.5-0.7
                reason = f"技术指标回退: {signal_counts['SELL']}个卖出信号 (RSI:{technical_signals['rsi']}, MA:{technical_signals['ma']}, 位置:{technical_signals['position']}, 趋势:{technical_signals['trend']})"
            else:
                final_signal = 'HOLD'
                confidence = 0.6  # HOLD信号保持中等信心
                reason = f"技术指标回退: 信号分歧，建议观望 (RSI:{technical_signals['rsi']}, MA:{technical_signals['ma']}, 位置:{technical_signals['position']}, 趋势:{technical_signals['trend']})"
            
            intelligent_signal = {
                'signal': final_signal,
                'confidence': min(0.8, confidence),  # 最大信心0.8
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'fallback_type': 'intelligent_technical',
                'technical_analysis': {
                    'rsi': rsi,
                    'ma_trend': ma_trend,
                    'ma_position': ma_position,
                    'trend_strength': trend_strength,
                    'signal_breakdown': technical_signals,
                    'signal_counts': signal_counts
                }
            }
            
            log_info(f"📊 使用智能技术回退信号: {final_signal} (信心: {confidence:.2f})")
            return intelligent_signal
            
        except Exception as e:
            log_error(f"智能回退信号生成失败: {e}")
            return self._create_fallback_signal(market_data)
    
    def _create_trend_based_fallback(self, current_price: float, price_history: list) -> Dict[str, Any]:
        """基于简单趋势的回退信号"""
        try:
            if len(price_history) >= 3:
                # 简单趋势判断
                recent_trend = (current_price - price_history[-3]) / price_history[-3]
                
                if recent_trend > 0.02:  # 上涨超过2%
                    signal = 'BUY'
                    confidence = 0.4 + min(0.3, abs(recent_trend) * 10)  # 0.4-0.7
                    reason = f"趋势回退: 近期价格上涨{recent_trend:.2%}"
                elif recent_trend < -0.02:  # 下跌超过2%
                    signal = 'SELL'
                    confidence = 0.4 + min(0.3, abs(recent_trend) * 10)  # 0.4-0.7
                    reason = f"趋势回退: 近期价格下跌{recent_trend:.2%}"
                else:
                    signal = 'HOLD'
                    confidence = 0.5
                    reason = f"趋势回退: 近期价格震荡{recent_trend:.2%}，建议观望"
            else:
                signal = 'HOLD'
                confidence = 0.4
                reason = "趋势回退: 数据不足，保守观望"
            
            return {
                'signal': signal,
                'confidence': confidence,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'fallback_type': 'simple_trend',
                'trend_analysis': {
                    'recent_change': recent_trend if len(price_history) >= 3 else 0
                }
            }
            
        except Exception as e:
            log_error(f"趋势回退信号生成失败: {e}")
            return self._create_fallback_signal({'price': current_price})
    
    def _should_refresh_signal(self) -> bool:
        """判断是否需要刷新信号"""
        # 简化逻辑：每15分钟或信号变化时刷新
        if not self.last_signal:
            return True
        
        # 检查时间间隔
        signal_age = time.time() - self.last_signal.get('timestamp', 0)
        return signal_age > config.get('ai', 'cache_duration')
    
    def _prepare_ai_market_data(self, market_data: Dict[str, Any], market_state: Dict[str, Any]) -> Dict[str, Any]:
        """准备AI分析所需的完整市场数据"""
        try:
            # 获取价格历史用于技术指标计算
            price_history = self._get_price_history_for_analysis()
            
            # 计算技术指标
            technical_data = {}
            trend_analysis = {}
            
            if price_history and len(price_history.get('close', [])) >= 14:
                closes = price_history['close']
                highs = price_history['high']
                lows = price_history['low']
                
                # 计算RSI
                if len(closes) >= 14:
                    rsi = self._calculate_rsi(closes, 14)
                    technical_data['rsi'] = rsi
                
                # 计算MACD
                if len(closes) >= 26:
                    macd_data = self._calculate_macd(closes)
                    technical_data.update(macd_data)
                
                # 计算均线状态
                if len(closes) >= 20:
                    ma_data = self._calculate_ma_status(closes)
                    technical_data.update(ma_data)
                    trend_analysis['overall'] = ma_data.get('ma_trend', 'N/A')
            
            # 获取AI信号历史
            ai_signal_history = []
            try:
                signal_history = memory_manager.get_history('signals', limit=10)
                if signal_history:
                    ai_signal_history = [
                        {
                            'signal': sig.get('signal', 'HOLD'),
                            'confidence': sig.get('confidence', 0.5),
                            'timestamp': sig.get('timestamp', '')
                        }
                        for sig in signal_history[-5:]  # 最近5个信号
                    ]
            except Exception as e:
                log_warning(f"获取AI信号历史失败: {e}")
            
            # 构建完整的市场数据结构
            enhanced_market_data = {
                **market_data,
                **market_state,
                'technical_data': technical_data,
                'trend_analysis': trend_analysis,
                'price_history': closes if 'closes' in locals() else [],
                'signal_history': ai_signal_history,
                'price_change_pct': market_data.get('price_change_pct', 0)
            }
            
            return enhanced_market_data
            
        except Exception as e:
            log_error(f"准备AI市场数据失败: {e}")
            # 返回基础数据
            return {**market_data, **market_state, 'technical_data': {}, 'trend_analysis': {}}
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            # 计算价格变化
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # 分离上涨和下跌
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # 计算平均收益和损失
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return max(0, min(100, rsi))
            
        except Exception as e:
            log_warning(f"RSI计算失败: {e}")
            return 50.0
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, Any]:
        """计算MACD指标"""
        try:
            if len(prices) < 26:
                return {'macd': 'N/A', 'macd_signal': 'N/A', 'macd_histogram': 'N/A'}
            
            # 计算EMA
            def ema(values, period):
                if len(values) < period:
                    return None
                alpha = 2 / (period + 1)
                ema_values = [sum(values[:period]) / period]
                for i in range(period, len(values)):
                    ema_values.append(alpha * values[i] + (1 - alpha) * ema_values[-1])
                return ema_values
            
            # 计算12日和26日EMA
            ema12 = ema(prices, 12)
            ema26 = ema(prices, 26)
            
            if not ema12 or not ema26:
                return {'macd': 'N/A', 'macd_signal': 'N/A', 'macd_histogram': 'N/A'}
            
            # 确保长度一致
            min_len = min(len(ema12), len(ema26))
            ema12 = ema12[-min_len:]
            ema26 = ema26[-min_len:]
            
            # 计算MACD线
            macd_line = [ema12[i] - ema26[i] for i in range(min_len)]
            
            # 计算信号线(9日EMA)
            signal_line = ema(macd_line, 9)
            
            if not signal_line or len(signal_line) < 1:
                return {'macd': 'N/A', 'macd_signal': 'N/A', 'macd_histogram': 'N/A'}
            
            # 计算柱状图
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            histogram = current_macd - current_signal
            
            # 判断MACD状态
            if current_macd > current_signal and current_macd > 0:
                macd_status = "金叉看涨"
            elif current_macd < current_signal and current_macd < 0:
                macd_status = "死叉看跌"
            else:
                macd_status = "中性震荡"
            
            return {
                'macd': macd_status,
                'macd_value': current_macd,
                'macd_signal': current_signal,
                'macd_histogram': histogram
            }
            
        except Exception as e:
            log_warning(f"MACD计算失败: {e}")
            return {'macd': 'N/A', 'macd_signal': 'N/A', 'macd_histogram': 'N/A'}
    
    def _calculate_ma_status(self, prices: List[float]) -> Dict[str, Any]:
        """计算均线状态"""
        try:
            if len(prices) < 20:
                return {'ma_trend': 'N/A', 'ma_position': 'N/A'}
            
            # 计算不同周期均线
            ma5 = sum(prices[-5:]) / 5
            ma10 = sum(prices[-10:]) / 10
            ma20 = sum(prices[-20:]) / 20
            
            current_price = prices[-1]
            
            # 判断均线排列
            if ma5 > ma10 > ma20:
                ma_trend = "多头排列"
            elif ma5 < ma10 < ma20:
                ma_trend = "空头排列"
            else:
                ma_trend = "震荡排列"
            
            # 判断价格相对均线位置
            if current_price > ma5 and current_price > ma10 and current_price > ma20:
                ma_position = "均线上方"
            elif current_price < ma5 and current_price < ma10 and current_price < ma20:
                ma_position = "均线下方"
            else:
                ma_position = "均线附近"
            
            return {
                'ma_trend': ma_trend,
                'ma_position': ma_position,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20
            }
            
        except Exception as e:
            log_warning(f"均线状态计算失败: {e}")
            return {'ma_trend': 'N/A', 'ma_position': 'N/A'}

    def analyze_market_state(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场状态
        
        综合分析当前市场状态，包括价格趋势、波动率、技术指标等
        
        Args:
            market_data: 市场数据字典，包含价格、成交量、持仓等信息
            
        Returns:
            Dict[str, Any]: 市场状态分析结果
        """
        try:
            # 验证输入参数
            if not market_data or not isinstance(market_data, dict):
                log_warning("⚠️ 市场数据无效，返回默认状态")
                return {}
                
            # 更新价格历史 - 添加数据验证
            current_price = market_data.get('price', 0)
            if current_price > 0:  # 验证价格有效性
                # 检查价格异常值（单日波动超过20%视为异常）
                if len(self.state.price_history) > 0:
                    last_price = self.state.price_history[-1]
                    if abs(current_price - last_price) / last_price > 0.2:
                        log_warning(f"⚠️ 检测到价格异常跳跃: {last_price} -> {current_price}")
                        # 可以选择不记录异常价格或使用平滑处理
                        current_price = last_price * 1.05 if current_price > last_price else last_price * 0.95
                
                self.state.price_history.append(current_price)
                if len(self.state.price_history) > 100:
                    self.state.price_history.pop(0)
            else:
                log_warning("⚠️ 无效的价格数据，跳过价格历史更新")

            # 获取完整的价格历史数据用于分析
            price_history = self._get_price_history_for_analysis()

            # 更新暴跌保护系统的价格历史
            crash_protection.price_history = self.state.price_history[-20:]  # 保留最近20个价格

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
            closes_for_trend = price_history.get('close', self.state.price_history)
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
                        position, market_data, self.state.price_history
                    )
                except Exception:
                    should_lock_profit = False

            # 检查暴跌保护
            try:
                crash_protection_decision = crash_protection.should_trigger_crash_protection(
                    position, market_data
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
    
    def execute_trading_cycle(self) -> None:
        """执行交易周期
        
        执行完整的交易周期，包括：
        - 获取市场数据
        - 分析市场状态
        - 获取AI信号
        - 执行交易决策
        - 风险管理
        - 系统维护
        """
        try:
            self.state.current_cycle += 1
            log_info(f"{'='*60}")
            log_info(f"🔄 第 {self.state.current_cycle} 轮交易周期开始")
            log_info(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 每10轮显示一次当前模式，确保用户知道当前状态
            if self.state.current_cycle % 10 == 1:  # 第1、11、21...轮显示
                test_mode = config.get('trading', 'test_mode')
                if test_mode:
                    log_info("🔧 当前模式: 🔴 模拟交易模式")
                else:
                    log_info("🔧 当前模式: 💰 实盘交易模式")
            
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
                # 准备增强的AI市场数据，包含完整的技术指标
                enhanced_market_data = self._prepare_ai_market_data(market_data, market_state)
                signal_data = self.get_ai_signal(enhanced_market_data)
                
                # 增强的AI信号日志 - 包含详细的决策分析
                signal = signal_data.get('signal', 'HOLD')
                confidence = signal_data.get('confidence', 0.5)
                reason = signal_data.get('reason', '')
                
                log_info(f"🤖 AI信号: {signal} (信心: {confidence:.2f})")
                
                # 详细的多AI融合分析
                fusion_analysis = signal_data.get('fusion_analysis', {})
                if fusion_analysis:
                    log_info(f"📊 【AI决策详细分析】")
                    log_info(f"   总提供商: {fusion_analysis.get('total_providers', 0)}")
                    log_info(f"   成功提供商: {fusion_analysis.get('successful_providers', 0)}")
                    log_info(f"   失败提供商: {fusion_analysis.get('failed_providers', 0)}")
                    log_info(f"   成功率: {fusion_analysis.get('success_rate', 0)*100:.1f}%")
                    
                    votes = signal_data.get('votes', {})
                    if votes:
                        log_info(f"   投票分布: BUY={votes.get('BUY', 0)}, SELL={votes.get('SELL', 0)}, HOLD={votes.get('HOLD', 0)}")
                    
                    confidences = signal_data.get('confidences', {})
                    if confidences:
                        log_info(f"   信心分布: BUY={confidences.get('BUY', 0):.2f}, SELL={confidences.get('SELL', 0):.2f}, HOLD={confidences.get('HOLD', 0):.2f}")
                    
                    log_info(f"   融合方法: {signal_data.get('fusion_method', 'unknown')}")
                    log_info(f"   决策理由: {fusion_analysis.get('fusion_reason', reason)}")
                
                # 简化的理由显示
                clean_reason = ' '.join(reason.replace('\n', ' ').replace('\r', ' ').split())
                log_info(f"💡 AI建议: {clean_reason}")
                
                # 基于信号提供具体的交易建议
                if signal == 'HOLD':
                    if confidence >= 0.8:
                        log_info(f"🎯 【交易建议】强烈建议保持观望，等待更明确的市场信号")
                    elif confidence >= 0.6:
                        log_info(f"🎯 【交易建议】建议保持观望，市场方向不明确")
                    else:
                        log_info(f"🎯 【交易建议】谨慎观望，AI信心较低")
                        
                elif signal == 'BUY':
                    if confidence >= 0.8:
                        log_info(f"🎯 【交易建议】强烈建议买入，市场出现明显的上涨信号")
                    elif confidence >= 0.6:
                        log_info(f"🎯 【交易建议】可以考虑买入，但建议分批建仓")
                    else:
                        log_info(f"🎯 【交易建议】谨慎买入，AI信心不足")
                        
                elif signal == 'SELL':
                    if confidence >= 0.8:
                        log_info(f"🎯 【交易建议】强烈建议卖出，市场出现明显的下跌信号")
                    elif confidence >= 0.6:
                        log_info(f"🎯 【交易建议】可以考虑卖出，但建议分批减仓")
                    else:
                        log_info(f"🎯 【交易建议】谨慎卖出，AI信心不足")
                
                # 保存AI信号到历史记录（用于横盘检测）
                memory_manager.add_to_history('signals', {
                    'signal': signal,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat(),
                    'reason': reason,
                    'fusion_analysis': fusion_analysis
                })
                
            except Exception as e:
                log_error(f"获取AI信号失败: {e}")
                return
            
            # 4. 初始化信号处理器
            signal_processor = StrategyBehaviorHandler(trading_engine)
            
            # 5. 处理信号并执行交易决策
            log_info("🔍 处理交易信号...")
            try:
                # 获取当前持仓状态用于决策分析
                current_position = market_data.get('position', {})
                has_position = current_position and current_position.get('size', 0) > 0
                
                log_info(f"📊 【当前交易状态分析】")
                log_info(f"   当前持仓状态: {'有持仓' if has_position else '无持仓'}")
                if has_position:
                    log_info(f"   持仓方向: {current_position.get('side', 'unknown')}")
                    log_info(f"   持仓数量: {current_position.get('size', 0)} BTC")
                    log_info(f"   入场价格: ${current_position.get('entry_price', 0):.2f}")
                    unrealized_pnl = current_position.get('unrealized_pnl', 0)
                    log_info(f"   未实现盈亏: ${unrealized_pnl:.2f}")
                    if current_position.get('entry_price', 0) > 0:
                        current_price = market_data.get('price', 0)
                        pnl_pct = ((current_price - current_position['entry_price']) / current_position['entry_price']) * 100
                        log_info(f"   盈亏百分比: {pnl_pct:+.2f}%")
                
                # 基于信号和持仓状态提供决策分析
                signal = signal_data.get('signal', 'HOLD')
                confidence = signal_data.get('confidence', 0.5)
                
                log_info(f"📊 【信号执行分析】")
                log_info(f"   AI信号: {signal}")
                log_info(f"   信号信心: {confidence:.2f}")
                log_info(f"   持仓状态: {'持仓中' if has_position else '空仓中'}")
                
                # 信号与持仓的匹配分析
                if signal == 'HOLD':
                    if has_position:
                        log_info(f"   🔄 决策分析: 保持现有持仓，不进行调整")
                        log_info(f"   💡 建议: 继续持观望态度，等待更明确的市场信号")
                    else:
                        log_info(f"   ⏸️ 决策分析: 继续空仓观望，不入场交易")
                        log_info(f"   💡 建议: 耐心等待入场时机，避免盲目交易")
                        
                elif signal == 'BUY':
                    if has_position:
                        if current_position.get('side') == 'long':
                            log_info(f"   📈 决策分析: 加仓信号，当前已有多头持仓")
                            log_info(f"   💡 建议: 可以考虑适量加仓，但注意风险控制")
                        else:
                            log_info(f"   🔄 决策分析: 买入信号，但当前持有空头仓位")
                            log_info(f"   💡 建议: 需要先平掉空头仓位，再考虑买入")
                    else:
                        log_info(f"   🚀 决策分析: 买入信号，当前空仓可入场")
                        log_info(f"   💡 建议: 可以考虑入场做多，设置好止盈止损")
                        
                elif signal == 'SELL':
                    if has_position:
                        if current_position.get('side') == 'long':
                            log_info(f"   📉 决策分析: 卖出信号，当前持有多头仓位")
                            log_info(f"   💡 建议: 考虑平仓或减仓，锁定利润或减少损失")
                        else:
                            log_info(f"   📈 决策分析: 卖出信号，当前已有空头持仓")
                            log_info(f"   💡 建议: 可以考虑加仓做空，但注意风险控制")
                    else:
                        log_info(f"   🚀 决策分析: 卖出信号，当前空仓可入场做空")
                        log_info(f"   💡 建议: 如果允许做空，可以考虑开空仓")
                
                success = signal_processor.process_signal(signal_data, market_data)
                if success:
                    log_info("✅ 信号执行完成")
                    
                    # 执行后状态更新
                    updated_position = trading_engine.get_position_info()
                    if updated_position['has_position']:
                        log_info(f"📊 【执行后状态】")
                        log_info(f"   新持仓方向: {updated_position['side']}")
                        log_info(f"   新持仓数量: {updated_position['size']} BTC")
                        log_info(f"   入场价格: ${updated_position['entry_price']:.2f}")
                    else:
                        log_info("📊 【执行后状态】继续保持空仓")
                        
                else:
                    log_warning("⚠️ 信号执行未完成或无需执行")
                    log_info("💡 可能原因: 信号与当前状态冲突、风险控制限制、或市场条件不适合")
                    
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
            log_info(f"✅ 第 {self.state.current_cycle} 轮交易周期完成")
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
                    'cycle': self.state.current_cycle
                })
            except Exception:
                pass
    
    def _execute_trade_signal(self, signal: str, signal_data: Dict[str, Any], 
                            market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """执行交易信号 - 使用增强型信号处理器"""
        try:
            # 使用增强型信号处理器
            from strategies import StrategyBehaviorHandler
            processor = StrategyBehaviorHandler(trading_engine)
            
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
        
        # 使用信号处理器处理 - 修复未定义变量问题
        try:
            from strategies import StrategyBehaviorHandler
            signal_processor = StrategyBehaviorHandler(trading_engine)
            processed_signal = signal_processor.process_signal(signal_data, market_data)
            if processed_signal == False:  # 注意：process_signal返回bool，需要检查逻辑
                log_info("📊 保持持仓，跳过交易")
                return
        except Exception as e:
            log_error(f"信号处理失败: {e}")
            return
        
        # 计算订单大小 - 使用策略选择器获取配置
        try:
            from strategies import StrategySelector
            selector = StrategySelector()
            strategy_config = selector.get_strategy_config()
            max_position_size = strategy_config.get('max_position_ratio', 0.01)
            
            # 简化的订单大小计算
            balance = market_data.get('balance', {}).get('free', 0)
            order_size = min(max_position_size * balance / current_price, 0.01)  # 最大0.01 BTC
        except Exception as e:
            log_error(f"订单大小计算失败: {e}")
            order_size = 0.001  # 默认订单大小
        
        if order_size <= 0:
            log_warning("⚠️ 订单大小为0，跳过交易")
            return
        
        # 计算止盈止损 - 使用策略选择器
        try:
            from strategies import RiskManager
            risk_manager = RiskManager()
            tp_sl_params = risk_manager.calculate_dynamic_tp_sl(
                signal, current_price, market_state, position
            )
        except Exception as e:
            log_error(f"止盈止损计算失败: {e}")
            # 使用默认的止盈止损
            tp_sl_params = {
                'stop_loss': current_price * 0.98,
                'take_profit': current_price * 1.06
            }
        
        # 执行交易
        success = trading_engine.execute_trade_with_tp_sl(
            signal, order_size, tp_sl_params['stop_loss'], tp_sl_params['take_profit']
        )
        
        if success:
            log_info("✅ 简化执行成功")
        else:
            log_error("❌ 简化执行失败")

    def _update_risk_management(self, market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """更新风险管理 - 增强版，包含详细决策分析"""
        position = market_data.get('position')
        if not position or position.get('size', 0) <= 0:
            log_info("📭 当前无持仓，跳过风险管理更新")
            return
        
        log_info("📊 【风险管理检查】检测到持仓，开始全面风险评估...")
        
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
        
        log_info(f"📊 【持仓风险分析】")
        log_info(f"   持仓方向: {side}")
        log_info(f"   持仓数量: {size} BTC")
        log_info(f"   入场价格: ${entry_price:.2f}")
        log_info(f"   当前价格: ${current_price:.2f}")
        log_info(f"   未实现盈亏: ${unrealized_pnl:.2f}")
        
        # 计算当前盈亏
        if side == 'long':
            pnl_percentage = (current_price - entry_price) / entry_price * 100
        else:  # short
            pnl_percentage = (entry_price - current_price) / entry_price * 100
        
        log_info(f"   盈亏百分比: {pnl_percentage:+.2f}%")
        
        # 风险等级评估
        if abs(pnl_percentage) >= 10:
            risk_level = "高风险"
            risk_color = "🔴"
        elif abs(pnl_percentage) >= 5:
            risk_level = "中等风险"
            risk_color = "🟡"
        else:
            risk_level = "低风险"
            risk_color = "🟢"
        
        log_info(f"   风险等级: {risk_color} {risk_level}")
        
        # 基于盈亏状态提供建议
        if pnl_percentage > 0:
            log_info(f"💰 【盈利状态建议】")
            log_info(f"   • 当前处于盈利状态，考虑设置保护性止盈")
            log_info(f"   • 可以适当上调止损位，保护已有利润")
            log_info(f"   • 关注市场是否出现反转信号")
            
            if pnl_percentage >= 10:
                log_info(f"   ⚠️ 盈利较高，注意获利了结的时机")
            elif pnl_percentage >= 5:
                log_info(f"   ✅ 盈利良好，可以继续持有观察")
                
        elif pnl_percentage < 0:
            log_info(f"📉 【亏损状态建议】")
            log_info(f"   • 当前处于亏损状态，严格执行止损纪律")
            log_info(f"   • 检查是否触及止损位，及时止损")
            log_info(f"   • 评估是否需要减仓或平仓")
            
            if pnl_percentage <= -10:
                log_info(f"   🚨 亏损较大，考虑立即止损或大幅减仓")
            elif pnl_percentage <= -5:
                log_info(f"   ⚠️ 亏损中等，密切关注市场走势")
        else:
            log_info(f"⚖️ 【平衡状态建议】")
            log_info(f"   • 当前接近盈亏平衡点")
            log_info(f"   • 关注价格突破方向，准备相应操作")
            log_info(f"   • 保持现有止盈止损设置")
        
        # 价格暴跌保护检查
        if self._check_price_crash_protection(current_position, market_data):
            return
        
        # 计算动态止盈止损 - 修复未定义变量问题
        try:
            from strategies import RiskManager
            risk_manager = RiskManager()
            signal = 'BUY' if current_position['side'] == 'long' else 'SELL'
            
            dynamic_tp_sl = risk_manager.calculate_dynamic_tp_sl(
                signal, current_price, market_state, current_position
            )
            
            log_info(f"📊 【动态止盈止损】")
            log_info(f"   建议止损价: ${dynamic_tp_sl['stop_loss']:.2f}")
            log_info(f"   建议止盈价: ${dynamic_tp_sl['take_profit']:.2f}")
            log_info(f"   止损幅度: {abs((dynamic_tp_sl['stop_loss'] - current_price) / current_price * 100):.2f}%")
            log_info(f"   止盈幅度: {abs((dynamic_tp_sl['take_profit'] - current_price) / current_price * 100):.2f}%")
            
            # 更新止盈止损
            tp_sl_success = trading_engine.update_risk_management(
                current_position,
                dynamic_tp_sl['stop_loss'],
                dynamic_tp_sl['take_profit']
            )
            
            if tp_sl_success:
                log_info("✅ 止盈止损更新成功")
            else:
                log_warning("⚠️ 止盈止损更新失败，使用现有设置")
                
        except Exception as e:
            log_error(f"风险管理更新失败: {e}")
    
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
                    # 使用交易引擎直接执行横盘处理动作
                    success = self._execute_consolidation_action(action, position, market_data)
                    
                    if success:
                        log_info(f"✅ 横盘处理动作执行成功：{action}")
                    else:
                        log_error(f"❌ 横盘处理动作执行失败：{action}")
                        
            else:
                # 检查是否应该退出横盘状态
                if consolidation_detector.should_exit_consolidation(market_data):
                    consolidation_detector.reset_consolidation_state()
                    log_info("🔄 退出横盘状态")
                
        except Exception as e:
            log_error(f"检查横盘利润锁定异常: {e}")
    
    def _execute_consolidation_action(self, action: str, position: Dict[str, Any],
                                    market_data: Dict[str, Any]) -> bool:
        """执行横盘处理动作 - 增强版，修复平仓失败问题"""
        try:
            log_info(f"🔄 执行横盘处理动作: {action}")
            log_info(f"📊 当前持仓信息:")
            log_info(f"   持仓方向: {position.get('side', 'unknown')}")
            log_info(f"   持仓数量: {position.get('size', 0)}")
            log_info(f"   入场价格: ${position.get('entry_price', 0):.2f}")
            
            if action == 'partial_close':
                # 部分平仓
                current_size = position.get('size', 0)
                close_ratio = config.get('strategies', 'profit_lock_strategy', {}).get('partial_close_ratio', 0.5)
                close_size = current_size * close_ratio
                
                log_info(f"📊 部分平仓计算:")
                log_info(f"   原始持仓: {current_size}")
                log_info(f"   平仓比例: {close_ratio}")
                log_info(f"   计算平仓数量: {close_size}")
                
                if close_size > 0:
                    # 确保平仓数量不超过持仓数量
                    actual_close_size = min(close_size, current_size)
                    log_info(f"   实际平仓数量: {actual_close_size} (限制后)")
                    
                    # 获取当前持仓方向
                    position_side = position.get('side', 'long')
                    if position_side not in ['long', 'short']:
                        position_side = 'long'  # 默认多头
                    
                    success = trading_engine.close_position(position_side, actual_close_size)
                    if success:
                        log_info(f"✅ 部分平仓成功: {actual_close_size} BTC")
                        return True
                    else:
                        log_error(f"❌ 部分平仓失败: {position_side} 方向 {actual_close_size} 张")
                        return False
                else:
                    log_warning(f"⚠️ 计算出的平仓数量无效: {close_size}")
                    return False
                        
            elif action == 'full_close':
                # 全部平仓
                current_size = position.get('size', 0)
                position_side = position.get('side', 'long')
                if position_side not in ['long', 'short']:
                    position_side = 'long'
                
                log_info(f"📊 全部平仓:")
                log_info(f"   平仓方向: {position_side}")
                log_info(f"   平仓数量: {current_size}")
                
                if current_size > 0:
                    success = trading_engine.close_position(position_side, current_size)
                    if success:
                        log_info("✅ 全部平仓成功")
                        return True
                    else:
                        log_error(f"❌ 全部平仓失败: {position_side} 方向 {current_size} 张")
                        return False
                else:
                    log_warning("⚠️ 持仓数量为0，无需平仓")
                    return True
                    
            elif action == 'cancel_orders':
                # 取消所有挂单
                success = trading_engine.cancel_all_orders()
                if success:
                    log_info("✅ 取消所有挂单成功")
                    return True
                else:
                    log_error("❌ 取消挂单失败")
                    return False
                    
            else:
                log_warning(f"⚠️ 未知的横盘处理动作: {action}")
                return False
                
        except Exception as e:
            log_error(f"执行横盘处理动作异常: {type(e).__name__}: {e}")
            import traceback
            log_error(f"横盘处理动作堆栈:\n{traceback.format_exc()}")
            return False
    
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
        if len(self.state.price_history) == 0:
            # 如果没有历史数据，提供默认值
            current_price = 50000  # 默认BTC价格
            log_warning("⚠️ 价格历史数据为空，使用默认值")
            return {
                'close': [current_price] * 6,
                'high': [current_price * 1.001] * 6,
                'low': [current_price * 0.999] * 6,
                'volume': [1000000] * 6
            }
        
        data_slice = self.state.price_history[-20:] if len(self.state.price_history) >= 20 else self.state.price_history
        
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
        if len(self.state.price_history) > 1000:
            self.state.price_history = self.state.price_history[-500:]
        
        # 内存管理 - 每10轮清理一次，显示易懂的统计信息
        if self.state.current_cycle % 10 == 0:  # 每10轮清理一次
            memory_stats = memory_manager.get_memory_stats()
            log_info("📊 【系统内存状态】")
            log_info(f"   💾 内存使用: {memory_stats['total_items']} 条记录")
            log_info(f"   🔑 数据类型: {memory_stats['keys_count']} 种")
            log_info(f"   📏 单类上限: {memory_stats['max_per_key']} 条")
            log_info(f"   💻 内存占用: {memory_stats['memory_usage_mb']:.2f} MB")
            log_info(f"   🟢 健康状态: {memory_stats['status']}")
        
        # 缓存管理 - 每20轮检查一次，显示易懂的统计信息
        if self.state.current_cycle % 20 == 0:  # 每20轮检查一次
            cache_stats = cache_manager.get_stats()
            log_info("📊 【系统缓存状态】")
            log_info(f"   📦 缓存数量: {cache_stats['size']} 条")
            log_info(f"   🎯 缓存上限: {cache_stats['max_size']} 条")
            log_info(f"   📈 使用率: {(cache_stats['size'] / cache_stats['max_size'] * 100):.1f}%")
        
        # 系统监控 - 每5轮更新一次，显示易懂的统计信息
        if self.state.current_cycle % 5 == 0:  # 每5轮更新一次
            system_stats = system_monitor.get_stats()
            log_info("📊 【系统运行状态】")
            log_info(f"   ⏱️ 运行时间: {system_stats['uptime_formatted']}")
            log_info(f"   📈 交易次数: {system_stats['trades']} 次")
            log_info(f"   🔍 API调用: {system_stats['api_calls']} 次")
            log_info(f"   ⚠️ 警告次数: {system_stats['warnings']} 次")
            log_info(f"   ❌ 错误次数: {system_stats['errors']} 次")
            log_info(f"   📊 错误率: {system_stats['error_rate']*100:.2f}%")
            log_info(f"   💯 健康分数: {system_stats['system_health']:.1f}/100")
            if 'status_description' in system_stats:
                log_info(f"   📋 状态描述: {system_stats['status_description']}")
        
        # 数据管理 - 保存性能指标
        if self.state.current_cycle % 10 == 0:  # 每10轮保存一次
            try:
                performance_metrics = {
                    'cycle': self.state.current_cycle,
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
        if self.state.current_cycle % 100 == 0:  # 每100轮清理一次
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
    
    def run(self) -> None:
        """运行交易机器人
        
        启动交易机器人的主循环，处理交易周期和异常恢复
        """
        try:
            # 在启动时明确显示当前模式
            test_mode = config.get('trading', 'test_mode')
            if test_mode:
                log_info("🚀 Alpha Pilot Bot OKX 交易机器人启动成功！")
                log_info("🔧 当前模式: 🔴 模拟交易模式 - 所有交易都是虚拟的")
            else:
                log_info("🚀 Alpha Pilot Bot OKX 交易机器人启动成功！")
                log_info("🔧 当前模式: 💰 实盘交易模式 - 所有交易都是真实的")
                log_warning("⚠️ 警告: 您正在使用真实资金进行交易，请确保了解相关风险！")
            
            self.state.is_running = True
            
            while self.state.is_running:
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
                    self.state.is_running = False
                    break
                except Exception as e:
                    log_error(f"交易循环异常: {e}")
                    time.sleep(60)  # 等待1分钟后重试
                    
        except Exception as e:
            log_error(f"启动失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止交易机器人
        
        安全停止交易机器人，清理资源并保存状态
        """
        self.state.is_running = False
        log_info("🛑 交易机器人已停止")
        
        # 关闭日志文件
        try:
            from utils import close_log_file
            close_log_file()
        except Exception as e:
            print(f"关闭日志文件失败: {e}")

def main():
    """主函数"""
    bot = AlphaArenaBot()
    bot.run()

if __name__ == "__main__":
    main()
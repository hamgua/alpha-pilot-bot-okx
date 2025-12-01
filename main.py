"""
Alpha Arena OKX - 重构版主程序
基于模块化架构的OKX自动交易系统
"""

import time
import threading
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional

# 导入模块
from config import config
from trading import trading_engine
from strategies import (
    market_analyzer, risk_manager, signal_processor, 
    consolidation_detector, crash_protection
)
from utils import (
    cache_manager, memory_manager, system_monitor, 
    data_validator, json_helper, time_helper, logger_helper
)
from logger_config import log_info, log_warning, log_error
from trade_logger import trade_logger
from data_manager import update_system_status, save_trade_record, data_management_system
from ai_client import ai_client
import asyncio

class AlphaArenaBot:
    """Alpha Arena OKX 交易机器人主类"""
    
    def __init__(self):
        self.is_running = False
        self.current_cycle = 0
        self.last_signal = None
        self.price_history = []
        self.signal_cache = {}
        self.data_manager = data_management_system
        
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
        return asyncio.run(self._get_ai_signal_async(market_data))
    
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
        """生成AI信号（简化版）"""
        # 这里应该调用实际的AI服务，暂时使用简化逻辑
        price = market_data['price']
        position = market_data['position']
        
        # 基础技术分析
        trend = self._analyze_simple_trend()
        volatility = self._calculate_recent_volatility()
        
        # 生成信号
        if trend > 0.6 and volatility < 5.0:
            signal = 'BUY'
            confidence = 0.8
            reason = '上升趋势 + 低波动率'
        elif trend < -0.6 and volatility < 5.0:
            signal = 'SELL'
            confidence = 0.8
            reason = '下降趋势 + 低波动率'
        else:
            signal = 'HOLD'
            confidence = 0.5
            reason = '趋势不明或波动过大'
        
        # 如果有持仓，考虑平仓逻辑
        if position and position.get('size', 0) > 0:
            entry_price = position.get('entry_price', 0)
            if entry_price > 0:
                profit_pct = (price - entry_price) / entry_price
                
                # 盈利保护
                if profit_pct > 0.05:  # 5%盈利
                    signal = 'SELL'
                    confidence = 0.9
                    reason = f'盈利保护 ({profit_pct:.2%})'
                elif profit_pct < -0.02:  # 2%亏损
                    signal = 'SELL'
                    confidence = 0.7
                    reason = f'止损保护 ({profit_pct:.2%})'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'trend': trend,
            'volatility': volatility
        }
    
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
        providers = ['deepseek', 'kimi']
        
        # 获取信号，设置超时
        try:
            signals = await asyncio.wait_for(
                ai_client.get_multi_ai_signals(market_data, providers),
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
        # 使用现有的简化版信号生成
        return self._generate_ai_signal(market_data)
    
    async def _get_fallback_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取回退信号（增强版）"""
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

            # 计算技术指标
            atr_pct = market_analyzer.calculate_atr(
                [market_data['price']] * 20,  # 简化版
                [market_data['price']] * 20,
                self.price_history,
                14
            )

            trend_strength = market_analyzer.identify_trend(self.price_history)

            # 波动率分类
            if atr_pct > 3.0:
                volatility = 'high'
            elif atr_pct < 1.0:
                volatility = 'low'
            else:
                volatility = 'normal'

            # 计算价格变化率
            price_change_pct = 0
            if len(self.price_history) >= 2:
                price_change_pct = (market_data['price'] - self.price_history[-2]) / self.price_history[-2]

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
            log_info(f"📈 BTC当前价格: ${current_price:,.2f}")
            log_info(f"📊 数据周期: {config.get('exchange', 'timeframe')}")
            
            # 2. 分析市场状态
            log_info("🔍 分析市场状态...")
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
            log_info("📊 获取新的AI信号...")
            try:
                signal_data = self.get_ai_signal({**market_data, **market_state})
                log_info(f"🤖 AI信号: {signal_data.get('signal', 'HOLD')} (信心: {signal_data.get('confidence', 'LOW')})")
                log_info(f"💡 AI理由: {signal_data.get('reason', '无')}")
            except Exception as e:
                log_error(f"获取AI信号失败: {e}")
                return
            
            # 4. 处理信号
            log_info("🔍 处理交易信号...")
            try:
                final_signal = signal_processor.process_signal(
                    signal_data, market_data.get('position')
                )
                log_info(f"🎯 最终交易信号: {final_signal}")
            except Exception as e:
                log_error(f"处理信号失败: {e}")
                return
            
            # 5. 执行交易决策
            if final_signal != 'HOLD':
                log_info(f"🎯 准备执行交易: {final_signal}")
                try:
                    self._execute_trade_signal(final_signal, signal_data, market_data, market_state)
                except Exception as e:
                    log_error(f"执行交易决策失败: {e}")
            else:
                log_info("📊 当前无交易信号，保持观望")
            
            # 6. 更新风险管理
            log_info("🔍 检查持仓止盈止损状态...")
            try:
                self._update_risk_management(market_data, market_state)
            except Exception as e:
                log_error(f"更新风险管理失败: {e}")
            
            # 7. 检查横盘利润锁定
            log_info("🔒 检查横盘利润锁定...")
            try:
                self._check_consolidation_profit_lock(market_data)
            except Exception as e:
                log_error(f"检查横盘利润锁定失败: {e}")
            
            # 8. 系统维护
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
        """执行交易信号"""
        log_info(f"🎯 执行交易信号: {signal}")
        
        current_price = market_data['price']
        position = market_data.get('position')
        
        # 检查暴跌保护
        crash_decision = market_state.get('crash_protection', {})
        if crash_decision.get('should_protect', False):
            log_info(f"🚨 暴跌保护触发 - 风险等级: {crash_decision.get('risk_level', 'unknown')}")
            log_info(f"   触发原因: {crash_decision.get('reason', '未知')}")
            
            # 根据风险等级调整交易行为
            if crash_decision.get('action') in ['IMMEDIATE_CLOSE', 'EMERGENCY_STOP']:
                signal = 'SELL'  # 强制平仓
                signal_data['reason'] = f'暴跌保护: {crash_decision.get("reason", "")}'
                log_info("🛑 执行强制平仓操作")
            elif crash_decision.get('action') == 'PROTECTIVE_STOP':
                # 继续交易但增强保护
                signal_data['reason'] = '暴跌保护模式'
                log_info("⚠️ 进入暴跌保护模式")
        
        # 检查横盘利润锁定
        if market_state.get('should_lock_profit', False) and position:
            log_info("🔒 检测到横盘利润锁定条件，执行平仓操作")
            signal = 'SELL'  # 强制平仓
            signal_data['reason'] = '横盘利润锁定'
        
        # 计算动态止盈止损
        log_info("📊 计算动态止盈止损...")
        tp_sl_params = risk_manager.calculate_dynamic_tp_sl(
            signal, current_price, market_state, position
        )
        
        log_info(f"📊 止盈止损参数:")
        log_info(f"   - 止损价格: ${tp_sl_params['stop_loss']:.2f}")
        log_info(f"   - 止盈价格: ${tp_sl_params['take_profit']:.2f}")
        log_info(f"   - 止损百分比: {tp_sl_params['sl_pct']:.2%}")
        log_info(f"   - 止盈百分比: {tp_sl_params['tp_pct']:.2%}")
        
        # 根据暴跌风险调整止盈止损
        crash_decision = market_state.get('crash_protection', {})
        if crash_decision.get('risk_level') == 'HIGH':
            # 高风险时收紧止损
            adjusted_sl = current_price * 0.99 if signal == 'BUY' else current_price * 1.01
            adjusted_tp = current_price * 1.01 if signal == 'BUY' else current_price * 0.99
            
            tp_sl_params['stop_loss'] = adjusted_sl
            tp_sl_params['take_profit'] = adjusted_tp
            
            log_info("⚠️ 高风险模式，收紧止盈止损:")
            log_info(f"   - 调整后止损: ${adjusted_sl:.2f}")
            log_info(f"   - 调整后止盈: ${adjusted_tp:.2f}")
        
        # 计算订单大小
        log_info("💰 计算订单大小...")
        order_size = signal_processor.calculate_order_size(
            market_data['balance'], signal, current_price
        )
        
        log_info(f"📊 订单详情:")
        log_info(f"   - 交易方向: {signal}")
        log_info(f"   - 订单数量: {order_size:.4f} 张")
        log_info(f"   - 当前价格: ${current_price:.2f}")
        log_info(f"   - 交易理由: {signal_data.get('reason', '策略信号')}")
        
        if order_size <= 0:
            log_warning("⚠️ 订单大小为0，跳过交易")
            return
        
        # 执行带止盈止损的交易
        log_info("🚀 执行交易...")
        success = trading_engine.execute_trade_with_tp_sl(
            signal, order_size, tp_sl_params['stop_loss'], tp_sl_params['take_profit']
        )
        
        if success:
            log_info("✅ 交易执行成功")
            # 记录交易日志
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'signal': signal,
                'price': current_price,
                'size': order_size,
                'stop_loss': tp_sl_params['stop_loss'],
                'take_profit': tp_sl_params['take_profit'],
                'reason': signal_data.get('reason', '策略信号'),
                'confidence': signal_data.get('confidence', 0.5)
            }
            
            try:
                self.data_manager.save_trade_record(trade_record)
                log_info("📊 交易记录已保存")
            except Exception as e:
                log_warning(f"保存交易记录失败: {e}")
        else:
            log_error("❌ 交易执行失败")
        
        if success:
            system_monitor.increment_counter('trades')
            logger_helper.log_trade_event('TRADE_EXECUTED', {
                'signal': signal,
                'price': market_data['price'],
                'size': order_size,
                'confidence': signal_data['confidence'],
                'reason': signal_data.get('reason', 'AI signal'),
                'stop_loss': tp_sl_params['stop_loss'],
                'take_profit': tp_sl_params['take_profit'],
                'risk_level': tp_sl_params['risk_level'],
                'tp_sl_confidence': tp_sl_params['confidence'],
                'crash_protection': crash_decision
            })
            
            # 保存交易记录
            self._save_trade_record(signal, market_data, signal_data, order_size)
    
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
        
        log_info(f"📊 当前持仓详情:")
        log_info(f"   - 方向: {side.upper()}")
        log_info(f"   - 数量: {size:.4f} 张")
        log_info(f"   - 入场价: ${entry_price:.2f}")
        log_info(f"   - 当前价: ${current_price:.2f}")
        log_info(f"   - 未实现盈亏: {unrealized_pnl:+.2f} USDT ({pnl_percentage:+.2f}%)")
        
        # 计算动态止盈止损
        log_info("📊 计算动态止盈止损...")
        signal = 'BUY' if current_position['side'] == 'long' else 'SELL'
        
        dynamic_tp_sl = risk_manager.calculate_dynamic_tp_sl(
            signal, current_price, market_state, current_position
        )
        
        log_info(f"📊 智能止盈止损计算结果:")
        log_info(f"   - 止损价格: ${dynamic_tp_sl['stop_loss']:.2f}")
        log_info(f"   - 止盈价格: ${dynamic_tp_sl['take_profit']:.2f}")
        log_info(f"   - 止损距离: {dynamic_tp_sl['sl_pct']:.2%}")
        log_info(f"   - 止盈距离: {dynamic_tp_sl['tp_pct']:.2%}")
        
        # 价格暴跌保护检查
        if self._check_price_crash_protection(current_position, market_data):
            log_info("🛡️ 价格暴跌保护激活，跳过止损更新")
            return
        
        # 检查当前止盈止损状态
        log_info("🔍 检查当前止盈止损状态...")
        
        # 更新止盈止损
        log_info("🔄 更新止盈止损...")
        success = trading_engine.update_risk_management(
            current_position,
            dynamic_tp_sl['stop_loss'],
            dynamic_tp_sl['take_profit']
        )
        
        if success:
            log_info(f"🛡️ 风险管理更新成功")
            log_info(f"   止损: ${dynamic_tp_sl['stop_loss']:.2f}")
            log_info(f"   止盈: ${dynamic_tp_sl['take_profit']:.2f}")
        else:
            log_error("❌ 风险管理更新失败")
    
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
        """检查横盘利润锁定"""
        position = market_data.get('position')
        
        if not position or position.get('size', 0) <= 0:
            log_info("📭 无持仓，跳过横盘利润锁定检查")
            return
        
        log_info("🔒 开始检查横盘利润锁定条件...")
        
        try:
            current_price = market_data['price']
            entry_price = position['entry_price']
            side = position['side']
            size = position['size']
            
            # 计算当前盈利
            if side == 'long':
                profit_pct = (current_price - entry_price) / entry_price * 100
            else:  # short
                profit_pct = (entry_price - current_price) / entry_price * 100
            
            log_info(f"📊 当前持仓盈利状态:")
            log_info(f"   - 方向: {side.upper()}")
            log_info(f"   - 数量: {size:.4f} 张")
            log_info(f"   - 入场价: ${entry_price:.2f}")
            log_info(f"   - 当前价: ${current_price:.2f}")
            log_info(f"   - 盈利百分比: {profit_pct:+.2f}%")
            
            price_history = self._get_price_history_for_analysis()
            
            if not price_history:
                log_warning("⚠️ 价格历史数据不足，跳过横盘检查")
                return
                
            log_info(f"📊 获取价格历史数据: {len(price_history)} 条记录")
            
            should_lock = consolidation_detector.should_lock_profit(position, market_data, price_history)
            
            if should_lock:
                log_info("✅ 横盘利润锁定条件满足")
                log_info(f"   - 触发锁定价格: ${current_price:.2f}")
                log_info(f"   - 锁定盈利: {profit_pct:.2f}%")
                
                # 记录锁定事件
                lock_record = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'CONSOLIDATION_LOCK',
                    'price': current_price,
                    'profit_pct': profit_pct,
                    'position_side': side,
                    'position_size': size
                }
                
                try:
                    self.data_manager.save_trade_record(lock_record)
                    log_info("📊 横盘锁定记录已保存")
                except Exception as e:
                    log_warning(f"保存横盘锁定记录失败: {e}")
            else:
                log_info("📊 横盘利润锁定条件不满足，继续持有")
                
        except Exception as e:
            log_error(f"检查横盘利润锁定异常: {e}")
    
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
        # 这里简化处理，实际应用中应该从交易所获取完整的历史数据
        # 确保至少有6个数据点来避免None错误
        min_data_points = max(6, len(self.price_history))
        
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
        
        log_info(f"📊 获取价格历史数据: {len(data_slice)} 条记录")
        if len(data_slice) < 6:
            log_warning(f"⚠️ 价格历史数据不足: {len(data_slice)} 条，可能影响分析准确性")
        
        return {
            'close': data_slice,
            'high': data_slice,
            'low': data_slice,
            'volume': [1000000] * len(data_slice)
        }
    
    def _perform_system_maintenance(self):
        """执行系统维护"""
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
    
    def run(self):
        """运行交易机器人"""
        try:
            log_info("🚀 Alpha Arena OKX 交易机器人启动成功！")
            self.is_running = True
            
            while self.is_running:
                try:
                    self.execute_trading_cycle()
                    
                    # 等待下个周期
                    sleep_time = time_helper.get_time_until_next(15)  # 15分钟周期
                    log_info(f"⏰ 等待下次循环: {sleep_time:.1f}秒")
                    time.sleep(sleep_time)
                    
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
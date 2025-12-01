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
    consolidation_detector
)
from utils import (
    cache_manager, memory_manager, system_monitor, 
    data_validator, json_helper, time_helper, logger_helper
)
from logger_config import log_info, log_warning, log_error
from trade_logger import trade_logger
from data_manager import update_system_status, save_trade_record
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
        
        log_info("🚀 Alpha Arena OKX 交易机器人初始化中...")
        self._display_startup_info()
    
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
        log_info("=" * 60)
        
        # 显示配置信息
        log_info(f"🔄 交易模式: {'模拟交易' if config.get('trading', 'test_mode') else '实盘交易'}")
        log_info(f"📈 交易对: {config.get('exchange', 'symbol')}")
        log_info(f"⏰ 时间框架: {config.get('exchange', 'timeframe')}")
        log_info(f"🔧 杠杆倍数: {config.get('trading', 'leverage')}x")
        log_info(f"🤖 AI模式: {'多模型' if config.get('ai', 'use_multi_ai') else '单模型'}")
        log_info("=" * 60)
    
    def get_ai_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取AI交易信号"""
        # 检查缓存
        cache_key = f"signal_{market_data['price']:.2f}"
        cached_signal = cache_manager.get(cache_key)
        
        if cached_signal and not self._should_refresh_signal():
            log_info("📊 使用缓存的AI信号")
            return cached_signal
        
        # 生成新信号
        log_info("📊 获取新的AI信号...")
        
        try:
            # 检查是否启用多AI模式
            use_multi_ai = config.get('ai', 'use_multi_ai')
            
            if use_multi_ai:
                # 多AI模式
                providers = ['deepseek', 'kimi']
                signals = asyncio.run(ai_client.get_multi_ai_signals(market_data, providers))
                
                if signals:
                    signal_data = ai_client.fuse_signals(signals)
                    log_info("📊 【多AI融合信号分析】")
                    log_info(f"   📈 最终信号: {signal_data['signal']}")
                    log_info(f"   💡 融合信心: {signal_data['confidence']:.1f}")
                else:
                    # 如果多AI失败，使用回退信号
                    signal_data = self._create_fallback_signal(market_data)
                    log_warning("多AI信号获取失败，使用回退信号")
            else:
                # 单AI模式 - 使用简化版
                signal_data = self._generate_ai_signal(market_data)
            
            # 缓存信号
            cache_manager.set(cache_key, signal_data, config.get('ai', 'cache_duration'))
            
            # 记录信号
            memory_manager.add_to_history('signals', signal_data)
            system_monitor.increment_counter('api_calls')
            
            return signal_data
            
        except Exception as e:
            log_error(f"AI信号生成失败: {e}")
            return self._create_fallback_signal(market_data)
    
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
        # 更新价格历史
        self.price_history.append(market_data['price'])
        if len(self.price_history) > 100:
            self.price_history.pop(0)
        
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
        
        return {
            'atr_pct': atr_pct,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'price': market_data['price'],
            'bid': market_data['bid'],
            'ask': market_data['ask']
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
            market_data = trading_engine.get_market_data()
            if not market_data or not market_data.get('price'):
                log_error("获取市场数据失败")
                return
            
            # 2. 分析市场状态
            market_state = self.analyze_market_state(market_data)
            
            # 3. 获取AI信号
            signal_data = self.get_ai_signal({**market_data, **market_state})
            
            # 4. 处理信号
            final_signal = signal_processor.process_signal(
                signal_data, market_data.get('position')
            )
            
            # 5. 执行交易决策
            if final_signal != 'HOLD':
                self._execute_trade_signal(final_signal, signal_data, market_data, market_state)
            
            # 6. 更新风险管理
            self._update_risk_management(market_data, market_state)
            
            # 7. 检查横盘利润锁定
            self._check_consolidation_profit_lock(market_data)
            
            # 8. 系统维护
            self._perform_system_maintenance()
            
            log_info(f"✅ 第 {self.current_cycle} 轮交易周期完成")
            
        except Exception as e:
            log_error(f"交易周期异常: {e}")
            system_monitor.increment_counter('errors')
    
    def _execute_trade_signal(self, signal: str, signal_data: Dict[str, Any], 
                            market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """执行交易信号"""
        log_info(f"🎯 执行交易信号: {signal}")
        
        # 计算订单大小
        order_size = signal_processor.calculate_order_size(
            market_data['balance'], signal, market_data['price']
        )
        
        if order_size <= 0:
            log_warning("订单大小为0，跳过交易")
            return
        
        # 执行交易
        success = trading_engine.execute_trade(signal, order_size)
        
        if success:
            system_monitor.increment_counter('trades')
            logger_helper.log_trade_event('TRADE_EXECUTED', {
                'signal': signal,
                'price': market_data['price'],
                'size': order_size,
                'confidence': signal_data['confidence']
            })
            
            # 保存交易记录
            self._save_trade_record(signal, market_data, signal_data, order_size)
    
    def _update_risk_management(self, market_data: Dict[str, Any], market_state: Dict[str, Any]):
        """更新风险管理"""
        position = market_data.get('position')
        if not position or position.get('size', 0) <= 0:
            return
        
        # 计算动态止盈止损
        current_position = trading_engine.get_position_info()
        if not current_position['has_position']:
            return
        
        # 获取信号方向用于计算
        signal = 'BUY' if current_position['side'] == 'long' else 'SELL'
        
        dynamic_tp_sl = risk_manager.calculate_dynamic_tp_sl(
            signal, market_data['price'], market_state, current_position
        )
        
        # 价格暴跌保护检查
        if self._check_price_crash_protection(current_position, market_data):
            log_info("🛡️ 价格暴跌保护激活，跳过止损更新")
            return
        
        # 更新止盈止损
        success = trading_engine.update_risk_management(
            current_position,
            dynamic_tp_sl['stop_loss'],
            dynamic_tp_sl['take_profit']
        )
        
        if success:
            log_info(f"🛡️ 风险管理更新成功")
            log_info(f"   止损: ${dynamic_tp_sl['stop_loss']:.2f}")
            log_info(f"   止盈: ${dynamic_tp_sl['take_profit']:.2f}")
    
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
            return
        
        # 这里需要传入价格历史数据
        # 简化版：直接调用检测器
        should_lock = consolidation_detector.should_lock_profit(position, market_data)
        
        if should_lock:
            log_info("🔒 横盘利润锁定条件满足")
            # 可以在这里添加具体的锁定逻辑
    
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
    
    def run(self):
        """运行交易机器人"""
        try:
            log_info("🚀 Alpha Arena OKX 交易机器人启动成功！")
            self.is_running = True
            
            while self.is_running:
                try:
                    self.execute_trading_cycle()
                    
                    # 等待下个周期
                    sleep_time = time_helper.get_time_until_next(5)  # 5分钟周期
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
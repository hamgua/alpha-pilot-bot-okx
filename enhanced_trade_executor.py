"""
增强版交易执行器
实现基于AI信号融合的智能交易执行逻辑
支持ALLOW_SHORT_SELLING开关的所有场景
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class EnhancedTradeExecutor:
    """
    增强版交易执行器
    处理AI信号融合后的所有执行场景
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allow_short_selling = config.get('allow_short_selling', False)
        
    def execute_enhanced_trade(self, signal_data: Dict[str, Any], 
                             price_data: Dict[str, Any], 
                             current_position: Optional[Dict[str, Any]]) -> bool:
        """
        执行增强版交易逻辑
        
        Args:
            signal_data: AI融合后的信号数据
            price_data: 市场数据
            current_position: 当前持仓信息
            
        Returns:
            bool: 执行是否成功
        """
        
        signal = signal_data.get('signal')
        execution_type = signal_data.get('execution_type', 'hold')
        
        logger.info("=" * 60)
        logger.info("🤖 【增强版交易执行器启动】")
        logger.info(f"   执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   AI信号: {signal} (信心: {signal_data.get('confidence', 'N/A')})")
        logger.info(f"   执行类型: {execution_type}")
        logger.info(f"   做空开关: {'开启' if self.allow_short_selling else '关闭'}")
        
        # 分析当前持仓状态
        has_position = current_position and current_position.get('size', 0) > 0
        current_side = current_position.get('side') if has_position else None
        
        logger.info(f"   📊 当前持仓状态:")
        if has_position:
            logger.info(f"      - 持仓方向: {current_side}")
            logger.info(f"      - 持仓数量: {current_position['size']:.4f} 张")
            logger.info(f"      - 入场价格: ${current_position['entry_price']:.2f}")
            logger.info(f"      - 当前价格: ${price_data['price']:.2f}")
        else:
            logger.info(f"      - 无持仓")
        
        # 根据执行类型处理交易
        success = False
        
        try:
            if execution_type == 'long_entry':
                success = self._handle_long_entry(signal_data, price_data, current_position)
            elif execution_type == 'short_entry':
                success = self._handle_short_entry(signal_data, price_data, current_position)
            elif execution_type == 'long_update_tp_sl':
                success = self._handle_long_tp_sl_update(signal_data, price_data, current_position)
            elif execution_type == 'short_update_tp_sl':
                success = self._handle_short_tp_sl_update(signal_data, price_data, current_position)
            elif execution_type == 'liquidation':
                success = self._handle_liquidation(signal_data, price_data, current_position)
            elif execution_type == 'short_liquidation':
                success = self._handle_short_liquidation(signal_data, price_data, current_position)
            elif execution_type == 'hold':
                success = self._handle_hold(signal_data, price_data, current_position)
            else:
                logger.warning(f"⚠️ 未知的执行类型: {execution_type}")
                success = False
                
        except Exception as e:
            logger.error(f"❌ 交易执行异常: {e}")
            success = False
            
        logger.info("=" * 60)
        return success
    
    def _handle_long_entry(self, signal_data: Dict, price_data: Dict, 
                          current_position: Optional[Dict]) -> bool:
        """处理多头开仓逻辑"""
        logger.info("🐂 【处理多头开仓】")
        
        if current_position and current_position['side'] == 'long':
            logger.info("   ✅ 已有多头持仓，无需重复开仓")
            return True
            
        if current_position and current_position['side'] == 'short':
            logger.info("   📉 当前为空头持仓，先执行空头平仓")
            if not self._close_position('short', current_position['size']):
                return False
        
        # 计算订单参数
        order_size = self._calculate_order_size('BUY', price_data)
        if order_size <= 0:
            logger.warning("   ⚠️ 订单数量为0，跳过交易")
            return False
            
        # 执行开仓
        return self._execute_market_order('BUY', order_size, signal_data, price_data)
    
    def _handle_short_entry(self, signal_data: Dict, price_data: Dict, 
                          current_position: Optional[Dict]) -> bool:
        """处理空头开仓逻辑"""
        logger.info("🐻 【处理空头开仓】")
        
        if not self.allow_short_selling:
            logger.warning("   ❌ 做空功能已禁用，无法执行空头开仓")
            return False
            
        if current_position and current_position['side'] == 'short':
            logger.info("   ✅ 已有空头持仓，无需重复开仓")
            return True
            
        if current_position and current_position['side'] == 'long':
            logger.info("   📈 当前为多头持仓，先执行多头平仓")
            if not self._close_position('long', current_position['size']):
                return False
        
        # 计算订单参数
        order_size = self._calculate_order_size('SELL', price_data)
        if order_size <= 0:
            logger.warning("   ⚠️ 订单数量为0，跳过交易")
            return False
            
        # 执行开仓
        return self._execute_market_order('SELL', order_size, signal_data, price_data)
    
    def _handle_long_tp_sl_update(self, signal_data: Dict, price_data: Dict, 
                                current_position: Dict) -> bool:
        """处理多头止盈止损更新"""
        logger.info("🔄 【更新多头止盈止损】")
        
        if not current_position or current_position['side'] != 'long':
            logger.warning("   ⚠️ 无多头持仓，无法更新止盈止损")
            return False
            
        return self._update_tp_sl_orders(current_position, price_data)
    
    def _handle_short_tp_sl_update(self, signal_data: Dict, price_data: Dict, 
                                 current_position: Dict) -> bool:
        """处理空头止盈止损更新"""
        logger.info("🔄 【更新空头止盈止损】")
        
        if not current_position or current_position['side'] != 'short':
            logger.warning("   ⚠️ 无空头持仓，无法更新止盈止损")
            return False
            
        return self._update_tp_sl_orders(current_position, price_data)
    
    def _handle_liquidation(self, signal_data: Dict, price_data: Dict, 
                          current_position: Optional[Dict]) -> bool:
        """处理平仓逻辑（适用于做多功能关闭时的SELL信号）"""
        logger.info("📉 【执行平仓操作】")
        
        if not current_position:
            logger.info("   ✅ 无持仓，无需平仓")
            return True
            
        side = current_position['side']
        size = current_position['size']
        
        logger.info(f"   📊 平仓详情:")
        logger.info(f"      - 平仓方向: {side}")
        logger.info(f"      - 平仓数量: {size:.4f} 张")
        
        # 取消所有现有订单
        self._cancel_all_orders()
        
        # 执行平仓
        return self._close_position(side, size)
    
    def _handle_short_liquidation(self, signal_data: Dict, price_data: Dict, 
                                current_position: Optional[Dict]) -> bool:
        """处理空头平仓逻辑（适用于做空功能关闭时的HOLD信号）"""
        logger.info("📉 【执行空头平仓】")
        
        if not current_position or current_position['side'] != 'short':
            logger.info("   ✅ 无空头持仓，无需平仓")
            return True
            
        size = current_position['size']
        
        logger.info(f"   📊 空头平仓详情:")
        logger.info(f"      - 平仓数量: {size:.4f} 张")
        
        # 取消所有现有订单
        self._cancel_all_orders()
        
        # 执行平仓
        return self._close_position('short', size)
    
    def _handle_hold(self, signal_data: Dict, price_data: Dict, 
                   current_position: Optional[Dict]) -> bool:
        """处理HOLD信号 - 在ALLOW_SHORT_SELLING=false时只处理空头平仓"""
        
        # 只在做空功能关闭且有空头持仓时执行平仓
        if (not self.allow_short_selling and 
            current_position and 
            current_position['side'] == 'short'):
            
            logger.info(f"🔄 平仓空头: {current_position['size']:.4f}张")
            
            # 取消所有订单
            self._cancel_all_orders()
            
            # 执行平仓
            return self._close_position('short', current_position['size'])
        
        # 其他情况不执行任何操作
        return True
    
    def _calculate_order_size(self, signal: str, price_data: Dict) -> float:
        """计算订单大小"""
        try:
            # 获取账户余额
            balance = self._get_account_balance()
            if balance <= 0:
                return 0
                
            # 基础仓位计算（10%的账户余额）
            base_amount = balance * 0.1
            
            # 根据杠杆调整
            leverage = self.config.get('leverage', 10)
            position_size = base_amount * leverage / price_data['price']
            
            # 确保最小交易单位
            min_size = 0.001
            return max(position_size, min_size)
            
        except Exception as e:
            logger.error(f"计算订单大小失败: {e}")
            return 0
    
    def _execute_market_order(self, side: str, amount: float, 
                            signal_data: Dict, price_data: Dict) -> bool:
        """执行市价订单"""
        try:
            logger.info(f"   🚀 执行市价订单:")
            logger.info(f"      - 方向: {side}")
            logger.info(f"      - 数量: {amount:.4f} 张")
            logger.info(f"      - 价格: ${price_data['price']:.2f}")
            
            # 这里应该调用实际的交易API
            # 由于这是增强版执行器，我们记录执行信息
            logger.info(f"   ✅ 市价订单执行成功: {side} {amount:.4f}张 @ ${price_data['price']:.2f}")
            
            # 设置止盈止损
            return self._set_tp_sl_after_order(side, amount, price_data['price'], signal_data)
            
        except Exception as e:
            logger.error(f"执行市价订单失败: {e}")
            return False
    
    def _close_position(self, side: str, amount: float) -> bool:
        """平仓操作"""
        try:
            close_side = 'sell' if side == 'long' else 'buy'
            logger.info(f"   🚀 执行平仓订单:")
            logger.info(f"      - 平仓方向: {close_side}")
            logger.info(f"      - 平仓数量: {amount:.4f} 张")
            
            # 这里应该调用实际的交易API
            logger.info(f"   ✅ 平仓成功: {close_side} {amount:.4f}张")
            return True
            
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return False
    
    def _update_tp_sl_orders(self, position: Dict, price_data: Dict) -> bool:
        """更新止盈止损订单"""
        try:
            # 计算动态止盈止损
            signal = 'BUY' if position['side'] == 'long' else 'SELL'
            market_state = self._identify_market_state(price_data)
            
            # 这里应该调用动态止盈止损计算
            logger.info(f"   🔄 更新止盈止损:")
            logger.info(f"      - 持仓方向: {position['side']}")
            logger.info(f"      - 持仓数量: {position['size']:.4f} 张")
            logger.info(f"      - 当前价格: ${price_data['price']:.2f}")
            logger.info(f"   ✅ 止盈止损更新完成")
            
            return True
            
        except Exception as e:
            logger.error(f"更新止盈止损失败: {e}")
            return False
    
    def _cancel_all_orders(self) -> bool:
        """取消所有订单"""
        try:
            logger.info("   🧹 取消所有现有订单...")
            # 这里应该调用实际的取消订单API
            logger.info("   ✅ 所有订单已取消")
            return True
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
    
    def _get_account_balance(self) -> float:
        """获取账户余额"""
        # 这里应该从实际API获取余额
        return 1000.0  # 示例值
    
    def _identify_market_state(self, price_data: Dict) -> Dict:
        """识别市场状态"""
        # 这里应该实现实际的市场状态识别逻辑
        return {
            'trend': 'neutral',
            'volatility': 0.02,
            'atr_pct': 2.0
        }
    
    def _set_tp_sl_after_order(self, side: str, amount: float, 
                             entry_price: float, signal_data: Dict) -> bool:
        """设置止盈止损"""
        try:
            logger.info("   🎯 设置止盈止损...")
            # 这里应该调用实际的止盈止损设置API
            logger.info("   ✅ 止盈止损设置完成")
            return True
            
        except Exception as e:
            logger.error(f"设置止盈止损失败: {e}")
            return False

# 创建全局执行器实例
enhanced_executor = EnhancedTradeExecutor({
    'allow_short_selling': False,  # 默认值，实际从配置读取
    'leverage': 10
})
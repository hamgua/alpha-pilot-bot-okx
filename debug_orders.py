#!/usr/bin/env python3
"""
调试脚本：测试订单获取功能
用于验证当前账户的订单识别问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading import trading_engine
from logger_config import log_info, log_error

def test_order_detection():
    """测试订单识别功能"""
    print("🧪 开始测试订单识别功能...")
    
    try:
        # 获取当前持仓信息
        position = trading_engine.exchange_manager.get_position()
        if position:
            print(f"📊 当前持仓: {position}")
        else:
            print("📊 当前无持仓")
        
        # 获取账户信息
        balance = trading_engine.exchange_manager.get_balance()
        print(f"💰 账户余额: {balance}")
        
        # 获取当前价格
        ticker = trading_engine.exchange_manager.fetch_ticker()
        print(f"💵 当前价格: ${ticker.get('last', 0):.2f}")
        
        # 测试订单识别
        print("🔍 开始识别止盈止损订单...")
        orders = trading_engine.order_manager._get_existing_tp_sl_orders()
        
        print(f"\n📊 识别结果总结:")
        print(f"   找到 {len(orders)} 个止盈止损订单")
        
        for i, order in enumerate(orders, 1):
            print(f"\n   订单 {i}:")
            print(f"      ID: {order['id']}")
            print(f"      类型: {order['type']}")
            print(f"      方向: {order['side']}")
            print(f"      持仓方向: {order['position_side']}")
            print(f"      触发价: ${order['triggerPx']:.2f}")
            print(f"      数量: {order['sz']}")
            print(f"      状态: {order['status']}")
            print(f"      来源: {order['source']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_order_detection()
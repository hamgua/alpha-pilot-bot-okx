"""
策略导入器 - 解决模块和文件同名冲突
"""

import importlib.util
import sys
import os
import asyncio
import inspect

def import_strategies_from_file():
    """从strategies.py文件导入，而不是从strategies包"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    strategies_file = os.path.join(current_dir, 'strategies.py')

    if not os.path.exists(strategies_file):
        raise ImportError("strategies.py not found in current directory")

    # 创建模块规范
    spec = importlib.util.spec_from_file_location("strategies_file", strategies_file)
    if spec is None:
        raise ImportError(f"Cannot load spec for {strategies_file}")

    # 创建模块
    module = importlib.util.module_from_spec(spec)

    # 执行模块
    spec.loader.exec_module(module)

    # 确保asyncio事件循环可用
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    return module

# 创建全局实例
_strategies_module = None

def get_strategies():
    """获取策略模块实例"""
    global _strategies_module
    if _strategies_module is None:
        _strategies_module = import_strategies_from_file()
    return _strategies_module
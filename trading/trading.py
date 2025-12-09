"""
交易模块 - 向后兼容文件
用于兼容仍从根目录导入交易功能的代码
"""

# 从重构后的模块导入所有必要组件
from trading.engine import *
from trading.exchange import *
from trading.position import *
from trading.models import *
from trading.trading import *

# 确保 trading_engine 可用
from trading.engine import trading_engine
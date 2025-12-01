"""
Alpha Arena OKX 启动脚本
用于启动重构后的交易机器人
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    required_modules = [
        'ccxt', 'numpy', 'pandas', 'requests', 'python-dotenv',
        'openai', 'aiohttp', 'asyncio', 'datetime', 'json', 'threading'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺失依赖: {', '.join(missing_modules)}")
        print("请运行: pip install ccxt numpy pandas requests python-dotenv openai aiohttp")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def check_environment():
    """检查环境变量"""
    required_envs = [
        'OKX_API_KEY', 'OKX_SECRET', 'OKX_PASSWORD'
    ]
    
    missing_envs = []
    for env_var in required_envs:
        if not os.getenv(env_var):
            missing_envs.append(env_var)
    
    if missing_envs:
        print(f"❌ 缺失环境变量: {', '.join(missing_envs)}")
        print("请设置以下环境变量:")
        for env in missing_envs:
            print(f"   export {env}=your_value")
        return False
    
    print("✅ 环境变量已配置")
    return True

def validate_files():
    """验证文件完整性"""
    required_files = [
        'config.py', 'trading.py', 'strategies.py', 'utils.py',
        'main.py', 'logger_config.py', 'trade_logger.py',
        'data_manager.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺失文件: {', '.join(missing_files)}")
        return False
    
    print("✅ 所有文件已就绪")
    return True

def run_tests():
    """运行基本测试"""
    try:
        # 测试配置加载
        from config import config
        print("✅ 配置加载测试通过")
        
        # 测试交易引擎
        from trading import trading_engine
        print("✅ 交易引擎测试通过")
        
        # 测试策略模块
        from strategies import market_analyzer, risk_manager
        print("✅ 策略模块测试通过")
        
        # 测试工具模块
        from utils import cache_manager, system_monitor
        print("✅ 工具模块测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主启动函数"""
    print("🚀 Alpha Arena OKX 启动检查中...")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查环境
    if not check_environment():
        print("⚠️  环境检查失败，将以模拟模式运行")
        os.environ['TEST_MODE'] = 'true'
    
    # 验证文件
    if not validate_files():
        sys.exit(1)
    
    # 运行测试
    if not run_tests():
        sys.exit(1)
    
    print("=" * 50)
    print("🎉 所有检查通过！准备启动交易机器人...")
    
    # 启动主程序
    try:
        from alpha_arena_okx import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")

if __name__ == "__main__":
    main()
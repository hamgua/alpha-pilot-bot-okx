#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alpha Pilot Bot OKX - 重构版统一启动程序
适用于宝塔面板等单入口部署场景

智能启动：
1. 交易程序（main.py）- 重构版优先
2. Web监控界面（streamlit）- 根据配置决定是否启动
3. 支持向后兼容旧版（deepseekok2.py）

基于模块化架构重构，支持配置与逻辑分离
"""

import os
import sys
import time
import signal
import subprocess
from multiprocessing import Process
from pathlib import Path

# 读取配置，决定是否启动Web界面
try:
    # 临时导入获取配置
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import config
    WEB_CONFIG = config.get('system', 'web_interface', {})
    WEB_ENABLED = WEB_CONFIG.get('enabled', False)
    WEB_PORT = WEB_CONFIG.get('port', 8501)
except Exception as e:
    print(f"[WARNING] 读取配置失败，使用默认配置: {e}")
    WEB_ENABLED = False
    WEB_PORT = 8501

# 只有在启用Web界面时才设置Streamlit环境变量
if WEB_ENABLED:
    os.environ['STREAMLIT_CONFIG_DIR'] = os.path.join(os.getcwd(), '.streamlit_config')
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'

# 全局进程列表
processes = []

from utils import log_info as log

def run_trading_bot():
    """运行交易程序（重构版）"""
    try:
        log("🤖 启动Alpha Pilot Bot OKX交易程序...")
        # 导入重构版交易程序主函数
        from main import AlphaArenaBot
        
        bot = AlphaArenaBot()
        bot.run()
        
    except KeyboardInterrupt:
        log("🛑 交易程序收到停止信号")
    except Exception as e:
        log(f"❌ 交易程序异常: {e}")
        import traceback
        traceback.print_exc()
        # 交易程序异常后等待一段时间再重试
        time.sleep(10)
        log("🔄 重启交易程序...")
        run_trading_bot()

def run_legacy_trading_bot():
    """运行旧版交易程序（备用）"""
    try:
        log("🤖 启动旧版交易程序...")
        # 导入旧版交易程序主函数
        import deepseekok2
        deepseekok2.main()
        
    except KeyboardInterrupt:
        log("🛑 旧版交易程序收到停止信号")
    except Exception as e:
        log(f"❌ 旧版交易程序异常: {e}")
        import traceback
        traceback.print_exc()
        # 交易程序异常后等待一段时间再重试
        time.sleep(10)
        log("🔄 重启旧版交易程序...")
        run_legacy_trading_bot()

def run_web_interface():
    """运行Web界面"""
    try:
        log("🌐 启动Web监控界面...")
        
        # 设置额外的环境变量
        env = os.environ.copy()
        env['STREAMLIT_SERVER_HEADLESS'] = 'true'
        env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
        env['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
        
        # 使用subprocess运行streamlit
        streamlit_cmd = [
            sys.executable,
            "-m", "streamlit",
            "run",
            "streamlit_app.py",
            "--server.headless", "true",
            "--server.address", "0.0.0.0",
            "--server.port", str(WEB_PORT),
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--server.fileWatcherType", "none"
        ]
        
        process = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env  # 传递环境变量
        )
        
        # 实时输出streamlit日志
        for line in process.stdout:
            log(f"[WEB] {line.strip()}")
        
        process.wait()
        
    except Exception as e:
        log(f"❌ Web界面异常: {e}")
        import traceback
        traceback.print_exc()
        # Web界面异常后等待一段时间再重试
        time.sleep(10)
        log("🔄 重启Web界面...")
        run_web_interface()

def signal_handler(signum, frame):
    """处理终止信号"""
    log("⚠️ 收到终止信号，正在停止所有服务...")
    
    # 终止所有子进程
    for p in processes:
        try:
            if p.is_alive():
                log(f"停止进程: {p.name}")
                p.terminate()
        except (ValueError, AttributeError) as e:
            # 进程已经终止或无效
            log(f"进程 {p.name} 已停止")
    
    # 等待所有进程结束
    for p in processes:
        try:
            p.join(timeout=5)
            if p.is_alive():
                log(f"强制终止进程: {p.name}")
                p.kill()
        except (ValueError, AttributeError) as e:
            # 进程已经终止或无效
            pass
    
    log("✅ 所有服务已停止")
    sys.exit(0)

def check_environment():
    """检查运行环境"""
    log("🔍 检查Alpha Pilot Bot OKX运行环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    log(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        log("❌ 错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 创建必要的目录
    try:
        # Streamlit配置目录
        streamlit_config_dir = os.path.join(os.getcwd(), '.streamlit_config')
        os.makedirs(streamlit_config_dir, exist_ok=True)
        log(f"✅ Streamlit配置目录: {streamlit_config_dir}")
        
        # 数据目录
        data_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # .streamlit目录（如果不存在）
        streamlit_dir = os.path.join(os.getcwd(), '.streamlit')
        os.makedirs(streamlit_dir, exist_ok=True)
    except Exception as e:
        log(f"⚠️ 警告: 创建目录失败 - {e}")
    
    # 检查必要文件
    required_files = ['main.py', 'config.py', 'trading.py', 'strategies.py', 'utils.py']
    for file in required_files:
        if not Path(file).exists():
            log(f"❌ 错误: 缺少必要文件 {file}")
            sys.exit(1)
    
    # 检查可选文件（仅作提示，不影响启动）
    legacy_files = ['deepseekok2.py']
    legacy_available = any(Path(file).exists() for file in legacy_files)
    
    if legacy_available:
        log("ℹ️ 检测到旧版文件，但将使用重构版")
    
    # 检查.env文件
    if not Path('.env').exists():
        log("⚠️ 警告: .env文件不存在")
        log("   请创建.env文件并配置API密钥")
        if Path('.env.example').exists():
            log("   可以从.env.example复制: cp .env.example .env")
    else:
        log("✅ 环境变量文件已配置")
    
    # 检查依赖包
    try:
        import ccxt
        import pandas
        import numpy
        log("✅ 核心依赖包已安装")
        
        # 可选依赖
        optional_deps = []
        try:
            import streamlit
            optional_deps.append("streamlit")
        except ImportError:
            if WEB_ENABLED:
                log("⚠️ 未安装streamlit，但配置文件启用了Web界面")
                log("   请运行: pip install streamlit")
            else:
                log("ℹ️ Web界面已禁用（如需启用请安装: pip install streamlit）")
        
        try:
            import openai
            optional_deps.append("openai")
        except ImportError:
            log("ℹ️ AI增强功能未启用（如需启用请安装: pip install openai）")
        
        if optional_deps:
            log(f"✅ 已启用: {', '.join(optional_deps)}")
        
    except ImportError as e:
        log(f"❌ 错误: 缺少核心依赖包 - {e}")
        log("   请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    log("✅ 环境检查通过")

def detect_version_preference():
    """检测版本偏好（始终使用重构版）"""
    # 检查重构版文件完整性
    new_files = ['main.py', 'config.py', 'trading.py', 'strategies.py', 'utils.py']
    new_complete = all(Path(file).exists() for file in new_files)
    
    if not new_complete:
        log("❌ 重构版文件不完整")
        missing = [f for f in new_files if not Path(f).exists()]
        log(f"缺失文件: {missing}")
        sys.exit(1)
    
    return True

def main():
    """主函数"""
    # 打印启动信息
    log("=" * 60)
    log("🤖 Alpha Pilot Bot OKX - 重构版统一启动程序")
    log("=" * 60)
    log("")
    
    # 检查环境
    check_environment()
    
    # 检测版本（始终使用重构版）
    detect_version_preference()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动信息
    if WEB_ENABLED:
        log("🚀 启动交易程序 + Web监控界面...")
    else:
        log("🚀 启动交易程序...")
    print()
    
    # 始终使用重构版
    log("✅ 使用重构版交易程序（模块化架构）")
    trading_target = run_trading_bot
    
    # 创建交易程序进程（始终启动）
    trading_process = Process(
        target=trading_target,
        name="TradingBot"
    )
    processes.append(trading_process)
    
    # 根据配置决定是否创建Web界面进程
    if WEB_ENABLED:
        web_process = Process(
            target=run_web_interface,
            name="WebInterface"
        )
        processes.append(web_process)
    
    # 启动进程
    trading_process.start()
    if WEB_ENABLED:
        time.sleep(2)  # 等待交易程序初始化
        web_process.start()
    
    if WEB_ENABLED:
        log("✅ 交易程序 + Web界面已启动")
        log("")
        log("=" * 60)
        log("📊 服务信息")
        log("=" * 60)
        log("🤖 交易程序: 运行中")
        log(f"🌐 Web监控界面: http://localhost:{WEB_PORT}")
        log("=" * 60)
    else:
        log("✅ 交易程序已启动")
        log("")
        log("=" * 60)
        log("📊 服务信息")
        log("=" * 60)
        log("🤖 交易程序: 运行中")
        if not WEB_ENABLED:
            log("🌐 Web界面: 已禁用")
        log("=" * 60)
    log("")
    log("💡 按 Ctrl+C 停止所有服务")
    log("")
    
    # 监控进程状态
    try:
        while True:
            time.sleep(10)
            
            # 检查进程是否存活
            for p in processes[:]:  # 使用副本遍历，避免修改列表时出错
                try:
                    if not p.is_alive():
                        log(f"⚠️ 警告: 进程 {p.name} 已停止，正在重启...")
                        
                        # 创建新进程
                        if p.name == "TradingBot":
                            new_process = Process(
                                target=trading_target,
                                name="TradingBot"
                            )
                        elif p.name == "WebInterface" and WEB_ENABLED:
                            new_process = Process(
                                target=run_web_interface,
                                name="WebInterface"
                            )
                        else:
                            continue  # 跳过不重启的进程
                        
                        # 替换进程
                        processes.remove(p)
                        processes.append(new_process)
                        new_process.start()
                        
                        log(f"✅ 进程 {new_process.name} 已重启")
                except (ValueError, AttributeError) as e:
                    log(f"⚠️ 检查进程状态时出错: {e}")
    
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
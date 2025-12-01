#!/usr/bin/env python3
"""
日志查看工具
用于快速查看程序运行日志
"""

import sys
from datetime import datetime
from pathlib import Path

def list_log_files():
    """列出所有日志文件"""
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ logs目录不存在")
        return []
    
    log_files = list(log_dir.glob("deepseekok2-*.log"))
    log_files.sort(reverse=True)  # 最新的在前面
    
    return log_files

def show_log_files():
    """显示所有日志文件列表"""
    log_files = list_log_files()
    
    if not log_files:
        print("📁 没有找到日志文件")
        return
    
    print("\n📊 日志文件列表:")
    print("-" * 50)
    
    for i, log_file in enumerate(log_files, 1):
        size = log_file.stat().st_size
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"{i}. 📄 {log_file.name}")
        print(f"   📅 修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   📏 文件大小: {size:,} 字节")
        print()

def tail_log_file(log_file, lines=50):
    """查看日志文件末尾内容"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        if not content:
            print("📄 日志文件为空")
            return
        
        print(f"\n📋 {log_file.name} 最近 {min(lines, len(content))} 行:")
        print("-" * 80)
        
        for line in content[-lines:]:
            print(line.rstrip())
            
    except Exception as e:
        print(f"❌ 读取日志文件失败: {e}")

def search_logs(keyword, log_file=None):
    """搜索日志内容"""
    log_files = [log_file] if log_file else list_log_files()
    
    if not log_files:
        print("❌ 没有找到日志文件")
        return
    
    found_lines = []
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if keyword.lower() in line.lower():
                        found_lines.append((log_file.name, line_num, line.rstrip()))
        except Exception as e:
            print(f"❌ 读取 {log_file.name} 失败: {e}")
    
    if found_lines:
        print(f"\n🔍 搜索 '{keyword}' 的结果:")
        print("-" * 80)
        for filename, line_num, line in found_lines[-20:]:  # 显示最近20条
            print(f"📄 {filename}:{line_num} | {line}")
    else:
        print(f"🔍 没有找到包含 '{keyword}' 的日志")

def show_help():
    """显示帮助信息"""
    print("""
📋 日志查看工具使用说明

用法:
    python3 view_logs.py [命令] [参数]

命令:
    list        - 列出所有日志文件
    tail [n]    - 查看最新日志最后n行(默认50行)
    tail [文件] [n] - 查看指定日志文件最后n行
    search [关键词] - 搜索所有日志文件
    search [文件] [关键词] - 搜索指定日志文件
    help        - 显示此帮助信息

示例:
    python3 view_logs.py list
    python3 view_logs.py tail
    python3 view_logs.py tail 100
    python3 view_logs.py tail deepseekok2-20251123.log 20
    python3 view_logs.py search "BUY信号"
    python3 view_logs.py search deepseekok2-20251123.log "ERROR"
    """)

def main():
    """主函数"""
    if len(sys.argv) == 1 or sys.argv[1] == 'help':
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        show_log_files()
    
    elif command == 'tail':
        log_files = list_log_files()
        if not log_files:
            print("❌ 没有找到日志文件")
            return
        
        if len(sys.argv) == 2:
            # 查看最新日志
            tail_log_file(log_files[0])
        elif len(sys.argv) == 3:
            try:
                lines = int(sys.argv[2])
                tail_log_file(log_files[0], lines)
            except ValueError:
                # 可能是文件名
                specified_file = Path("logs") / sys.argv[2]
                if specified_file.exists():
                    tail_log_file(specified_file)
                else:
                    print(f"❌ 文件不存在: {specified_file}")
        elif len(sys.argv) == 4:
            specified_file = Path("logs") / sys.argv[2]
            try:
                lines = int(sys.argv[3])
                if specified_file.exists():
                    tail_log_file(specified_file, lines)
                else:
                    print(f"❌ 文件不存在: {specified_file}")
            except ValueError:
                print("❌ 参数格式错误")
    
    elif command == 'search':
        if len(sys.argv) == 3:
            search_logs(sys.argv[2])
        elif len(sys.argv) == 4:
            specified_file = Path("logs") / sys.argv[3]
            if specified_file.exists():
                search_logs(sys.argv[2], specified_file)
            else:
                print(f"❌ 文件不存在: {specified_file}")
        else:
            print("❌ 搜索参数错误")
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()
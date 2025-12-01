#!/usr/bin/env python3
"""
日志系统设置脚本
自动将deepseekok2.py中的print语句转换为日志函数
"""

import re
import os
import shutil
from datetime import datetime

def setup_logging_for_file():
    """为deepseekok2.py设置日志系统"""
    
    # 备份原文件
    backup_file = f"deepseekok2_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy2('deepseekok2.py', backup_file)
    print(f"✅ 已创建备份文件: {backup_file}")
    
    # 读取原文件
    with open('deepseekok2.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换print语句为日志函数
    # 处理不同级别的日志
    
    # 1. 信息日志 (包含表情符号的print)
    info_patterns = [
        (r'print\("([🔍✅📊💰🎯📈📉🔄⏰📋🆕📦💡🚀🎉🤖].*?)"\)', r'log_info("\1")'),
        (r'print\(f"([🔍✅📊💰🎯📈📉🔄⏰📋🆕📦💡🚀🎉🤖].*?)"\)', r'log_info(f"\1")'),
    ]
    
    # 2. 警告日志
    warning_patterns = [
        (r'print\("([⚠️🚨].*?)"\)', r'log_warning("\1")'),
        (r'print\(f"([⚠️🚨].*?)"\)', r'log_warning(f"\1")'),
    ]
    
    # 3. 错误日志
    error_patterns = [
        (r'print\("([❌💀].*?)"\)', r'log_error("\1")'),
        (r'print\(f"([❌💀].*?)"\)', r'log_error(f"\1")'),
    ]
    
    # 4. 普通print转info
    normal_patterns = [
        (r'print\("(.*?)"\)', r'log_info("\1")'),
        (r'print\(f"(.*?)"\)', r'log_info(f"\1")'),
        (r'print\(([^"].*?)\)', r'log_info(\1)'),  # 变量或表达式
    ]
    
    # 应用替换
    new_content = content
    
    # 先处理import
    import_pattern = r'from logger_config import log_info, log_warning, log_error, log_debug, print_to_log'
    if not re.search(import_pattern, new_content):
        # 找到最后一个import后面插入
        last_import_match = re.search(r'^(import .*|from .* import .*)$', new_content, re.MULTILINE)
        if last_import_match:
            last_import_line = last_import_match.group(0)
            new_content = new_content.replace(
                last_import_line,
                f"{last_import_line}\nfrom logger_config import log_info, log_warning, log_error, log_debug"
            )
    
    # 处理print语句
    lines = new_content.split('\n')
    new_lines = []
    
    for line in lines:
        original_line = line
        
        # 跳过import行
        if 'import' in line and 'logger_config' not in line:
            new_lines.append(line)
            continue
            
        # 跳过空行和注释
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            new_lines.append(line)
            continue
            
        # 处理print语句
        if 'print(' in line:
            # 判断日志级别
            if any(emoji in line for emoji in ['⚠️', '🚨']):
                line = re.sub(r'print\((.*)\)', r'log_warning(\1)', line)
            elif any(emoji in line for emoji in ['❌', '💀']):
                line = re.sub(r'print\((.*)\)', r'log_error(\1)', line)
            elif any(emoji in line for emoji in ['🔍', '✅', '📊', '💰', '🎯', '📈', '📉', '🔄', '⏰', '📋', '🆕', '📦', '💡', '🚀', '🎉', '🤖']):
                line = re.sub(r'print\((.*)\)', r'log_info(\1)', line)
            else:
                line = re.sub(r'print\((.*)\)', r'log_info(\1)', line)
        
        new_lines.append(line)
    
    new_content = '\n'.join(new_lines)
    
    # 写入新文件
    with open('deepseekok2.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ 日志系统设置完成！")
    print("📁 日志将保存在: logs/deepseekok2-YYYYMMDD.log")
    print("📊 每天自动创建新的日志文件")
    print("🗑️  自动清理30天前的旧日志")

if __name__ == "__main__":
    setup_logging_for_file()
#!/usr/bin/env python3
"""
语法检查脚本 - 验证Python文件是否有语法错误
"""

import ast
import os
import sys

def check_file_syntax(filepath):
    """检查单个文件的语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试解析AST
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"其他错误: {e}"

def main():
    """主函数"""
    print("🔍 开始语法检查...")
    
    # 需要检查的文件列表
    files_to_check = [
        'utils.py',
        'strategies.py', 
        'trading.py',
        'config.py',
        'main.py',
        'run.py',
        'streamlit_app.py'
    ]
    
    all_passed = True
    
    for filename in files_to_check:
        if os.path.exists(filename):
            print(f"\n📄 检查 {filename}...")
            passed, error = check_file_syntax(filename)
            if passed:
                print(f"   ✅ {filename} - 语法正确")
            else:
                print(f"   ❌ {filename} - {error}")
                all_passed = False
        else:
            print(f"   ⚠️  {filename} - 文件不存在")
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 所有文件语法检查通过！")
        return 0
    else:
        print("❌ 部分文件存在语法错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())
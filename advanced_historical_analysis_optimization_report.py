#!/usr/bin/env python3
"""
修正版历史交易分析器
使用正确的列名分析历史交易数据
"""

import pandas as pd
import numpy as np
import glob
import os
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class FixedHistoricalAnalyzer:
    def __init__(self):
        self.historical_dir = "/Users/hamgua/code/github/alpha-arena-okx-hamgua/historical_trades"
        self.data_json_dir = "/Users/hamgua/code/github/alpha-arena-okx-hamgua/data_json"
        
    def find_latest_csv_files(self):
        """查找最新的CSV交易文件"""
        trade_files = glob.glob(f"{self.historical_dir}/*交易明细*.csv")
        
        if not trade_files:
            print("❌ 未找到历史交易文件")
            return None
            
        # 按文件名中的日期排序，取最新的
        def extract_date(filename):
            basename = os.path.basename(filename)
            date_part = basename.split('~')[0].split('_')[-1]
            return datetime.strptime(date_part, '%Y-%m-%d')
            
        latest_trade = max(trade_files, key=extract_date)
        
        print(f"📊 分析文件: {os.path.basename(latest_trade)}")
        return latest_trade
    
    def load_and_clean_data(self, trade_file):
        """加载并清理数据"""
        try:
            # 加载交易明细
            trades_df = pd.read_csv(trade_file, encoding='utf-8-sig')
            
            # 清理列名中的特殊字符
            trades_df.columns = trades_df.columns.str.replace('﻿', '').str.strip()
            
            # 转换时间格式
            trades_df['交易时间'] = pd.to_datetime(trades_df['交易时间'])
            trades_df['hour'] = trades_df['交易时间'].dt.hour
            trades_df['date'] = trades_df['交易时间'].dt.date
            
            # 转换数值类型
            numeric_cols = ['数量', '成交价格', '成交额', '手续费']
            for col in numeric_cols:
                if col in trades_df.columns:
                    trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
            
            return trades_df
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return None
    
    def analyze_trading_patterns(self, trades_df):
        """深度分析交易模式"""
        analysis = {}
        
        # 基础统计
        total_trades = len(trades_df)
        if total_trades == 0:
            return analysis
            
        # 时间范围
        start_date = trades_df['交易时间'].min().date()
        end_date = trades_df['交易时间'].max().date()
        days = (end_date - start_date).days + 1
        
        # 每日交易次数
        daily_trades = trades_df.groupby('date').size()
        avg_daily_trades = daily_trades.mean()
        max_daily_trades = daily_trades.max()
        
        # 交易时段分析
        hourly_trades = trades_df.groupby('hour').size()
        peak_hours = hourly_trades.nlargest(5).index.tolist()
        
        # 费用分析
        total_fees = trades_df['手续费'].sum()
        avg_fee_per_trade = trades_df['手续费'].mean()
        
        # 成交类型分析
        maker_trades = trades_df[trades_df['流动性方向'] == '挂单']
        taker_trades = trades_df[trades_df['流动性方向'] == '吃单']
        
        maker_ratio = len(maker_trades) / total_trades * 100
        taker_ratio = 100 - maker_ratio
        
        # 交易方向分析
        buy_trades = trades_df[trades_df['数量'] > 0]
        sell_trades = trades_df[trades_df['数量'] < 0]
        
        # 交易规模分析
        avg_trade_size = trades_df['数量'].abs().mean()
        total_volume = trades_df['成交额'].sum()
        
        # 价格分析
        avg_price = trades_df['成交价格'].mean()
        price_std = trades_df['成交价格'].std()
        
        # 时间间隔分析
        trades_sorted = trades_df.sort_values('交易时间')
        time_diffs = trades_sorted['交易时间'].diff().dt.total_seconds() / 60
        avg_time_interval = time_diffs.mean()
        
        analysis.update({
            'period': f"{start_date} to {end_date}",
            'total_days': days,
            'total_trades': total_trades,
            'avg_daily_trades': round(avg_daily_trades, 2),
            'max_daily_trades': max_daily_trades,
            'peak_hours': peak_hours,
            'total_fees': round(total_fees, 6),
            'avg_fee_per_trade': round(avg_fee_per_trade, 6),
            'maker_ratio': round(maker_ratio, 2),
            'taker_ratio': round(taker_ratio, 2),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'avg_trade_size': round(avg_trade_size, 4),
            'total_volume': round(total_volume, 4),
            'avg_price': round(avg_price, 2),
            'price_volatility': round(price_std, 2),
            'avg_time_interval_minutes': round(avg_time_interval, 1)
        })
        
        return analysis
    
    def generate_business_logic_optimizations(self, analysis):
        """生成业务逻辑和参数优化建议"""
        optimizations = []
        
        # 1. 交易频率优化
        if analysis['avg_daily_trades'] > 6:
            optimizations.append({
                'type': '频率控制',
                'current': f"日均{analysis['avg_daily_trades']}次",
                'target': '3-5次/天',
                'code_changes': [
                    "TRADE_CONFIG['frequency_control']['max_daily_trades'] = 5",
                    "TRADE_CONFIG['frequency_control']['min_trade_interval'] = 45"
                ],
                'logic_changes': [
                    '在check_trade_frequency_control()中增加更严格的频率检查',
                    '增加交易冷却期：从30分钟延长到45分钟'
                ]
            })
        
        # 2. 手续费优化
        if analysis['maker_ratio'] < 20:
            optimizations.append({
                'type': '成本控制',
                'current': f"挂单比例{analysis['maker_ratio']:.1f}%",
                'target': '50%+挂单',
                'code_changes': [
                    "TRADE_CONFIG['limit_order']['enabled'] = True",
                    "TRADE_CONFIG['limit_order']['confidence_threshold'] = 0.7"
                ],
                'logic_changes': [
                    'execute_intelligent_trade()使用determine_order_type()决定订单类型',
                    '高信心信号(HIGH)强制使用限价单',
                    '增加价格缓冲机制确保成交'
                ]
            })
        
        # 3. 交易时段优化
        peak_hours = analysis['peak_hours']
        if len(peak_hours) > 0:
            optimizations.append({
                'type': '时机选择',
                'current': f"高峰时段: {peak_hours}",
                'target': '优化到高波动时段',
                'code_changes': [
                    "TRADE_CONFIG['frequency_control']['optimal_trading_hours'] = [8,9,10,21,22,23,0,1]"
                ],
                'logic_changes': [
                    '在check_trade_frequency_control()中增加时段过滤',
                    '非最优时段自动跳过交易信号'
                ]
            })
        
        # 4. 仓位规模优化
        if analysis['avg_trade_size'] > 0.1:
            optimizations.append({
                'type': '仓位管理',
                'current': f"平均仓位{analysis['avg_trade_size']}张",
                'target': '降低单笔规模',
                'code_changes': [
                    "TRADE_CONFIG['position_management']['base_usdt_amount'] = 15",
                    "TRADE_CONFIG['position_management']['max_position_ratio'] = 0.3"
                ],
                'logic_changes': [
                    'calculate_intelligent_position()降低基础倍数',
                    '增加仓位上限检查'
                ]
            })
        
        # 5. 交易间隔优化
        if analysis['avg_time_interval_minutes'] < 20:
            optimizations.append({
                'type': '间隔控制',
                'current': f"平均间隔{analysis['avg_time_interval_minutes']}分钟",
                'target': '最小30分钟',
                'code_changes': [
                    "TRADE_CONFIG['frequency_control']['min_trade_interval'] = 30"
                ],
                'logic_changes': [
                    '在check_trade_frequency_control()中增加时间间隔检查',
                    '记录上次交易时间用于间隔计算'
                ]
            })
        
        return optimizations
    
    def run_analysis(self):
        """运行完整分析"""
        print("🚀 启动历史交易分析...")
        
        # 1. 查找文件
        trade_file = self.find_latest_csv_files()
        if not trade_file:
            return None
        
        # 2. 加载数据
        trades_df = self.load_and_clean_data(trade_file)
        if trades_df is None:
            return None
        
        # 3. 分析交易模式
        print("🔍 分析交易模式...")
        analysis = self.analyze_trading_patterns(trades_df)
        
        # 4. 生成优化建议
        print("💡 生成优化建议...")
        optimizations = self.generate_business_logic_optimizations(analysis)
        
        # 5. 保存结果
        result = {
            'analysis_time': datetime.now().isoformat(),
            'data_period': analysis['period'],
            'historical_analysis': analysis,
            'business_logic_optimizations': optimizations,
            'implementation_ready': True
        }
        
        # 保存到JSON文件
        output_file = f"{self.data_json_dir}/historical_optimization_report.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 分析完成！结果已保存到: {output_file}")
        return result

def main():
    """主函数"""
    analyzer = FixedHistoricalAnalyzer()
    result = analyzer.run_analysis()
    
    if result:
        analysis = result['historical_analysis']
        optimizations = result['business_logic_optimizations']
        
        print("\n" + "="*70)
        print("📊 历史交易分析结果")
        print("="*70)
        
        print(f"📅 数据期间: {analysis['period']}")
        print(f"📊 总交易次数: {analysis['total_trades']}")
        print(f"📈 日均交易: {analysis['avg_daily_trades']}次")
        print(f"💰 总手续费: {analysis['total_fees']}USDT")
        print(f"🎯 挂单比例: {analysis['maker_ratio']}% vs 吃单{analysis['taker_ratio']}%")
        print(f"⚖️ 买卖比例: 买{analysis['buy_trades']}次 vs 卖{analysis['sell_trades']}次")
        print(f"📏 平均仓位: {analysis['avg_trade_size']}张")
        print(f"⏱️ 平均间隔: {analysis['avg_time_interval_minutes']}分钟")
        print(f"🕐 高峰时段: {analysis['peak_hours'][:3]}")
        
        print("\n🔧 业务逻辑优化建议:")
        print("-" * 50)
        
        for i, opt in enumerate(optimizations, 1):
            print(f"\n{i}. {opt['type']} - {opt['current']} → {opt['target']}")
            print("   代码修改:")
            for code_change in opt['code_changes']:
                print(f"   ✅ {code_change}")
            print("   逻辑修改:")
            for logic_change in opt['logic_changes']:
                print(f"   🔧 {logic_change}")

if __name__ == "__main__":
    main()
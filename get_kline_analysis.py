#!/usr/bin/env python3
"""
获取OKX 11月30日21点至今的5分钟K线数据分析
用于分析您提出的三个问题
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import pytz

def get_okx_kline_data():
    """获取OKX 5分钟K线数据"""
    
    # 初始化OKX交易所
    exchange = ccxt.okx({
        'options': {
            'defaultType': 'swap',
        }
    })
    
    # 设置时间范围：11月30日21点到当前时间
    end_time = datetime.now()
    start_time = datetime(2024, 11, 30, 21, 0, 0)
    
    # 转换为毫秒时间戳
    since = int(start_time.timestamp() * 1000)
    
    print(f"开始获取数据：{start_time} 到 {end_time}")
    
    try:
        # 获取5分钟K线数据
        ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT:USDT',  # OKX永续合约格式
            '5m',
            since=since,
            limit=5000  # 获取足够的数据
        )
        
        # 转换为DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 计算技术指标
        df = calculate_technical_indicators(df)
        
        # 保存数据
        df.to_csv('okx_btc_5min_data.csv', index=False)
        
        print(f"获取完成：共{len(df)}条记录")
        print(f"时间范围：{df['timestamp'].min()} 到 {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def calculate_technical_indicators(df):
    """计算技术指标"""
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR（平均真实波幅）
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['atr'] = ranges.max(axis=1).rolling(window=14).mean()
    
    # 价格波动率
    df['volatility'] = (df['high'] - df['low']) / df['close'] * 100
    
    # 价格变化百分比
    df['price_change_pct'] = df['close'].pct_change() * 100
    
    return df

def analyze_data(df):
    """分析数据特征"""
    
    if df is None or len(df) == 0:
        return
    
    print("\n" + "="*60)
    print("📊 5分钟K线数据分析报告")
    print("="*60)
    
    # 基本统计
    print(f"📈 数据条数: {len(df)}")
    print(f"💰 当前价格: ${df['close'].iloc[-1]:,.2f}")
    print(f"📊 价格区间: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
    print(f"📈 平均波动: {df['volatility'].mean():.2f}%")
    print(f"⚡ 最大单日跌幅: {df['price_change_pct'].min():.2f}%")
    
    # 识别暴跌时段
    crash_threshold = -2.0  # 5分钟内跌幅超过2%
    crash_periods = df[df['price_change_pct'] < crash_threshold]
    print(f"🚨 暴跌时段(5min跌幅>{crash_threshold}%): {len(crash_periods)}次")
    
    if len(crash_periods) > 0:
        print("📋 暴跌时段详情:")
        for idx, row in crash_periods.head(5).iterrows():
            print(f"   {row['timestamp']}: {row['price_change_pct']:.2f}%")
    
    # 横盘识别
    sideways_threshold = 0.5  # 5分钟内波动小于0.5%
    sideways_periods = df[df['volatility'] < sideways_threshold]
    print(f"🟡 横盘时段(5min波动<{sideways_threshold}%): {len(sideways_periods)}次")
    
    # 波动率分析
    low_volatility = df[df['atr'] < df['atr'].quantile(0.25)]
    high_volatility = df[df['atr'] > df['atr'].quantile(0.75)]
    
    print(f"📉 低波动时段: {len(low_volatility)}次")
    print(f"📈 高波动时段: {len(high_volatility)}次")
    
    return df

if __name__ == "__main__":
    df = get_okx_kline_data()
    if df is not None:
        analyze_data(df)
        print("\n✅ 数据已保存到 okx_btc_5min_data.csv")
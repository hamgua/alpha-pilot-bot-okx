# Alpha Arena OKX - 重构版交易系统

## 🎯 项目概述

这是一个基于OKX交易所的自动化交易系统，采用模块化架构设计，实现了配置与业务逻辑的完全分离，提供了更强的可扩展性和维护性。

## 🏗️ 架构设计

### 模块化结构

```
alpha-arena-okx/
├── main.py    # 主程序
├── config.py             # 配置管理模块
├── trading.py            # 交易逻辑模块
├── strategies.py         # 策略模块
├── utils.py              # 工具模块
├── run.py                # 启动脚本
├── ai_client.py          # AI客户端
└── README.md             # 项目文档
```

Builder



### ✅ 最终保留的Python文件
核心模块（7个指定文件）：

- ✅ main.py - 主程序
- ✅ config.py - 配置管理模块
- ✅ trading.py - 交易逻辑模块
- ✅ strategies.py - 策略模块
- ✅ utils.py - 工具模块
- ✅ run.py - 启动脚本
- ✅ README.md - 项目文档
必要的系统支持文件：

- ✅ ai_client.py - AI客户端
- ✅ data_manager.py - 数据管理
- ✅ trade_logger.py - 交易日志
- ✅ circuit_breaker.py - 熔断保护
- ✅ logger_config.py - 日志配置
- ✅ streamlit_app.py - Web界面（可选）
- ✅ 其他必要的系统模块



### 模块职责

#### 1. 配置管理模块 (`config.py`)
- **功能**: 集中管理所有配置项
- **特点**: 配置与代码完全分离，支持环境变量
- **包含**: 交易所配置、交易参数、策略配置、风险控制、AI配置、系统配置

#### 2. 交易逻辑模块 (`trading.py`)
- **功能**: 封装所有交易相关操作
- **组件**:
  - `ExchangeManager`: 交易所连接管理
  - `OrderManager`: 订单管理
  - `TradingEngine`: 交易引擎

#### 3. 策略模块 (`strategies.py`)
- **功能**: 包含所有交易策略和风险管理
- **组件**:
  - `MarketAnalyzer`: 市场分析器
  - `RiskManager`: 风险管理器
  - `SignalProcessor`: 信号处理器
  - `ConsolidationDetector`: 横盘检测器

#### 4. 工具模块 (`utils.py`)
- **功能**: 通用工具函数和辅助功能
- **组件**:
  - `CacheManager`: 缓存管理
  - `MemoryManager`: 内存管理
  - `SystemMonitor`: 系统监控
  - `DataValidator`: 数据验证
  - `LoggerHelper`: 日志辅助

#### 5. 主程序 (`main.py`)
- **功能**: 整合所有模块，执行交易循环
- **特点**: 简洁的主逻辑，易于理解和维护

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone [your-repo-url]
cd alpha-arena-okx-hamgua

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 交易所配置
OKX_API_KEY=your_api_key
OKX_SECRET=your_secret_key
OKX_PASSWORD=your_password
OKX_SANDBOX=false

# 交易配置
TEST_MODE=true
MAX_POSITION_SIZE=0.01
MIN_TRADE_AMOUNT=0.001
LEVERAGE=10
ALLOW_SHORT_SELLING=false

# AI配置
USE_MULTI_AI=false
KIMI_API_KEY=your_kimi_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key

# 系统配置
LOG_LEVEL=INFO
```

### 3. 启动系统

```bash
# 运行启动检查
python start.py

# 或者直接启动
python main.py
```

## 🔧 功能特性

### 核心功能
- ✅ **智能交易**: 基于AI信号自动交易
- ✅ **风险管理**: 动态止盈止损，盈利保护
- ✅ **横盘检测**: 低波动环境下的利润锁定
- ✅ **暴跌保护**: 价格暴跌时停止止损更新
- ✅ **做空开关**: 灵活配置做空功能
- ✅ **模拟交易**: 支持测试模式

### 增强功能
- ✅ **配置分离**: 所有配置集中管理
- ✅ **缓存系统**: AI信号缓存，减少API调用
- ✅ **内存管理**: 防止内存泄漏
- ✅ **系统监控**: 实时系统状态监控
- ✅ **错误处理**: 完善的异常处理机制

## 📊 配置说明

### 策略配置

```python
# 横盘利润锁定策略
profit_lock_strategy = {
    'enabled': True,
    'min_profit_pct': 0.005,        # 最小盈利0.5%
    'consolidation_threshold': 0.008, # 横盘阈值0.8%
    'lookback_periods': 6,          # 检测6根K线
    'consolidation_duration': 20,   # 横盘持续20分钟
    'volatility_adaptive': True     # 自适应波动率
}

# 智能止盈止损
smart_tp_sl = {
    'enabled': True,
    'base_sl_pct': 0.02,            # 基础止损2%
    'base_tp_pct': 0.06,            # 基础止盈6%
    'adaptive_mode': True,          # 自适应模式
    'high_vol_multiplier': 1.5,    # 高波动倍数
    'low_vol_multiplier': 0.8      # 低波动倍数
}

# 价格暴跌保护
price_crash_protection = {
    'enabled': True,
    'crash_threshold': 0.03        # 3%跌幅触发保护
}
```

## 🔍 监控与调试

### 日志系统
- **交易日志**: 记录所有交易操作
- **系统日志**: 记录系统状态和错误
- **性能日志**: 记录执行时间和资源使用

### 监控指标
- 交易次数
- 盈亏统计
- 系统运行时间
- 内存使用情况
- 缓存命中率

## 🛠️ 扩展开发

### 添加新策略

1. 在 `strategies.py` 中添加新策略类
2. 在 `config.py` 中添加相应配置
3. 在 `main.py` 中集成新策略

### 添加新交易所

1. 在 `trading.py` 中添加新的交易所管理器
2. 在 `config.py` 中添加交易所配置
3. 更新启动检查

## ⚠️ 风险提示

- **模拟模式**: 首次运行请使用模拟模式
- **风险控制**: 合理设置仓位大小和止损
- **监控运行**: 定期检查系统日志
- **备份配置**: 定期备份配置文件

## 📞 技术支持

如有问题，请检查：
1. 环境变量是否正确设置
2. 网络连接是否正常
3. API密钥是否有效
4. 查看系统日志获取详细信息

## 📝 更新日志

### v2.0 (重构版)
- ✅ 模块化架构重构
- ✅ 配置与代码分离
- ✅ 增强的缓存系统
- ✅ 改进的内存管理
- ✅ 完善的错误处理
- ✅ 新增暴跌保护机制
- ✅ 优化横盘检测逻辑
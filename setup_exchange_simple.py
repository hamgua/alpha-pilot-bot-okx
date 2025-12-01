from logger_config import log_info, log_warning, log_error

def setup_exchange():
    """设置交易所参数 - 极简版，仅设置持仓模式和杠杆"""
    try:
        log_info("🔍 开始交易所设置...")

        # 获取合约规格信息
        log_info("🔍 获取BTC合约规格...")
        markets = exchange.load_markets()
        btc_market = markets[TRADE_CONFIG['symbol']]

        # 获取合约乘数
        contract_size = float(btc_market['contractSize'])
        log_info(f"✅ 合约规格: 1张 = {contract_size} BTC")

        # 存储合约规格到全局配置
        TRADE_CONFIG['contract_size'] = contract_size
        TRADE_CONFIG['min_amount'] = btc_market['limits']['amount']['min']
        log_info(f"📏 最小交易量: {TRADE_CONFIG['min_amount']} 张")

        # 设置单向持仓模式
        log_info("🔄 设置单向持仓模式...")
        try:
            exchange.set_position_mode(False, TRADE_CONFIG['symbol'])
            log_info("✅ 已设置单向持仓模式")
        except Exception as e:
            log_warning(f"⚠️ 设置单向持仓模式失败: {e}")

        # 设置全仓模式和杠杆
        log_info("⚙️ 设置全仓模式和杠杆...")
        try:
            exchange.set_leverage(
                TRADE_CONFIG['leverage'],
                TRADE_CONFIG['symbol'],
                {'mgnMode': 'cross'}
            )
            log_info(f"✅ 已设置全仓模式，杠杆倍数: {TRADE_CONFIG['leverage']}x")
        except Exception as e:
            log_warning(f"⚠️ 设置杠杆失败: {e}")

        log_info("🔍 交易所设置完成")
        return True
        
    except Exception as e:
        log_error(f"❌ 交易所设置失败: {e}")
        return False
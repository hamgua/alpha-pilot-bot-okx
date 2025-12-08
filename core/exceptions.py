"""
自定义异常类
提供统一的错误处理机制
"""

class TradingBotError(Exception):
    """交易机器人基础异常"""
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.context = context or {}
        self.timestamp = None  # 将在初始化时设置
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context,
            'timestamp': self.timestamp
        }

class AIError(TradingBotError):
    """AI相关异常"""
    def __init__(self, message: str, provider: str = None, error_code: str = "AI_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.provider = provider

class StrategyError(TradingBotError):
    """策略相关异常"""
    def __init__(self, message: str, strategy_type: str = None, error_code: str = "STRATEGY_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.strategy_type = strategy_type

class TradingError(TradingBotError):
    """交易相关异常"""
    def __init__(self, message: str, order_id: str = None, error_code: str = "TRADING_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.order_id = order_id

class ConfigurationError(TradingBotError):
    """配置相关异常"""
    def __init__(self, message: str, config_key: str = None, error_code: str = "CONFIG_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.config_key = config_key

class NetworkError(TradingBotError):
    """网络相关异常"""
    def __init__(self, message: str, url: str = None, error_code: str = "NETWORK_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.url = url

class APIError(TradingBotError):
    """API相关异常"""
    def __init__(self, message: str, api_name: str = None, status_code: int = None, error_code: str = "API_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.api_name = api_name
        self.status_code = status_code

class DataError(TradingBotError):
    """数据相关异常"""
    def __init__(self, message: str, data_type: str = None, error_code: str = "DATA_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.data_type = data_type

class ValidationError(TradingBotError):
    """验证相关异常"""
    def __init__(self, message: str, field: str = None, error_code: str = "VALIDATION_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.field = field

class TimeoutError(TradingBotError):
    """超时异常"""
    def __init__(self, message: str, timeout_value: float = None, error_code: str = "TIMEOUT_ERROR", context: dict = None):
        super().__init__(message, error_code, context)
        self.timeout_value = timeout_value
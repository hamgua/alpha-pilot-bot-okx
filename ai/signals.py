"""
AI信号数据结构
定义信号相关的数据类和枚举
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class SignalType(Enum):
    """信号类型枚举"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"

class ConfidenceLevel(Enum):
    """信心等级枚举"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class AISignal:
    """AI信号数据结构"""
    provider: str
    signal: str
    confidence: float
    reason: str
    timestamp: str
    raw_response: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证信号数据"""
        if self.signal not in [SignalType.BUY.value, SignalType.SELL.value, SignalType.HOLD.value]:
            raise ValueError(f"Invalid signal type: {self.signal}")
        
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got: {self.confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'provider': self.provider,
            'signal': self.signal,
            'confidence': self.confidence,
            'reason': self.reason,
            'timestamp': self.timestamp,
            'raw_response': self.raw_response
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AISignal':
        """从字典创建实例"""
        return cls(**data)
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """获取信心等级"""
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

@dataclass
class SignalFusionResult:
    """信号融合结果"""
    signal: str
    confidence: float
    reason: str
    providers: List[str]
    fusion_method: str
    fusion_analysis: Dict[str, Any]
    signal_statistics: Dict[str, Any]
    diversity_analysis: Dict[str, Any]
    raw_signals: List[Dict[str, Any]]
    votes: Dict[str, int]
    confidences: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'signal': self.signal,
            'confidence': self.confidence,
            'reason': self.reason,
            'providers': self.providers,
            'fusion_method': self.fusion_method,
            'fusion_analysis': self.fusion_analysis,
            'signal_statistics': self.signal_statistics,
            'diversity_analysis': self.diversity_analysis,
            'raw_signals': self.raw_signals,
            'votes': self.votes,
            'confidences': self.confidences
        }

@dataclass
class TimeoutConfig:
    """超时配置"""
    connection_timeout: float = 8.0
    response_timeout: float = 12.0
    total_timeout: float = 20.0
    retry_base_delay: float = 3.0
    max_retries: int = 3
    performance_score: float = 0.75
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'connection_timeout': self.connection_timeout,
            'response_timeout': self.response_timeout,
            'total_timeout': self.total_timeout,
            'retry_base_delay': self.retry_base_delay,
            'max_retries': self.max_retries,
            'performance_score': self.performance_score
        }

@dataclass
class RetryCostConfig:
    """重试成本配置"""
    max_daily_cost: float = 150.0
    current_daily_cost: float = 0.0
    cost_weights: Dict[str, float] = field(default_factory=lambda: {
        'deepseek': 1.2,
        'kimi': 1.3,
        'qwen': 1.0,
        'openai': 1.8
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'max_daily_cost': self.max_daily_cost,
            'current_daily_cost': self.current_daily_cost,
            'cost_weights': self.cost_weights
        }

@dataclass
class FallbackSignal:
    """回退信号"""
    signal: str
    confidence: float
    reason: str
    is_fallback: bool = True
    fallback_type: str = "technical"
    signal_score: float = 0.0
    confidence_factors: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'signal': self.signal,
            'confidence': self.confidence,
            'reason': self.reason,
            'is_fallback': self.is_fallback,
            'fallback_type': self.fallback_type,
            'signal_score': self.signal_score,
            'confidence_factors': self.confidence_factors
        }

@dataclass
class DiversityAnalysis:
    """信号多样性分析"""
    diversity_score: float
    is_homogeneous: bool
    unique_signals: List[str]
    signal_distribution: Dict[str, int]
    confidence_stats: Dict[str, float]
    analysis: str
    requires_intervention: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'diversity_score': self.diversity_score,
            'is_homogeneous': self.is_homogeneous,
            'unique_signals': self.unique_signals,
            'signal_distribution': self.signal_distribution,
            'confidence_stats': self.confidence_stats,
            'analysis': self.analysis,
            'requires_intervention': self.requires_intervention
        }

@dataclass
class SignalStatistics:
    """信号统计"""
    total_signals: int
    signal_distribution: Dict[str, int]
    confidence_stats: Dict[str, float]
    provider_breakdown: Dict[str, Any]
    quality_score: float
    diversity_index: float
    consensus_level: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_signals': self.total_signals,
            'signal_distribution': self.signal_distribution,
            'confidence_stats': self.confidence_stats,
            'provider_breakdown': self.provider_breakdown,
            'quality_score': self.quality_score,
            'diversity_index': self.diversity_index,
            'consensus_level': self.consensus_level
        }
"""代理轮换器实现

提供多种代理轮换策略，包括轮询、随机、权重、地理位置等。
支持智能故障转移和负载均衡。
"""

import asyncio
import random
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
from .proxy_pool import ProxyInfo, ProxyStatus

logger = logging.getLogger(__name__)

class RotationStrategy(Enum):
    """轮换策略枚举"""
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"  # 随机
    WEIGHTED = "weighted"  # 权重
    FASTEST = "fastest"  # 最快
    LEAST_USED = "least_used"  # 最少使用
    GEOGRAPHIC = "geographic"  # 地理位置
    ADAPTIVE = "adaptive"  # 自适应

class ProxyRotator:
    """代理轮换器基类"""
    
    def __init__(self, strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 使用统计
        self.usage_stats = defaultdict(int)
        self.last_used = {}
        self.failure_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        
        # 轮换状态
        self.current_index = 0
        self.last_rotation_time = time.time()
        
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """选择代理（子类实现）"""
        raise NotImplementedError
    
    def record_usage(self, proxy: ProxyInfo, success: bool = True, response_time: float = None):
        """记录使用情况"""
        proxy_key = f"{proxy.host}:{proxy.port}"
        
        self.usage_stats[proxy_key] += 1
        self.last_used[proxy_key] = time.time()
        
        if success:
            self.success_counts[proxy_key] += 1
            if response_time:
                # 更新响应时间（移动平均）
                if hasattr(proxy, 'avg_response_time'):
                    proxy.avg_response_time = (proxy.avg_response_time + response_time) / 2
                else:
                    proxy.avg_response_time = response_time
        else:
            self.failure_counts[proxy_key] += 1
    
    def get_proxy_score(self, proxy: ProxyInfo) -> float:
        """计算代理评分"""
        proxy_key = f"{proxy.host}:{proxy.port}"
        
        # 基础分数
        score = 100.0
        
        # 成功率影响
        total_uses = self.usage_stats[proxy_key]
        if total_uses > 0:
            success_rate = self.success_counts[proxy_key] / total_uses
            score *= success_rate
        
        # 响应时间影响
        if hasattr(proxy, 'avg_response_time') and proxy.avg_response_time:
            # 响应时间越短分数越高
            time_score = max(0, 10 - proxy.avg_response_time)
            score += time_score * 10
        
        # 使用频率影响（避免过度使用）
        usage_penalty = min(self.usage_stats[proxy_key] * 0.1, 20)
        score -= usage_penalty
        
        # 最近使用时间影响
        last_use_time = self.last_used.get(proxy_key, 0)
        time_since_last_use = time.time() - last_use_time
        if time_since_last_use < 60:  # 1分钟内使用过
            score -= 10
        
        return max(score, 0)
    
    def filter_available_proxies(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """过滤可用代理"""
        available = []
        current_time = time.time()
        
        for proxy in proxies:
            # 检查状态
            if proxy.status != ProxyStatus.ACTIVE:
                continue
            
            # 检查冷却时间
            proxy_key = f"{proxy.host}:{proxy.port}"
            last_use = self.last_used.get(proxy_key, 0)
            
            # 如果最近失败过，增加冷却时间
            failure_count = self.failure_counts[proxy_key]
            cooldown = min(failure_count * 30, 300)  # 最多5分钟冷却
            
            if current_time - last_use >= cooldown:
                available.append(proxy)
        
        return available

class RoundRobinRotator(ProxyRotator):
    """轮询轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.ROUND_ROBIN)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """轮询选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 轮询选择
        proxy = available_proxies[self.current_index % len(available_proxies)]
        self.current_index += 1
        
        return proxy

class RandomRotator(ProxyRotator):
    """随机轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.RANDOM)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """随机选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        return random.choice(available_proxies)

class WeightedRotator(ProxyRotator):
    """权重轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.WEIGHTED)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """基于权重选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 计算权重
        weights = []
        for proxy in available_proxies:
            score = self.get_proxy_score(proxy)
            weights.append(max(score, 1))  # 确保权重为正
        
        # 权重随机选择
        return self._weighted_random_choice(available_proxies, weights)
    
    def _weighted_random_choice(self, items: List[Any], weights: List[float]) -> Any:
        """权重随机选择"""
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(items)
        
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for item, weight in zip(items, weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return item
        
        return items[-1]  # fallback

class FastestRotator(ProxyRotator):
    """最快代理轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.FASTEST)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """选择最快的代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 按响应时间排序
        sorted_proxies = sorted(
            available_proxies,
            key=lambda p: getattr(p, 'avg_response_time', float('inf'))
        )
        
        # 从最快的几个中随机选择（避免总是使用同一个）
        top_count = min(3, len(sorted_proxies))
        return random.choice(sorted_proxies[:top_count])

class LeastUsedRotator(ProxyRotator):
    """最少使用轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.LEAST_USED)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """选择使用次数最少的代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 按使用次数排序
        sorted_proxies = sorted(
            available_proxies,
            key=lambda p: self.usage_stats[f"{p.host}:{p.port}"]
        )
        
        # 从使用最少的几个中选择
        least_used_count = min(3, len(sorted_proxies))
        return random.choice(sorted_proxies[:least_used_count])

class GeographicRotator(ProxyRotator):
    """地理位置轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.GEOGRAPHIC)
        self.country_rotation = defaultdict(int)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """基于地理位置选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 获取目标国家（如果指定）
        target_country = kwargs.get('target_country')
        
        if target_country:
            # 优先选择目标国家的代理
            country_proxies = [
                p for p in available_proxies 
                if p.country and p.country.lower() == target_country.lower()
            ]
            if country_proxies:
                return random.choice(country_proxies)
        
        # 按国家分组
        country_groups = defaultdict(list)
        for proxy in available_proxies:
            country = proxy.country or 'unknown'
            country_groups[country].append(proxy)
        
        # 轮换国家
        countries = list(country_groups.keys())
        if not countries:
            return random.choice(available_proxies)
        
        # 选择下一个国家
        country_index = self.country_rotation['current'] % len(countries)
        selected_country = countries[country_index]
        self.country_rotation['current'] += 1
        
        return random.choice(country_groups[selected_country])

class AdaptiveRotator(ProxyRotator):
    """自适应轮换器"""
    
    def __init__(self):
        super().__init__(RotationStrategy.ADAPTIVE)
        self.performance_history = defaultdict(deque)
        self.strategy_weights = {
            'fastest': 0.3,
            'least_used': 0.2,
            'weighted': 0.3,
            'random': 0.2
        }
        
        # 子轮换器
        self.sub_rotators = {
            'fastest': FastestRotator(),
            'least_used': LeastUsedRotator(),
            'weighted': WeightedRotator(),
            'random': RandomRotator()
        }
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """自适应选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 根据当前性能调整策略权重
        self._adjust_strategy_weights()
        
        # 选择策略
        strategy = self._select_strategy()
        
        # 使用选定的策略
        rotator = self.sub_rotators[strategy]
        
        # 同步使用统计
        rotator.usage_stats = self.usage_stats
        rotator.last_used = self.last_used
        rotator.failure_counts = self.failure_counts
        rotator.success_counts = self.success_counts
        
        return rotator.select_proxy(available_proxies, **kwargs)
    
    def _adjust_strategy_weights(self):
        """调整策略权重"""
        # 基于最近的性能数据调整权重
        current_time = time.time()
        recent_threshold = current_time - 300  # 最近5分钟
        
        strategy_performance = {}
        
        for strategy in self.strategy_weights.keys():
            recent_performance = [
                perf for perf in self.performance_history[strategy]
                if perf['timestamp'] > recent_threshold
            ]
            
            if recent_performance:
                avg_success_rate = sum(p['success_rate'] for p in recent_performance) / len(recent_performance)
                avg_response_time = sum(p['response_time'] for p in recent_performance) / len(recent_performance)
                
                # 综合评分
                score = avg_success_rate * 100 - avg_response_time * 10
                strategy_performance[strategy] = max(score, 0)
            else:
                strategy_performance[strategy] = 50  # 默认分数
        
        # 归一化权重
        total_score = sum(strategy_performance.values())
        if total_score > 0:
            for strategy in self.strategy_weights.keys():
                self.strategy_weights[strategy] = strategy_performance[strategy] / total_score
    
    def _select_strategy(self) -> str:
        """选择轮换策略"""
        strategies = list(self.strategy_weights.keys())
        weights = list(self.strategy_weights.values())
        
        # 权重随机选择
        total_weight = sum(weights)
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for strategy, weight in zip(strategies, weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return strategy
        
        return strategies[-1]  # fallback
    
    def record_usage(self, proxy: ProxyInfo, success: bool = True, response_time: float = None):
        """记录使用情况（增强版）"""
        super().record_usage(proxy, success, response_time)
        
        # 记录策略性能
        if hasattr(self, '_last_strategy'):
            strategy = self._last_strategy
            
            # 计算成功率
            proxy_key = f"{proxy.host}:{proxy.port}"
            total_uses = self.usage_stats[proxy_key]
            success_rate = self.success_counts[proxy_key] / total_uses if total_uses > 0 else 0
            
            # 记录性能数据
            performance_data = {
                'timestamp': time.time(),
                'success_rate': success_rate,
                'response_time': response_time or 0
            }
            
            self.performance_history[strategy].append(performance_data)
            
            # 保持历史记录大小
            if len(self.performance_history[strategy]) > 100:
                self.performance_history[strategy].popleft()

class SmartRotator(ProxyRotator):
    """智能轮换器（带机器学习特性）"""
    
    def __init__(self):
        super().__init__(RotationStrategy.ADAPTIVE)
        self.learning_data = defaultdict(list)
        self.proxy_clusters = {}
        self.request_patterns = defaultdict(int)
    
    def select_proxy(self, proxies: List[ProxyInfo], **kwargs) -> Optional[ProxyInfo]:
        """智能选择代理"""
        available_proxies = self.filter_available_proxies(proxies)
        
        if not available_proxies:
            return None
        
        # 分析请求模式
        request_type = kwargs.get('request_type', 'default')
        target_domain = kwargs.get('target_domain', 'unknown')
        
        # 更新请求模式
        pattern_key = f"{request_type}:{target_domain}"
        self.request_patterns[pattern_key] += 1
        
        # 基于历史数据选择最佳代理
        best_proxy = self._select_best_proxy_for_pattern(
            available_proxies, pattern_key
        )
        
        if best_proxy:
            return best_proxy
        
        # 如果没有历史数据，使用自适应策略
        adaptive_rotator = AdaptiveRotator()
        adaptive_rotator.usage_stats = self.usage_stats
        adaptive_rotator.last_used = self.last_used
        adaptive_rotator.failure_counts = self.failure_counts
        adaptive_rotator.success_counts = self.success_counts
        
        return adaptive_rotator.select_proxy(available_proxies, **kwargs)
    
    def _select_best_proxy_for_pattern(self, proxies: List[ProxyInfo], pattern: str) -> Optional[ProxyInfo]:
        """为特定模式选择最佳代理"""
        if pattern not in self.learning_data or not self.learning_data[pattern]:
            return None
        
        # 计算每个代理对该模式的适应性
        proxy_scores = {}
        
        for proxy in proxies:
            proxy_key = f"{proxy.host}:{proxy.port}"
            
            # 查找该代理在此模式下的历史表现
            pattern_data = [
                data for data in self.learning_data[pattern]
                if data['proxy_key'] == proxy_key
            ]
            
            if pattern_data:
                # 计算平均性能
                avg_success_rate = sum(d['success'] for d in pattern_data) / len(pattern_data)
                avg_response_time = sum(d['response_time'] for d in pattern_data if d['response_time']) / len(pattern_data)
                
                # 综合评分
                score = avg_success_rate * 100 - avg_response_time * 5
                proxy_scores[proxy_key] = score
        
        if not proxy_scores:
            return None
        
        # 选择评分最高的代理
        best_proxy_key = max(proxy_scores.keys(), key=lambda k: proxy_scores[k])
        
        for proxy in proxies:
            if f"{proxy.host}:{proxy.port}" == best_proxy_key:
                return proxy
        
        return None
    
    def record_usage(self, proxy: ProxyInfo, success: bool = True, response_time: float = None, **kwargs):
        """记录使用情况（学习版）"""
        super().record_usage(proxy, success, response_time)
        
        # 记录学习数据
        request_type = kwargs.get('request_type', 'default')
        target_domain = kwargs.get('target_domain', 'unknown')
        pattern_key = f"{request_type}:{target_domain}"
        
        learning_record = {
            'timestamp': time.time(),
            'proxy_key': f"{proxy.host}:{proxy.port}",
            'success': success,
            'response_time': response_time or 0,
            'request_type': request_type,
            'target_domain': target_domain
        }
        
        self.learning_data[pattern_key].append(learning_record)
        
        # 保持学习数据大小
        if len(self.learning_data[pattern_key]) > 200:
            self.learning_data[pattern_key] = self.learning_data[pattern_key][-100:]
    
    def get_learning_insights(self) -> Dict:
        """获取学习洞察"""
        insights = {
            'patterns': {},
            'proxy_performance': {},
            'recommendations': []
        }
        
        # 分析模式
        for pattern, data in self.learning_data.items():
            if len(data) >= 10:  # 至少10个样本
                success_rate = sum(d['success'] for d in data) / len(data)
                avg_response_time = sum(d['response_time'] for d in data if d['response_time']) / len(data)
                
                insights['patterns'][pattern] = {
                    'sample_count': len(data),
                    'success_rate': success_rate,
                    'avg_response_time': avg_response_time
                }
        
        # 分析代理性能
        proxy_performance = defaultdict(lambda: {'total': 0, 'success': 0, 'response_times': []})
        
        for pattern_data in self.learning_data.values():
            for record in pattern_data:
                proxy_key = record['proxy_key']
                proxy_performance[proxy_key]['total'] += 1
                if record['success']:
                    proxy_performance[proxy_key]['success'] += 1
                if record['response_time']:
                    proxy_performance[proxy_key]['response_times'].append(record['response_time'])
        
        for proxy_key, perf in proxy_performance.items():
            if perf['total'] >= 5:  # 至少5个样本
                success_rate = perf['success'] / perf['total']
                avg_response_time = sum(perf['response_times']) / len(perf['response_times']) if perf['response_times'] else 0
                
                insights['proxy_performance'][proxy_key] = {
                    'success_rate': success_rate,
                    'avg_response_time': avg_response_time,
                    'sample_count': perf['total']
                }
        
        # 生成建议
        insights['recommendations'] = self._generate_learning_recommendations(insights)
        
        return insights
    
    def _generate_learning_recommendations(self, insights: Dict) -> List[str]:
        """生成学习建议"""
        recommendations = []
        
        # 基于代理性能的建议
        if insights['proxy_performance']:
            best_proxies = sorted(
                insights['proxy_performance'].items(),
                key=lambda x: (x[1]['success_rate'], -x[1]['avg_response_time']),
                reverse=True
            )[:3]
            
            if best_proxies:
                recommendations.append(
                    f"表现最佳的代理: {', '.join([p[0] for p in best_proxies])}"
                )
        
        # 基于模式的建议
        if insights['patterns']:
            problematic_patterns = [
                pattern for pattern, data in insights['patterns'].items()
                if data['success_rate'] < 0.7
            ]
            
            if problematic_patterns:
                recommendations.append(
                    f"需要优化的请求模式: {', '.join(problematic_patterns)}"
                )
        
        return recommendations

# 工厂函数
def create_proxy_rotator(strategy: str = "round_robin", **kwargs) -> ProxyRotator:
    """创建代理轮换器"""
    strategy_map = {
        "round_robin": RoundRobinRotator,
        "random": RandomRotator,
        "weighted": WeightedRotator,
        "fastest": FastestRotator,
        "least_used": LeastUsedRotator,
        "geographic": GeographicRotator,
        "adaptive": AdaptiveRotator,
        "smart": SmartRotator
    }
    
    if strategy not in strategy_map:
        raise ValueError(f"不支持的轮换策略: {strategy}")
    
    return strategy_map[strategy]()
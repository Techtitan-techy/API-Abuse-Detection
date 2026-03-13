from typing import Dict, Optional
from features.redis_client import RedisFeatureStore
import config

class RuleBasedDetector:
    def __init__(self):
        self.redis = RedisFeatureStore()
        self.thresholds = config.RULE_BASED_THRESHOLDS

    def detect(self, user_id: str, ip: str, features: Dict[str, float]) -> Dict:
        if self.redis.is_blacklisted(ip, "ip"):
            return {
                'is_attack': True,
                'confidence': 1.0,
                'reason': 'blacklisted_ip',
                'action': 'block',
                'rule': 'blacklist'
            }

        if self.redis.is_blacklisted(user_id, "user"):
            return {
                'is_attack': True,
                'confidence': 1.0,
                'reason': 'blacklisted_user',
                'action': 'block',
                'rule': 'blacklist'
            }

        if features.get('request_rate_1m', 0) > self.thresholds['requests_per_minute']:
            return {
                'is_attack': True,
                'confidence': 0.95,
                'reason': f"rate_limit_1m_exceeded ({features['request_rate_1m']:.0f} > {self.thresholds['requests_per_minute']})",
                'action': 'block',
                'rule': 'rate_limit_1m'
            }

        if features.get('request_rate_5m', 0) > self.thresholds['requests_per_5min']:
            return {
                'is_attack': True,
                'confidence': 0.90,
                'reason': f"rate_limit_5m_exceeded ({features['request_rate_5m']:.0f} > {self.thresholds['requests_per_5min']})",
                'action': 'rate_limit',
                'rule': 'rate_limit_5m'
            }

        if features.get('failed_auth_sequence', 0) >= self.thresholds['failed_auth_per_hour']:
            return {
                'is_attack': True,
                'confidence': 0.92,
                'reason': f"brute_force_detected ({features['failed_auth_sequence']:.0f} failed attempts)",
                'action': 'block',
                'rule': 'brute_force'
            }

        if features.get('error_rate_5m', 0) > self.thresholds['error_rate_threshold']:
            return {
                'is_attack': True,
                'confidence': 0.85,
                'reason': f"high_error_rate ({features['error_rate_5m']:.2%} > {self.thresholds['error_rate_threshold']:.0%})",
                'action': 'rate_limit',
                'rule': 'high_error_rate'
            }

        if features.get('endpoint_diversity_15m', 0) > self.thresholds['endpoint_diversity_threshold']:
            return {
                'is_attack': True,
                'confidence': 0.88,
                'reason': f"scraping_detected ({features['endpoint_diversity_15m']:.0f} unique endpoints)",
                'action': 'rate_limit',
                'rule': 'scraping'
            }

        if features.get('ip_user_cardinality', 0) > 20:
            return {
                'is_attack': True,
                'confidence': 0.90,
                'reason': f"credential_stuffing ({features['ip_user_cardinality']:.0f} users from IP)",
                'action': 'block',
                'rule': 'credential_stuffing'
            }

        if features.get('user_ip_cardinality', 0) > 10:
            return {
                'is_attack': True,
                'confidence': 0.87,
                'reason': f"distributed_attack ({features['user_ip_cardinality']:.0f} IPs)",
                'action': 'rate_limit',
                'rule': 'distributed_attack'
            }

        user_agent = features.get('user_agent_suspicion', 0)
        if user_agent > 0.8:
            return {
                'is_attack': True,
                'confidence': 0.88,
                'reason': 'bot_user_agent_detected',
                'action': 'block',
                'rule': 'bot_user_agent'
            }

        if features.get('geolocation_velocity', 0) > 0.8:
            return {
                'is_attack': True,
                'confidence': 0.93,
                'reason': 'impossible_travel_detected',
                'action': 'block',
                'rule': 'impossible_travel'
            }

        return {
            'is_attack': False,
            'confidence': 0.0,
            'reason': 'passed_all_rules',
            'action': 'allow',
            'rule': None
        }

    def add_to_blacklist(self, identifier: str, identifier_type: str = "ip", duration: int = 86400):
        self.redis.add_to_blacklist(identifier, identifier_type, ttl=duration)

    def get_statistics(self) -> Dict:
        return {
            "detector": "rule_based",
            "expected_precision": 0.92,
            "expected_recall": 0.62,
            "avg_latency_ms": 1.2
        }

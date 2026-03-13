import numpy as np
from typing import Dict, List
from datetime import datetime
from scipy.stats import entropy
from features.redis_client import RedisFeatureStore
import config

class FeatureExtractor:
    def __init__(self):
        self.redis = RedisFeatureStore()

    def extract_features(self, request: Dict) -> Dict[str, float]:
        timestamp = request.get('timestamp', datetime.now().timestamp())
        user_id = request['user_id']
        ip = request['ip']

        features = {}
        features.update(self._extract_sliding_window_features(user_id, timestamp))
        features.update(self._extract_entropy_features(user_id, request))
        features.update(self._extract_temporal_features(user_id, timestamp))
        features.update(self._extract_sequence_features(user_id, request, timestamp))
        features.update(self._extract_fingerprint_features(user_id, ip, request))
        self._store_request_data(user_id, request, timestamp)
        return features

    def _extract_sliding_window_features(self, user_id: str, timestamp: float) -> Dict[str, float]:
        features = {}
        features['request_rate_1m'] = self.redis.increment_request_count(user_id, timestamp, 60)
        features['request_rate_5m'] = self.redis.increment_request_count(user_id, timestamp, 300)
        features['request_rate_15m'] = self.redis.increment_request_count(user_id, timestamp, 900)
        features['error_rate_5m'] = self.redis.get_error_rate(user_id, 300)
        features['rate_acceleration'] = features['request_rate_1m'] - (features['request_rate_5m'] / 5.0)
        return features

    def _extract_entropy_features(self, user_id: str, request: Dict) -> Dict[str, float]:
        features = {}
        intervals = self.redis.get_request_intervals(user_id, limit=20)
        if len(intervals) >= 3:
            bins = [0, 1, 5, 15, 60, np.inf]
            hist, _ = np.histogram(intervals, bins=bins)
            if hist.sum() > 0:
                probs = hist / hist.sum()
                features['timing_entropy'] = entropy(probs + 1e-10, base=2)
            else:
                features['timing_entropy'] = 0.0
        else:
            features['timing_entropy'] = 0.0

        param_str = str(request.get('params', ''))
        if len(param_str) > 5:
            char_counts = {}
            for char in param_str:
                char_counts[char] = char_counts.get(char, 0) + 1
            char_probs = np.array(list(char_counts.values())) / len(param_str)
            features['parameter_entropy'] = entropy(char_probs, base=2)
        else:
            features['parameter_entropy'] = 0.0

        return features

    def _extract_temporal_features(self, user_id: str, timestamp: float) -> Dict[str, float]:
        features = {}
        intervals = self.redis.get_request_intervals(user_id, limit=20)
        if len(intervals) >= 2:
            features['interval_mean'] = np.mean(intervals)
            features['interval_stddev'] = np.std(intervals)
            features['interval_cv'] = features['interval_stddev'] / (features['interval_mean'] + 1e-6)
        else:
            features['interval_mean'] = 0.0
            features['interval_stddev'] = 0.0
            features['interval_cv'] = 0.0

        hour = datetime.fromtimestamp(timestamp).hour
        features['hour_of_day'] = hour
        ewma_result = self.redis.update_ewma(user_id, "hour", hour, alpha=config.EWMA_ALPHA)
        features['hour_z_score'] = abs(ewma_result['z_score'])
        return features

    def _extract_sequence_features(self, user_id: str, request: Dict, timestamp: float) -> Dict[str, float]:
        features = {}
        if request.get('status_code') == 401:
            failed_count = self.redis.track_failed_auth(request['ip'], timestamp)
            features['failed_auth_sequence'] = min(failed_count, 10)
        else:
            failed_count = self.redis.client.zcard(f"auth_fail:{request['ip']}") or 0
            features['failed_auth_sequence'] = min(failed_count, 10)

        method_map = {'GET': 0, 'POST': 1, 'PUT': 2, 'DELETE': 3, 'PATCH': 4}
        features['http_method'] = method_map.get(request.get('method', 'GET'), 0)
        features['status_code'] = request.get('status_code', 200)
        return features

    def _extract_fingerprint_features(self, user_id: str, ip: str, request: Dict) -> Dict[str, float]:
        features = {}
        ip_user_card = self.redis.update_ip_user_cardinality(ip, user_id)
        features['ip_user_cardinality'] = min(ip_user_card, 100)

        user_ip_card = self.redis.update_user_ip_cardinality(user_id, ip)
        features['user_ip_cardinality'] = min(user_ip_card, 50)

        endpoint_count = self.redis.add_endpoint_access(user_id, request['endpoint'], 900)
        features['endpoint_diversity_15m'] = min(endpoint_count, 100)

        previous_ua = self.redis.get_user_agent_history(user_id)
        current_ua = request.get('user_agent', '')

        if previous_ua is None:
            features['user_agent_changed'] = 0.0
            self.redis.set_user_agent(user_id, current_ua)
        else:
            features['user_agent_changed'] = 1.0 if previous_ua != current_ua else 0.0

        features['user_agent_suspicion'] = self._analyze_user_agent(current_ua)

        if request.get('geolocation'):
            features['geolocation_velocity'] = self._calculate_geo_velocity(user_id, request['geolocation'], request['timestamp'])
        else:
            features['geolocation_velocity'] = 0.0

        return features

    def _analyze_user_agent(self, user_agent: str) -> float:
        if not user_agent:
            return 0.5

        ua_lower = user_agent.lower()
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'scrapy',
            'wget', 'curl', 'python-requests', 'python-urllib',
            'java/', 'go-http-client', 'axios', 'postman'
        ]

        for pattern in bot_patterns:
            if pattern in ua_lower:
                return 0.95

        if len(user_agent) < 20:
            return 0.7

        browser_indicators = ['mozilla', 'chrome', 'safari', 'firefox', 'edge']
        has_browser = any(indicator in ua_lower for indicator in browser_indicators)

        if not has_browser:
            return 0.6

        return 0.0

    def _calculate_geo_velocity(self, user_id: str, current_geo: Dict, timestamp: float) -> float:
        key = f"user:{user_id}:last_geo"
        last_geo_str = self.redis.client.get(key)

        if last_geo_str is None:
            import json
            self.redis.client.setex(key, 3600, json.dumps({
                'lat': current_geo['lat'],
                'lon': current_geo['lon'],
                'timestamp': timestamp
            }))
            return 0.0

        import json
        last_geo = json.loads(last_geo_str)

        from math import radians, sin, cos, sqrt, atan2

        lat1, lon1 = radians(last_geo['lat']), radians(last_geo['lon'])
        lat2, lon2 = radians(current_geo['lat']), radians(current_geo['lon'])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = 6371 * c

        time_diff_hours = (timestamp - last_geo['timestamp']) / 3600

        if time_diff_hours < 0.01:
            return 0.0

        velocity_kmh = distance_km / time_diff_hours

        self.redis.client.setex(key, 3600, json.dumps({
            'lat': current_geo['lat'],
            'lon': current_geo['lon'],
            'timestamp': timestamp
        }))

        if velocity_kmh > 1000:
            return 1.0
        elif velocity_kmh > 500:
            return (velocity_kmh - 500) / 500
        else:
            return 0.0

    def _store_request_data(self, user_id: str, request: Dict, timestamp: float):
        if request.get('status_code', 200) >= 400:
            for window in config.SLIDING_WINDOWS:
                self.redis.increment_error_count(user_id, timestamp, window)

        sequence_data = {
            'timestamp': timestamp,
            'endpoint': request['endpoint'],
            'method': request.get('method', 'GET'),
            'status_code': request.get('status_code', 200)
        }
        self.redis.add_to_sequence(user_id, sequence_data, max_length=config.SEQUENCE_LENGTH)

    def extract_sequence_features_for_lstm(self, user_id: str) -> np.ndarray:
        key = f"user:{user_id}:sequence"
        sequence = self.redis.client.lrange(key, 0, -1)

        if not sequence:
            return np.zeros((config.SEQUENCE_LENGTH, 4))

        import json
        sequence_data = [json.loads(item) for item in sequence]

        features_list = []
        method_map = {'GET': 0, 'POST': 1, 'PUT': 2, 'DELETE': 3, 'PATCH': 4}

        for item in sequence_data:
            features = [
                method_map.get(item['method'], 0),
                item['status_code'] / 500,
                hash(item['endpoint']) % 1000 / 1000,
                0.0
            ]
            features_list.append(features)

        while len(features_list) < config.SEQUENCE_LENGTH:
            features_list.insert(0, [0.0, 0.0, 0.0, 0.0])

        features_list = features_list[-config.SEQUENCE_LENGTH:]

        return np.array(features_list, dtype=np.float32)

    def normalize_features(self, features: Dict[str, float]) -> np.ndarray:
        feature_order = [
            'request_rate_1m', 'request_rate_5m', 'request_rate_15m',
            'error_rate_5m', 'rate_acceleration',
            'timing_entropy', 'parameter_entropy',
            'interval_mean', 'interval_stddev', 'interval_cv',
            'hour_of_day', 'hour_z_score',
            'failed_auth_sequence', 'http_method', 'status_code',
            'ip_user_cardinality', 'user_ip_cardinality',
            'endpoint_diversity_15m', 'user_agent_changed',
            'user_agent_suspicion', 'geolocation_velocity'
        ]

        feature_array = np.array([features.get(f, 0.0) for f in feature_order], dtype=np.float32)

        skewed_indices = [0, 1, 2, 15, 16, 17]
        feature_array[skewed_indices] = np.log1p(feature_array[skewed_indices])

        return feature_array

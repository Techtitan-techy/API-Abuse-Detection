import redis
import json
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import config

class RedisFeatureStore:
    def __init__(self):
        try:
            self.client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
            self.client.ping()
        except Exception as e:
            print(f"Warning: Could not connect to Redis ({e}). Using FakeRedis.")
            import fakeredis
            self.client = fakeredis.FakeRedis(decode_responses=True)

    def increment_request_count(self, user_id: str, timestamp: float, window_seconds: int) -> int:
        key = f"user:{user_id}:requests:{window_seconds}s"
        pipe = self.client.pipeline()
        pipe.zadd(key, {str(timestamp): timestamp})
        pipe.zremrangebyscore(key, 0, timestamp - window_seconds)
        pipe.zcard(key)
        pipe.expire(key, window_seconds * 2)
        _, _, count, _ = pipe.execute()
        return count

    def increment_error_count(self, user_id: str, timestamp: float, window_seconds: int) -> int:
        key = f"user:{user_id}:errors:{window_seconds}s"
        pipe = self.client.pipeline()
        pipe.zadd(key, {str(timestamp): timestamp})
        pipe.zremrangebyscore(key, 0, timestamp - window_seconds)
        pipe.zcard(key)
        pipe.expire(key, window_seconds * 2)
        _, _, count, _ = pipe.execute()
        return count

    def get_error_rate(self, user_id: str, window_seconds: int) -> float:
        error_count = self.client.zcard(f"user:{user_id}:errors:{window_seconds}s") or 0
        total_count = self.client.zcard(f"user:{user_id}:requests:{window_seconds}s") or 1
        return error_count / total_count

    def add_endpoint_access(self, user_id: str, endpoint: str, window_seconds: int) -> int:
        key = f"user:{user_id}:endpoints:{window_seconds}s"
        self.client.pfadd(key, endpoint)
        self.client.expire(key, window_seconds * 2)
        return self.client.pfcount(key)

    def add_to_sequence(self, user_id: str, data: Dict, max_length: int = 10) -> List[Dict]:
        key = f"user:{user_id}:sequence"
        self.client.rpush(key, json.dumps(data))
        self.client.ltrim(key, -max_length, -1)
        self.client.expire(key, 3600)
        sequence = self.client.lrange(key, 0, -1)
        return [json.loads(item) for item in sequence]

    def track_failed_auth(self, identifier: str, timestamp: float) -> int:
        key = f"auth_fail:{identifier}"
        pipe = self.client.pipeline()
        pipe.zadd(key, {str(timestamp): timestamp})
        pipe.zremrangebyscore(key, 0, timestamp - 3600)
        pipe.zcard(key)
        pipe.expire(key, 7200)
        _, _, count, _ = pipe.execute()
        return count

    def update_ip_user_cardinality(self, ip: str, user_id: str) -> int:
        key = f"ip:{ip}:users"
        self.client.pfadd(key, user_id)
        self.client.expire(key, 3600)
        return self.client.pfcount(key)

    def update_user_ip_cardinality(self, user_id: str, ip: str) -> int:
        key = f"user:{user_id}:ips"
        self.client.pfadd(key, ip)
        self.client.expire(key, 3600)
        return self.client.pfcount(key)

    def get_user_agent_history(self, user_id: str) -> Optional[str]:
        key = f"user:{user_id}:user_agent"
        return self.client.get(key)

    def set_user_agent(self, user_id: str, user_agent: str):
        key = f"user:{user_id}:user_agent"
        self.client.setex(key, 86400, user_agent)

    def update_ewma(self, user_id: str, metric: str, value: float, alpha: float = 0.3) -> Dict[str, float]:
        mean_key = f"ewma:{user_id}:{metric}:mean"
        std_key = f"ewma:{user_id}:{metric}:std"
        current_mean = float(self.client.get(mean_key) or value)
        current_std = float(self.client.get(std_key) or 1.0)
        z_score = (value - current_mean) / (current_std + 1e-6)
        new_mean = alpha * value + (1 - alpha) * current_mean
        new_std = np.sqrt(alpha * (value - new_mean)**2 + (1 - alpha) * current_std**2)
        self.client.setex(mean_key, 3600, float(new_mean))
        self.client.setex(std_key, 3600, float(new_std))
        return {
            "mean": new_mean,
            "std": new_std,
            "z_score": z_score
        }

    def get_request_intervals(self, user_id: str, limit: int = 20) -> List[float]:
        key = f"user:{user_id}:requests:900s"
        timestamps = self.client.zrange(key, 0, -1, withscores=True)
        if len(timestamps) < 2:
            return []
        intervals = []
        for i in range(1, min(len(timestamps), limit)):
            interval = timestamps[i][1] - timestamps[i-1][1]
            intervals.append(interval)
        return intervals

    def is_blacklisted(self, identifier: str, identifier_type: str = "ip") -> bool:
        key = f"{identifier_type}:blacklist"
        return self.client.sismember(key, identifier)

    def add_to_blacklist(self, identifier: str, identifier_type: str = "ip", ttl: int = 86400):
        key = f"{identifier_type}:blacklist"
        self.client.sadd(key, identifier)
        self.client.expire(key, ttl)

    def flush_all(self):
        self.client.flushdb()

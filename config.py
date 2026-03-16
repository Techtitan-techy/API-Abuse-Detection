import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

RULE_BASED_THRESHOLDS = {
    "requests_per_minute": 60,
    "requests_per_5min": 250,
    "failed_auth_per_hour": 5,
    "error_rate_threshold": 0.50,
    "endpoint_diversity_threshold": 50
}

EWMA_ALPHA = 0.3
EWMA_THRESHOLD = 3.0
ISOLATION_FOREST_CONTAMINATION = 0.01

ENSEMBLE_WEIGHTS = {
    "xgboost": 0.50,
    "lstm": 0.30,
    "autoencoder": 0.20
}

DETECTION_THRESHOLD = 0.45
ADAPTIVE_THRESHOLD_ALPHA = 0.1

SLIDING_WINDOWS = [60, 300, 900]
SEQUENCE_LENGTH = 10

SCALE_POS_WEIGHT = 99
SMOTE_SAMPLING_STRATEGY = 0.1

MAX_LATENCY_MS = 50

XGBOOST_MODEL_PATH = os.environ.get("XGBOOST_MODEL_PATH", "models/trained/xgboost_model.json")
LSTM_MODEL_PATH = os.environ.get("LSTM_MODEL_PATH", "models/trained/lstm_model.pth")
AUTOENCODER_MODEL_PATH = os.environ.get("AUTOENCODER_MODEL_PATH", "models/trained/autoencoder_model.pth")
FEATURE_SCALER_PATH = os.environ.get("FEATURE_SCALER_PATH", "models/trained/feature_scaler.pkl")

POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "postgresql://user:password@localhost:5432/api_abuse_detection")
CLICKHOUSE_HOST = os.environ.get("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.environ.get("CLICKHOUSE_PORT", 9000))

ENABLE_PROMETHEUS = os.environ.get("ENABLE_PROMETHEUS", "True").lower() == "true"
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 9090))

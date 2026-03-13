from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Optional
import time
from datetime import datetime

from features import FeatureExtractor
from models import RuleBasedDetector, StatisticalDetector, MLEnsembleDetector

app = FastAPI(title="API Abuse Detection System", version="1.0.0")

feature_extractor = FeatureExtractor()
rule_detector = RuleBasedDetector()
statistical_detector = StatisticalDetector()
ml_detector = MLEnsembleDetector()

try:
    ml_detector.load_models()
    print("✓ Pre-trained models loaded")
except:
    print("⚠ No pre-trained models found - will use default behavior")

class APIRequest(BaseModel):
    user_id: str
    ip: str
    endpoint: str
    method: str = "GET"
    status_code: int = 200
    user_agent: str = ""
    params: Optional[Dict] = None
    geolocation: Optional[Dict] = None
    timestamp: Optional[float] = None

class DetectionResponse(BaseModel):
    action: str
    confidence: float
    risk_score: float
    reason: str
    latency_ms: float
    details: Dict

@app.get("/")
async def root():
    return {
        "service": "API Abuse Detection System",
        "status": "running",
        "version": "1.0.0",
        "layers": ["rule_based", "statistical", "ml_ensemble"]
    }

@app.post("/detect", response_model=DetectionResponse)
async def detect_abuse(request: APIRequest):
    start_time = time.time()

    request_dict = {
        'user_id': request.user_id,
        'ip': request.ip,
        'endpoint': request.endpoint,
        'method': request.method,
        'status_code': request.status_code,
        'user_agent': request.user_agent,
        'params': request.params or {},
        'geolocation': request.geolocation,
        'timestamp': request.timestamp or time.time()
    }

    features = feature_extractor.extract_features(request_dict)
    rule_result = rule_detector.detect(request.user_id, request.ip, features)

    if rule_result['is_attack']:
        latency_ms = (time.time() - start_time) * 1000
        return DetectionResponse(
            action=rule_result['action'],
            confidence=rule_result['confidence'],
            risk_score=rule_result['confidence'],
            reason=rule_result['reason'],
            latency_ms=latency_ms,
            details={
                'layer': 'rule_based',
                'rule': rule_result['rule'],
                'features': features
            }
        )

    feature_array = feature_extractor.normalize_features(features)
    stat_result = statistical_detector.detect(request.user_id, feature_array)

    if stat_result['is_anomaly'] and stat_result['anomaly_score'] > 0.75:
        latency_ms = (time.time() - start_time) * 1000
        return DetectionResponse(
            action='rate_limit',
            confidence=stat_result['anomaly_score'],
            risk_score=stat_result['anomaly_score'],
            reason=f"statistical_anomaly_detected ({stat_result['method']})",
            latency_ms=latency_ms,
            details={
                'layer': 'statistical',
                'method': stat_result['method'],
                'details': stat_result['details']
            }
        )

    sequence_features = feature_extractor.extract_sequence_features_for_lstm(request.user_id)
    ml_result = ml_detector.detect(feature_array, sequence_features)

    if ml_result['prediction'] == 'attack':
        if ml_result['ensemble_score'] > 0.85:
            action = 'block'
        elif ml_result['ensemble_score'] > 0.65:
            action = 'rate_limit'
        else:
            action = 'allow'
    else:
        action = 'allow'

    combined_score = max(ml_result['ensemble_score'], stat_result['anomaly_score'] * 0.8)

    latency_ms = (time.time() - start_time) * 1000

    return DetectionResponse(
        action=action,
        confidence=ml_result['ensemble_score'],
        risk_score=combined_score,
        reason=f"ml_ensemble_decision (consensus: {ml_result['consensus']})",
        latency_ms=latency_ms,
        details={
            'layer': 'ml_ensemble',
            'model_scores': ml_result['model_scores'],
            'consensus': ml_result['consensus'],
            'statistical_score': stat_result['anomaly_score']
        }
    )

@app.post("/feedback")
async def submit_feedback(user_id: str, request_id: str, is_false_positive: bool):
    return {
        "status": "feedback_recorded",
        "user_id": user_id,
        "request_id": request_id,
        "is_false_positive": is_false_positive
    }

@app.get("/stats")
async def get_statistics():
    return {
        "rule_detector": rule_detector.get_statistics(),
        "statistical_detector": statistical_detector.get_statistics(),
        "ml_ensemble": ml_detector.get_statistics()
    }

@app.post("/blacklist/add")
async def add_to_blacklist(identifier: str, identifier_type: str = "ip", duration: int = 86400):
    rule_detector.add_to_blacklist(identifier, identifier_type, duration)
    return {
        "status": "added_to_blacklist",
        "identifier": identifier,
        "type": identifier_type,
        "duration": duration
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("Starting API Abuse Detection System")
    print("=" * 60)
    print("Endpoint: http://localhost:8000/detect")
    print("Docs: http://localhost:8000/docs")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

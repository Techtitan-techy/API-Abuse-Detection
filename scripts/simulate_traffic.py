import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import requests
import time
import random
from typing import Dict, List
from utils.metrics import MetricsCalculator

class TrafficGenerator:
    def __init__(self, attack_ratio=0.01):
        self.attack_ratio = attack_ratio
        self.user_ids = [f"user_{i}" for i in range(100)]
        self.ip_pool = [f"192.168.{i}.{j}" for i in range(1, 11) for j in range(1, 26)]
        self.endpoints = ["/api/login", "/api/dashboard", "/api/profile", "/api/products",
                         "/api/cart", "/api/checkout", "/api/search", "/api/settings"]

    def generate_normal_request(self) -> Dict:
        user_id = random.choice(self.user_ids)
        ip = random.choice(self.ip_pool)
        return {
            "user_id": user_id,
            "ip": ip,
            "endpoint": random.choice(self.endpoints),
            "method": random.choices(["GET", "POST", "PUT"], weights=[0.7, 0.25, 0.05])[0],
            "status_code": random.choices([200, 404, 500], weights=[0.95, 0.03, 0.02])[0],
            "user_agent": f"Mozilla/5.0 Chrome/{random.randint(90, 120)}",
            "params": {"q": random.choice(["product", "service", "info"])},
            "label": 0
        }

    def generate_attack_request(self, attack_type: str = None) -> Dict:
        if attack_type is None:
            attack_type = random.choice(["brute_force", "scraping", "credential_stuffing", "ddos"])

        if attack_type == "brute_force":
            ip = random.choice(self.ip_pool[:10])
            return {
                "user_id": random.choice(self.user_ids),
                "ip": ip,
                "endpoint": "/api/login",
                "method": "POST",
                "status_code": 401,
                "user_agent": "Python-requests/2.28.0",
                "params": {"username": "admin", "password": random.randint(1000, 9999)},
                "label": 1
            }

        elif attack_type == "scraping":
            user_id = f"bot_{random.randint(1, 10)}"
            return {
                "user_id": user_id,
                "ip": random.choice(self.ip_pool[:5]),
                "endpoint": random.choice(self.endpoints),
                "method": "GET",
                "status_code": 200,
                "user_agent": "Scrapy/2.7.0",
                "params": {},
                "label": 1
            }

        elif attack_type == "credential_stuffing":
            ip = random.choice(self.ip_pool[:5])
            return {
                "user_id": f"user_{random.randint(1, 1000)}",
                "ip": ip,
                "endpoint": "/api/login",
                "method": "POST",
                "status_code": random.choices([401, 200], weights=[0.95, 0.05])[0],
                "user_agent": "Python-requests/2.28.0",
                "params": {},
                "label": 1
            }

        else:
            return {
                "user_id": f"bot_{random.randint(1, 20)}",
                "ip": random.choice(self.ip_pool),
                "endpoint": random.choice(self.endpoints),
                "method": "GET",
                "status_code": 200,
                "user_agent": "Mozilla/5.0",
                "params": {},
                "label": 1
            }

    def generate_traffic(self, num_requests: int) -> List[Dict]:
        requests_list = []
        num_attacks = int(num_requests * self.attack_ratio)
        num_normal = num_requests - num_attacks
        print(f"Generating {num_requests} requests ({num_normal} normal, {num_attacks} attacks)...")
        for _ in range(num_normal):
            requests_list.append(self.generate_normal_request())
        for _ in range(num_attacks):
            requests_list.append(self.generate_attack_request())
        random.shuffle(requests_list)
        return requests_list

def train_models_offline():
    print("\n" + "=" * 60)
    print("OFFLINE MODEL TRAINING")
    print("=" * 60)

    generator = TrafficGenerator(attack_ratio=0.01)
    training_requests = generator.generate_traffic(num_requests=10000)
    print(f"Generated {len(training_requests)} training samples")

    from features import FeatureExtractor
    feature_extractor = FeatureExtractor()

    X_features = []
    X_sequences = []
    y_labels = []

    print("Extracting features...")
    for idx, req in enumerate(training_requests):
        if idx % 1000 == 0:
            print(f"  Processed {idx}/{len(training_requests)} requests...")

        features = feature_extractor.extract_features(req)
        feature_array = feature_extractor.normalize_features(features)
        sequence_array = feature_extractor.extract_sequence_features_for_lstm(req['user_id'])

        X_features.append(feature_array)
        X_sequences.append(sequence_array)
        y_labels.append(req['label'])

        if idx < 100:
            time.sleep(0.001)

    X_features = np.array(X_features)
    X_sequences = np.array(X_sequences)
    y_labels = np.array(y_labels)

    print(f"Feature extraction complete. Shape: {X_features.shape}")

    X_normal = X_features[y_labels == 0]
    print(f"Normal samples for autoencoder: {len(X_normal)}")

    print("\nTraining Statistical Detector...")
    from models import StatisticalDetector
    stat_detector = StatisticalDetector()
    stat_detector.train_isolation_forest(X_normal)

    print("\nTraining ML Ensemble...")
    from models import MLEnsembleDetector
    ml_detector = MLEnsembleDetector()
    ml_detector.train_all(X_features, y_labels, X_sequences, X_normal)

    ml_detector.save_models()

    print("\n" + "=" * 60)
    print("MODEL TRAINING COMPLETE")
    print("=" * 60)
    print("Models saved to models/trained/")
    print("You can now run the detection API with: python main.py")
    print("=" * 60 + "\n")

def evaluate_system():
    print("\n" + "=" * 60)
    print("SYSTEM EVALUATION")
    print("=" * 60)

    try:
        response = requests.get("http://localhost:8000/")
        print("✓ API is running")
    except:
        print("✗ API is not running. Start it with: python main.py")
        return

    generator = TrafficGenerator(attack_ratio=0.01)
    test_requests = generator.generate_traffic(num_requests=100)

    print(f"Generated {len(test_requests)} test requests")
    print("Sending requests to detection API...")

    metrics = MetricsCalculator()

    for idx, req in enumerate(test_requests):
        if idx % 100 == 0:
            print(f"  Progress: {idx}/{len(test_requests)}")

        label = req.pop('label')

        try:
            response = requests.post("http://localhost:8000/detect", json=req, timeout=5)
            result = response.json()
            prediction = 1 if result['action'] in ['block', 'rate_limit'] else 0
            score = result['risk_score']
            latency = result['latency_ms']
            metrics.add_prediction(label, prediction, score, latency)
        except Exception as e:
            print(f"Error processing request: {e}")
            continue

    metrics.print_report()

    optimal_threshold = metrics.get_optimal_threshold(method='f1')
    print(f"Optimal threshold for F1: {optimal_threshold:.3f}")

    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60 + "\n")

def run_live_demo():
    print("\n" + "=" * 60)
    print("LIVE DEMONSTRATION")
    print("=" * 60)
    print("Generating continuous traffic... Press Ctrl+C to stop\n")

    generator = TrafficGenerator(attack_ratio=0.05)

    try:
        request_count = 0
        attack_count = 0
        blocked_count = 0

        while True:
            if random.random() < 0.2:
                req = generator.generate_attack_request()
                is_attack = True
                attack_count += 1
            else:
                req = generator.generate_normal_request()
                is_attack = False

            label = req.pop('label')

            try:
                response = requests.post("http://localhost:8000/detect", json=req, timeout=5)
                result = response.json()

                request_count += 1

                action = result['action']
                if action in ['block', 'rate_limit']:
                    blocked_count += 1
                    status_icon = "🚫" if action == 'block' else "⚠️"
                else:
                    status_icon = "✓"

                print(f"{status_icon} [{request_count}] {req['user_id']:12s} | "
                      f"{req['ip']:15s} | {action:12s} | "
                      f"Risk: {result['risk_score']:.2f} | "
                      f"{'ATTACK' if is_attack else 'NORMAL':7s} | "
                      f"{result['latency_ms']:.1f}ms")

                if request_count % 50 == 0:
                    print(f"\n--- Stats: {request_count} requests, {attack_count} attacks, "
                          f"{blocked_count} blocked ({blocked_count/request_count:.1%}) ---\n")

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(random.uniform(0.1, 0.5))

    except KeyboardInterrupt:
        print("\n\nDemo stopped by user")
        print(f"Total: {request_count} requests, {attack_count} attacks, {blocked_count} blocked")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python simulate_traffic.py train     - Train models offline")
        print("  python simulate_traffic.py evaluate  - Evaluate system accuracy")
        print("  python simulate_traffic.py demo      - Run live demonstration")
        sys.exit(1)

    command = sys.argv[1]

    if command == "train":
        train_models_offline()
    elif command == "evaluate":
        evaluate_system()
    elif command == "demo":
        run_live_demo()
    else:
        print(f"Unknown command: {command}")
        print("Use: train, evaluate, or demo")

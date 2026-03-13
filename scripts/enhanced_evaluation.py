import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import requests
import time
import random
import json
from typing import Dict, List, Tuple
from utils.metrics import MetricsCalculator


class EnhancedTrafficGenerator:
    def __init__(self, attack_ratio=0.01):
        self.attack_ratio = attack_ratio
        self.user_ids = [f"user_{i}" for i in range(100)]
        self.ip_pool = [f"192.168.{i}.{j}" for i in range(1, 11) for j in range(1, 26)]
        self.bot_ips = [f"10.0.0.{i}" for i in range(1, 20)]
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

    def generate_brute_force_attack(self) -> Dict:
        ip = random.choice(self.bot_ips)
        return {
            "user_id": random.choice(["admin", "root", "user_1"]),
            "ip": ip,
            "endpoint": "/api/login",
            "method": "POST",
            "status_code": 401,
            "user_agent": "Python-requests/2.28.0",
            "params": {"username": "admin", "password": str(random.randint(1000, 9999))},
            "label": 1
        }

    def generate_scraping_attack(self) -> Dict:
        user_id = f"bot_{random.randint(1, 10)}"
        ip = random.choice(self.bot_ips)
        return {
            "user_id": user_id,
            "ip": ip,
            "endpoint": random.choice(self.endpoints),
            "method": "GET",
            "status_code": 200,
            "user_agent": random.choice(["Scrapy/2.7.0", "wget/1.20", "curl/7.68.0"]),
            "params": {},
            "label": 1
        }

    def generate_ddos_attack(self) -> Dict:
        return {
            "user_id": f"bot_{random.randint(1, 20)}",
            "ip": random.choice(self.bot_ips),
            "endpoint": random.choice(self.endpoints),
            "method": "GET",
            "status_code": 200,
            "user_agent": "Mozilla/5.0",
            "params": {},
            "label": 1
        }

    def generate_credential_stuffing_attack(self) -> Dict:
        ip = random.choice(self.bot_ips[:5])
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

    def generate_attack_request(self, attack_type: str = None) -> Dict:
        if attack_type is None:
            attack_type = random.choice([
                "brute_force", "scraping", "credential_stuffing", "ddos"
            ])
        if attack_type == "brute_force":
            return self.generate_brute_force_attack()
        elif attack_type == "scraping":
            return self.generate_scraping_attack()
        elif attack_type == "credential_stuffing":
            return self.generate_credential_stuffing_attack()
        else:
            return self.generate_ddos_attack()

    def generate_traffic(self, num_requests: int, attack_ratio: float = None) -> List[Dict]:
        if attack_ratio is None:
            attack_ratio = self.attack_ratio
        requests_list = []
        num_attacks = max(1, int(num_requests * attack_ratio))
        num_normal = num_requests - num_attacks
        print(f"Generating {num_requests} requests ({num_normal} normal, {num_attacks} attacks)...")
        for _ in range(num_normal):
            requests_list.append(self.generate_normal_request())
        attack_types = ["brute_force", "scraping", "credential_stuffing", "ddos"]
        for i in range(num_attacks):
            attack_type = attack_types[i % len(attack_types)]
            requests_list.append(self.generate_attack_request(attack_type))
        random.shuffle(requests_list)
        return requests_list


def evaluate_dataset(dataset_name: str, test_requests: List[Dict],
                     api_url: str = "http://localhost:8000/detect") -> Dict:
    print(f"\n{'='*70}")
    print(f"EVALUATING: {dataset_name}")
    print(f"{'='*70}")

    metrics = MetricsCalculator()

    total_attacks = sum(1 for req in test_requests if req.get('label') == 1)
    total_normal = len(test_requests) - total_attacks
    print(f"Dataset: {len(test_requests)} requests ({total_normal} normal, {total_attacks} attacks)")
    print("Processing requests...")

    for idx, req in enumerate(test_requests):
        if idx % 50 == 0 and idx > 0:
            print(f"  Progress: {idx}/{len(test_requests)}")

        label = req.pop('label')

        try:
            response = requests.post(api_url, json=req, timeout=5)
            result = response.json()
            prediction = 1 if result['action'] in ['block', 'rate_limit'] else 0
            score = result['risk_score']
            latency = result['latency_ms']
            metrics.add_prediction(label, prediction, score, latency)
        except Exception as e:
            print(f"Error processing request: {e}")
            continue

    results = metrics.compute_metrics()
    results['latency_stats'] = {
        'average': results['latency']['avg_ms'],
        'median': results['latency']['p50_ms'],
        'p95': results['latency']['p95_ms'],
        'p99': results['latency']['p99_ms']
    }
    return results


def run_three_dataset_evaluation():
    print("\n" + "="*70)
    print("MULTI-DATASET EVALUATION")
    print("="*70)

    try:
        response = requests.get("http://localhost:8000/")
        print("✓ API is running\n")
    except:
        print("✗ API is not running. Start it with: python main.py")
        return

    generator = EnhancedTrafficGenerator()

    print("\n" + "="*70)
    print("DATASET 1: Realistic Production Traffic (1% attack rate)")
    print("="*70)
    print("Simulates: Real-world scenario with rare attacks")

    dataset1 = generator.generate_traffic(num_requests=20, attack_ratio=0.01)
    results1 = evaluate_dataset("Dataset 1 - Low Attack Rate (1%)", dataset1)

    print("\n" + "="*70)
    print("DATASET 2: System Under Attack (10% attack rate)")
    print("="*70)
    print("Simulates: Active attack scenario")

    dataset2 = generator.generate_traffic(num_requests=30, attack_ratio=0.10)
    results2 = evaluate_dataset("Dataset 2 - Moderate Attack Rate (10%)", dataset2)

    print("\n" + "="*70)
    print("DATASET 3: Heavy Attack Scenario (25% attack rate)")
    print("="*70)
    print("Simulates: Coordinated attack campaign")

    dataset3 = generator.generate_traffic(num_requests=25, attack_ratio=0.25)
    results3 = evaluate_dataset("Dataset 3 - High Attack Rate (25%)", dataset3)

    print("\n" + "="*70)
    print("COMPARATIVE SUMMARY - ALL THREE DATASETS")
    print("="*70)

    datasets = [
        ("Dataset 1 (1% attacks)", results1),
        ("Dataset 2 (10% attacks)", results2),
        ("Dataset 3 (25% attacks)", results3)
    ]

    print(f"\n{'Dataset':<30} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'FPR':<10}")
    print("-" * 80)
    for name, results in datasets:
        precision = results.get('precision', 0) * 100
        recall = results.get('recall', 0) * 100
        f1 = results.get('f1_score', 0) * 100
        fpr = results.get('fpr', 0) * 100
        print(f"{name:<30} | {precision:>8.2f}% | {recall:>8.2f}% | {f1:>8.2f}% | {fpr:>8.2f}%")

    print("\n" + "="*70)
    print("LATENCY COMPARISON")
    print("="*70)
    print(f"\n{'Dataset':<30} | {'Avg (ms)':<10} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'P99 (ms)':<10}")
    print("-" * 90)
    for name, results in datasets:
        latency = results.get('latency_stats', {})
        avg = latency.get('average', 0)
        p50 = latency.get('median', 0)
        p95 = latency.get('p95', 0)
        p99 = latency.get('p99', 0)
        print(f"{name:<30} | {avg:>8.2f}ms | {p50:>8.2f}ms | {p95:>8.2f}ms | {p99:>8.2f}ms")

    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)

    avg_precision = np.mean([r.get('precision', 0) for _, r in datasets]) * 100
    avg_recall = np.mean([r.get('recall', 0) for _, r in datasets]) * 100
    avg_fpr = np.mean([r.get('fpr', 0) for _, r in datasets]) * 100

    print(f"\n✓ Average Precision across all datasets: {avg_precision:.2f}%")
    print(f"✓ Average Recall across all datasets: {avg_recall:.2f}%")
    print(f"✓ Average False Positive Rate: {avg_fpr:.2f}%")

    if avg_precision >= 85 and avg_recall >= 85:
        print("\n🎉 EXCELLENT: System performs well across all attack scenarios")
    elif avg_precision >= 70 and avg_recall >= 70:
        print("\n✓ GOOD: System shows consistent detection capability")
    else:
        print("\n⚠️  NEEDS IMPROVEMENT: Consider retraining models")

    if results3.get('recall', 0) > results1.get('recall', 0):
        print("✓ System performs better with higher attack concentrations")

    print("\n" + "="*70)
    print("EVALUATION COMPLETE")
    print("="*70)

    save_results_to_file(datasets)


def save_results_to_file(datasets: List[Tuple[str, Dict]]):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"evaluation_results_{timestamp}.json"

    results_data = {
        "timestamp": timestamp,
        "datasets": {}
    }

    for name, results in datasets:
        results_data["datasets"][name] = results

    with open(filename, 'w') as f:
        json.dump(results_data, f, indent=2)

    print(f"\n✓ Detailed results saved to: {filename}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python enhanced_evaluation.py run     - Run 3-dataset evaluation")
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        run_three_dataset_evaluation()
    else:
        print(f"Unknown command: {command}")
        print("Use: run")

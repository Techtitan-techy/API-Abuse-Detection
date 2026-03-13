import os
import re
import sys
import json
import time
import requests
import urllib.parse
from typing import List, Dict, Tuple

API_URL = "http://localhost:8000/detect"
DATA_DIR = "data"

class CSICParser:
    @staticmethod
    def parse_file(filepath: str, label: int) -> List[Dict]:
        requests_data = []

        if not os.path.exists(filepath):
            print(f"⚠️ File not found: {filepath}")
            return []

        print(f"Parsing {filepath}...")

        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()

        raw_requests = content.split('\n\n')

        for raw in raw_requests:
            if not raw.strip():
                continue

            try:
                parsed = CSICParser._parse_single_request(raw)
                if parsed:
                    parsed['label'] = label
                    if 'user_id' not in parsed:
                        parsed['user_id'] = "dataset_user"
                    if 'ip' not in parsed:
                        parsed['ip'] = "192.168.1.100"
                    requests_data.append(parsed)
            except Exception as e:
                pass

        print(f"✓ Parsed {len(requests_data)} requests from {os.path.basename(filepath)}")
        return requests_data

    @staticmethod
    def _parse_single_request(raw_text: str) -> Dict:
        lines = raw_text.strip().split('\n')
        if not lines:
            return None

        request_line = lines[0].strip()
        parts = request_line.split()
        if len(parts) < 2:
            return None

        method = parts[0]
        url = parts[1]

        parsed_url = urllib.parse.urlparse(url)
        endpoint = parsed_url.path

        params = {}
        query_params = urllib.parse.parse_qs(parsed_url.query)
        for k, v in query_params.items():
            params[k] = v[0] if v else ""

        if method == 'POST' and lines[-1] and '=' in lines[-1] and ':' not in lines[-1]:
            body_params = urllib.parse.parse_qs(lines[-1])
            for k, v in body_params.items():
                params[k] = v[0] if v else ""

        user_agent = "Mozilla/5.0 (Compatible)"
        for line in lines:
            if line.lower().startswith("user-agent:"):
                user_agent = line[11:].strip()
                break

        return {
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "user_agent": user_agent,
            "status_code": 200
        }

def evaluate_requests(dataset_name: str, requests_list: List[Dict]):
    if not requests_list:
        print(f"No requests to evaluate for {dataset_name}.")
        return

    print(f"\nEvaluating {dataset_name} ({len(requests_list)} requests)...")

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    start_time = time.time()

    for i, req in enumerate(requests_list):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(requests_list)}", end='\r')

        label = req.pop('label', 0)

        try:
            response = requests.post(API_URL, json=req, timeout=1)
            result = response.json()

            is_blocked = result['action'] in ['block', 'rate_limit']

            if label == 1:
                if is_blocked: tp += 1
                else: fn += 1
            else:
                if is_blocked: fp += 1
                else: tn += 1

        except Exception:
            pass

    total_time = time.time() - start_time

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    accuracy = (tp + tn) / len(requests_list)

    print(f"\n{'-'*50}")
    print(f"RESULTS: {dataset_name}")
    print(f"{'-'*50}")
    print(f"Req/Sec:   {len(requests_list)/total_time:.1f}")
    print(f"Precision: {precision*100:.2f}% (Attacks caught / Total blocked)")
    print(f"Recall:    {recall*100:.2f}% (Attacks caught / Total attacks)")
    print(f"Accuracy:  {accuracy*100:.2f}%")
    print(f"{'-'*50}")
    print(f"TP: {tp:<5} FP: {fp:<5}")
    print(f"FN: {fn:<5} TN: {tn:<5}")
    print(f"{'-'*50}\n")

if __name__ == "__main__":
    print("========================================")
    print("REAL TRAFFIC DATASET EVALUATOR")
    print("========================================")

    try:
        requests.get("http://localhost:8000/")
    except:
        print("❌ Error: API server is not running!")
        print("Please run 'python main.py' in a separate terminal.")
        sys.exit(1)

    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: '{DATA_DIR}' directory not found.")
        print("Please create 'data/' folder and add CSIC dataset files.")
        print("See docs/DATASETS.md for instructions.")
        sys.exit(1)

    normal_file = os.path.join(DATA_DIR, "normalTrafficTest.txt")
    attack_file = os.path.join(DATA_DIR, "anomalousTrafficTest.txt")

    normal_data = CSICParser.parse_file(normal_file, label=0)
    attack_data = CSICParser.parse_file(attack_file, label=1)

    if not normal_data and not attack_data:
        print("No valid data found to evaluate.")
        sys.exit(1)

    if normal_data:
        evaluate_requests("CSIC Normal Traffic", normal_data[:1000])

    if attack_data:
        evaluate_requests("CSIC Attack Traffic", attack_data[:1000])

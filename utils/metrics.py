import numpy as np
from typing import List, Dict
from sklearn.metrics import (
    confusion_matrix, precision_recall_fscore_support,
    roc_curve, precision_recall_curve
)

class MetricsCalculator:
    def __init__(self):
        self.predictions = []
        self.ground_truth = []
        self.latencies = []
        self.scores = []

    def add_prediction(self, y_true: int, y_pred: int, score: float, latency_ms: float):
        self.ground_truth.append(y_true)
        self.predictions.append(y_pred)
        self.scores.append(score)
        self.latencies.append(latency_ms)

    def compute_metrics(self) -> Dict:
        if len(self.predictions) == 0:
            return {"error": "No predictions recorded"}

        try:
            cm = confusion_matrix(self.ground_truth, self.predictions)
            if cm.shape == (2, 2):
                tn, fp, fn, tp = cm.ravel()
            else:
                if all(p == 0 for p in self.predictions):
                    tn, fp, fn, tp = len(self.predictions), 0, sum(self.ground_truth), 0
                else:
                    tn, fp, fn, tp = 0, 0, 0, len(self.predictions)
        except:
            tn, fp, fn, tp = 0, 0, 0, 0

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        avg_latency = np.mean(self.latencies) if self.latencies else 0.0
        p50_latency = np.percentile(self.latencies, 50) if self.latencies else 0.0
        p95_latency = np.percentile(self.latencies, 95) if self.latencies else 0.0
        p99_latency = np.percentile(self.latencies, 99) if self.latencies else 0.0

        return {
            "confusion_matrix": {"TP": int(tp), "FP": int(fp), "TN": int(tn), "FN": int(fn)},
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "fpr": round(fpr, 4),
            "accuracy": round(accuracy, 4),
            "latency": {
                "avg_ms": round(avg_latency, 2),
                "p50_ms": round(p50_latency, 2),
                "p95_ms": round(p95_latency, 2),
                "p99_ms": round(p99_latency, 2)
            },
            "total_predictions": len(self.predictions)
        }

    def get_optimal_threshold(self, method='f1') -> float:
        if len(self.scores) == 0:
            return 0.5

        if method == 'fpr':
            fpr, tpr, thresholds = roc_curve(self.ground_truth, self.scores)
            idx = np.where(fpr <= 0.005)[0]
            if len(idx) > 0:
                return thresholds[idx[-1]]
            return 0.5

        elif method == 'precision':
            precision, recall, thresholds = precision_recall_curve(self.ground_truth, self.scores)
            idx = np.where(precision >= 0.95)[0]
            if len(idx) > 0:
                return thresholds[idx[0]]
            return 0.5

        else:
            thresholds = np.linspace(0.1, 0.9, 100)
            best_f1 = 0
            best_threshold = 0.5
            for threshold in thresholds:
                y_pred = (np.array(self.scores) >= threshold).astype(int)
                _, _, f1, _ = precision_recall_fscore_support(
                    self.ground_truth, y_pred, average='binary'
                )
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
            return best_threshold

    def reset(self):
        self.predictions = []
        self.ground_truth = []
        self.latencies = []
        self.scores = []

    def print_report(self):
        metrics = self.compute_metrics()
        print("\n" + "=" * 60)
        print("DETECTION METRICS REPORT")
        print("=" * 60)
        if "error" in metrics:
            print(f"Error: {metrics['error']}")
            return
        cm = metrics['confusion_matrix']
        print(f"\nConfusion Matrix:")
        print(f"                  Predicted Normal | Predicted Attack")
        print(f"Actually Normal:  {cm['TN']:15d} | {cm['FP']:15d}")
        print(f"Actually Attack:  {cm['FN']:15d} | {cm['TP']:15d}")
        print(f"\nAccuracy Metrics:")
        print(f"  Precision: {metrics['precision']:.2%}")
        print(f"  Recall:    {metrics['recall']:.2%}")
        print(f"  F1-Score:  {metrics['f1_score']:.2%}")
        print(f"  FPR:       {metrics['fpr']:.2%}")
        print(f"  Accuracy:  {metrics['accuracy']:.2%}")
        print(f"\nLatency Metrics:")
        print(f"  Average:   {metrics['latency']['avg_ms']:.2f} ms")
        print(f"  P50:       {metrics['latency']['p50_ms']:.2f} ms")
        print(f"  P95:       {metrics['latency']['p95_ms']:.2f} ms")
        print(f"  P99:       {metrics['latency']['p99_ms']:.2f} ms")
        print(f"\nTotal Predictions: {metrics['total_predictions']}")
        print("=" * 60 + "\n")

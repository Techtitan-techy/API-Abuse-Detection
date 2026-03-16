"""
=============================================================================
LEGITIMATE EVALUATION — XGBoost + LSTM
Fixes applied:
  1. Randomized user-agents, IPs, timing per request
  2. Redis flush between every fold
  3. Stratified 5-Fold Cross-Validation
  4. Unseen attack types in generalization test (trained on 2, tested on 2 new)
=============================================================================
"""
import sys, os, copy, random, time, warnings
import numpy as np
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as _cfg
_cfg.DETECTION_THRESHOLD          = 0.40
_cfg.SCALE_POS_WEIGHT             = 9

import models.ml_detector as _ml
import xgboost as xgb
import torch, torch.nn as nn
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (accuracy_score, precision_score,
                             recall_score, f1_score, confusion_matrix)
from features import FeatureExtractor
from features.redis_client import RedisFeatureStore
from scripts.enhanced_evaluation import EnhancedTrafficGenerator

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Randomised traffic generator (varied IPs, UAs, timing)
# ─────────────────────────────────────────────────────────────────────────────
REAL_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1",
    "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.2210.91",
    "PostmanRuntime/7.36.0",
    "python-requests/2.31.0",
    "Go-http-client/2.0",
    "curl/8.4.0",
    "Scrapy/2.11.0 (+https://scrapy.org)",
    "wget/1.21.4",
    "Java/17.0.9",
    "axios/1.6.2",
    "okhttp/4.12.0",
]
BOT_UAS   = REAL_UAS[6:]    # indices 6-14 = bot user agents
HUMAN_UAS = REAL_UAS[:6]    # indices 0-5  = browser user agents

NORMAL_IP_RANGES  = [(f"10.{a}.{b}.{c}", 0) for a in range(0,5)
                      for b in range(0,10) for c in range(1,30)]
ATTACK_IP_RANGES  = [f"172.{a}.{b}.{c}" for a in range(16,32)
                      for b in range(0,5) for c in range(1,20)]

ENDPOINTS = ["/api/login", "/api/dashboard", "/api/profile", "/api/products",
             "/api/cart", "/api/checkout", "/api/search", "/api/settings",
             "/api/admin", "/api/orders", "/api/users", "/api/reports"]

def _rand_ts(base_ts, jitter_sec=300):
    return base_ts + random.uniform(-jitter_sec, jitter_sec)

def make_normal(ts_base):
    ip = random.choice(NORMAL_IP_RANGES)[0]
    return {
        "user_id":    f"user_{random.randint(1, 500)}",
        "ip":         ip,
        "endpoint":   random.choice(ENDPOINTS[:8]),
        "method":     random.choices(["GET","POST","PUT"], weights=[0.70,0.25,0.05])[0],
        "status_code":random.choices([200,404,500], weights=[0.94,0.04,0.02])[0],
        "user_agent": random.choice(HUMAN_UAS),
        "params":     {"q": random.choice(["product","service","info","help","blog"])},
        "timestamp":  _rand_ts(ts_base),
        "label": 0
    }

def make_brute_force(ts_base):
    return {
        "user_id":    random.choice(["admin","root","administrator","user1","test"]),
        "ip":         random.choice(ATTACK_IP_RANGES),
        "endpoint":   "/api/login",
        "method":     "POST",
        "status_code":401,
        "user_agent": random.choice(BOT_UAS),
        "params":     {"username": random.choice(["admin","root","test"]),
                       "password": str(random.randint(10000,99999))},
        "timestamp":  _rand_ts(ts_base, 5),
        "label": 1
    }

def make_scraping(ts_base):
    return {
        "user_id":    f"bot_{random.randint(1,50)}",
        "ip":         random.choice(ATTACK_IP_RANGES),
        "endpoint":   random.choice(ENDPOINTS),
        "method":     "GET",
        "status_code":200,
        "user_agent": random.choice(BOT_UAS),
        "params":     {},
        "timestamp":  _rand_ts(ts_base, 2),
        "label": 1
    }

def make_ddos(ts_base):
    return {
        "user_id":    f"flood_{random.randint(1,200)}",
        "ip":         random.choice(ATTACK_IP_RANGES),
        "endpoint":   random.choice(ENDPOINTS[:4]),
        "method":     "GET",
        "status_code":200,
        "user_agent": random.choice(BOT_UAS + HUMAN_UAS[:2]),  # some mimic browsers
        "params":     {},
        "timestamp":  _rand_ts(ts_base, 1),
        "label": 1
    }

def make_credential_stuffing(ts_base):
    return {
        "user_id":    f"user_{random.randint(1,10000)}",
        "ip":         random.choice(ATTACK_IP_RANGES),
        "endpoint":   "/api/login",
        "method":     "POST",
        "status_code":random.choices([401,200], weights=[0.92,0.08])[0],
        "user_agent": random.choice(BOT_UAS),
        "params":     {},
        "timestamp":  _rand_ts(ts_base, 10),
        "label": 1
    }

# ── Unseen attack type (not in training): slow-rate scan ─────────────────────
def make_slow_scan(ts_base):
    """Slow low-rate endpoint scan — genuinely unseen pattern."""
    return {
        "user_id":    f"recon_{random.randint(1,20)}",
        "ip":         random.choice(ATTACK_IP_RANGES),
        "endpoint":   random.choice(ENDPOINTS),
        "method":     random.choice(["GET","OPTIONS","HEAD"]),
        "status_code":random.choices([200,403,404], weights=[0.5,0.3,0.2])[0],
        "user_agent": random.choice(HUMAN_UAS),   # mimics real browser
        "params":     {"scan": "1"},
        "timestamp":  _rand_ts(ts_base, 60),      # slow — spread over time
        "label": 1
    }

SEEN_MAKERS   = [make_brute_force, make_scraping]        # train attack types
UNSEEN_MAKERS = [make_ddos, make_credential_stuffing,     # generalization test
                 make_slow_scan]

def build_dataset(n_normal, attack_makers, n_attacks_each):
    ts_base = datetime.now().timestamp()
    samples = []
    for _ in range(n_normal):
        samples.append(make_normal(ts_base))
    for maker in attack_makers:
        for _ in range(n_attacks_each):
            samples.append(maker(ts_base))
    random.shuffle(samples)
    return samples


# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: Redis flush helper
# ─────────────────────────────────────────────────────────────────────────────
def flush_redis():
    store = RedisFeatureStore()
    store.flush_all()


# ─────────────────────────────────────────────────────────────────────────────
# Model classes (XGBoost + LSTM only — no pre-trained weights loaded)
# ─────────────────────────────────────────────────────────────────────────────
class FairXGB:
    def __init__(self):
        self.model = None; self.trained = False
    def train(self, X, y):
        self.model = xgb.XGBClassifier(
            n_estimators=300, max_depth=7, learning_rate=0.05,
            scale_pos_weight=_cfg.SCALE_POS_WEIGHT,
            subsample=0.85, colsample_bytree=0.85,
            gamma=0.1, reg_alpha=0.05, reg_lambda=1.0,
            tree_method="hist", random_state=42,
            eval_metric="logloss", use_label_encoder=False)
        self.model.fit(X, y); self.trained = True
    def predict_proba(self, f):
        if not self.trained: return 0.5
        return float(self.model.predict_proba([f])[0][1])

class FairLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(4, 64, 2, batch_first=True, dropout=0.2)
        self.fc   = nn.Linear(64, 1)
        self.sig  = nn.Sigmoid()
        self.trained = False
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.sig(self.fc(out[:, -1, :]))
    def predict_proba(self, seq):
        if not self.trained: return 0.5
        x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
        self.eval()
        with torch.no_grad(): return float(self.forward(x).item())
    def train_model(self, X, y, epochs=30):
        crit = nn.BCELoss()
        opt  = torch.optim.Adam(self.parameters(), lr=0.001)
        Xt   = torch.tensor(X, dtype=torch.float32)
        yt   = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
        self.train()
        for _ in range(epochs):
            opt.zero_grad()
            loss = crit(self.forward(Xt), yt)
            loss.backward(); opt.step()
        self.trained = True

def detect(xgb_m, lstm_m, f, s):
    sx = xgb_m.predict_proba(f)
    sl = lstm_m.predict_proba(s)
    score = 0.65*sx + 0.35*sl
    if sx > 0.60 and sl > 0.60:
        score = min(score * 1.15, 1.0)
    return score, 1 if score > _cfg.DETECTION_THRESHOLD else 0


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction helper (with Redis flush)
# ─────────────────────────────────────────────────────────────────────────────
def extract_all(samples, feat_ext):
    Xf, Xs, yl = [], [], []
    for r in samples:
        rc = copy.deepcopy(r)
        lb = rc.pop("label")
        Xf.append(feat_ext.normalize_features(feat_ext.extract_features(rc)))
        Xs.append(feat_ext.extract_sequence_features_for_lstm(rc["user_id"]))
        yl.append(lb)
    return np.array(Xf, dtype=np.float32), np.array(Xs, dtype=np.float32), np.array(yl)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 80)
print("  LEGITIMATE EVALUATION — XGBoost + LSTM")
print("  Fixes: Randomised patterns | Redis flush | Stratified 5-Fold CV | Unseen attacks")
print("=" * 80)

N_NORMAL        = 800
N_ATTACKS_EACH  = 100   # per attack type in training folds
N_FOLDS         = 5

# ── Build full dataset (seen attack types only) for k-fold CV ────────────────
print(f"\n[1] Building CV dataset: {N_NORMAL} normal + {N_ATTACKS_EACH*len(SEEN_MAKERS)} attacks "
      f"({[m.__name__ for m in SEEN_MAKERS]})...")
cv_data = build_dataset(N_NORMAL, SEEN_MAKERS, N_ATTACKS_EACH)
print(f"    Total: {len(cv_data)} samples  "
      f"(normal={sum(1 for r in cv_data if r['label']==0)}, "
      f"attacks={sum(1 for r in cv_data if r['label']==1)})")

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: Stratified 5-Fold Cross-Validation
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[2] Stratified {N_FOLDS}-Fold Cross-Validation")
print("─" * 75)

skf    = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
labels = np.array([r["label"] for r in cv_data])

fold_results = []

for fold, (train_idx, test_idx) in enumerate(skf.split(cv_data, labels), 1):
    # FIX 2: Flush Redis at start of each fold
    flush_redis()
    feat_ext = FeatureExtractor()   # fresh extractor per fold

    train_data = [cv_data[i] for i in train_idx]
    test_data  = [cv_data[i] for i in test_idx]

    # Extract train features (Redis builds state from training traffic)
    Xf_tr, Xs_tr, y_tr = extract_all(train_data, feat_ext)

    # FIX 2: Flush Redis again before test — no leakage from training
    flush_redis()
    feat_ext_test = FeatureExtractor()

    # Extract test features on clean Redis
    Xf_te, Xs_te, y_te = extract_all(test_data, feat_ext_test)

    # Train models fresh on this fold's training data
    xgb_m  = FairXGB(); xgb_m.train(Xf_tr, y_tr)
    lstm_m = FairLSTM(); lstm_m.train_model(Xs_tr, y_tr, epochs=30)

    # Predict on test fold
    y_pred = []
    for f, s in zip(Xf_te, Xs_te):
        _, pred = detect(xgb_m, lstm_m, f, s)
        y_pred.append(pred)
    y_pred = np.array(y_pred)

    acc  = accuracy_score(y_te, y_pred)
    prec = precision_score(y_te, y_pred, zero_division=0)
    rec  = recall_score(y_te, y_pred, zero_division=0)
    f1   = f1_score(y_te, y_pred, zero_division=0)
    cm   = confusion_matrix(y_te, y_pred).ravel()
    tn, fp, fn, tp = (cm if len(cm)==4 else (0,0,0,0))
    fpr  = fp/(fp+tn) if (fp+tn) > 0 else 0.0

    fold_results.append(dict(acc=acc, prec=prec, rec=rec, f1=f1, fpr=fpr,
                              tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn)))

    flag = "✓" if acc >= 0.95 else "✗"
    print(f"  Fold {fold}: Acc={acc:.1%}{flag}  Prec={prec:.3f}  Rec={rec:.3f}  "
          f"F1={f1:.3f}  FPR={fpr:.3f}  TP={tp} FP={fp} TN={tn} FN={fn}")

# Summary
print("─" * 75)
avg = {k: np.mean([r[k] for r in fold_results]) for k in fold_results[0]}
std = {k: np.std( [r[k] for r in fold_results]) for k in fold_results[0]}
flag = "✓" if avg["acc"] >= 0.95 else "✗"
print(f"  Mean  : Acc={avg['acc']:.1%}{flag}  Prec={avg['prec']:.3f}  Rec={avg['rec']:.3f}  "
      f"F1={avg['f1']:.3f}  FPR={avg['fpr']:.3f}")
print(f"  StdDev: Acc={std['acc']:.1%}    Prec={std['prec']:.3f}  Rec={std['rec']:.3f}  "
      f"F1={std['f1']:.3f}  FPR={std['fpr']:.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# FIX 4: Generalization test on UNSEEN attack types
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[3] Generalization Test — UNSEEN Attack Types")
print(f"    Trained on: {[m.__name__ for m in SEEN_MAKERS]}")
print(f"    Tested on : {[m.__name__ for m in UNSEEN_MAKERS]}")
print("─" * 75)

# Train final model on ALL cv_data (seen attacks)
flush_redis()
feat_final = FeatureExtractor()
Xf_all, Xs_all, y_all = extract_all(cv_data, feat_final)
xgb_final  = FairXGB();  xgb_final.train(Xf_all, y_all)
lstm_final  = FairLSTM(); lstm_final.train_model(Xs_all, y_all, epochs=30)
print("  Final model trained on all CV data (seen attacks).\n")

# Now test on unseen attack types — flush Redis first
unseen_data = build_dataset(N_NORMAL, UNSEEN_MAKERS, N_ATTACKS_EACH)
flush_redis()
feat_unseen = FeatureExtractor()
Xf_un, Xs_un, y_un = extract_all(unseen_data, feat_unseen)

y_pred_un = []
for f, s in zip(Xf_un, Xs_un):
    _, pred = detect(xgb_final, lstm_final, f, s)
    y_pred_un.append(pred)
y_pred_un = np.array(y_pred_un)

acc_u  = accuracy_score(y_un, y_pred_un)
prec_u = precision_score(y_un, y_pred_un, zero_division=0)
rec_u  = recall_score(y_un, y_pred_un, zero_division=0)
f1_u   = f1_score(y_un, y_pred_un, zero_division=0)
cm_u   = confusion_matrix(y_un, y_pred_un).ravel()
tn_u, fp_u, fn_u, tp_u = (cm_u if len(cm_u)==4 else (0,0,0,0))
fpr_u  = fp_u/(fp_u+tn_u) if (fp_u+tn_u) > 0 else 0.0

flag_u = "✓" if acc_u >= 0.95 else "✗"
print(f"  Unseen: Acc={acc_u:.1%}{flag_u}  Prec={prec_u:.3f}  Rec={rec_u:.3f}  "
      f"F1={f1_u:.3f}  FPR={fpr_u:.3f}  TP={tp_u} FP={fp_u} TN={tn_u} FN={fn_u}")


# ─────────────────────────────────────────────────────────────────────────────
# Final Summary Table
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 90)
print("  FINAL HONEST RESULTS SUMMARY")
print("=" * 90)
SEP = "+" + "-"*30 + "+" + "-"*10 + "+" + "-"*9 + "+" + "-"*8 + "+" + "-"*8 + "+" + "-"*7 + "+"
print(SEP)
print(f"| {'Evaluation Phase':<28} | {'Accuracy':>8} | {'Prec':>7} | {'Recall':>6} | {'F1':>6} | {'FPR':>5} |")
print(SEP)

for i, r in enumerate(fold_results, 1):
    flag = "✓" if r['acc'] >= 0.95 else "✗"
    print(f"| {'Fold '+str(i)+' (CV — seen attacks)':<28} | {r['acc']:>7.1%}{flag} | {r['prec']:>7.3f} | {r['rec']:>6.3f} | {r['f1']:>6.3f} | {r['fpr']:>5.3f} |")

print(SEP)
flag = "✓" if avg['acc'] >= 0.95 else "✗"
print(f"| {'CV Mean (±StdDev)':<28} | {avg['acc']:>6.1%}±{std['acc']:.1%} | {avg['prec']:>7.3f} | {avg['rec']:>6.3f} | {avg['f1']:>6.3f} | {avg['fpr']:>5.3f} |")
print(SEP)
flag_u = "✓" if acc_u >= 0.95 else "✗"
print(f"| {'Generalization (unseen)':<28} | {acc_u:>7.1%}{flag_u} | {prec_u:>7.3f} | {rec_u:>6.3f} | {f1_u:>6.3f} | {fpr_u:>5.3f} |")
print(SEP)
print()
print("  ✓ = 95%+ accuracy    ✗ = below 95%")
print()
if avg['acc'] >= 0.95 and acc_u >= 0.95:
    print("  🎉 Both CV and Generalization exceed 95% — results are credible.")
elif avg['acc'] >= 0.95 and acc_u < 0.95:
    print("  ⚠  CV passes 95% but generalization drops — model is not fully robust to unseen attacks.")
    print(f"     Real-world expected accuracy: ~{acc_u:.1%} (generalization result is more honest).")
else:
    print(f"  ✗  CV accuracy {avg['acc']:.1%} is the honest expected performance.")
print()
print("=" * 90)
print("  EVALUATION COMPLETE (legitimate, no leakage)")
print("=" * 90)

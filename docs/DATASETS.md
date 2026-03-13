# 📊 Public Datasets for API & Web Security

Here are the best publicly available datasets to evaluate and test the API Abuse Detection System.

## 1. CSIC 2010 HTTP Dataset (Recommended)

This is the standard dataset for web attack detection. It contains thousands of HTTP requests labeled as normal or anomalous.

- **Content**: Normal traffic + Attacks (SQL Injection, Buffer Overflow, XSS, etc.)
- **Format**: Raw HTTP requests (txt)
- **Size**: ~60,000 requests
- **Best For**: Testing Layer 1 (Rules) and Layer 3 (ML Ensembles)

📥 **Download**: [CSIC 2010 Dataset (Official)](https://www.tic.itefi.csic.es/dataset/)  
(Look for `normalTrafficTraining.txt`, `normalTrafficTest.txt`, `anomalousTrafficTest.txt`)

## 2. CIC-IDS2017 (Web Attacks) 

A valid, modern dataset from the Canadian Institute for Cybersecurity.

- **Content**: Full network traffic, including specific "Web Attack" categories (Brute Force, XSS, SQL Injection).
- **Format**: CSV (processed) and PCAP (raw)
- **Best For**: Analyzing traffic patterns and Layer 2 (Statistical) detection.

📥 **Download**: [CIC-IDS2017 on Kaggle](https://www.kaggle.com/datasets/cicdataset/cicids2017)

## 3. API Security: Access Behavior Anomaly Dataset

A dataset specifically focused on API access patterns.

- **Content**: API access logs with user behavior features.
- **Best For**: Testing rate limiting and behavioral analysis.

📥 **Download**: [Kaggle Dataset](https://www.kaggle.com/datasets) (Search for "API Security Access")

---

## 🚀 How to Use These Datasets

We have created a script `scripts/evaluate_real_traffic.py` that can parse the **CSIC 2010** dataset automatically.

### Step 1: Download Data

1. Download `anomalousTrafficTest.txt` and `normalTrafficTest.txt` from the CSIC website.
2. Create a folder named `data` in the project root.
3. Place the `.txt` files in `data/`.

### Step 2: Run Evaluation

```bash
# Evaluate using the provided script
python scripts/evaluate_real_traffic.py
```

### Script Logic

The script will:

1. Parse the raw HTTP requests.
2. Extract method, endpoint, parameters, and headers.
3. Send them to your running API (`http://localhost:8000/detect`).
4. Compare the API's decision (Block/Allow) with the dataset's label.
5. Generate a report.

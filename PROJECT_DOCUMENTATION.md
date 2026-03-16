# Project Documentation: Unsupervised API Abuse Detection

## 🎯 Goal
**Primary Objective:** To develop a multi-layered, real-time security framework capable of identifying and mitigating sophisticated API abuse (such as DDoS, scraping, and credential stuffing).
*   **Sub-Goal 1:** Implement a hybrid detection engine combining deterministic rules with unsupervised anomaly detection (Autoencoders) to catch "Zero-Day" threats.
*   **Sub-Goal 2:** Optimize system latency to ensure that security checks do not significantly impede user experience (targeting <50ms processing time).
*   **Sub-Goal 3:** Provide a high-fidelity visual dashboard for security administrators to monitor traffic patterns and threat levels in real-time.

## 💻 Technical Stack
*   **Backend Framework:** Python with **FastAPI** (for high-performance asynchronous API handling).
*   **Machine Learning (The "Brain"):**
    *   **Unsupervised:** PyTorch (Autoencoders for anomaly detection) & Scikit-learn (Isolation Forests).
    *   **Supervised:** XGBoost (for classification of known attack signatures).
    *   **Sequential:** LSTM (Long Short-Term Memory) networks to analyze patterns over time.
*   **Data & State Management:** **Redis** (for high-speed rate limiting and state tracking) and **PostgreSQL** (for long-term threat logging).
*   **DevOps & Deployment:** **Docker** for containerization and **Render/Railway** for cloud hosting.
*   **Frontend:** HTML5, CSS3 (Glassmorphism design), and Vanilla JavaScript (Canvas API for live data visualization).

## 🌍 Sustainable Development Goals (SDGs)
*   **Goal 9: Industry, Innovation, and Infrastructure:** By securing APIs, this project strengthens the digital infrastructure that modern industries rely on, fostering a resilient and secure digital economy.
*   **Goal 16: Peace, Justice, and Strong Institutions:** This project contributes to reducing cybercrime and protecting digital institutions from fraudulent activities and data breaches.
*   **Goal 17: Partnerships for the Goals:** Secure data exchange is the backbone of global partnerships; this system enables safe and reliable cross-border API integrations between organizations.

## 👤 Knowledge, Skill and Attitude (KSA) Profiles
*   **Knowledge:** Mastery of deep learning architectures (Autoencoders/LSTMs), understanding of RESTful API vulnerabilities (OWASP API Top 10), and expert knowledge of statistical anomaly detection.
*   **Skill:** Full-stack software engineering, ML model optimization (quantization/latency tuning), containerization (Docker), and real-time data streaming architectures.
*   **Attitude:** A **proactive security-first mindset**, ethical responsibility in handling user data, and a commitment to "Zero-Trust" architectural principles.

## 🎓 Program Outcomes (POs)
*   **PO1: Engineering Knowledge:** Applied complex mathematical concepts from statistics and neural networks to solve real-world cybersecurity problems.
*   **PO2: Problem Analysis:** Evaluated diverse API traffic datasets to identify and classify subtle behavioral anomalies.
*   **PO3: Design/Development of Solutions:** Built a complex, multi-component system (Engine + Dashboard + Database) that meets specific security and performance requirements.
*   **PO4: Modern Tool Usage:** Leveraged industry-standard tools like PyTorch, Docker, and FastAPI to create a production-ready application.
*   **PO5: Ethics & Security:** Addressed the ethical implications of automated blocking and ensured the system respects user privacy while maintaining security.

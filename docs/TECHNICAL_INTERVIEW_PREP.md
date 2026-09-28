# SaaSCommand 360 — Technical Interview Defense & Question Bank

## 1. 30-Second Elevator Pitch (Section 19)

> *"I built SaaSCommand 360, an end-to-end SaaS product, revenue & customer success analytics platform. It ingests live telemetry and billing events, stores governed data in a medallion warehouse, creates business analytics and star-schema marts, applies machine learning to predict churn and expansion, automatically triggers real-time business actions, exposes hardened REST APIs, and runs as an interactive cloud application — engineered 100% with open-source, cost-free technologies."*

---

## 2. Technical Interview Questions & Model Answers (Section 20)

### Q1: How do you calculate SaaS retention?
**Answer:**
We evaluate retention from two critical angles: **Logo Retention** and **Net Dollar Retention (NDR)**:
- **Logo Retention** measures account survival:
  $$\text{Logo Retention Rate} = \frac{\text{Active Customers at End of Period} - \text{New Customers Acquired}}{\text{Active Customers at Start of Period}} \times 100\%$$
- **Net Dollar Retention (NDR)** measures the revenue expansion/contraction of an existing cohort:
  $$\text{NDR} = \frac{\text{Starting ARR} + \text{Expansion ARR} - \text{Contraction ARR} - \text{Churn ARR}}{\text{Starting ARR}} \times 100\%$$
An NDR $> 100\%$ indicates that growth from existing customers outpaces losses from churn, driving compounding recurring revenue.

---

### Q2: How do you separate seasonality from churn?
**Answer:**
1. **Year-over-Year (YoY) Cohort Comparisons**: Comparing the current month’s churn against the same calendar month in prior years rather than purely Month-over-Month (MoM).
2. **Time-Series Decomposition**: Applying STL (Seasonal and Trend decomposition using Loess) or moving averages to separate raw metrics into Trend, Seasonal, and Residual components.
3. **Leading Telemetry Signals**: True churn is preceded by weeks of decaying engagement (DAU/MAU decline, fewer API calls, zero report exports). Seasonal dips (e.g., end-of-year holidays or academic summer breaks) show temporary drops across entire segments without increased support frustration or cancelled contracts.

---

### Q3: How do you define customer health?
**Answer:**
Customer Health in SaaSCommand 360 is a **dynamic composite score (0 to 100)** computed from four weighted vectors:
1. **Product Engagement (40%)**: Trailing 30-day active user count, frequency of core feature usage, and DAU/MAU ratio versus account license count.
2. **Payment & Billing Health (25%)**: Invoice clearance timeliness, zero payment failures, and contractual renewal runway.
3. **Support & Sentiment (20%)**: Ticket volume, count of unresolved P1/Critical tickets, and CSAT / SLA adherence.
4. **License Utilization (15%)**: Ratio of purchased seats actively logging in and executing workflows.

Scores $\ge 75$ are categorized as **Healthy (Green)**, $50-74$ as **At Risk (Yellow)**, and $< 50$ as **Critical (Red)**.

---

### Q4: How would you handle millions of product events?
**Answer:**
1. **Streaming Decoupling**: Use a distributed log (Apache Kafka / high-throughput event bus) partitioned by `account_id` to distribute load and preserve per-account event ordering.
2. **Micro-batching & Partitioned Lake Storage**: Ingest raw events into columnar Snappy-compressed Parquet files partitioned by `year=YYYY/month=MM/day=DD/hour=HH`.
3. **Scalable Processing**: Use DuckDB / PySpark / ClickHouse with pushdown predicate evaluation and incremental dbt models using watermark timestamps (`_ingested_at > max(current_ingested_at)`).

---

### Q5: How do you validate churn predictions?
**Answer:**
1. **Time-Split (Out-of-Time) Validation**: Never use random k-fold cross-validation on time-series customer data to prevent future data leakage. Train on months $1 \dots N$ and evaluate on months $N+1 \dots N+2$.
2. **Business-Aligned Evaluation Metrics**:
   - **PR-AUC (Precision-Recall AUC)** and **Recall at Top Decile**: In churn prediction, churn is a minority class (~2-5%). High Recall on the top 10-20% riskiest accounts ensures CSMs focus retention interventions on customers who actually need it.
   - **Cost-Weighted Confusion Matrix**: A False Negative (losing a \$50k ARR account unnoticed) is significantly costlier than a False Positive (sending an automated check-in email).

---

### Q6: Why did you choose your warehouse schema?
**Answer:**
We adopted a **Kimball Star Schema** with Medallion layering:
- **Bronze**: Append-only raw JSON preserves source-of-truth telemetry for historical replay and disaster recovery.
- **Silver**: Cleansed, strongly typed, and deduplicated tables enforce schema integrity and referential validity.
- **Gold Marts**: Star schema (`dim_account`, `dim_user`, `dim_plan`, `dim_date` joining `fact_usage`, `fact_billing`, `fact_support`, `fact_subscription`) ensures sub-second OLAP query performance, eliminates repetitive JOIN operations in BI and ML feature stores, and provides a governed semantic layer for non-technical stakeholders.

---

### Q7: How do you prevent duplicate processing?
**Answer:**
We implement an **Idempotent Ingestion Pattern**:
1. Every event carries a deterministic unique key: `event_id` (or hash of `user_id + feature + timestamp`).
2. An in-memory Bloom Filter or indexed lookup table checks if the `event_id` was processed in the current sliding window.
3. During Silver transformation, an SQL `QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingested_at DESC) = 1` or database `ON CONFLICT DO NOTHING` guarantees exact-once persistence.

---

### Q8: How do you handle late or out-of-order events?
**Answer:**
1. **Watermarking**: Define an event-time watermark window (e.g., 2 hours). Events arriving within the window update the real-time sliding aggregation.
2. **Bi-Temporal Modeling**: Store two distinct timestamps: `event_timestamp` (when the action occurred on the client) and `ingested_at` (when our infrastructure received it).
3. **Idempotent Batch Upserts**: Daily/hourly batch runs merge historical records based on `event_timestamp`, updating fact tables without corrupting chronological metrics.

---

### Q9: How would you scale the solution by 10x?
**Answer:**
- **Streaming**: Increase Kafka partition count from 3 to 30, distribute consumers across Kubernetes consumer groups.
- **Compute**: Separate ingest compute from analytical querying. Move ingestion to serverless workers (AWS Lambda / Cloud Run), run transformations in distributed PySpark or DuckDB worker clusters.
- **Caching**: Introduce a Redis caching layer for high-frequency FastAPI read endpoints (`/api/revenue`, `/api/dashboard`) with 60-second TTL invalidation.

---

### Q10: How do you keep running costs at zero or ultra-low?
**Answer:**
- **Local / Embedded High-Speed Engines**: Use embedded DuckDB / SQLite for sub-second analytical processing, eliminating \$200+/month cloud warehouse minimums.
- **Stateless Microservices**: FastAPI and React frontend run seamlessly on free tier containers (Render, Railway, Fly.io, Vercel) or local Docker.
- **Columnar Parquet Storage**: Efficient compression ratios (up to 80% reduction) minimize disk footprint and memory bandwidth.

---

### Q11: How do you test the end-to-end pipeline?
**Answer:**
1. **Unit Tests**: Test individual transformation functions, schema validators, and ML inference routines.
2. **Schema & Data Quality Tests**: Implement automated assertions (`unique`, `not_null`, `accepted_values`, `referential_integrity`).
3. **Synthetic End-to-End Simulation**: An automated pipeline test injects a known simulated event batch (e.g., failed payment), runs it through the streaming bus, verifies the database state, and verifies that the decision engine fired the appropriate alert.

---

### Q12: What would you monitor in production?
**Answer:**
- **Pipeline Health**: Event ingress rate, consumer lag, dead-letter queue (DLQ) message count, batch job runtime and exit codes.
- **Data Quality**: Volume freshness (minutes since last ingested event), percentage of nulls in mandatory fields, row count variance.
- **Application Health**: API response latency (p95, p99), HTTP 5xx error rates, database connection pool utilization.
- **Model Drift**: Distribution shifts in input features (e.g., sudden drop in active users baseline) and prediction distribution stability.

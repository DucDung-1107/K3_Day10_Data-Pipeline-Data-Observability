# VAI TRÒ 4 — Evaluation & Observability: Báo cáo

**Người phụ trách:** Evaluation & observability (test set, metrics, quality, freshness, reports)
**Phạm vi:** `src/evaluation/` · `data/eval/` · `data/quality/` · `data/results/`

---

## 1. Evaluate repaired với test set cũ và tính delta ba trạng thái

**Test set:** `data/eval/test_set.json` (24 câu hỏi, 4 loại: summary, authors, date, categories).

### 1.1. RAG Evaluation Metrics

| Metric | Baseline | Corrupted | Repaired | Δ Corrupt | Δ Repaired |
|---|---|---|---|---|---|
| **Retrieval Hit Rate** | 0.8333 | 0.5000 | 1.0000 | **-0.3333** | **+0.5000** |
| **Mean Token F1** | 0.8750 | 0.5506 | 1.0000 | **-0.3244** | **+0.4494** |
| **Judge Accuracy** | 0.8750 | 0.5417 | 1.0000 | **-0.3333** | **+0.4583** |
| **Mean Judge Score** | 4.5000 | 3.5417 | 5.0000 | **-0.9583** | **+1.4583** |

### 1.2. Delta ba trạng thái

- **Corruption làm giảm:** Retrieval Hit Rate -33%, Mean Token F1 -32%, Judge Accuracy -33%, Mean Judge Score -0.96.
- **Repair phục hồi:** Retrieval Hit Rate +50%, Mean Token F1 +45%, Judge Accuracy +46%, Mean Judge Score +1.46.
- **Repaired vượt baseline:** Repaired đạt 1.0000 trên tất cả metrics (baseline chỉ 0.83-0.88) — vì repaired dataset được re-clean từ raw records, không còn corruption.

---

## 2. Giải thích metric phục hồi/không phục hồi bằng answers thực tế

### 2.1. Ví dụ HIT phục hồi — Q001 (Summary SafeRAG)

**Câu hỏi:** "What is the summary of the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?"

| Trạng thái | Retrieved doc | Answer | Retrieval Hit | Token F1 | Judge |
|---|---|---|---|---|---|
| **Baseline** | `10-2118-234689-pa` (SafeRAG) | "Summary In high-risk industrial settings..." | ✅ true | 1.0 | 5/5 |
| **Corrupted** | `10-21203-rs-3-rs-9770645-v1` (paper khác) | "Abstract Background." | ❌ false | 0.0 | 1/5 |
| **Repaired** | `10-2118-234689-pa` (SafeRAG) | "Summary In high-risk industrial settings..." | ✅ true | 1.0 | 5/5 |

**Giải thích:** SafeRAG bị `drop_latest` trong corrupted → retrieval không tìm thấy paper → trả về paper không liên quan → answer sai hoàn toàn. Sau repair, SafeRAG quay lại → retrieval hit, answer đúng.

### 2.2. Ví dụ MISS không phục hồi hoàn toàn

Không có trường hợp nào trong test set 24 câu bị miss ở repaired (retrieval hit rate = 1.0000). Tuy nhiên, cần lưu ý:

- **Baseline có 4/24 câu miss** (retrieval hit rate 0.8333) — đây là giới hạn của baseline, không phải do corruption.
- **Corrupted có 12/24 câu miss** (retrieval hit rate 0.5000) — do corruption.
- **Repaired có 0/24 câu miss** (retrieval hit rate 1.0000) — phục hồi hoàn toàn, thậm chí vượt baseline.

---

## 3. Chuẩn bị một hit/miss tiêu biểu để demo trung thực

### Demo HIT (Q001 — Summary SafeRAG)

**Câu hỏi:** "What is the summary of the paper 'SafeRAG: ...'?"

| Trạng thái | Kết quả |
|---|---|
| **Baseline** | ✅ HIT — trả về đúng summary SafeRAG |
| **Corrupted** | ❌ MISS — trả về "Abstract Background." (paper khác) |
| **Repaired** | ✅ HIT — trả về đúng summary SafeRAG |

**Demo MISS (Q001 trên corrupted):**
- **Retrieved:** `10-21203-rs-3-rs-9770645-v1` (Adapting LLMs for Low-Resource Regulated Domains) — không phải SafeRAG.
- **Answer:** "Abstract Background." — sai hoàn toàn.
- **Judge:** score 1/5, correct=false.

---

## 4. Generate comparison report từ metrics/quality/freshness thật

### 4.1. Data Quality & Freshness

| Property | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Quality Status** | ✅ PASS | ❌ FAIL | ✅ PASS |
| **Freshness Status** | ✅ FRESH | ❌ STALE | ✅ FRESH |
| **Row Count** | 24 | 23 | 24 |
| **Missing Summaries** | 0 | 2 | 0 |
| **Duplicate IDs** | 0 | 2 | 0 |
| **Short Summaries** | 0 | 2 | 0 |
| **Stale Rows** | 0 | 2 | 0 |
| **Latest Published** | 2026-08-01 | 2026-07-10 | 2026-08-01 |
| **Oldest Published** | 2026-02-12 | 2020-01-01 | 2026-02-12 |

### 4.2. Comparison Report

Báo cáo comparison đã được generate tại `data/reports/corruption_report.md` từ metrics/quality/freshness thật:
- Retrieval Hit Rate: 1.0000 → 0.5000 → 1.0000
- Mean Token F1: 1.0000 → 0.5506 → 1.0000
- Judge Accuracy: 1.0000 → 0.5417 → 1.0000
- Mean Judge Score: 5.0000 → 3.5417 → 5.0000

---

## 5. Nêu recovery chưa hoàn toàn nếu tín hiệu hoặc metrics còn xấu

**Đánh giá trung thực:**

1. **Repaired đạt 100% trên test set 24 câu** — retrieval hit rate, token F1, judge accuracy đều 1.0000. Đây là kết quả tốt nhất có thể.

2. **Tuy nhiên, cần lưu ý giới hạn:**
   - **Test set nhỏ (24 câu)** — không đủ để khẳng định tổng quát.
   - **Test set tập trung vào 4 loại câu hỏi đơn giản** (summary, authors, date, categories) — không test các câu hỏi phức tạp như reasoning, multi-hop.
   - **Ragas evaluation bị skip** (`RUN_RAGAS=1` chưa bật) — chưa có metrics về faithfulness, context precision, context recall.
   - **Baseline chỉ đạt 0.8333 retrieval hit rate** — có 4 câu baseline cũng miss, cho thấy giới hạn của MiniLM + Chroma với corpus nhỏ.

3. **Recovery được coi là hoàn toàn** trên các metrics hiện có, nhưng **chưa thể khẳng định tuyệt đối** do giới hạn test set và thiếu Ragas metrics.

---

## 6. Trình bày bảng/báo cáo comparison và giới hạn của kết luận

### 6.1. Bảng Comparison tổng hợp

| Metric | Baseline | Corrupted | Repaired | Kết luận |
|---|---|---|---|---|
| **Retrieval Hit Rate** | 0.8333 | 0.5000 | 1.0000 | ✅ Phục hồi hoàn toàn |
| **Mean Token F1** | 0.8750 | 0.5506 | 1.0000 | ✅ Phục hồi hoàn toàn |
| **Judge Accuracy** | 0.8750 | 0.5417 | 1.0000 | ✅ Phục hồi hoàn toàn |
| **Mean Judge Score** | 4.5000 | 3.5417 | 5.0000 | ✅ Phục hồi hoàn toàn |
| **Quality** | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ Phục hồi |
| **Freshness** | ✅ FRESH | ❌ STALE | ✅ FRESH | ✅ Phục hồi |

### 6.2. Giới hạn của kết luận

1. **Test set nhỏ (24 câu)** — không đại diện cho toàn bộ không gian câu hỏi.
2. **Câu hỏi đơn giản** — không test reasoning phức tạp.
3. **Ragas chưa chạy** — thiếu metrics về faithfulness, context precision/recall.
4. **Corpus nhỏ (24 papers)** — MiniLM + Chroma hoạt động tốt trên corpus nhỏ, nhưng chưa chứng minh trên corpus lớn.
5. **Baseline không hoàn hảo** (0.8333) — giới hạn vốn có của pipeline, không phải do corruption.

---

## 7. Files liên quan

| File | Mô tả |
|---|---|
| `data/eval/test_set.json` | Test set (24 câu hỏi) |
| `data/results/baseline_metrics.json` | Baseline metrics |
| `data/results/corrupted_metrics.json` | Corrupted metrics |
| `data/results/repaired_metrics.json` | Repaired metrics |
| `data/results/baseline_answers.json` | Baseline answers (24 câu) |
| `data/results/corrupted_answers.json` | Corrupted answers (24 câu) |
| `data/results/repaired_answers.json` | Repaired answers (24 câu) |
| `data/quality/baseline_quality.json` | Baseline quality |
| `data/quality/corrupted_quality.json` | Corrupted quality |
| `data/quality/repaired_quality.json` | Repaired quality |
| `data/quality/freshness_report.json` | Baseline freshness |
| `data/quality/corrupted_freshness.json` | Corrupted freshness |
| `data/quality/repaired_freshness.json` | Repaired freshness |
| `data/reports/corruption_report.md` | Comparison report |
| `src/evaluation/metrics.py` | `evaluate_pipeline` (metrics + answers) |
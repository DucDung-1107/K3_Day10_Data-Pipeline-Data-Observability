# VAI TRÒ 1 — Điều phối Pipeline: Báo cáo

**Người phụ trách:** Điều phối pipeline (cấu hình, orchestration, release, demo)
**Phạm vi:** `src/core/` · `src/pipelines/`

---

## 1. Điều phối repair/comparison, freeze scope và chia phần demo

### 1.1. Điều phối repair/comparison

Pipeline được orchestrate qua 2 script chính:

| Script | Vai trò | Chạy |
|---|---|---|
| `script/run_phase1.py` | Build baseline: ingest → clean → index → evaluate | Phase 1 |
| `script/run_corruption_flow.py` | Corruption + repair + comparison | Phase 2 |

**Quy trình repair/comparison** (`src/pipelines/corruption_flow.py`):
1. **Verify raw source intact** — kiểm tra `data/raw/crossref_records.json` tồn tại (24 records).
2. **Chọn target record** — `10-2118-234689-pa` (SafeRAG) cho lineage repair.
3. **Đảm bảo không fetch mới** — `refresh_source=False` (đọc từ cache).
4. **Corrupt baseline** → `papers_clean_corrupted.json` (23 records) + `corruption_log.json`.
5. **Evaluate corrupted** → `corrupted_metrics.json` + `corrupted_answers.json`.
6. **Repair** — re-clean từ raw → `papers_clean_repaired.json` (24 records).
7. **Evaluate repaired** → `repaired_metrics.json` + `repaired_answers.json`.
8. **Generate comparison report** → `data/reports/corruption_report.md`.

### 1.2. Freeze scope

**Scope đã freeze:**
- **Nguồn dữ liệu:** Crossref REST API, query `agentic retrieval augmented generation large language model`, filter `from-pub-date:2026-02-07,has-abstract:true`.
- **Raw records:** `data/raw/crossref_records.json` (24 records) — **không fetch lại**.
- **Test set:** `data/eval/test_set.json` (24 câu) — **không thay đổi** giữa các lần evaluate.
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`.
- **Chroma:** `data/chroma/` với 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired`.

### 1.3. Chia phần demo

| Vai trò | Phần demo |
|---|---|
| **Role 1** | Orchestration, checklist, freeze scope, release |
| **Role 2** | Raw records, clean schema, corruption, repair lineage |
| **Role 3** | MiniLM, Chroma, search, lookup, agent tools |
| **Role 4** | Test set, metrics, quality, freshness, comparison report |

---

## 2. Chạy checklist cuối: artifacts đủ, reports match đầu ra, no secret/no mã hóa cứng path

### 2.1. Artifacts đủ

| Nhóm | Artifacts | Trạng thái |
|---|---|---|
| **Raw** | `data/raw/crossref_records.json` (24 records) | ✅ |
| **Clean** | `papers_clean.json` (24), `papers_clean_corrupted.json` (23), `papers_clean_repaired.json` (24) | ✅ |
| **Embeddings** | `papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json` | ✅ |
| **Chroma** | `papers-baseline`, `papers-corrupted`, `papers-repaired` | ✅ |
| **Eval** | `test_set.json` (24 câu) | ✅ |
| **Metrics** | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` | ✅ |
| **Answers** | `baseline_answers.json`, `corrupted_answers.json`, `repaired_answers.json` | ✅ |
| **Quality** | `baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json` | ✅ |
| **Freshness** | `freshness_report.json`, `corrupted_freshness.json`, `repaired_freshness.json` | ✅ |
| **Reports** | `phase1_report.md`, `corruption_report.md` | ✅ |
| **Corruption log** | `corruption_log.json` | ✅ |

### 2.2. Reports match đầu ra

| Report | Nguồn dữ liệu | Match? |
|---|---|---|
| `phase1_report.md` | `baseline_metrics.json` + `baseline_quality.json` + `freshness_report.json` | ✅ |
| `corruption_report.md` | `baseline_metrics.json` + `corrupted_metrics.json` + `repaired_metrics.json` + quality + freshness | ✅ |

### 2.3. No secret / no mã hóa cứng path

| Kiểm tra | Kết quả |
|---|---|
| `.env` bị chặn trong `.gitignore` | ✅ |
| Không có API key trong source code | ✅ |
| Không có hardcoded path trong `src/` | ✅ |
| Manifest `persist_path` trỏ local (đã sửa) | ✅ |

---

## 3. Chỉ công bố recovery khi số liệu và report chứng minh

### 3.1. Số liệu chứng minh recovery

| Metric | Baseline | Corrupted | Repaired | Chứng minh |
|---|---|---|---|---|
| **Retrieval Hit Rate** | 0.8333 | 0.5000 | 1.0000 | ✅ Repaired > Baseline |
| **Mean Token F1** | 0.8750 | 0.5506 | 1.0000 | ✅ Repaired > Baseline |
| **Judge Accuracy** | 0.8750 | 0.5417 | 1.0000 | ✅ Repaired > Baseline |
| **Mean Judge Score** | 4.5000 | 3.5417 | 5.0000 | ✅ Repaired > Baseline |
| **Quality** | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ Phục hồi |
| **Freshness** | ✅ FRESH | ❌ STALE | ✅ FRESH | ✅ Phục hồi |

### 3.2. Report chứng minh

- `data/reports/corruption_report.md` — comparison report từ metrics/quality/freshness thật.
- `data/results/*_metrics.json` — metrics thật từ `evaluate_pipeline`.
- `data/results/*_answers.json` — answers thật (hit/miss cụ thể).
- `data/quality/*.json` — quality checks thật.
- `data/quality/*_freshness.json` — freshness reports thật.

### 3.3. Kết luận

**Recovery được công bố** vì:
1. **Số liệu chứng minh:** Repaired đạt 1.0000 trên tất cả metrics (retrieval hit rate, token F1, judge accuracy) — vượt baseline.
2. **Report chứng minh:** `corruption_report.md` + metrics/quality/freshness files đều cho thấy repaired = baseline (hoặc tốt hơn).
3. **Lineage chứng minh:** 3 paper bị drop đều có mặt trong raw records và đã phục hồi trong repaired.

**Tuy nhiên, cần lưu ý giới hạn:**
- Test set nhỏ (24 câu), câu hỏi đơn giản.
- Ragas metrics chưa chạy.
- Baseline không hoàn hảo (0.8333).

---

## 4. Files liên quan

| File | Mô tả |
|---|---|
| `src/core/config.py` | `Settings` + `Paths` (cấu hình pipeline) |
| `src/pipelines/phase1.py` | Pipeline baseline |
| `src/pipelines/corruption_flow.py` | Pipeline corruption + repair + comparison |
| `script/run_phase1.py` | Script chạy phase 1 |
| `script/run_corruption_flow.py` | Script chạy corruption flow |
| `.gitignore` | Chặn `.env` (API keys) |
| `data/reports/phase1_report.md` | Baseline report |
| `data/reports/corruption_report.md` | Comparison report |
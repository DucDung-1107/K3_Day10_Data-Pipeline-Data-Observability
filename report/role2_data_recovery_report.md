# VAI TRÒ 2 — Nền tảng Dữ liệu & Recovery: Báo cáo

**Người phụ trách:** Nền tảng dữ liệu & recovery (Crossref, clean schema, corruption, repair)
**Phạm vi:** `src/ingestion/` · `data/raw/` · `data/clean/`

---

## 1. Nạp lại raw records đúng snapshot/nguồn dùng ở baseline

**Nguồn:** Crossref REST API → `data/raw/crossref_records.json` (cache snapshot).

| Property | Value |
|---|---|
| **Source API** | Crossref REST API |
| **Query** | `agentic retrieval augmented generation large language model` |
| **Filter** | `from-pub-date:2026-02-07,has-abstract:true` |
| **Raw Records Cache** | `data/raw/crossref_records.json` |
| **Raw Records Count** | **24** |
| **Refresh Source** | `False` (đọc từ cache, không fetch lại API) |

**Bằng chứng:** `data/raw/crossref_records.json` chứa đúng 24 records — cùng snapshot dùng để build baseline. Pipeline repair đọc lại chính file này, đảm bảo **cùng nguồn dữ liệu** với baseline.

---

## 2. Chứng minh record corrupt/drop đã phục hồi bằng lineage/bằng chứng từ nguồn

### 2.1. Các record bị drop trong corruption

Theo `data/results/corruption_log.json`, 3 paper bị `drop_latest`:

| Paper ID | Title | Trong raw? | Trong repaired? |
|---|---|---|---|
| `10-2118-234689-pa` | SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation | ✅ Có | ✅ Có |
| `10-1111-exsy-70341` | Hi-RAG: A Hierarchical Retrieval-Augmented Generation Framework for Scalable and Generalisable Tool Selection in Large Language Model Agents | ✅ Có | ✅ Có |
| `10-1007-s10278-026-02086-9` | JADE-Plus: A Multimodal Agentic Retrieval-Augmented Generation Large Language Framework for Diagnostic Support in Jawbone Lesions | ✅ Có | ✅ Có |

**Kết luận:** Cả 3 paper bị drop đều **có mặt trong raw records** (bằng chứng từ nguồn) và **đã được phục hồi** trong `papers_clean_repaired.json` (24 records).

### 2.2. Các record bị corrupt khác

| Loại corruption | Paper ID | Trong repaired? |
|---|---|---|
| `blank_summary` | `10-21203-rs-3-rs-10178277-v1`, `10-2196-preprints-106157` | ✅ Có (summary đầy đủ) |
| `inject_noise` | `10-3390-buildings16132637`, `10-21079-11681-50309` | ✅ Có (không noise) |
| `truncate_title` | `10-63646-kpqm1958`, `10-47576-2949-1894-2026-7-7-023` | ✅ Có (title đầy đủ) |
| `stale_date` | `10-21203-rs-3-rs-10012178-v1`, `10-21203-rs-3-rs-9882260-v1` | ✅ Có (published đúng) |
| `duplicate` | `10-52060-juptik-v4i1-4318`, `10-54254-2753-8818-2026-dl34055` | ✅ Có (không duplicate) |

---

## 3. Hỗ trợ kiểm tra config/API key không lọt vào Git

### 3.1. `.gitignore` đã chặn `.env`

`.gitignore` chứa:
```
.env
.venv/
solution/
lab.txt
src/*.egg-info/
lab/
**/__pycache__/
```

**Kết luận:** File `.env` (chứa API keys) **đã được chặn** khỏi Git. Không có secret nào lọt vào repository.

### 3.2. Kiểm tra hardcoded path trong source

Đã quét toàn bộ `src/` tìm các path cứng (macOS path `/Users/langthiphuonghue/...`, `/mnt/`, `AITHUCCHIEN`):
- **Không tìm thấy** hardcoded path trong `src/` source code.
- Các path được quản lý qua `Settings.paths` trong `src/core/config.py` (dùng `Path` tương đối từ project root).

> ⚠️ **Lưu ý:** Manifest files (`data/embeddings/papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json`) ban đầu có `persist_path` trỏ sang máy khác (`/Users/langthiphuonghue/...`). **Đã sửa** bằng rebuild index local → `persist_path` = `D:\VINAI\...\data\chroma`.

---

## 4. Re-run cleaning từ raw tạo repaired dataset, không copy sửa tay từ baseline

**Quy trình repair** (`src/pipelines/corruption_flow.py`):
1. Load raw records từ cache (`data/raw/crossref_records.json`).
2. Chạy lại `build_clean_dataframe(raw_records, run_date)` — **re-clean từ raw**, không dùng dữ liệu corrupted, không copy/sửa tay từ baseline.
3. Lưu `papers_clean_repaired.csv` + `papers_clean_repaired.json`.

**Bằng chứng:** `papers_clean_repaired.json` có đầy đủ 24 records với schema chuẩn (18 fields), không phải bản copy của baseline hay corrupted.

---

## 5. Kiểm tra repaired schema, row count và tín hiệu quality

### 5.1. Schema

`papers_clean_repaired.json` có đầy đủ 18 fields:
```
paper_id, title, summary, authors, authors_joined, categories, categories_joined,
primary_category, published, updated, age_days, abs_url, pdf_url, comment,
summary_chars, text_for_embedding, id, abstract
```

### 5.2. Row count

| Trạng thái | Row count |
|---|---|
| Baseline | 24 |
| Corrupted | 23 |
| **Repaired** | **24** ✅ |

### 5.3. Quality & Freshness

| Property | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Quality Status** | ✅ PASS | ❌ FAIL | ✅ PASS |
| **Freshness Status** | ✅ FRESH | ❌ STALE | ✅ FRESH |
| **Missing Summaries** | 0 | 2 | 0 |
| **Duplicate IDs** | 0 | 2 | 0 |
| **Short Summaries** | 0 | 2 | 0 |
| **Stale Rows** | 0 | 2 | 0 |

---

## 6. Trình bày khác biệt clean/corrupted/repaired cho team

| Đặc điểm | Clean (Baseline) | Corrupted | Repaired |
|---|---|---|---|
| **Nguồn** | Crossref raw cache | Baseline clean + corruption | Crossref raw cache (re-clean) |
| **Row count** | 24 | 23 | 24 |
| **Quality** | ✅ PASS | ❌ FAIL | ✅ PASS |
| **Freshness** | ✅ FRESH | ❌ STALE | ✅ FRESH |
| **Missing summaries** | 0 | 2 | 0 |
| **Duplicates** | 0 | 2 | 0 |
| **Stale rows** | 0 | 2 | 0 |
| **Chroma collection** | `papers-baseline` | `papers-corrupted` | `papers-repaired` |
| **Embeddings manifest** | `papers_embeddings.json` | `papers_embeddings_corrupted.json` | `papers_embeddings_repaired.json` |

**Kết luận:** Repaired dataset **khôi phục hoàn toàn** về đúng trạng thái baseline (24 records, quality PASS, freshness FRESH) bằng cách **re-clean từ raw records** — không copy tay, không dùng dữ liệu corrupted.

---

## 7. Files liên quan

| File | Mô tả |
|---|---|
| `data/raw/crossref_records.json` | Raw records cache (24 records, nguồn baseline) |
| `data/clean/papers_clean.json` | Clean baseline (24 records) |
| `data/clean/papers_clean_corrupted.json` | Corrupted clean (23 records) |
| `data/clean/papers_clean_repaired.json` | Repaired clean (24 records) |
| `data/results/corruption_log.json` | Log chi tiết các thao tác corruption |
| `src/ingestion/cleaning.py` | `build_clean_dataframe` (re-clean từ raw) |
| `src/ingestion/corruption.py` | `corrupt_clean_dataframe` |
| `src/pipelines/corruption_flow.py` | Pipeline corruption + repair |
| `.gitignore` | Chặn `.env` (API keys) khỏi Git |
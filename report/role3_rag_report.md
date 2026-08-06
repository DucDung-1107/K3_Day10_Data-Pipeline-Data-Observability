# VAI TRÒ 3 — RAG & Agent: Báo cáo Pipeline, Corruption & Recovery

**Người phụ trách:** RAG & agent (MiniLM, Chroma, search, lookup)
**Phạm vi:** `src/retrieval/` · `data/embeddings/` · `data/chroma/`
**Mốc:** Tạo papers-corrupted, chạy lại query baseline, kiểm tra papers-baseline không bị mutate, tạo papers-repaired, test agent, trình bày 3 collection.

---

## 1. Tổng quan Pipeline

Pipeline gồm 3 trạng thái dữ liệu, mỗi trạng thái có **clean data riêng**, **embeddings manifest riêng**, và **Chroma collection riêng**:

| Trạng thái | Clean data | Embeddings manifest | Chroma collection | Số docs |
|---|---|---|---|---|
| **Baseline** | `data/clean/papers_clean.json` | `data/embeddings/papers_embeddings.json` | `papers-baseline` | 24 |
| **Corrupted** | `data/clean/papers_clean_corrupted.json` | `data/embeddings/papers_embeddings_corrupted.json` | `papers-corrupted` | 23 |
| **Repaired** | `data/clean/papers_clean_repaired.json` | `data/embeddings/papers_embeddings_repaired.json` | `papers-repaired` | 24 |

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (384 chiều, cosine similarity)
**Chroma persist path:** `data/chroma/` (dùng chung cho cả 3 collection, tách biệt bằng collection name)

---

## 2. Cách tạo từng Collection

### 2.1. Baseline (`papers-baseline`)

**Nguồn:** Crossref REST API → `data/raw/crossref_records.json` (24 records cache).

**Quy trình clean** (`src/ingestion/cleaning.py` → `build_clean_dataframe`):
1. Đọc raw records từ cache (không fetch lại API).
2. Chuẩn hóa schema: `paper_id`, `title`, `summary`, `authors`, `authors_joined`, `categories`, `categories_joined`, `primary_category`, `published`, `updated`, `age_days`, `abs_url`, `pdf_url`, `comment`, `summary_chars`, `text_for_embedding`, `id`, `abstract`.
3. Tạo `text_for_embedding` = `"Title: ...\nAuthors: ...\nCategories: ...\nSummary: ..."` — đây là nội dung dùng để embedding.
4. Lưu `papers_clean.csv` + `papers_clean.json`.

**Build index** (`LocalEmbeddingIndex.build`):
1. Đọc clean JSON → DataFrame.
2. `_build_documents()`: mỗi row → document với `record_id = "{paper_id}::{index}"`, `content = text_for_embedding`, `metadata` (paper_id, title, published, authors_joined, categories_joined, summary, abs_url, pdf_url, eff_date, owner, src_url).
3. Embed toàn bộ documents bằng MiniLM.
4. Tạo Chroma collection `papers-baseline` (cosine space), add embeddings + documents + metadatas.
5. Ghi manifest `papers_embeddings.json` (backend, embedding_model, persist_path, collection_name, documents).

### 2.2. Corrupted (`papers-corrupted`)

**Nguồn:** Lấy từ **baseline clean data** rồi làm bẩn (không fetch lại nguồn).

**Quy trình corruption** (`src/ingestion/corruption.py` → `corrupt_clean_dataframe`), ghi log vào `data/results/corruption_log.json`:

| Loại corruption | Số record | Mô tả | Ảnh hưởng |
|---|---|---|---|
| `drop_latest` | 3 | Xóa 3 paper mới nhất (SafeRAG `10-2118-234689-pa`, Hi-RAG `10-1111-exsy-70341`, JADE-Plus `10-1007-s10278-026-02086-9`) | Mất 3 docs → 21 docs |
| `blank_summary` | 2 | Xóa summary của 2 paper (để `summary=""`) | Summary rỗng → embedding mất ngữ nghĩa |
| `inject_noise` | 2 | Chèn chuỗi rác `[CORRUPTED_NOISE_ERROR_404_GARBAGE]` vào summary | Nhiễu embedding |
| `truncate_title` | 2 | Cắt ngắn title (vd "The Age of..." thay vì title đầy đủ) | Mất thông tin title |
| `stale_date` | 2 | Đổi ngày published về `2020-01-01` | Freshness FAIL |
| `duplicate` | 2 | Nhân đôi 2 paper (Fatwa `10-52060-juptik-v4i1-4318`, Hallucination `10-54254-2753-8818-2026-dl34055`) | 21 + 2 = 23 docs, trùng ID |

**Kết quả:** 24 → 23 docs (3 drop, 2 duplicate thêm vào).

**Build index:** Tương tự baseline nhưng dùng `papers_clean_corrupted.json` → collection `papers-corrupted`, manifest `papers_embeddings_corrupted.json`.

> ⚠️ **Fail case phát hiện:** Manifest `papers_embeddings_corrupted.json` ban đầu có `persist_path` trỏ sang máy khác (`/Users/langthiphuonghue/...`), khiến `LocalEmbeddingIndex.load()` không tìm thấy collection. **Đã sửa** bằng cách rebuild index local → `persist_path` = `D:\VINAI\...\data\chroma`.

### 2.3. Repaired (`papers-repaired`)

**Nguồn:** Đọc lại **raw records cache** (`data/raw/crossref_records.json`) — cùng snapshot dùng ở baseline, **không copy/sửa tay từ baseline**.

**Quy trình repair** (`src/pipelines/corruption_flow.py`):
1. Load raw records từ cache (đảm bảo cùng nguồn baseline).
2. Chạy lại `build_clean_dataframe(raw_records, run_date)` — **re-clean từ raw**, không dùng dữ liệu corrupted.
3. Lưu `papers_clean_repaired.csv` + `papers_clean_repaired.json` (24 records).
4. Build index → collection `papers-repaired`, manifest `papers_embeddings_repaired.json`.

> ⚠️ **Fail case phát hiện:** Manifest `papers_embeddings_repaired.json` cũng có `persist_path` trỏ sai máy khác. **Đã sửa** bằng rebuild local.

---

## 3. Kết quả Test giữa các Collection

### 3.1. Data Quality & Freshness

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

### 3.2. RAG Evaluation Metrics (test set 24 câu)

| Metric | Baseline | Corrupted | Repaired | Δ Corrupt | Δ Repaired |
|---|---|---|---|---|---|
| **Retrieval Hit Rate** | 0.8333 | 0.5000 | 1.0000 | **-0.3333** | **+0.5000** |
| **Mean Token F1** | 0.8750 | 0.5506 | 1.0000 | **-0.3244** | **+0.4494** |
| **Judge Accuracy** | 0.8750 | 0.5417 | 1.0000 | **-0.3333** | **+0.4583** |
| **Mean Judge Score** | 4.5000 | 3.5417 | 5.0000 | **-0.9583** | **+1.4583** |

### 3.3. Retrieval Comparison (7 queries baseline, top-4)

**Baseline vs Corrupted: 5/7 queries thay đổi thứ hạng/top-k**

| # | Query | Baseline top-4 | Corrupted top-4 | Thay đổi |
|---|---|---|---|---|
| 1 | Summary SafeRAG | `10-2118-234689-pa` (SafeRAG) đứng #1 | SafeRAG **biến mất** (bị drop) | ❌ |
| 2 | Authors SafeRAG | `10-2118-234689-pa` đứng #1 | SafeRAG **biến mất** | ❌ |
| 3 | RAG for LLM | `10-55041-isjem07213`, `10-20944-...`, `10-36227-...`, `10-1111-exsy-70341` | `10-55041-...`, `10-2196-preprints-106157` (blank summary), `10-20944-...`, `10-36227-...` | ❌ |
| 4 | Agentic AI | `10-63646-kpqm1958`, `10-20944-...`, `10-55041-...`, `10-32473-...` | **Giống baseline** | ✅ |
| 5 | Hallucination | `10-54254-...`, `10-70121-...`, `10-36227-...`, `10-1093-...` | `10-54254-...` **xuất hiện 2 lần** (duplicate), `10-2196-...`, `10-70121-...` | ❌ |
| 6 | Age of Autonomous Agents | `10-63646-kpqm1958`, `10-3390-...`, `10-21203-...`, `10-36227-...` | **Giống baseline** | ✅ |
| 7 | Chatbot Fatwa | `10-52060-juptik-v4i1-4318`, `10-35314-...`, `10-55041-...`, `10-32473-...` | `10-52060-...` **xuất hiện 2 lần** (duplicate) | ❌ |

**Baseline vs Repaired: 0/7 queries thay đổi** — retrieval đã phục hồi hoàn toàn.

---

## 4. Fail Cases & Cách Phục Hồi

### Fail Case 1: Drop paper mới nhất (SafeRAG)
- **Nguyên nhân:** `drop_latest` xóa 3 paper mới nhất khỏi corrupted data.
- **Ảnh hưởng:** Query về SafeRAG (`10-2118-234689-pa`) không còn tìm thấy paper → retrieval hit rate giảm, answer sai (trả về "Abstract Background." từ paper khác).
- **Phục hồi:** Re-clean từ raw records → SafeRAG quay lại trong `papers-repaired` → query trả về đúng paper.

### Fail Case 2: Blank summary
- **Nguyên nhân:** `blank_summary` xóa summary của 2 paper → `text_for_embedding` chỉ còn title + authors + categories, mất phần summary.
- **Ảnh hưởng:** Embedding của paper bị thiếu ngữ nghĩa → paper `10-2196-preprints-106157` (blank summary) xuất hiện trong top-4 của query "RAG for LLM" dù không liên quan.
- **Phục hồi:** Re-clean từ raw → summary đầy đủ → embedding chính xác.

### Fail Case 3: Duplicate records
- **Nguyên nhân:** `duplicate` nhân đôi 2 paper → cùng paper_id xuất hiện 2 lần trong collection.
- **Ảnh hưởng:** Query "hallucination" trả về `10-54254-...` 2 lần (chiếm 2/4 vị trí top-k), làm giảm đa dạng kết quả. Query "Fatwa" cũng bị duplicate `10-52060-...`.
- **Phục hồi:** Re-clean từ raw → không còn duplicate → top-k đa dạng trở lại.

### Fail Case 4: Truncate title
- **Nguyên nhân:** `truncate_title` cắt ngắn title → mất thông tin quan trọng trong embedding.
- **Ảnh hưởng:** Paper `10-63646-kpqm1958` (title bị cắt thành "The Age of...") có thể không match đúng query về "Autonomous Agents".
- **Phục hồi:** Re-clean từ raw → title đầy đủ.

### Fail Case 5: Stale date
- **Nguyên nhân:** `stale_date` đổi published về `2020-01-01` → freshness FAIL.
- **Ảnh hưởng:** Không ảnh hưởng trực tiếp retrieval nhưng làm quality/freshness report FAIL.
- **Phục hồi:** Re-clean từ raw → published đúng → freshness FRESH.

### Fail Case 6 (kỹ thuật): Manifest persist_path sai máy
- **Nguyên nhân:** Manifest `papers_embeddings_corrupted.json` và `papers_embeddings_repaired.json` có `persist_path` trỏ sang máy khác (`/Users/langthiphuonghue/...`).
- **Ảnh hưởng:** `LocalEmbeddingIndex.load()` không tìm thấy collection → không load được index.
- **Phục hồi:** Rebuild index local → `persist_path` = `D:\VINAI\...\data\chroma` → load OK.

---

## 5. Agent Tool Test (trên papers-repaired)

Agent dùng 2 tools: `semantic_search_papers` (search) và `lookup_paper` (lookup).

| Câu hỏi | Tool dùng | Kết quả |
|---|---|---|
| "Use the lookup tool to find the paper with paper_id '10-2118-234689-pa' and tell me its title." | `lookup_paper` | ✅ Trả về đúng title "SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation" |
| "Use the semantic search tool to find papers about 'retrieval augmented generation for large language models' and list the top paper_id." | `semantic_search_papers` | ✅ Trả về top 4 paper_id đúng: `10-55041-isjem07213`, `10-20944-preprints202604-0339-v1`, `10-36227-techrxiv-177272838-89432844-v1`, `10-1111-exsy-70341` |

> ⚠️ **Fail case kỹ thuật:** `create_react_agent()` trong langgraph version hiện tại dùng tham số `prompt` (không phải `state_modifier`/`system_prompt`). **Đã sửa** `src/retrieval/agent.py` để dùng `prompt=system_prompt`.

---

## 6. Kết luận

1. **Corruption làm giảm chất lượng retrieval rõ rệt:** retrieval hit rate giảm từ 0.8333 → 0.5000 (-33%), mean token F1 giảm từ 0.875 → 0.5506 (-32%), judge accuracy giảm từ 0.875 → 0.5417 (-33%).
2. **Recovery phục hồi hoàn toàn:** re-clean từ raw records (cùng snapshot baseline) đưa retrieval hit rate lên 1.0000, mean token F1 lên 1.0000, judge accuracy lên 1.0000 — **vượt cả baseline**.
3. **Ba collection tách biệt, tái lập được:** mỗi trạng thái có clean data + embeddings manifest + Chroma collection riêng, đều build được từ nguồn tương ứng.
4. **papers-baseline không bị mutate:** 24 docs, paper_id & title không đổi sau khi build corrupted/repaired.
5. **Agent hoạt động đúng:** dùng `lookup_paper` và `semantic_search_papers` trả về document repaired chính xác.

---

## 7. Files liên quan

| File | Mô tả |
|---|---|
| `script/run_role3_rag.py` | Script chính: build corrupted/repaired index, so sánh retrieval, verify baseline, test agent |
| `script/check_role3_state.py` | Script diagnostic: kiểm tra trạng thái manifest |
| `src/retrieval/agent.py` | Agent (đã fix `prompt` param) |
| `src/retrieval/index.py` | `LocalEmbeddingIndex` (build/load/search/lookup) |
| `src/retrieval/embeddings.py` | MiniLM embeddings |
| `data/embeddings/papers_embeddings.json` | Manifest baseline |
| `data/embeddings/papers_embeddings_corrupted.json` | Manifest corrupted (đã sửa persist_path) |
| `data/embeddings/papers_embeddings_repaired.json` | Manifest repaired (đã sửa persist_path) |
| `data/results/role3_retrieval_comparison.json` | Kết quả so sánh retrieval + agent tool test |
| `data/results/corruption_log.json` | Log chi tiết các thao tác corruption |
| `data/quality/*.json` | Quality & freshness reports |
| `data/results/*_metrics.json` | RAG evaluation metrics |

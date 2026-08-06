# Group Report — Day 10: Data Pipeline & Data Observability

> Dùng mẫu này cho báo cáo chung của nhóm 3–5 thành viên. Thay toàn bộ nội dung trong dấu `[ ]` bằng thông tin và kết quả thực tế. Xóa các dòng hướng dẫn không còn cần thiết trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | [Tên hoặc mã nhóm]     |
| Repository         | https://github.com/DucDung-1107/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | [YYYY-MM-DD]               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | [Họ tên — GitHub `phuonghue1395`] | [MSSV] | Ingestion, Cleaning & Evaluation/Observability | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py`, `script/validate_clean_data.py`, `script/smoke_test_index.py` |
| 2 | Đặng Đức Hòa | [MSSV] | Pipeline integrator | `src/pipelines/phase1.py` — điều phối raw → clean → index → test set → evaluate → quality/freshness → report |
| 3 | [Họ tên — GitHub `DucDung-1107`] | [MSSV] | Chủ repository | Quản lý repo nhóm, review và merge |
| 4 | Quan_01863 | [MSSV] | Corruption & Comparison | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `tests/test_role4_evaluation_observability.py` |

> Phân công ở trên được đối chiếu với lịch sử commit thực tế (`git log --name-only`), không phải bảng phân vai dự kiến ban đầu.
> Cần điền nốt: MSSV của cả bốn thành viên, họ tên đầy đủ của STT 1/3/4, và tên nhóm.

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

[Viết phần tóm tắt tại đây.]

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API, query/filter trong `src/core/config.py` | Fetch có retry/backoff, parse payload thành `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | STT 1 |
| Cleaning          | `data/raw/crossref_records.json` | Chuẩn hóa title/summary/authors/categories, dedupe theo `paper_id`, tính `age_days`, dựng `text_for_embedding` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 dòng) | STT 1 |
| Embedding/index   | Cleaned dataframe | MiniLM `all-MiniLM-L6-v2` (384 chiều) + Chroma collection `papers-baseline`, cosine | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Starter code, tích hợp bởi STT 2 |
| Evaluation        | Cleaned dataframe + baseline index | 24 câu hỏi (6 paper × 4 loại), chấm `retrieval_hit_rate`, token F1, LLM judge | `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | STT 1 |
| Observability     | Cleaned dataframe | 6 quality check (rows, title, summary, duplicate, short summary, negative age) + freshness theo ngưỡng 180 ngày | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md` | STT 1 |
| Corruption/repair | `data/clean/papers_clean.csv` + `data/raw/crossref_records.json` | **Chưa triển khai** — còn `TODO(student)` | `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json`, `data/reports/corruption_report.md` | STT 4 |
| Orchestration     | Settings + toàn bộ khối trên | `phase1.py` đã chạy end-to-end; `corruption_flow.py` **chưa triển khai** | `data/reports/phase1_report.md` | STT 2 (phase 1), STT 4 (phase 2) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` khai báo trong `.env`; vì `GOOGLE_API_KEY` trống nên pipeline tự chuyển sang `openai` |
| `LLM_MODEL`                | `gemini-2.5-flash` khai báo; thực tế chạy `gpt-4o-mini` sau khi fallback |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Số lượng Crossref records | 24 raw → 24 clean (không record nào bị loại) |
| Retrieval`top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Random seed, nếu có        | Không dùng. Cả `build_test_set` lẫn `corrupt_clean_dataframe` chọn record theo thứ tự cố định nên chạy lại cho kết quả giống hệt |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |
| `pytest tests/` | 60 passed | 2026-08-06 | `tests/test_role4_evaluation_observability.py` |

Trên Windows cần chạy với `PYTHONIOENCODING=utf-8`, vì pipeline in thông báo tiếng Việt còn console mặc định dùng cp1252.

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | [Crossref endpoint/dataset thực tế] |
| Query/filter                | [Query hoặc filter]                  |
| Thời điểm lấy dữ liệu | [Timestamp]                           |
| Số record nhận được    | [Số lượng]                         |
| Cơ chế retry/backoff      | [Mô tả ngắn]                       |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| [Tên trường] | [Kiểu]         | [Có/Không] | [Ý nghĩa] | [Cách xử lý]        |
| [Tên trường] | [Kiểu]         | [Có/Không] | [Ý nghĩa] | [Cách xử lý]        |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| [Ví dụ: loại record không có title] | [Completeness/Validity/...]  |              [Số lượng] | [Artifact/kiểm tra] |
| [Quy tắc thực tế]                     | [Dimension]                  |              [Số lượng] | [Artifact/kiểm tra] |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

[Mô tả tại đây.]

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24 (6 paper × 4 loại câu hỏi) |
| Các`question_type`                    | `summary`, `authors`, `date`, `categories` — mỗi loại 6 câu |
| Ground-truth document ID                 | Lấy trực tiếp `paper_id` của paper được chọn từ cleaned dataset, không tự đặt ID |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB, ba collection tách biệt: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval`top_k`                       | 4 |
| LLM provider/model                       | OpenAI `gpt-4o-mini`, temperature 0.0 (dùng cho LLM judge) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` — 24 câu, sinh một lần và giữ nguyên |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Ba lần đánh giá chỉ có ý nghĩa nếu **biến duy nhất thay đổi là trạng thái dữ liệu**. Nếu sinh lại test set cho từng trạng thái thì câu hỏi và ground truth sẽ khác nhau, và mọi chênh lệch số liệu không còn phân biệt được là do dữ liệu hỏng hay do bộ câu hỏi đổi. Vì vậy test set được sinh một lần ở phase 1 rồi đóng băng; `corruption_flow.py` đọc lại đúng file đó cho cả corrupted và repaired, và `generate_corruption_report` in cảnh báo nếu ba lần chạy có số `samples` khác nhau.

Câu hỏi được thiết kế bám đúng cách `retrieval/qa.py` trích câu trả lời: mỗi câu chứa đúng một cụm khóa mà `_extract_answer` nhận diện (`who authored`, `when was`, `what categories`, hoặc không cụm nào cho loại summary), và tiêu đề paper được bọc trong dấu nháy đơn để kích hoạt exact lookup. `ground_truth` được sinh bằng đúng phép trích đó trên document đúng, nên khi retrieval trúng thì token F1 đạt 1.0 và khi trượt thì tụt rõ rệt — nhờ vậy metric đo chất lượng dữ liệu chứ không đo độ vênh cách diễn đạt.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | `crossref_response.json` và `crossref_records.json`, 24 record |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv` và `.json`, 24 dòng, `paper_id` unique |
| Embedding manifest/index | `data/embeddings/`                   | Có | `papers_embeddings.json`, collection `papers-baseline` |
| Evaluation set           | `data/eval/`                         | Có | `test_set.json`, 24 câu, đóng băng dùng cho cả ba trạng thái |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` chứa toàn bộ câu trả lời và nhận xét của judge |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality.json` PASS 8/8, `freshness_report.json` FRESH |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Sinh tự động từ artifact, không nhập tay số liệu |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 | Cả 24/24 câu đều lấy được đúng document chứa đáp án trong top-4 |
| `mean_token_f1`      | 1.0000 | Đạt tuyệt đối vì `ground_truth` được sinh bằng đúng phép trích của `qa._extract_answer`; khi retrieval trúng thì câu trả lời trùng khít ground truth. Đây là mốc trần có chủ đích, để mọi mức sụt sau này quy hết về chất lượng dữ liệu |
| `judge_accuracy`     | 0.9583 | 23/24 câu được LLM judge chấm là đúng về bản chất |
| `mean_judge_score`   | 4.9167 | Thang 1–5. Không đạt 5.0 tuyệt đối vì judge trừ điểm ở câu trả lời quá ngắn gọn dù không sai |
| Ragas, nếu có        | Không chạy | `metrics.py` bỏ qua Ragas trừ khi đặt `RUN_RAGAS=1`; nhóm không bật để tiết kiệm thời gian và chi phí gọi LLM |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `schema_columns_present` | Validity | Đủ 6 cột bắt buộc | Pass — không thiếu cột | `data/quality/baseline_quality.json` |
| `row_count_minimum` | Completeness | ≥ `top_k` = 4 dòng | Pass — 24 dòng | nt |
| `paper_id_not_null` | Completeness | 0 dòng trống ID | Pass — 0 | nt |
| `paper_id_unique` | Uniqueness | 0 ID trùng | Pass — 0 | nt |
| `title_not_empty` | Completeness | 0 title rỗng | Pass — 0 | nt |
| `text_for_embedding_not_empty` | Completeness | 0 dòng rỗng | Pass — 0 | nt |
| `summary_min_length` | Validity | 0 dòng dưới 100 ký tự | Pass — 0 | nt |
| `freshness_age_days` | Timeliness | 0 dòng quá 180 ngày | Pass — 0 stale, 0 không xác định tuổi | nt |

Ngưỡng 100 ký tự của `summary_min_length` khớp đúng quy tắc `cleaning.py` đang dùng để loại record, nên dữ liệu sạch hợp lệ không bao giờ bị báo lỗi oan.

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned dataset, cột `published` và `age_days`; ghi ra `data/quality/freshness_report*.json` |
| Timestamp mới nhất       | `2026-08-01` (baseline), paper cũ nhất `2026-02-12`, tuổi lớn nhất 175 ngày |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | FRESH |
| Lý do                     | 0/24 dòng vượt ngưỡng và 0 dòng có ngày không parse được. Filter nguồn Crossref chỉ lấy paper trong 180 ngày gần nhất, nên dữ liệu sạch **không thể** có dòng stale — bất kỳ dòng stale nào xuất hiện về sau đều là do bị chèn vào. Vì vậy `is_fresh` được định nghĩa là `stale_rows == 0`, thay vì xét ngày mới nhất (cách đó sẽ bỏ lọt corruption chỉ làm cũ một phần dữ liệu) |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Xóa hẳn paper mới nhất khỏi dataset, ưu tiên paper mà test set có hỏi tới | 2 | Giảm row count | `retrieval_hit_rate` 1.0 → 0.667: document không còn trong index thì không thể lấy ra được | Nạp lại từ raw snapshot |
| `blank_summary` | Gán `summary = ""` | 2 | `summary_min_length` FAIL | `summary_min_length` FAIL. Câu hỏi loại summary mất đáp án | nt |
| `inject_noise` | Chèn 130 ký tự rác vào `summary` rồi dựng lại `text_for_embedding` | 2 | Không có check nào bắt được | Làm loãng embedding, kéo token F1 xuống nhưng không tạo tín hiệu quality nào | nt |
| `truncate_title` | Cắt title còn 12 ký tự | 2 | Không có check nào bắt được | Phá exact lookup theo tiêu đề trong `qa.answer_question` | nt |
| `stale_published_date` | Đặt `published = 2000-01-01`, tính lại `age_days = 9714` | 2 | `freshness_age_days` FAIL, freshness STALE | Đúng như kỳ vọng: 2/23 dòng stale, `is_fresh` false | nt |
| `duplicate_rows` | Nhân bản dòng, giữ nguyên `paper_id` | 1 | `paper_id_unique` FAIL | Đúng như kỳ vọng. Một paper chiếm nhiều slot trong top-4 | nt |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 kịch bản, mỗi kịch bản kèm danh sách `paper_id` bị tác động, tham số cụ thể, số dòng trước/sau, và cờ `hits_ground_truth`. Log còn tổng hợp `ground_truth_coverage = 1.0`, tức **cả 6/6 paper mà test set hỏi tới đều bị corrupt**. Đây là điều kiện bắt buộc: nếu chỉ làm hỏng những paper không câu hỏi nào đụng tới thì metric sẽ đứng yên và thí nghiệm không chứng minh được gì.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair chạy lại đúng `build_clean_dataframe` trên `data/raw/crossref_records.json` — bản snapshot đã lưu ở phase 1 — chứ không sửa tay dataset hỏng và cũng không gọi lại Crossref API. `corruption_flow.py` không import `fetch_source_records`, nên về mặt mã nguồn nó **không thể** lấy dữ liệu mới; nếu fetch lại thì corpus sẽ khác đi và ba trạng thái mất tính so sánh. Bằng chứng cho thấy repair thật sự phục hồi chứ không phải che số liệu: repaired trùng khít baseline ở cả bốn metric (1.0000 / 1.0000 / 0.9583 / 4.9167) và quay lại đủ 24 dòng, PASS 8/8 quality check.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.0000 | 0.6667 | 1.0000 | −0.3333 | 100% | 8/24 câu trượt vì document bị xóa khỏi index |
| `mean_token_f1`        | 1.0000 | 0.6737 | 1.0000 | −0.3263 | 100% | Trượt retrieval kéo theo câu trả lời lấy từ document sai |
| `judge_accuracy`       | 0.9583 | 0.7083 | 0.9583 | −0.2500 | 100% | 6 câu bị judge đánh là sai bản chất |
| `mean_judge_score`     | 4.9167 | 3.9167 | 4.9167 | −1.0000 | 100% | Mất trọn 1 điểm trên thang 5 |
| Quality checks pass/fail | PASS 8/8 | FAIL 5/8 | PASS 8/8 | 3 check chuyển sang FAIL | 100% | FAIL ở `paper_id_unique`, `summary_min_length`, `freshness_age_days` |
| Freshness status         | FRESH | STALE | FRESH | 0 → 2 dòng stale | 100% | Ngày cũ nhất tụt từ 2026-02-12 xuống 2000-01-01 |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. **Xóa 2 paper mà test set hỏi tới + nhân bản `paper_id` + làm rỗng summary** → `paper_id_unique`, `summary_min_length`, `freshness_age_days` chuyển FAIL và freshness thành STALE → `retrieval_hit_rate` tụt 1.0000 → 0.6667 và `judge_accuracy` tụt 0.9583 → 0.7083. Truy vết được từng bước qua `corruption_log.json` → `corrupted_quality.json` → `corrupted_metrics.json`.
2. **Chạy lại cleaning từ `data/raw/crossref_records.json`** → quality trở lại PASS 8/8 và freshness trở lại FRESH → cả bốn metric quay về **đúng** giá trị baseline. Trùng khít chứ không chỉ xấp xỉ, vì repaired được dựng lại từ cùng snapshot raw đã tạo ra baseline.

Giới hạn của kết luận này: `inject_noise` và `truncate_title` **không kích hoạt bất kỳ quality check nào**. Chúng vẫn góp phần kéo metric xuống, nhưng nếu chỉ nhìn báo cáo data quality thì hai dạng lỗi này hoàn toàn vô hình. Nói cách khác, quality gate hiện tại phát hiện được thiếu và trùng dữ liệu, nhưng chưa phát hiện được dữ liệu *bị bóp méo*.

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** [Lỗi hoặc kết quả sai.]
- **Nguyên nhân:** [Root cause.]
- **Cách xử lý:** [Thay đổi đã thực hiện.]
- **Cách xác minh:** [Lệnh và artifact.]

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [ ] Baseline, corrupted và repaired dùng cùng evaluation set.
- [ ] Bảng metrics khớp với các file trong `data/results/`.
- [ ] Quality/freshness conclusions khớp với `data/quality/`.
- [ ] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

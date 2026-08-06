# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lăng Thị Phương Huế            |
| MSSV               | 2A202601915                    |
| Khóa/Lớp         | K3             |
| Tên nhóm         | E1    |
| Vai trò chính    | Xử lý Nền tảng dữ liệu & recovery             |
| Repository         | https://github.com/DucDung-1107/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Kiểm tra điều kiện dừng & hao hụt dữ liệu** | `src/pipelines/phase1.py` | `Settings` | bundle.summary | Hoàn thành |
| **Thu thập dữ liệu thô & cache** | `src/ingestion/crossref.py` | Settings & query parameters | File cache thô `crossref_records.json` | Hoàn thành |
| **Làm sạch & chuẩn hóa dữ liệu** | `src/ingestion/cleaning.py` | Danh sách `PaperRecord` thô | Bảng cleaned DataFrame và các file `papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| **Kiểm tra schema & dừng khẩn cấp** | `src/pipelines/phase1.py` (`validate_clean_schema`, checks) | pandas DataFrame sạch | Lỗi runtime dừng khẩn cấp nếu hao hụt > 80% hoặc thiếu trường | Hoàn thành |
| **Độ đo chất lượng & độ tươi mới** | `src/observability/quality.py` | pandas DataFrame sạch & Settings | Báo cáo `baseline_quality.json` và `freshness_report.json` | Hoàn thành |
| **Giả lập phá hủy dữ liệu** | `src/ingestion/corruption.py` | pandas DataFrame sạch | DataFrame hỏng & tệp log lỗi `corruption_log.json` | Hoàn thành |
| **Khôi phục dữ liệu tự động** | `src/pipelines/corruption_flow.py` | Dữ liệu raw cache thô gốc | Báo cáo so sánh 3 trạng thái `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| **Tích hợp Pipeline** | Cả nhóm / `phase1.py` | Tích hợp thành công các bước Ingestion, Cleaning, Indexing, Evaluation và Observability trong cùng 1 luồng |
| **Cấu hình Fallback LLM** | Role 4 (Evaluation) | Cấu hình tự động chuyển đổi sang OpenAI GPT-4o-mini khi thiếu khóa Gemini, đảm bảo pipeline không bị gián đoạn |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Ingestion & Cache Model | `src/ingestion/crossref.py` | [crossref_records.json](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_records.json) | Lệnh `uv run python script/smoke_test_index.py` đọc cache thành công |
| Cleaning, Deduplication & Aliases | `src/ingestion/cleaning.py` | [papers_clean.json](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/clean/papers_clean.json) | Lệnh `uv run python script/validate_clean_data.py` |
| Quality Checks & Freshness | `src/observability/quality.py` | [baseline_quality.json](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/quality/baseline_quality.json) | Lệnh `uv run python script/run_phase1.py` |
| Corruption & Recovery flow | `src/pipelines/corruption_flow.py` | [corruption_report.md](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/reports/corruption_report.md) | Lệnh `uv run python script/run_corruption_flow.py` |

Một output cụ thể:
Tệp báo cáo so sánh [corruption_report.md](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/reports/corruption_report.md) cho thấy sự sụt giảm hiệu năng RAG (Hit Rate từ 1.0 giảm còn 0.5) khi giả lập lỗi dữ liệu thô, và sự phục hồi hoàn chỉnh về 1.0 khi chạy luồng repair nạp lại raw records snapshot.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong một hệ thống RAG, chất lượng dữ liệu đầu vào quyết định trực tiếp hiệu năng tìm kiếm và câu trả lời của LLM. Vấn đề cụ thể bao gồm:
1. Tránh gọi đi gọi lại API ngoài làm mất tính baseline cố định và tránh lỗi Rate Limit bằng cơ chế lưu snapshot thô cục bộ.
2. Dữ liệu thô chứa khoảng trắng thừa, thiếu thông tin quan trọng hoặc trùng lặp DOI, làm nhiễu cơ sở dữ liệu vector.
3. Phát hiện sớm lỗi hao hụt dữ liệu bất thường (mất quá 80% bản ghi sau làm sạch) hoặc sai lệch schema để dừng khẩn cấp pipeline.
4. Khi dữ liệu trong môi trường production bị suy thoái (corruption), hệ thống cần cơ chế cảnh báo sớm và khôi phục tự động (auto-repair) một cách nhanh chóng.

### Cách triển khai

1. **Ingestion & Caching:** Tải dữ liệu qua REST API và lưu trữ thành snapshot thô `crossref_response.json` (dữ liệu API gốc) và `crossref_records.json` (các đối tượng `PaperRecord` đã parse). Lượt chạy sau chỉ đọc từ cache cục bộ nếu `refresh_source` bằng `False`.
2. **Cleaning & Deduplication:** 
   - Lọc bỏ dòng thiếu `title` hoặc `summary`.
   - Chuẩn hóa khoảng trắng (`.strip()`).
   - Sắp xếp dữ liệu theo ngày cập nhật `updated` giảm dần và độ dài summary giảm dần, sau đó dùng `drop_duplicates(subset=["paper_id"])` để giữ lại bản ghi mới nhất và đầy đủ nhất.
   - Tính toán cột `text_for_embedding` bằng cách ghép Title, Authors, Categories, và Summary theo định dạng chuẩn.
   - Tính toán cột `age_days` dựa trên khoảng cách giữa ngày chạy và ngày xuất bản `published`.
3. **Kiểm tra schema & dừng khẩn cấp:** Trong `phase1.py`, tích hợp bộ kiểm định schema `validate_clean_schema` và cơ chế ngắt mạch: dừng khẩn cấp hệ thống nếu số lượng dòng sau clean bằng 0 hoặc hao hụt dữ liệu vượt quá 80%.
4. **Data Corruption:** Hàm `corrupt_clean_dataframe` phá hủy dữ liệu có kiểm soát bằng cách: drop 3 bài báo mới nhất, đặt rỗng tóm tắt của 2 dòng, chèn chuỗi rác vào tóm tắt của 2 dòng, cắt ngắn tiêu đề của 2 dòng, chuyển ngày xuất bản của 2 dòng về 2020 để gây stale, và nhân bản 2 dòng.
5. **Data Repair:** Luồng repair gọi hàm `build_clean_dataframe` trực tiếp trên cache thô ban đầu để tạo ra bảng dữ liệu sạch đã được khắc phục lỗi mà không sao chép thủ công.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Dữ liệu JSON thô nhận từ Crossref REST API |
| Output                         | pandas DataFrame sạch chứa 18 cột (bao gồm cột chuẩn hóa, `age_days`, `text_for_embedding`, `id`, `abstract` phục vụ validator) |
| Module phụ thuộc             | `src/ingestion/crossref.py` (Ingestion) |
| Module sử dụng output        | `src/retrieval/index.py` (Index), `src/evaluation/testset.py` (Test Set) |
| Điều kiện lỗi cần xử lý | Xử lý lỗi Rate Limit 429, lỗi thiếu Abstract/Title trong dữ liệu thô |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Baseline pipeline chạy thành công vượt qua schema validation; khi chạy corruption flow, hệ thống phát hiện lỗi và phục hồi đầy đủ về 24 dòng sạch.
- **Kết quả thực tế:**
  - Báo cáo chất lượng baseline: PASS, 0 dòng lỗi.
  - Báo cáo so sánh lỗi: RAG Hit Rate rớt xuống 0.5 ở pha lỗi và khôi phục 1.0 ở pha sửa.
- **Artifact/log:**
  - Báo cáo baseline: [phase1_report.md](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/reports/phase1_report.md)
  - Log lỗi giả lập: [corruption_log.json](file:///Users/langthiphuonghue/AITHUCCHIEN/LAB/K3_Day10_Data-Pipeline-Data-Observability/data/results/corruption_log.json)

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp tạo ID duy nhất cho bài báo (`paper_id`) làm cơ sở để deduplicate và liên kết chỉ mục vector.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Tạo mã tự động số nguyên tăng dần hoặc mã ngẫu nhiên UUID.
  - *Phương án B:* Chuẩn hóa chuỗi DOI thành safe slug (thay `/` bằng `-`) làm ID duy nhất (ví dụ: `10-2118-234689-pa`).
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Trade-off về tính tái lập dữ liệu (reproducibility) và tính liên kết dòng đời (lineage). Dùng UUID dễ triển khai nhưng làm thay đổi ID ở mỗi lượt chạy khác nhau, dẫn tới mất dấu vết lineage khi debug lỗi. Dùng safe slug của DOI đảm bảo ID ổn định (stable) và dễ đối chiếu dòng thô gốc.
- **Bằng chứng quyết định phù hợp:** Bài báo `10-2118-234689-pa` được truy vết thành công qua cả 3 trạng thái thô, sạch, lỗi và sửa lỗi trên database.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ValueError: Blocker: Clean Schema không ổn định! Thiếu các cột bắt buộc: {'id', 'abstract'}
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `uv run python script/run_phase1.py` sau khi git pull.
- **Nguyên nhân gốc:** Thành viên khác đã cập nhật bộ kiểm tra tính ổn định của Schema trong `phase1.py` yêu cầu cột `id` và `abstract`, trong khi cleaning module ban đầu xuất cột `paper_id` và `summary`.
- **Cách xử lý:** Tôi đã thực hiện sửa đổi trong `cleaning.py` để tự động sao chép hai cột bí danh dự phòng trước khi xuất DataFrame:
  ```python
  df["id"] = df["paper_id"]
  df["abstract"] = df["summary"]
  ```
- **Cách xác minh sau khi sửa:** Chạy lại `run_phase1.py`, vượt qua validation thành công.
- **Điều học được:** Cần xây dựng các cột bí danh (aliases) dự phòng để tương thích ngược khi tích hợp code từ nhiều thành viên khác nhau.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu API $\rightarrow$ lưu cache thô JSON $\rightarrow$ parse thành dataclass `PaperRecord` $\rightarrow$ làm sạch & loại bỏ trùng lặp $\rightarrow$ tạo file CSV/JSON sạch $\rightarrow$ nạp vào ChromaDB dưới dạng embedding vectors.
2. **Evaluation set và ground-truth document IDs dùng để đo chất lượng:** Bộ câu hỏi (test set) chứa câu hỏi và danh sách ID của bài báo gốc chứa đáp án. Khi Agent trả lời câu hỏi, ta so sánh tài liệu Agent tìm thấy với ID chuẩn (Retrieval Hit Rate) và so sánh câu trả lời của Agent với câu trả lời chuẩn (Mean Token F1, Judge Accuracy).
3. **Quality checks khác freshness monitoring:** Quality checks kiểm tra tính toàn vẹn kỹ thuật (null, empty text, duplicates). Freshness monitoring giám sát khía cạnh thời gian (tuổi thọ của bài báo so với thời gian hiện tại dựa trên `age_days`).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired:** Để đảm bảo so sánh công bằng hiệu năng RAG của Agent qua cả 3 trạng thái.
5. **Repair được xem là thành công dựa trên:** Quality báo `PASS`, Freshness báo `FRESH`, số lượng dòng khôi phục đầy đủ về `24`, và các metrics RAG khôi phục về `1.0`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.5000 |   1.0000 | Lỗi làm rớt 50% khả năng tìm kiếm |
| `mean_token_f1`      |   1.0000 |    0.5506 |   1.0000 | Từ vựng câu trả lời bị lệch mạnh khi mất bài báo |
| `judge_accuracy`     |   1.0000 |    0.5417 |   1.0000 | Tỷ lệ trả lời chính xác giảm gần một nửa |
| `mean_judge_score`   |   5.0000 |    3.5417 |   5.0000 | Điểm đánh giá trung bình bị giảm sút |
| Quality checks         |     PASS |      FAIL |     PASS | Phát hiện chính xác lỗi trùng lặp/thiếu |
| Freshness status       |    FRESH |     STALE |    FRESH | Cảnh báo đúng khi có dòng dữ liệu cũ |

### Kết luận từ số liệu

1. **Chuỗi ảnh hưởng của lỗi:** [Data corruption: Xóa 3 bài báo mới nhất & tẩy trắng tóm tắt] $\rightarrow$ [Quality báo FAIL, Freshness báo STALE] $\rightarrow$ [Retrieval Hit Rate giảm còn 0.5, Judge Accuracy giảm còn 0.5417].
2. **Chuỗi khôi phục:** [Repair action: Reload raw records & clean] $\rightarrow$ [Quality báo PASS, Freshness báo FRESH] $\rightarrow$ [RAG Agent phục hồi hoàn toàn Hit Rate 1.0 và Judge Score 5.0].

**Phân tích chi tiết:**
Lỗi **Drop Latest Records** (xóa bài báo mới nhất) ảnh hưởng rõ rệt nhất vì làm biến mất hoàn toàn ngữ cảnh mới nhất khiến Agent trả lời sai hoặc bịa đặt (hallucinate). Việc reload dữ liệu từ Raw Cache gốc giúp phục hồi hoàn toàn hiệu năng RAG.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Lưu cache snapshot dữ liệu thô giúp pipeline độc lập, đáng tin cậy và có khả năng sửa chữa lỗi tự động.
2. Observability (Quality & Freshness) giúp cảnh báo lỗi sớm trước khi cập nhật chỉ mục vector.
3. Chất lượng dữ liệu thô quyết định trực tiếp hiệu năng suy luận của RAG Agent.

### Hướng cải thiện

Tôi muốn phát triển thêm cơ chế **Tự động sửa lỗi (Auto-Healing)** trong pipeline. Cụ thể: Khi phát hiện dữ liệu lỗi (như trùng lặp hoặc stale date), hệ thống sẽ tự động gửi yêu cầu (hoặc nạp lại bản ghi đó từ nguồn) và tự chữa lành bản ghi đó mà không cần phải thực hiện chạy lại (re-run) toàn bộ pipeline từ đầu, giúp tiết kiệm thời gian và chi phí vận hành.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lăng Thị Phương Huế
**Ngày xác nhận:** 2026-08-06

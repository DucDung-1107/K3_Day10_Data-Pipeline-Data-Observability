# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hải Quân |
| MSSV               | 2A202601863 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | E1 |
| Vai trò chính    | Evaluation, Observability, Corruption & Integration |
| Repository         | https://github.com/DucDung-1107/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Evaluation set | `src/evaluation/testset.py` → `build_test_set` | Cleaned dataframe | `data/eval/test_set.json` (24 câu) | Hoàn thành |
| Data quality gate | `src/observability/quality.py` → `run_data_quality_checks` | Cleaned/corrupted/repaired dataframe | `data/quality/{baseline,corrupted,repaired}_quality.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` → `build_freshness_report` | nt | `data/quality/freshness_report*.json` | Hoàn thành |
| Báo cáo baseline | `src/observability/reporting.py` → `generate_phase1_report` | source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Báo cáo so sánh | `src/observability/reporting.py` → `generate_corruption_report` | Metrics + quality + freshness của ba trạng thái | `data/reports/corruption_report.md` | Hoàn thành |
| Controlled corruption | `src/ingestion/corruption.py` → `corrupt_clean_dataframe` | Cleaned dataframe + `ground_truth_doc_ids` | Corrupted dataframe, `data/results/corruption_log.json` | Hoàn thành |
| Orchestration phase 2 | `src/pipelines/corruption_flow.py` → `main` | Artifact của phase 1 | corrupted/repaired metrics, answers, quality, freshness, comparison report | Hoàn thành |
| Test tự động | `tests/test_role4_evaluation_observability.py` | — | 60 test, toàn bộ pass | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | -------------------------------- | ---------- |
| Sửa lỗi chặn pipeline | `script/run_phase1.py` | Sửa `SyntaxError` (thiếu ngoặc đóng dòng 6) và sai module path `src.pipelines.phase1` → `pipelines.phase1`. Trước khi sửa, entrypoint baseline không chạy được trên bất kỳ máy nào |
| Phát hiện lỗi schema | `src/pipelines/phase1.py` | Báo `validate_clean_schema` đòi các cột `id`/`abstract` không tồn tại trong cleaned dataframe, khiến hàm luôn raise. Chủ sở hữu file đã sửa theo đề xuất |
| Bảo mật repo | `.env.example` | Phát hiện API key thật bị dán vào `.env.example` (file được git track). Chuyển key sang `.env` đã được `.gitignore` chặn và trả `.env.example` về bản trống |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ---------------- |
| Sinh evaluation set đóng băng | `testset.py` | 24 câu, 6 paper × 4 loại | `python -c "import json;print(len(json.load(open('data/eval/test_set.json'))))"` |
| Dựng quality gate 8 check | `quality.py` | baseline PASS 8/8, corrupted FAIL 5/8 | So `data/quality/baseline_quality.json` với `corrupted_quality.json` |
| Dựng freshness monitor | `quality.py` | baseline FRESH, corrupted STALE (2 dòng) | `data/quality/freshness_report_corrupted.json` |
| Sinh 6 kịch bản corruption có log | `corruption.py` | 24 → 23 dòng, coverage ground truth 1.0 | `data/results/corruption_log.json` |
| Ghép flow phase 2 | `corruption_flow.py` | corrupted + repaired metrics/answers/quality/freshness/report | `PYTHONIOENCODING=utf-8 python script/run_corruption_flow.py` |
| Viết test tự động | `tests/` | 60 passed | `python -m pytest tests/ -q` |

Một output cụ thể mà phần việc của tôi tạo ra hoặc giúp xác minh:

`data/reports/corruption_report.md` — bảng so sánh ba trạng thái được sinh hoàn toàn từ file JSON thật, kèm phần diễn giải tự động nêu rõ mỗi metric sụt bao nhiêu và repair khép lại được bao nhiêu phần khoảng cách. Nếu repair chưa phục hồi hết, báo cáo ghi thẳng "still X below baseline" thay vì làm tròn thành "đã phục hồi".

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bài lab phải chứng minh dữ liệu hỏng làm giảm chất lượng RAG. Muốn vậy cần ba thứ: một thước đo không đổi giữa ba trạng thái, một cơ chế phát hiện dữ liệu hỏng, và một cách gây lỗi vừa có chủ đích vừa đo được. Phần của tôi phụ trách cả ba.

### Cách triển khai

**Evaluation set.** `retrieval/qa.py` (code starter, không sửa) chọn field metadata để trả lời bằng cách so khớp chuỗi trên câu hỏi đã lowercase, theo đúng thứ tự: `who authored`/`list the authors` → `authors_joined`; `when was`/`publication date`/`published on` → `published`; `what categories` → `categories_joined`; không khớp gì → `first_sentence(summary)`. Ngoài ra `answer_question` lấy khóa exact-lookup bằng regex `'([^']+)'`.

Vì vậy mỗi câu hỏi được sinh sao cho chứa **đúng một** cụm khóa và bọc tiêu đề trong dấu nháy đơn, còn `ground_truth` được tính bằng **chính phép trích đó** trên document đúng. Hệ quả: retrieval trúng thì token F1 = 1.0, retrieval trượt thì tụt hẳn — metric đo chất lượng dữ liệu chứ không đo cách diễn đạt. Paper nào có dấu nháy đơn trong tiêu đề đều bị loại, vì regex sẽ cắt cụt khóa lookup và làm hỏng thầm lặng.

**Quality gate.** 8 check, mỗi check ghi lại `observed` và `expected` để khi FAIL có thể lần ngược về dòng dữ liệu, thay vì chỉ trả về true/false. Ngưỡng `summary_min_length` đặt bằng 100 ký tự để khớp đúng quy tắc loại record của `cleaning.py` — lệch ngưỡng sẽ báo lỗi oan trên dữ liệu sạch hợp lệ.

**Freshness.** `is_fresh` định nghĩa là `stale_rows == 0`, không phải "ngày mới nhất còn trong ngưỡng". Lý do: filter nguồn Crossref chỉ lấy paper trong 180 ngày, nên dữ liệu sạch không thể có dòng stale; định nghĩa theo ngày mới nhất sẽ bỏ lọt corruption chỉ làm cũ một phần dữ liệu. Ngày không parse được cũng được đếm riêng và không bao giờ tính là "tươi".

**Corruption.** Sáu kịch bản, và điểm mấu chốt là hàm nhận thêm `target_paper_ids` để **ưu tiên làm hỏng đúng những paper mà test set hỏi tới**. Riêng `drop_latest_records` là kịch bản duy nhất có thể làm `retrieval_hit_rate` thay đổi, vì các kịch bản còn lại chỉ bóp méo nội dung chứ không gỡ document khỏi index — nên nó chọn paper mới nhất **trong số paper được đánh giá**. Sau mỗi lần sửa `title` hoặc `summary`, cột `text_for_embedding` được dựng lại đúng định dạng của `cleaning.py`; nếu lệch định dạng thì mức sụt sẽ đến từ chênh lệch format chứ không phải từ dữ liệu hỏng.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | Cleaned dataframe với các cột `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding`, `summary_chars` |
| Output | `test_set.json`; `*_quality.json`; `freshness_report*.json`; `phase1_report.md`; `corruption_report.md`; `corruption_log.json`; corrupted/repaired dataset, index, metrics, answers |
| Module phụ thuộc | `ingestion/cleaning.py` (schema đầu vào), `retrieval/qa.py` (cách trích đáp án), `retrieval/index.py`, `evaluation/metrics.py` |
| Module sử dụng output | `pipelines/phase1.py` dùng test set + quality + freshness + report |
| Điều kiện lỗi cần xử lý | Thiếu cột contract → raise kèm tên cột; dataset quá nhỏ → raise; không paper nào đủ điều kiện → raise; thiếu artifact baseline → `require_baseline_artifacts` chặn phase 2 |

### Cách xác minh

```bash
PYTHONIOENCODING=utf-8 REFRESH_TEST_SET=1 python script/run_phase1.py
PYTHONIOENCODING=utf-8 python script/run_corruption_flow.py
python -m pytest tests/ -q
```

- **Kết quả mong đợi:** baseline PASS mọi quality check và FRESH; corrupted làm ít nhất một quality check FAIL, freshness STALE, và cả bốn metric giảm; repaired quay lại đúng mức baseline.
- **Kết quả thực tế:** đúng như mong đợi. Baseline 1.0000/1.0000/0.9583/4.9167 → corrupted 0.6667/0.6737/0.7083/3.9167 → repaired quay lại **chính xác** 1.0000/1.0000/0.9583/4.9167. Quality PASS 8/8 → FAIL 5/8 → PASS 8/8. Freshness FRESH → STALE → FRESH. `pytest`: 60 passed.
- **Artifact/log:** `data/results/`, `data/quality/`, `data/reports/`. Không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn nội dung cho `ground_truth` của evaluation set.
- **Các phương án đã cân nhắc:** (a) Viết câu trả lời chuẩn bằng ngôn ngữ tự nhiên do người soạn; (b) Sinh `ground_truth` bằng đúng phép trích mà `qa._extract_answer` sẽ dùng trên document đúng.
- **Phương án đã chọn:** (b).
- **Lý do:** Với (a), token F1 luôn dưới 1.0 kể cả khi retrieval hoàn toàn chính xác, vì cách diễn đạt khác nhau. Khoảng sụt sau corruption khi đó lẫn hai nguồn: dữ liệu hỏng và độ vênh ngôn ngữ, không tách được. Với (b), baseline đạt trần 1.0 nên **mọi mức sụt đều quy về chất lượng dữ liệu**. Đánh đổi là baseline bão hòa, không còn dư địa để đo cải tiến retrieval — nhưng bài lab này đo tác động của dữ liệu chứ không tối ưu retrieval.
- **Bằng chứng quyết định phù hợp:** `mean_token_f1` baseline 1.0000, corrupted 0.6737, repaired trở lại đúng 1.0000. Mức sụt 0.3263 quy hoàn toàn về 6 paper bị corrupt, đối chiếu được qua `corruption_log.json`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `SyntaxError: '(' was never closed` tại `script/run_phase1.py` dòng 6; sau khi sửa lại gặp tiếp `UnicodeEncodeError: 'charmap' codec can't encode character 'ợ'` tại `src/pipelines/phase1.py` dòng 65.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py` trên Windows.
- **Nguyên nhân gốc:** Hai nguyên nhân độc lập. (1) `run_phase1.py` thiếu một dấu đóng ngoặc và import sai đường dẫn module — `pyproject.toml` khai `package-dir = {"" = "src"}` nên module đúng là `pipelines.phase1`, không có tiền tố `src.`. (2) Pipeline in thông báo tiếng Việt ra stdout, trong khi console Windows mặc định dùng codepage cp1252 không mã hóa được ký tự tiếng Việt.
- **Cách xử lý:** Sửa dấu ngoặc và đường dẫn import. Với lỗi encoding, chạy pipeline với `PYTHONIOENCODING=utf-8`.
- **Cách xác minh sau khi sửa:** `PYTHONIOENCODING=utf-8 python script/run_phase1.py` chạy hết, in `Hoàn thành Pipeline Phase 1!` và sinh đủ artifact trong `data/`.
- **Điều học được:** Lỗi thứ hai không phải lỗi logic mà là lỗi môi trường, và nó chỉ lộ ra khi thực sự chạy trên máy khác. Một pipeline "chạy được trên máy tôi" mà crash trên console mặc định của hệ điều hành thì vẫn là chưa chạy được — vì người chấm bài sẽ chạy trên máy của họ.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

`fetch_source_records` gọi Crossref REST API với query và filter lấy từ `Settings`, lưu nguyên response HTTP vào `data/raw/crossref_response.json` rồi parse thành danh sách `PaperRecord` lưu tiếp vào `crossref_records.json`. Hai file này là điểm khôi phục: mọi bước sau đều dựng lại được từ đây mà không cần gọi API lần nữa. `build_clean_dataframe` nhận danh sách record đó, loại bản ghi thiếu tiêu đề hoặc summary dưới 100 ký tự, chuẩn hóa tác giả và chủ đề thành chuỗi, parse ngày xuất bản để tính `age_days`, khử trùng theo `paper_id`, rồi ghép `text_for_embedding` theo khuôn `Title / Authors / Categories / Summary`. `LocalEmbeddingIndex.build` mã hóa đúng cột đó bằng MiniLM thành vector 384 chiều, nạp vào một collection ChromaDB riêng kèm metadata, và ghi manifest ra `data/embeddings/`. Điểm quan trọng: mỗi trạng thái dùng một collection riêng (`papers-baseline`, `papers-corrupted`, `papers-repaired`) nên index cũ không bị ghi đè.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Mỗi mẫu trong test set gồm câu hỏi, `ground_truth` và `ground_truth_doc_ids`. Khi đánh giá, agent lấy top-4 document và trả lời; evaluator so danh sách `paper_id` lấy được với `ground_truth_doc_ids` — trùng ít nhất một là tính `retrieval_hit`. Đây là thước đo tầng **tìm kiếm**: nó chỉ hỏi "có lấy đúng tài liệu không", không quan tâm câu trả lời. Sau đó `ground_truth` được đem so với câu trả lời theo hai cách: token F1 đo mức trùng từ vựng, còn LLM judge chấm 1–5 và phán đúng/sai về bản chất. Đây là thước đo tầng **trả lời**. Tách hai tầng cho phép chỉ ra lỗi nằm ở đâu: hit rate tụt nghĩa là retrieval hỏng, còn hit rate giữ nguyên mà token F1 tụt nghĩa là tài liệu vẫn tìm ra được nhưng nội dung bên trong đã hỏng.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality check hỏi "dữ liệu có đúng hình dạng không" — đủ cột, `paper_id` không rỗng và không trùng, tiêu đề không rỗng, summary đủ dài. Freshness hỏi "dữ liệu có còn kịp thời không" — so `age_days` với ngưỡng 180 ngày. Khác biệt về bản chất: một bản ghi có thể hoàn toàn hợp lệ về cấu trúc nhưng đã cũ ba năm, và ngược lại một bản ghi vừa xuất bản hôm qua vẫn có thể rỗng summary. Trong thí nghiệm này hai tín hiệu bắt hai loại lỗi khác nhau: `blank_summary` và `duplicate_rows` làm quality FAIL, còn `stale_published_date` chỉ freshness bắt được.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì thí nghiệm chỉ có nghĩa khi **biến duy nhất thay đổi là dữ liệu**. Nếu sinh lại test set cho từng trạng thái thì câu hỏi và đáp án chuẩn cũng đổi theo, và khi metric tụt sẽ không phân biệt được là do dữ liệu hỏng hay do bộ câu hỏi mới khó hơn. Cùng lý do đó, ba lần chạy phải dùng chung evaluator, chung `top_k` và chung LLM judge. `generate_corruption_report` in cảnh báo nếu ba lần chạy có số `samples` khác nhau, vì đó là dấu hiệu test set đã bị đổi giữa chừng.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Dựa trên bốn bằng chứng cùng lúc, không phải một. Thứ nhất, `data/clean/papers_clean_repaired.csv` quay lại đủ 24 dòng. Thứ hai, `data/quality/repaired_quality.json` trở lại PASS 8/8 và `freshness_report_repaired.json` trở lại FRESH. Thứ ba, `data/results/repaired_metrics.json` khớp đúng baseline ở cả bốn chỉ số — 1.0000 / 1.0000 / 0.9583 / 4.9167. Thứ tư, và quan trọng nhất về mặt phương pháp: repair được thực hiện bằng cách chạy lại `build_clean_dataframe` trên raw snapshot, chứ không sửa tay dataset hỏng. Nếu chỉ nhìn metric mà không nhìn cách repair thì không phân biệt được phục hồi thật với việc ghi đè số liệu cho đẹp.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | 8/24 câu trượt. Chỉ do 2 document bị xóa khỏi index — bóp méo nội dung không làm document biến mất |
| `mean_token_f1`      | 1.0000 | 0.6737 | 1.0000 | Sụt gần bằng retrieval, cho thấy khi lấy nhầm document thì câu trả lời sai theo |
| `judge_accuracy`     | 0.9583 | 0.7083 | 0.9583 | Sụt ít hơn retrieval: một số câu tuy lấy nhầm document nhưng vẫn được judge chấp nhận |
| `mean_judge_score`   | 4.9167 | 3.9167 | 4.9167 | Mất trọn 1.0 điểm trên thang 5 |
| Quality checks         | PASS 8/8 | FAIL 5/8 | PASS 8/8 | FAIL ở `paper_id_unique`, `summary_min_length`, `freshness_age_days` |
| Freshness status       | FRESH | STALE | FRESH | 2/23 dòng stale, ngày cũ nhất tụt về 2000-01-01 |

### Kết luận từ số liệu

1. Xóa 2 paper được đánh giá + nhân bản `paper_id` + làm rỗng summary → `paper_id_unique`, `summary_min_length`, `freshness_age_days` chuyển FAIL và freshness thành STALE → `retrieval_hit_rate` 1.0000 → 0.6667, `judge_accuracy` 0.9583 → 0.7083.
2. Chạy lại cleaning từ `data/raw/crossref_records.json` → quality trở lại PASS 8/8, freshness trở lại FRESH → cả bốn metric quay về đúng giá trị baseline, không sai lệch dù chỉ một chữ số.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records`. Đây là kịch bản duy nhất **gỡ hẳn document khỏi index**; năm kịch bản còn lại chỉ bóp méo nội dung, mà một document bị bóp méo thì vẫn tìm ra được. Bằng chứng trực tiếp: ở lần chạy đầu tiên, `drop_latest_records` xóa 2 paper không nằm trong test set, và `retrieval_hit_rate` giữ nguyên 1.0000 dù năm kịch bản kia vẫn chạm 5/6 paper được đánh giá. Sau khi đổi để nó ưu tiên xóa paper mà test set hỏi tới, hit rate mới tụt xuống 0.6667.

Kết quả nào khác với kỳ vọng ban đầu?

Kỳ vọng ban đầu là mọi corruption đều để lại dấu vết trong data quality report. Thực tế `inject_noise` và `truncate_title` **không kích hoạt bất kỳ check nào** — chúng vẫn kéo metric xuống nhưng hoàn toàn vô hình với quality gate. Đã kiểm tra bằng cách đối chiếu danh sách `failed_check_names` trong `corrupted_quality.json` với 6 loại corruption trong `corruption_log.json`: chỉ 3 loại để lại tín hiệu. Bài học là quality gate hiện tại phát hiện được dữ liệu *thiếu* và *trùng*, nhưng chưa phát hiện được dữ liệu *bị bóp méo*.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline — raw snapshot là thứ quyết định pipeline có sửa được hay không.** Lúc đầu tôi xem việc lưu `crossref_response.json` chỉ là bước phụ để audit. Đến pha repair mới thấy đó là điều kiện tiên quyết: vì có snapshot nên khôi phục chỉ là chạy lại đúng logic cleaning, và kết quả trùng khít baseline. Nếu repair bằng cách gọi lại Crossref thì corpus sẽ khác đi và ba trạng thái mất tính so sánh — nói cách khác, không có snapshot thì không có cách nào chứng minh repair thành công.

2. **Về data quality/observability — một quality gate chỉ phát hiện được đúng những gì nó được viết ra để hỏi.** Tôi tạo sáu kịch bản corruption nhưng chỉ ba kịch bản làm quality report FAIL. `inject_noise` và `truncate_title` vẫn kéo metric xuống mà không sinh bất kỳ tín hiệu nào. Bài học là "quality PASS" không đồng nghĩa với "dữ liệu tốt" — nó chỉ có nghĩa là dữ liệu vượt qua các câu hỏi mình đã nghĩ ra. Đây cũng là lý do tôi bắt mỗi check ghi lại `observed` và `expected` thay vì chỉ trả về true/false: khi FAIL còn lần ngược được về dòng dữ liệu, khi PASS còn biết nó đã kiểm cái gì.

3. **Về ảnh hưởng của dữ liệu tới RAG agent — không phải mọi lỗi dữ liệu đều tác động như nhau, và điều đó đo được.** Ở lần chạy đầu tiên, `retrieval_hit_rate` giữ nguyên 1.0000 dù năm kịch bản corruption đã chạm tới 5/6 paper được đánh giá. Nguyên nhân: chỉ kịch bản xóa document mới làm retrieval trượt, còn các kịch bản khác chỉ bóp méo nội dung nên tài liệu vẫn tìm ra được. Sau khi sửa để việc xóa nhắm đúng paper mà test set hỏi tới, hit rate mới tụt xuống 0.6667. Điều rút ra là phải phân biệt lỗi làm **mất** dữ liệu với lỗi làm **hỏng** dữ liệu: loại thứ nhất đánh vào tầng retrieval, loại thứ hai đánh vào tầng câu trả lời, và chúng để lại dấu vết khác nhau trên metric.

### Nếu có thêm thời gian

Một hướng cụ thể: thêm check phát hiện dữ liệu bị bóp méo vào quality gate — ví dụ theo dõi phân phối độ dài `summary` và tỉ lệ ký tự không phải chữ trong `text_for_embedding`, cảnh báo khi lệch quá ngưỡng so với snapshot trước. Đo hiệu quả bằng cách chạy lại đúng corruption flow hiện tại và kiểm tra `inject_noise` cùng `truncate_title` có làm quality FAIL hay không — hiện tại cả hai đều lọt.

[Bổ sung hướng cải thiện của riêng bạn nếu có.]

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hải Quân
**Ngày xác nhận:** 2026-08-06

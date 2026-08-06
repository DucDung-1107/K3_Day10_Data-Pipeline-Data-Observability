from __future__ import annotations
from core.config import load_settings

# Giả sử bạn chốt với nhóm sẽ có các hàm này từ các thư mục khác
# from ingestion.data_pipeline import fetch_raw_records, clean_records
# from retrieval.rag_pipeline import build_chroma_index
# from evaluation.evaluator import run_evaluation, generate_report

def main() -> None:
    # 1. Load settings (Bạn phụ trách)
    print("Loading settings...")
    settings = load_settings()
    
    # 2 & 3 & 4. Lấy dữ liệu và làm sạch (Vai trò 2 phụ trách)
    print(f"Bắt đầu luồng Vai trò 2. Lưu raw tại: {settings.paths.raw_records_json}")
    # raw_data = fetch_raw_records(settings)
    # clean_data = clean_records(raw_data, settings.paths.clean_json)
    
    # 5. Lập chỉ mục Chroma (Vai trò 3 phụ trách)
    print(f"Bắt đầu luồng Vai trò 3. Build index tại: {settings.paths.chroma_dir}")
    # index = build_chroma_index(clean_data, settings.paths.chroma_dir)
    
    # 6 & 7 & 8. Đánh giá chất lượng (Vai trò 4 phụ trách)
    print("Bắt đầu luồng Vai trò 4. Đánh giá RAG...")
    # eval_results = run_evaluation(index, settings)
    
    # 9 & 10. Tạo báo cáo (Bạn và Vai trò 4)
    print(f"Tạo báo cáo tại: {settings.paths.baseline_report}")
    # generate_report(eval_results, settings.paths.baseline_report)
    
    print("Hoàn thành Pipeline Phase 1!")

if __name__ == "__main__":
    main()
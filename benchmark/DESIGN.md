# Benchmark trước thực nghiệm

Theo BENCHMARK.md, GUIDE.md và RULES.md: `questions.jsonl` chứa **20 câu**
tiếng Anh theo ngôn ngữ corpus, có đáp án kỳ vọng, nguồn, trang PDF vật lý
(bắt đầu từ 1) và evidence trích nguyên văn từ văn bản đã chuẩn hóa.

## Phân chia và filter

- **Dev:** q01–q15, dùng để thử/chọn cấu hình.
- **Test:** q16–q20, chỉ đánh giá sau khi cố định cấu hình.
- **Filter:** q10 (`chapter=3`), q12/q15/q18 (`chapter=4`); q18 thuộc test.
  Chương được nêu trực tiếp trong câu hỏi, là input trước truy xuất.
- Test dành các nội dung kiểm soát tiền thuê, thặng dư tiêu dùng, trần lãi
  suất không ràng buộc, tín hiệu giá và dịch chuyển đồng thời cung/cầu y tá.
  Dev có các chủ đề lân cận trong cùng sách và chương, nên chưa phải đánh
  giá độc lập theo tài liệu. Chia trang/chủ đề giúp giảm trùng câu nhưng
  không loại hết rò rỉ về kiến thức.

Bộ câu hỏi/split được tạo ngày **2026-11-14**, trước khi chạy embedding,
retrieval hoặc đánh giá chiến lược. AI đã đọc test để soạn và kiểm chứng;
điều này là bước xây benchmark, không phải kết quả test dùng để chỉnh mô
hình. Sau khi bắt đầu thực nghiệm, không chỉnh cấu hình hoặc sửa câu hỏi
dựa trên kết quả test rồi báo như holdout độc lập. Nếu phải sửa, ghi lý do
và thay đổi, đồng thời tạo test mới nếu có thể theo RULES.md.

## Chọn chiến lược trước khi xem test

Giữ cùng corpus, embedding model, vector store, cosine và benchmark cho
A/B/C. So sánh A–B về chunking; B–C chỉ thay metadata filter. C không lọc
với câu không cung cấp filter.

Tiêu chí chọn trên **dev**: ưu tiên Evidence Hit@3, tiếp theo Hit@1;
nếu hòa, ưu tiên cấu hình có thời gian ingest thấp hơn trong cùng điều
kiện đo. Sau đó cố định cấu hình và báo test cho cả ba cấu hình, không
dùng test để chọn lại. Coherence, metadata, grounding và tài nguyên vẫn
phải được đánh giá/báo cáo đầy đủ theo GUIDE.md.

## Kiểm chứng và tái tạo

```powershell
python scripts/build_benchmark.py
python scripts/validate_benchmark.py
```

Lệnh build tái tạo đúng bộ câu hỏi đã soạn, không tự sinh câu hỏi mới.
Validation đối chiếu evidence với lần trích xuất mới từ PDF gốc và ghi
`results/benchmark_validation.json`. Đây là kiểm tra nội dung tồn tại và
cấu trúc; **không phải nhãn chấm thủ công của học viên**. Người học cần đọc
evidence cùng trang PDF để xác nhận đáp án, đơn vị, điều kiện và lỗi trích
xuất trước khi chạy. q16 tính thiếu hụt bằng 19.000 − 15.000 = 4.000.

Evidence có thể chứa xuống dòng hoặc ký tự trích xuất khác bản hiển thị.
Không tự sửa câu trích để tạo match. Các hình/bảng cần kiểm tra bố cục với
PDF; q04 giữ cả chú thích và bảng để có đơn vị triệu gallon.

Một chunk chỉ hit khi đúng nguồn/trang và chứa đủ evidence hoặc bằng
chứng tương đương được người chấm xác nhận. Nếu có nguồn/trang hợp lệ khác,
ghi alternative gold và chấp nhận nó; không mặc định chỉ trang gold đã liệt
kê mới đúng. Ví dụ đáp án cân bằng y tá q11 cũng xuất hiện tại trang PDF
104. Không dùng phép match chuỗi để suy ra grounding hay coherence.

Ghi công phần trích sách: **Principles of Economics 3e, OpenStax, Rice
University. Access for free at openstax.org.** Điều khoản CC BY-NC-SA 4.0
và ngoại lệ được ghi trong `data/manifest.json` và trang PDF 4.

Retrieval đã được chạy sau khi chốt bộ câu hỏi; xem `report/individual/2A202603906_CaoMinhQuang.md`,
trace và metric dev/test. Nhãn nội dung đã được Codex (AI) điền và người
dùng xác nhận trong `results/manual/`; phương pháp và giới hạn được công bố
trong báo cáo, không khẳng định học viên chấm lại độc lập. Công cụ AI hỗ trợ
soạn câu hỏi, đọc evidence và viết validation; học viên cần ghi việc sử
dụng AI và cách kiểm tra trong báo cáo theo RULES.md.

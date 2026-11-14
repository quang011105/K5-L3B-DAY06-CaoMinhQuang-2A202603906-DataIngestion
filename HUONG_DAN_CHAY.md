# Data Ingestion Engineering — Cao Minh Quang

**MSSV:** 2A202603906 · **Lớp:** L3B · **Ngày thực nghiệm:** 14/11/2026

Bài làm xây pipeline truy xuất kiến thức cung–cầu từ sách *Principles of
Economics 3e* (OpenStax), dùng **BGE-M3 local + Chroma**. So sánh ba cấu
hình chunking/filter trên **48 trang nội dung** và **20 câu hỏi**.

## Bắt đầu đọc từ đâu?

| Bạn cần | Mở file |
|---|---|
| Cài đặt, chạy và hiểu cấu trúc bài làm | HUONG_DAN_CHAY.md này |
| Kết quả, phân tích đủ 5 khía cạnh, giới hạn | [Báo cáo cá nhân](report/individual/2A202603906_CaoMinhQuang.md) |
| Checklist bài nộp | [SUBMISSION.md](SUBMISSION.md) |
| Nội dung giới thiệu đề bài ban đầu | [README.md](README.md) |

`src/` là code bài làm hiện tại. `starter/` là khung PostgreSQL mẫu của đề,
giữ để tham khảo; **không cần chạy Docker hoặc theo setup trong starter
để chạy phương án Chroma này**.

## Cấu trúc bài nộp

```text
STUDENT.md                             Thông tin học viên
README.md                              Giới thiệu đề bài gốc, giữ nguyên khi clone
HUONG_DAN_CHAY.md                       Hướng dẫn cài đặt/chạy bài làm: file này
src/                                   Code pipeline với AI hỗ trợ
scripts/                               Chuẩn bị corpus, benchmark và audit
configs/strategies.json                 Tham số A/B/C và model revision
requirements-pipeline.txt               Dependencies
data/
  principles-economics-3e_-_WEB.pdf      Sách gốc do học viên cung cấp
  manifest.json                        Nguồn, quyền, snapshot, trang được chọn
  processed/pages.jsonl                Văn bản chuẩn hóa, giữ nguồn/trang
benchmark/
  questions.jsonl                      20 câu hỏi, split và gold evidence
  DESIGN.md                            Chi tiết thiết kế benchmark
artifacts/experiment_log.csv            Giả thuyết, cấu hình, kết quả A/B/C
results/                               Metric, trace, chunk, log, nhãn audit
report/individual/
  2A202603906_CaoMinhQuang.md            Báo cáo phân tích chính
```

GUIDE.md, BENCHMARK.md, RULES.md, RUBRIC.md và `starter/` là tài liệu/khung
đề bài. `.local/` chứa Chroma, cache embedding và ảnh kiểm tra ở máy chạy;
thư mục này được gitignore, cần ingest để tái tạo.

## 1. Cài môi trường

Cần **Python 3.12**, đủ RAM/dung lượng chạy BGE-M3 trên CPU và mạng cho lần
tải dependencies/model đầu tiên. Chạy từ **thư mục gốc repo**:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-pipeline.txt
```

Không cần API key. Model `BAAI/bge-m3` pin revision
`5617a9f61b028005a4858fdac845db406aefb181`, dense 1024 chiều, float32 CPU.
Query/document cùng encoder, không prefix, chuẩn hóa L2; batch 8, seed 42,
4 threads. Context 8192 token; từ chối đầu vào quá dài thay vì âm thầm
truncate. Phiên bản đã chạy xem [environment.json](results/environment.json).

## 2. Dữ liệu và benchmark

PDF nằm tại `data/principles-economics-3e_-_WEB.pdf`. Chọn trang PDF
**64–93** (chương 3) và **102–119** (chương 4), tổng **48 trang** trình bày
chính; loại bìa/mục lục/trang mở chương/bài tập. Dùng số trang vật lý PDF
bắt đầu từ 1: PDF 64 tương ứng trang in 48, không dùng lẫn hai hệ.

Trang PDF 4 ghi **CC BY-NC-SA 4.0**, kèm điều kiện ghi công, phi thương mại,
chia sẻ cùng loại giấy phép và ngoại lệ về nhãn hiệu. Ghi công:
**Principles of Economics 3e, OpenStax, Rice University.
Access for free at openstax.org.**
URL tham chiếu: https://openstax.org/details/books/principles-economics-3e

[Manifest](data/manifest.json) ghi snapshot/checksum, quyền và quy tắc tính
từng trang. PyMuPDF trích text, chuẩn hóa NFC/whitespace trong dòng, giữ
dòng/nguồn/trang. Không OCR hay tự đoán ký tự; hình không tự chuyển thành
mô tả, bảng cần đối chiếu PDF. Ngày kiểm tra local 14/11/2026, chưa xác
minh ngày/URL tải gốc.

Dữ liệu và benchmark đã có trong repo. Khi cần tái tạo đúng bản đã soạn:

```powershell
python scripts/prepare_corpus.py
python scripts/build_benchmark.py
python scripts/validate_benchmark.py
```

Benchmark có **15 dev / 5 test**, chia trước thực nghiệm; 4 câu filter,
gồm 1 câu test. Giữ nguyên benchmark khi tái lập; chi tiết trong
[benchmark/DESIGN.md](benchmark/DESIGN.md). `data/format-example.json`
chỉ là ví dụ schema của đề, không phải corpus/benchmark dùng thực nghiệm.

## 3. Ingest và chạy dev/test

| Strategy | Chunking | Kích thước / overlap ký tự | Filter |
|---|---|---|---|
| A | Cửa sổ cố định | 1000 / 100 | Không |
| B | Ưu tiên ranh giới câu/dòng/đoạn | Tối đa 1000 / 0 | Không |
| C | Chính xác cùng chunks/vectors như B | Tối đa 1000 / 0 | `chapter` nếu câu hỏi cung cấp |

Cùng corpus/model/store/cosine. B/C dùng câu/dòng bổ trợ vì PDF không giữ
đủ đoạn, không phục hồi hoàn hảo cấu trúc sách. Chunk giữ nguyên substring
và offset, không vượt trang. Metadata gồm `document_id`, `source`, `page`,
`chapter`, `chapter_title`, `language` và offsets; chương lấy từ bookmarks.
Không đưa gold/đáp án vào query hoặc filter.

Lần đầu chưa có model trong cache:

```powershell
python -m src.run ingest --allow-model-download
python -m src.run dev
```

Có model cache thì dùng `python -m src.run ingest` để chạy offline.
Chroma lưu `.local/chroma/`, collections `economics_a`, `economics_b`,
`economics_c`; cosine HNSW ANN, ef_search=100, ef_construction=100,
max_neighbors=16. Không tuyên bố exact search. ID chunk ổn định, ingest
refresh toàn snapshot, upsert rồi xóa ID lỗi thời. Cache embedding ở
`.local/embeddings/`; B/C dùng chung, không encode lặp. Lỗi không fallback mock.

**Chọn cấu hình trước test:** ưu tiên dev Evidence Hit@3, rồi Hit@1, rồi
thời gian ingest. Với thí nghiệm mới chưa có freeze:

```powershell
python -m src.run freeze
python -m src.run test
```

**Repo hiện đã có [frozen_selection.json](results/frozen_selection.json),
chọn A trước test.** Tái lập bản này: sau ingest/dev chỉ chạy
`python -m src.run test`; không chạy lại freeze vì lệnh từ chối ghi đè.
Nếu đổi code/config/corpus/benchmark, phải lưu phiên bản thí nghiệm mới;
không chỉnh theo test rồi báo như holdout độc lập.

Kiểm tra logic:

```powershell
python -m unittest discover -s tests -v
```

Model có thể cần vài phút chạy CPU. Chi phí dịch vụ trả phí **0 USD**;
điện/RAM chưa đo. Sự cố thread Transformers kiểm tra mạng khi nạp model
local và cách ép offline ghi trong [runtime_notes.json](results/runtime_notes.json).

## 4. Đọc kết quả

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Chunks |
|---|---|---|---|---|---:|
| A | 9/15 | 13/15 | 2/5 | 3/5 | 171 |
| B | 8/15 | 11/15 | 1/5 | 2/5 | 169 |
| C | 8/15 | 11/15 | 1/5 | 2/5 | 169 |

Đây là raw metric: đúng nguồn/trang và đủ nguyên evidence trong một chunk
sau chuẩn hóa whitespace, có xét alternative gold đã khai báo. Không phải
độ chính xác câu trả lời LLM. Báo cáo phân tích evidence tương đương và
lỗi match chuỗi; không ghi đè raw metric. A được chọn từ dev, không chọn lại từ test.

| Muốn kiểm tra | Artifact |
|---|---|
| Metric theo split | [dev_metrics.json](results/dev_metrics.json), [test_metrics.json](results/test_metrics.json) |
| Top-3, text, score, metadata, gold | [dev_traces.jsonl](results/dev_traces.jsonl), [test_traces.jsonl](results/test_traces.jsonl) |
| Count/token/độ dài/thời gian/cache/nạp lại | [ingest_stats.json](results/ingest_stats.json) |
| Chunk và offset | `results/chunks_A.jsonl`, `chunks_B.jsonl`, `chunks_C.jsonl` |
| Coherence: 10 vị trí × 3 cấu hình | [coherence_samples.jsonl](results/manual/coherence_samples.jsonl) |
| Metadata/filter/grounding: 5 test × 3 cấu hình | [test_audit.jsonl](results/manual/test_audit.jsonl) |
| Kiểm chứng corpus/evidence | [corpus_extraction_audit.json](results/corpus_extraction_audit.json), [benchmark_validation.json](results/benchmark_validation.json) |
| Nhận định audit AI chi tiết | [REVIEW.md](results/ai_audit/REVIEW.md) |

Tổng 60 trace/180 bản ghi top-3; nạp lại không tăng count. A/B ingest
khoảng 203/181 giây, C khoảng 1 giây vì cache B; không coi là so cold-start
độc lập. Phân tích đầy đủ nằm trong
[báo cáo cá nhân](report/individual/2A202603906_CaoMinhQuang.md).

Nhãn nội dung do **Codex (AI)** đọc/đối chiếu nguồn, có lý do từng mẫu;
người dùng đã xác nhận ngày 14/11/2026 (`human_confirmed=true`). Không
khẳng định học viên đã chấm lại độc lập. AI hỗ trợ code/benchmark và đã
thấy điểm nên audit không mù, có thiên lệch. `results/ai_audit/` giữ đề
xuất trước xác nhận; `results/manual/` giữ nhãn hiện tại và xác nhận.
Không suy coherence/grounding từ Hit@3. Các script audit chỉ tái ghi
nhãn đã soạn, không phải một lượt chấm độc lập; không cần chạy lại để
xem kết quả. Script apply từ chối ghi đè nhãn đã xác nhận.

## 5. Trước khi nộp

Đọc [SUBMISSION.md](SUBMISSION.md), kiểm tra [STUDENT.md](STUDENT.md),
[báo cáo](report/individual/2A202603906_CaoMinhQuang.md), manifest/corpus,
benchmark, experiment log và artifacts. Commit bài làm là `f959715`, ghi
trong `STUDENT.md`; nộp link theo kênh lớp là bước riêng. Không commit
`.env`, key, môi trường ảo hoặc `.local/`.

Tài liệu đề bài để tra cứu: [GUIDE.md](GUIDE.md), [BENCHMARK.md](BENCHMARK.md),
[RULES.md](RULES.md), [RUBRIC.md](RUBRIC.md), [CHECKPOINTS.md](CHECKPOINTS.md).
Nội dung giới thiệu ban đầu giữ nguyên tại [README.md](README.md).
Hướng dẫn PostgreSQL nguyên bản tại [starter/README.md](starter/README.md)
chỉ dành cho phương án starter.

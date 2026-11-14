# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

- **Họ và tên:** Cao Minh Quang
- **MSSV:** 2A202603906
- **Lớp:** L3B
- **Ngày thực nghiệm:** 14/11/2026
- **Repo:** https://github.com/quang011105/K5-L3B-DAY06-CaoMinhQuang-2A202603906-DataIngestion

## Dữ liệu và pipeline

### Chủ đề, nguồn và quyền sử dụng

Bài thực hành xây kho truy xuất kiến thức **cung–cầu trong thị trường hàng
hóa, lao động và tài chính**, từ sách *Principles of Economics 3e*, OpenStax,
Rice University. Học viên cung cấp file `data/principles-economics-3e_-_WEB.pdf`,
gồm **995 trang vật lý**. URL tham chiếu ghi trong sách:
https://openstax.org/details/books/principles-economics-3e

Trang PDF 4 của bản sử dụng ghi **CC BY-NC-SA 4.0**, kèm điều kiện ghi
công, phi thương mại, chia sẻ cùng loại giấy phép và ngoại lệ về nhãn hiệu.
Ghi công: **Principles of Economics 3e, OpenStax, Rice University.
Access for free at openstax.org.**

Corpus chọn **48 trang nội dung**, đáp ứng tối thiểu 30 trang:

| Chương | Trang PDF, tính cả hai đầu | Số trang |
|---|---|---:|
| 3 — Demand and Supply | 64–93 | 30 |
| 4 — Labor and Financial Markets | 102–119 | 18 |

Chỉ tính phần trình bày chính, gồm hình/bảng phục vụ nội dung; loại bìa,
mục lục, trang mở chương, thuật ngữ/tóm tắt/bài tập cuối chương và các
trang ngoài phạm vi. Không áp dụng ngưỡng 1.500 ký tự dành cho nguồn không
phân trang để thay quy tắc PDF. Văn bản chuẩn hóa có **139.066 ký tự**,
gồm header/footer giữ lại. Số trang trong corpus/benchmark là số vật lý
PDF, bắt đầu từ 1; PDF 64 tương ứng trang in 48.

[Manifest](../../data/manifest.json) ghi nguồn, quyền, danh sách trang, số
ký tự, kích thước file và SHA256 của snapshot. Ngày kiểm tra local là
14/11/2026; ngày và URL tải gốc chưa được xác minh độc lập.

### Chuẩn hóa và giới hạn xử lý

Python/PyMuPDF trích text từng trang, chuẩn hóa Unicode NFC, gom khoảng
trắng trong dòng và giữ ranh giới dòng. Chunk giữ nguyên substring và
offset trong trang để truy vết. Không OCR, không tự đoán ký tự hay phục
hồi từ ngắt dòng. Audit 48 trang chọn không có trang rỗng hoặc U+FFFD.
Một số ký tự đặc biệt hiển thị khác khi xuất terminal, nên vẫn đối chiếu
PDF khi kiểm chứng evidence.

Hình không tự chuyển thành mô tả; bảng có thể bị trải thành các dòng.
Audit đã xem trực quan PDF 88, 90, 116–119 để đối chiếu bố cục, định nghĩa
và hình y tá. Chia theo trang có thể làm mất ngữ cảnh nối trang, như bảng
ở PDF 67–68. Dữ liệu tại [pages.jsonl](../../data/processed/pages.jsonl),
log tại [corpus_extraction_audit.json](../../results/corpus_extraction_audit.json),
script tại [prepare_corpus.py](../../scripts/prepare_corpus.py).

### Model, vector store và cách chạy

| Thành phần | Cấu hình thực nghiệm |
|---|---|
| Python | 3.12.0 |
| Embedding | BAAI/bge-m3, dense local CPU, float32, 1024 chiều |
| Revision | `5617a9f61b028005a4858fdac845db406aefb181` |
| Thư viện | Sentence Transformers 5.4.1; Torch 2.9.0; PyMuPDF 1.27.2.3 |
| Query/document | Cùng encoder, không prefix, chuẩn hóa L2; batch 8 |
| Context | 8192 token; từ chối đầu vào vượt giới hạn, không âm thầm truncate |
| Seed/CPU | Seed 42, 4 threads |
| Store | Chroma 1.5.9 PersistentClient, lưu `.local/chroma/` |
| Search | Cosine HNSW ANN; ef_search=100, ef_construction=100, max_neighbors=16 |
| Collections | `economics_a`, `economics_b`, `economics_c` |
| Chi phí | Dịch vụ trả phí 0 USD; chưa đo điện/tài nguyên local |

Dùng embedding thật, store lưu bền vững và hỗ trợ metadata filter. Không
dùng vector mock hoặc phép tính Python thay vector store. Chroma quản lý
lưu trữ của nó, không tự quản SQLite thay vector database. PostgreSQL
starter là tùy chọn, không dùng cho thực nghiệm này. Code bài làm ở `src/`
tại root, đúng vị trí SUBMISSION.md cho phép.

Sau khi cài `requirements-pipeline.txt`, chạy từ root:

```powershell
python scripts/prepare_corpus.py
python scripts/build_benchmark.py
python scripts/validate_benchmark.py
python -m src.run ingest
python -m src.run dev
python -m src.run freeze
python -m src.run test
python -m unittest discover -s tests -v
```

Lần đầu thiếu model cache, dùng `ingest --allow-model-download` trên máy
có mạng; mặc định ép offline. `freeze` chỉ chạy khi chưa có lựa chọn đã cố
định; repo hiện đã có freeze của lần thực nghiệm này nên không ghi đè.
Xem hướng dẫn setup tại [HUONG_DAN_CHAY.md](../../HUONG_DAN_CHAY.md).

Lần ingest đầu, thread chuyển đổi trọng số Transformers thử truy cập mạng
và bị chặn WinError 10013; trọng số local vẫn nạp và tạo embedding thật.
Các lệnh sau đặt Hugging Face/Transformers offline trước import. Không
đổi model hay fallback mock. Sự cố ghi trong
[runtime_notes.json](../../results/runtime_notes.json); lỗi pipeline được
ghi vào `results/pipeline_errors.log`.

ID chunk là SHA256 từ nguồn/trang/cấu hình/offset/text. Khi refresh toàn
snapshot, upsert ID hiện hành rồi xóa ID lỗi thời trong collection do
pipeline quản lý. Nạp lại giữ số lượng: **A 171→171, B 169→169, C 169→169**.
Dev/test mở store ở process sau ingest, truy xuất được dữ liệu lưu trên
đĩa. Ba test logic đã qua, kiểm tra coverage/offset, evidence và alternative
gold, persistence/filter/upsert/xóa chunk lỗi thời. Vector tổng hợp chỉ
dùng trong test logic store, không dùng làm embedding benchmark.

### Metadata

| Trường | Kiểu | Nguồn và tác dụng |
|---|---|---|
| `document_id` | string | ID snapshot nguồn trong manifest |
| `source` | string | Đường dẫn tương đối đến PDF |
| `page` | integer | Trang PDF vật lý để mở đúng evidence |
| `chapter` | integer | 3 hoặc 4 từ bookmarks, dùng filter |
| `chapter_title` | string | Tên chương từ bookmarks |
| `language` | string | `en`, ngôn ngữ quan sát từ nguồn |
| `start_char`, `end_char` | integer | Ranh giới substring trong trang chuẩn hóa |

`chapter` có hai giá trị phân biệt được từ nguồn. Chỉ lọc khi chương đã
nêu trong câu hỏi trước truy xuất, không lấy từ gold/đáp án. `page` và
offset giúp truy vết; metadata đầy đủ không tự bảo đảm evidence liên quan.

## Cấu hình và benchmark

### Ba cấu hình và giả thuyết

| Cấu hình | Chunking | Kích thước tối đa | Overlap | Filter |
|---|---|---:|---:|---|
| A | Cửa sổ ký tự cố định | 1000 | 100 | Không |
| B | Ưu tiên ranh giới đoạn/câu/dòng ngắn | 1000 | 0 | Không |
| C | Chính xác cùng chunks/vectors như B | 1000 | 0 | `chapter` khi câu hỏi cung cấp |

PDF ít giữ dòng trống giữa đoạn nên B/C dùng ranh giới câu/dòng bổ trợ,
hard split khi cần; không tuyên bố phục hồi hoàn hảo cấu trúc sách. A–B
thay cấu hình chunking; B–C chỉ thay filter. Giữ cùng corpus, model,
revision, store, cosine, bộ câu hỏi và định nghĩa metric.

Giả thuyết trước truy xuất: A đơn giản nhưng dễ cắt evidence; B có thể
giữ ý tốt hơn; C có thể loại nhiễu ngoài phạm vi chương. C chạy không lọc
với câu không có filter. Tham số nằm trong
[strategies.json](../../configs/strategies.json); giả thuyết/kết quả nằm
trong [experiment_log.csv](../../artifacts/experiment_log.csv).

### Câu hỏi, gold và lựa chọn trên dev

[questions.jsonl](../../benchmark/questions.jsonl) có **20 câu tiếng Anh**:
**15 dev** q01–q15 và **5 test** q16–q20, chia trước chạy embedding/retrieval.
Có câu trực tiếp, diễn đạt lại và điều kiện/ngoại lệ. **4 câu có filter**:
q10 chương 3, q12/q15/q18 chương 4; q18 thuộc test. Mỗi câu có đáp án,
nguồn, trang PDF và evidence. q11 có alternative gold PDF 104 ngoài PDF 103.

Evidence được kiểm tra với lần trích xuất mới từ PDF gốc, **20/20 khớp**,
ghi trong [benchmark_validation.json](../../results/benchmark_validation.json).
Match chứng minh evidence tồn tại, không thay đánh giá đủ điều kiện hay
grounding. Cách chia/kiểm chứng ghi trong
[benchmark/DESIGN.md](../../benchmark/DESIGN.md).

Tiêu chí chọn chốt trước test: ưu tiên **dev Evidence Hit@3**, tiếp theo
**dev Hit@1**, nếu hòa thì thời gian ingest đo được. **Chọn A trên dev**,
freeze lúc **09:36:50 ngày 14/11/2026, giờ Việt Nam**, trước chạy test.
Không dùng test để tinh chỉnh. B/C hòa metric, thứ tự phụ có lợi cho C do
cache; không diễn giải đó là lợi thế cold-start. A thắng tiêu chí đầu
tiên nên không phụ thuộc cách phá hòa này.

## Kết quả

### Retrieval accuracy và tài nguyên

Raw hit yêu cầu một chunk đúng nguồn/trang, chứa toàn bộ evidence sau
chuẩn hóa whitespace; có xét alternative gold đã khai báo. Hit@1 xét rank
1; Evidence Hit@3 cần một hit trong top-3. Không ghép nhiều chunk thành
một raw hit. Bảng sau giữ kết quả tự động ban đầu.

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Ingest (giây) | Chi phí dịch vụ |
|---|---|---|---|---:|---:|---|
| A | dev | 9/15 | 13/15 | 171 | 203,18 | 0 USD |
| A | test | 2/5 | 3/5 | 171 | 203,18 | 0 USD |
| B | dev | 8/15 | 11/15 | 169 | 181,48 | 0 USD |
| B | test | 1/5 | 2/5 | 169 | 181,48 | 0 USD |
| C | dev | 8/15 | 11/15 | 169 | 0,96, cache B | 0 USD |
| C | test | 1/5 | 2/5 | 169 | 0,96, cache B | 0 USD |

Ingest đo một lần mỗi cấu hình, gồm kiểm tra nạp lại; lặp giá trị ở hai
split không nghĩa là ingest hai lần. Thời gian khởi tạo model được ghi
riêng ở `environment.json`, không cộng vào bảng ingest. C dùng cache B,
không so 0,96 giây với B như hai lần cold-start độc lập. Trace giữ thời
gian truy xuất riêng từng câu. Chưa đo điện/RAM hoặc chi phí tải model.

| Strategy | Tổng ký tự sau chunking | Tổng token | Min / median / max ký tự | P90 |
|---|---:|---:|---|---:|
| A | 151.366 | 35.683 | 126 / 1000 / 1000 | 1000 |
| B | 139.066 | 32.725 | 56 / 921 / 998 | 982 |
| C | 139.066 | 32.725 | 56 / 921 / 998 | 982 |

Nguồn: [ingest_stats.json](../../results/ingest_stats.json),
[dev_metrics.json](../../results/dev_metrics.json),
[test_metrics.json](../../results/test_metrics.json),
[environment.json](../../results/environment.json).

### Coherence, metadata và grounding

**Người đánh giá và phương pháp:** Codex (AI) đọc từng mẫu/top-3, đối chiếu
PDF và ghi nhãn/lý do riêng. Cao Minh Quang đã xác nhận các nhãn hiện tại
qua trao đổi ngày 14/11/2026; các file `results/manual/` ghi
`human_confirmed=true`. Đây là đánh giá AI hỗ trợ được người dùng xác
nhận, **không khẳng định học viên đã chấm lại độc lập hoặc tự đối chiếu
từng trang PDF**. Cùng trợ lý hỗ trợ xây benchmark/code và đã thấy điểm,
nên audit không mù, không độc lập và có nguy cơ thiên lệch.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N) | Grounding 0/1/2 (số câu); trung bình /2 |
|---|---|---|---|---|
| A | 1,0 (10) | 15/15 | 0/1 | 0 / 0 / 5; 2,0 |
| B | 1,7 (10) | 15/15 | 1/1 | 0 / 0 / 5; 2,0 |
| C | 1,7 (10) | 15/15 | 1/1 | 0 / 0 / 5; 2,0 |

Coherence dùng cùng midpoint của 10 trang đầu đã sắp xếp, PDF 64–73,
được cố định trước khi xem retrieval; khi overlap, chọn chunk có start
offset sớm nhất. Thang 0=không hiểu do cắt ý/thiếu chủ thể, 1=hiểu một
phần nhưng thiếu ngữ cảnh, 2=tự hiểu và giữ trọn ý. A có 10 mẫu mức 1;
B/C có 3 mẫu mức 1 và 7 mẫu mức 2 mỗi cấu hình. B/C cùng chunk nên không
xem các nhãn giống nhau là hai nhóm mẫu độc lập.

Metadata kiểm tra **45 bản ghi**: 5 test × top-3 × 3 cấu hình. Nguồn,
trang, offsets và chương đều khớp PDF/bookmarks. Filter tính theo câu có
yêu cầu phạm vi, chỉ q18 trong test; 0/1 ở A không nghĩa metadata sai,
mà có kết quả ngoài phạm vi câu hỏi.

Grounding đọc toàn top-3: 0=không có evidence, 1=thiếu điều kiện/ngữ cảnh,
2=đủ trả lời và truy nguồn. Cả 15 trường hợp được đánh giá mức 2, kèm lý
do riêng. Đây không phải độ chính xác trả lời LLM. Top-3 có evidence
tương đương dù không chứa nguyên gold trong một chunk, nên có thể đủ
grounding nhưng raw miss.

### Artifacts và trace

- [dev_traces.jsonl](../../results/dev_traces.jsonl): 45 lượt truy xuất.
- [test_traces.jsonl](../../results/test_traces.jsonl): 15 lượt truy xuất.
- [coherence_samples.jsonl](../../results/manual/coherence_samples.jsonl): 30 mẫu, điểm/lý do/reviewer/xác nhận.
- [test_audit.jsonl](../../results/manual/test_audit.jsonl): 15 trường hợp, nhãn metadata/filter/grounding và lý do.
- [REVIEW.md](../../results/ai_audit/REVIEW.md): phương pháp AI judge và phân tích từng khía cạnh.
- [HUONG_DAN_CHAY.md](../../HUONG_DAN_CHAY.md): phạm vi xác nhận của người dùng.
- [frozen_selection.json](../../results/frozen_selection.json): lựa chọn A và fingerprint trước test.

Tổng **60 trace, 180 bản ghi top-3**; mỗi trace có question, chunk ID/text,
metadata, cosine distance/score, gold/evidence và nhãn match.

## Phân tích và kết luận

### Tác động A–B và B–C

A có raw dev Hit@3 **13/15**, cao hơn B **11/15**, nên được chọn theo tiêu
chí đã chốt. Test A đạt **3/5**, B đạt **2/5**. A xử lý thêm **2.958 token**,
khoảng **9,0%** so với B, chủ yếu do overlap. B có coherence tốt hơn ở mẫu
đã chấm (**1,7/2** so với **1,0/2**) vì ít cắt từ/câu. Ranh giới câu vẫn
có thể chia một evidence dài; coherence tốt không bảo đảm raw hit tăng.

Ví dụ PDF 65: A mở bằng `line in a table`, kết thúc `Price (pe`; B giữ
đủ định nghĩa demand schedule/curve. B vẫn thiếu ngữ cảnh như `those 18
months` ở PDF 64 và bảng nối trang 67–68. A/B khác cả cấu hình chunking,
chưa tách riêng tác động overlap khỏi từng quy tắc chọn boundary.

B/C có cùng chunks/vectors và cùng top-3 ở cả 5 câu test, raw metric
không đổi. q18 của B tình cờ nằm toàn chương 4 dù không lọc; C thực thi
filter nên bảo đảm cùng phạm vi. Một câu test filter chưa đủ chứng minh
C tăng retrieval trung bình. Ở A, q18 rank 3 là PDF 91/chương 3, ngoài
yêu cầu chương 4 dù metadata bản thân đúng. `page` giúp truy vết và
`chapter` giúp giới hạn phạm vi, nhưng không sửa mọi lỗi xếp hạng.

### Ví dụ lỗi và evidence tương đương

| Câu | Nguồn | Hiện tượng và phân tích |
|---|---|---|
| q16 | PDF 88, Figure 3.21/Table 3.7 | A/B/C raw miss do nguyên gold bị chia; rank 1 đã có giá $500, cung 15.000/cầu 19.000, đủ tính thiếu 4.000. Match chuỗi có thể đánh giá thấp retrieval. |
| q17 | PDF 90–91 | Cả ba xếp producer/social surplus ở rank 1; định nghĩa consumer surplus ở rank 2 PDF 90. Đây là lỗi top-1, dù top-3 đủ grounding. |
| q19 | PDF 117 | B/C tách gold ở offset 1880; kết luận giá oats tăng và mở rộng sản xuất có lời nằm rank 2. Raw match nguyên đoạn và grounding top-3 là hai phép đánh giá khác nhau. |
| q20 | PDF 118–119, Figure 4.11 | Rank 1 PDF 119 nêu cầu tăng/cung giảm, lương tăng và lượng chưa xác định; gold chỉ ghi PDF 118. Có trang evidence hợp lệ khác, không phải thiếu hết bằng chứng. |

Nhận định evidence tương đương lưu trong `results/ai_audit/`; không sửa
benchmark hoặc ghi đè raw metric sau test. Báo cáo giữ điểm tự động để
tái lập và giải thích false negative. Nếu bổ sung bảng hit đã thẩm định,
cần công bố rõ evidence alternative và áp dụng cùng phương pháp; không
âm thầm dùng cách chấm khác để thay điểm.

### Lựa chọn, giới hạn và hướng cải tiến

Giữ **A** làm cấu hình được chọn từ dev trong lần thực nghiệm này. Đánh
đổi là raw retrieval tốt hơn nhưng dễ cắt ý và tăng token do overlap.
B/C giữ ý tốt hơn ở mẫu coherence; C bổ sung kiểm soát phạm vi. Không có
căn cứ kết luận một cấu hình tốt nhất ngoài corpus này.

Giới hạn: chỉ 5 test cùng sách/chương với dev; 10 mẫu coherence đều thuộc
chương 3; một câu test filter; query/corpus cùng tiếng Anh; chưa thử OCR,
nhiều tài liệu/version; một lần đo CPU; ANN chưa đối chiếu exact; thời
gian C có cache; chưa đo điện/RAM. Cùng trợ lý AI hỗ trợ xây benchmark
và audit, có thiên lệch đã công bố; xác nhận của người dùng không biến
đánh giá thành chấm độc lập.

Thí nghiệm sau có thể tăng câu hỏi/nguồn độc lập, chuẩn bị alternative
gold trước chạy, có người chấm thứ hai, thử chunk theo cấu trúc PDF/token
và bảo toàn bảng/ngữ cảnh nối trang. Chọn tham số bằng dev; tạo test mới
nếu đã dùng test cũ để sửa. Hybrid/BM25 là mở rộng tùy chọn, chưa được
triển khai trong kết quả báo cáo này.

### Công bố sử dụng AI và kiểm chứng

Codex hỗ trợ đọc yêu cầu, chọn phạm vi corpus, viết code, soạn benchmark,
chạy kiểm tra và đọc audit. Nhãn nội dung ban đầu do AI đánh giá theo
GUIDE.md, có lý do từng trường hợp và đã được người dùng xác nhận; không
ghi giả học viên là người chấm độc lập. Metric/thời gian/số chunk/test
logic lấy từ lần chạy thật. Không tạo số liệu chưa chạy, không chỉnh
test/config để nâng điểm sau đánh giá. Model local không gửi corpus đến
API embedding.


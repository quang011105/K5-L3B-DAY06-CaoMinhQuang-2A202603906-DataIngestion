# Audit nội dung do AI hỗ trợ — cần học viên xem lại

**Cập nhật 2026-11-14:** Người dùng đã yêu cầu ghi nhận xác nhận các nhãn
hiện tại trong `results/manual/`. Xem [HUONG_DAN_CHAY.md](../../HUONG_DAN_CHAY.md). Phần dưới
giữ mô tả đề xuất AI tại thời điểm tạo; người chấm ban đầu vẫn là Codex.

Người đánh giá: **Codex, trợ lý AI trong phiên**, ngày 2026-11-14. Đây là
nhãn đề xuất của AI, **chưa phải nhãn chấm thủ công đã được học viên xác
nhận**. Cùng trợ lý đã hỗ trợ xây benchmark/code và đã nhìn thấy metric,
nên việc đọc không mù, không độc lập; có nguy cơ thiên lệch. Không ghi học
viên là người chấm khi họ chưa thực hiện việc đó.

Phương pháp theo thang GUIDE.md: đọc từng chunk mẫu, từng top-3 test và
đối chiếu văn bản nguồn. Đã xem trực quan trang PDF 88, 90, 116–119 để kiểm
tra bố cục bảng, định nghĩa và hình y tá. Metadata được kiểm tra thêm với
lần trích xuất mới, offsets và bookmarks từ PDF gốc; checksum PDF khớp
manifest. Đây là kiểm chứng hỗ trợ đọc nội dung, không lấy Hit@3 làm nhãn.

## 1. Retrieval accuracy

Giữ nguyên điểm tự động đã chạy, cùng benchmark và cấu hình đã freeze:

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---|---|---|---|
| A | 9/15 | 13/15 | 2/5 | 3/5 |
| B | 8/15 | 11/15 | 1/5 | 2/5 |
| C | 8/15 | 11/15 | 1/5 | 2/5 |

Định nghĩa cho phép evidence tương đương được người chấm xác nhận. AI
đề xuất các trường hợp trong `test_labels.jsonl`, gồm rank, chunk ID,
trang và lý do. Nếu học viên xác nhận **toàn bộ** các đề xuất này, số hit
test tương ứng sẽ là A Hit@1=4/5, B/C=3/5, và Hit@3=5/5 cho cả ba. Đây
**chưa phải điểm chính thức thay cho bảng trên**; chưa audit tương đương
trên dev, không so dev raw với test đã mở rộng evidence như cùng phép đo.
Không sửa gold, không chạy lại hay chọn cấu hình bằng các nhận định test.

Các lỗi/giới hạn cụ thể:

- **q16, PDF 88, A/B/C:** rank 1 chứa Figure 3.21 và hàng bảng tiền thuê
  $500, cung 15.000/cầu mới 19.000, đủ suy ra thiếu 4.000. Nguyên đoạn gold
  bắt đầu ở phần văn xuôi phía dưới bị cắt qua hai chunk nên raw miss.
  Đây là false negative có khả năng của match chuỗi, không phải thiếu hết
  bằng chứng. Bảng và đoạn văn cùng trang hỗ trợ kết luận.
- **q19, PDF 117, B/C:** nguyên gold bị chia ở boundary 1880. Rank 1 giữ
  việc nông dân không cần biết chi tiết; rank 2 giữ câu giá oats tăng và
  mở rộng sản xuất có lời. AI đề xuất rank 2 là evidence tương đương đủ
  với điều kiện câu hỏi đã nêu. Không ghép hai chunk để giả thành một raw
  hit; grounding đọc top-3 có thể đủ dù raw miss.
- **q20, PDF 118–119, A/B/C:** rank 1 là trang 119, Figure 4.11, có cầu
  tăng, cung giảm, lương tăng và lượng chưa xác định so với ban đầu. Gold
  chỉ ghi trang 118; ở B/C đoạn gold còn bị chia. AI đề xuất trang 119 là
  alternative evidence hợp lệ, giữ nguyên gold cũ và ghi nhận ngoài raw.
- **q17, PDF 90–91:** cả ba đưa producer/social surplus ở rank 1; định
  nghĩa consumer surplus nằm rank 2 trang 90. Đây là lỗi xếp hạng top-1,
  khác với lỗi match chuỗi; top-3 vẫn có định nghĩa đúng.

## 2. Chunk coherence

Mẫu đã cố định trước khi có điểm: midpoint của 10 trang nguồn đầu đã sắp
xếp, PDF 64–73; khi overlap thì chọn chunk bao phủ có offset bắt đầu sớm
nhất. B/C có chunk giống hệt nên nhận cùng nhãn, không phải 20 mẫu độc lập.

| Strategy | Nhãn 0/1/2 (số mẫu) | Trung bình đề xuất /2 | Số mẫu |
|---|---|---|---|
| A | 0 / 10 / 0 | 1,0 | 10 |
| B | 0 / 3 / 7 | 1,7 | 10 |
| C | 0 / 3 / 7 | 1,7 | 10 |

A thường cắt đầu/cuối từ hoặc câu nhưng vẫn giữ phần ý hiểu được, nên
được đề xuất mức 1 thay vì mặc định 0 cho mọi câu bị cắt. Ví dụ PDF 65
bắt đầu ở `line in a table` và kết thúc ở `Price (pe`; B giữ nguyên định
nghĩa demand schedule/curve. B vẫn có hạn chế: trang 64 thiếu tham chiếu
`those 18 months`, trang 67 có bảng tiếp sang trang 68, trang 69 mở bằng
`This decline` thiếu ngữ cảnh ban đầu. Nhãn và lý do riêng từng mẫu nằm
trong `coherence_labels.jsonl`.

## 3. Metadata usefulness

| Strategy | Bản ghi metadata đủ/đúng | Câu filter có top-3 đúng phạm vi |
|---|---|---|
| A | 15/15 | 0/1 |
| B | 15/15 | 1/1 |
| C | 15/15 | 1/1 |

Đối chiếu `document_id`, `source`, trang/offset/text, `chapter`,
`chapter_title` và ngôn ngữ. Chi tiết từng rank nằm trong `test_labels.jsonl`.
Không phát hiện trường metadata sai trong 45 bản ghi đã kiểm tra.

`page` dùng số trang PDF vật lý, giúp mở đúng bằng chứng dù số in trong
sách khác; `chapter` có nguồn từ bookmarks, có thể giới hạn phạm vi trước
truy xuất. **Metadata đúng không bảo đảm kết quả liên quan.** Ở q18 A rank
3 là trang PDF 91/chương 3: metadata bản thân đúng nhưng không tuân thủ
phạm vi chapter=4 mà câu hỏi yêu cầu. B tình cờ trả toàn chương 4 dù không
bật lọc; C thực thi filter. B/C trả giống hệt top-3 ở cả 5 câu test, nên
mẫu này chưa chứng minh C tăng retrieval so với B. Chỉ một câu test có
filter, không suy rộng tỷ lệ 1/1. Corpus một sách chỉ có hai chương nên
metadata chưa thử được version/năm hay nhiều tài liệu cạnh tranh.

## 4. Grounding quality

| Strategy | Nhãn đề xuất 0/1/2 (số câu) | Trung bình /2 | Số câu |
|---|---|---|---|
| A | 0 / 0 / 5 | 2,0 | 5 |
| B | 0 / 0 / 5 | 2,0 | 5 |
| C | 0 / 0 / 5 | 2,0 | 5 |

AI đọc top-3 của từng câu, không suy điểm từ raw hit. q16 đủ số liệu tiền
thuê; q17 có định nghĩa đúng ở rank 2; q18 có điều kiện nonbinding ở rank
1; q19 có kết luận lợi nhuận; q20 có điều kiện cung/cầu và tính chưa xác
định của lượng ở trang 119. Đều truy được nguồn nên đề xuất mức 2. Mỗi
trường hợp có lý do riêng trong file nhãn. **Đây không phải độ chính xác
câu trả lời LLM hoặc bằng chứng hệ thống đạt 100% tổng quát.** Điểm cao
ở grounding không xóa lỗi rank/filter hay thay raw metric. Học viên cần
kiểm tra các nhãn mức 2 trước khi sử dụng trong báo cáo như kết quả đã xác nhận.

## 5. Data strategy impact và đánh đổi

A tốt hơn theo tiêu chí dev đã chốt: raw Hit@3 13/15 so với 11/15 của B/C.
Giữ lựa chọn A trong `../frozen_selection.json`. B/C có coherence đề xuất
tốt hơn, cho thấy retrieval và tính trọn ý không nhất thiết cùng tăng.
Chunk B/C vẫn có thể tách một evidence dài ngay tại ranh giới câu.

A có 171 chunk, 151.366 ký tự sau overlap, 35.683 token; B/C có 169 chunk,
139.066 ký tự, 32.725 token. A xử lý thêm 2.958 token, khoảng 9,0% so với
B, đổi lại phần overlap có thể giúp giữ đủ evidence trong một chunk.
Số liệu chỉ cho thấy tương quan trong lần chạy này, không tách riêng tác
động overlap khỏi mọi chi tiết khác của cấu hình chunking.

Ingest A khoảng 203,18 giây, B khoảng 181,48 giây; C khoảng 0,96 giây
**do tái sử dụng cache B**, không phải phép đo cold-start độc lập. Upsert
lại không đổi count. Chi phí dịch vụ trả phí 0 USD; điện/CPU/RAM chưa đo.
Không thay đổi model/store/corpus giữa các cấu hình.

Giới hạn: 5 câu test cùng sách với dev; 10 mẫu coherence đều trong chương
3; câu hỏi cùng ngôn ngữ tiếng Anh với sách; một lần chạy CPU; ANN chưa
đối chiếu exact; AI tự đánh giá phần mình hỗ trợ xây và đã thấy điểm số.
Nên tăng corpus/test và có người chấm khác ở thí nghiệm tiếp theo; không
tinh chỉnh bằng test hiện tại rồi giữ tuyên bố holdout độc lập.

## Xem lại và tái tạo

```powershell
python scripts/materialize_ai_audit.py
```

Script chỉ ghi lại các quyết định đọc đã soạn trong phiên, kiểm chứng
provenance và cộng số liệu; không tự sinh nhãn mới bằng công thức Hit@3.
AI đã thực hiện vai trò LLM judge được công bố phương pháp ở trên. Các
trường `human_confirmed` đều `false`. Các đánh giá đã được điền vào
`results/manual/` bằng `python scripts/apply_ai_audit.py`, ghi người chấm là
Codex (AI), không ghi học viên đã xác nhận. Học viên có thể xem lại và ghi
điểm/lý do/người chấm của chính mình khi thực sự thực hiện việc đánh giá.
Ghi rõ công cụ và phương pháp này trong báo cáo theo RULES.md. Không xem
việc tái chạy script là một lượt đánh giá độc lập.

Ghi công phần trích sách: **Principles of Economics 3e, OpenStax, Rice
University. Access for free at openstax.org.** Điều khoản nguồn: trang PDF
4 và `data/manifest.json`.

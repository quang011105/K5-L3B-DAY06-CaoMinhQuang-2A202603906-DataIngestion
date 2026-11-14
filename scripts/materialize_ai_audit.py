"""Save case-by-case AI reading judgments, separately from pending human labels.

Judgments below were authored after reading chunks, traces and PDF source in
this session. This script validates provenance and aggregates those judgments;
it is not an automatic LLM judge and does not infer labels from retrieval scores.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pymupdf
from prepare_corpus import normalize

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = "Codex (AI assistant in this session; not the student)"
STATUS = "AI proposal; pending student review"

# Page-specific judgments of the predefined sampled chunks, not retrieval hits.
COHERENCE = {
    64: ((1, "Hiểu được ví dụ giá xăng và vai trò cung–cầu, nhưng đầu chunk còn mảnh tiêu đề và cuối bị cắt giữa từ averaged."),
         (1, "Các câu chính nguyên vẹn nhưng those 18 months không có khoảng thời gian tham chiếu trong chunk; danh sách mục tiêu mới có một phần.")),
    65: ((1, "Định nghĩa demand schedule và trục đồ thị vẫn đọc được, nhưng đầu cắt giữa gasoline và cuối cắt tiêu đề bảng Price (pe."),
         (2, "Có định nghĩa đầy đủ demand schedule, demand curve, đơn vị và trục; bắt đầu/kết thúc tại ranh giới câu.")),
    66: ((1, "Phân biệt demand/quantity demanded còn đủ ý, nhưng mở đầu cắt terminology và kết thúc cắt ví dụ về hành động nhà sản xuất."),
         (2, "Phân biệt đường cầu với điểm trên đường cầu đầy đủ; phần mở đầu về cung cũng kết thúc bằng câu trọn vẹn.")),
    67: ((1, "Giữ được phân biệt supply/quantity supplied, nhưng vị trí mẫu ở cuối bị cắt ngay trong định nghĩa supply curve."),
         (1, "Định nghĩa đường cung rõ và các câu hoàn chỉnh, nhưng bảng đi kèm chỉ có một phần dãy giá/lượng; phần còn lại nằm ở trang 68.")),
    68: ((1, "Có giải thích kết hợp cung–cầu nhưng mở bằng phần tiếp bảng trang trước và cuối cắt câu giới thiệu Figure 3.4."),
         (2, "Giới thiệu hình, chú thích cân bằng, điều kiện dư cung/cầu và bảng với đơn vị được giữ chung, đủ hiểu ví dụ.")),
    69: ((1, "Đầu cắt từ câu trước; cơ chế dư cung còn hiểu được nhưng cuối cắt từ expenses làm lý giải chưa trọn vẹn."),
         (1, "Kết thúc nguyên câu và định nghĩa surplus rõ, nhưng This decline thiếu mức giá/lượng ban đầu giải thích đợt giảm; ngữ cảnh chỉ một phần.")),
    70: ((1, "Đọc được các yếu tố ngoài giá nhưng đầu là mảnh learning objective và cuối cắt giải thích tastes/preferences."),
         (2, "Giữ đầy đủ phần chuyển sang yếu tố ngoài giá, định nghĩa willingness/ability và tastes/preferences; không cắt giữa câu.")),
    71: ((1, "Ví dụ giá/lượng xe còn đọc được; đầu cắt Additionally và cuối cắt giả định ceteris paribus."),
         (2, "Có điều kiện các yếu tố khác giữ nguyên, tác động thu nhập và ví dụ giá 20.000/22.000 USD; các câu đầy đủ.")),
    72: ((1, "Hiểu được dịch trái và phân biệt thay đổi thị trường/cá nhân, nhưng thiếu đầu câu và cắt định nghĩa normal good cuối chunk."),
         (2, "Giữ rõ nguyên nhân giảm thu nhập, dịch D0 sang D2, ví dụ lượng xe và cảnh báo về mức thị trường; các câu không bị cắt.")),
    73: ((1, "Định nghĩa substitute có thể hiểu nhưng đầu là đuôi ví dụ dân số và cuối cắt Since people are, thiếu phần kết ví dụ."),
         (2, "Các ý về dân số, substitute và giá tablet được viết đủ câu; phần định nghĩa và hướng tác động tự hiểu được.")),
}

# Equivalent evidence proposals require student review; never rewrite gold or raw metrics.
TEST_READINGS = {
    'A': {
        'q16': ([1, 2], "Trang PDF 88: rank 1 có chú thích và hàng bảng giá $500, cung 15.000/cầu mới 19.000; rank 2 cũng nêu hai lượng và thiếu hụt nhà thuê. Tính 19.000−15.000=4.000. Gold dài bị cắt nhưng evidence tương đương đủ."),
        'q17': ([2], "Rank 2 trang PDF 90 định nghĩa trực tiếp willingness to pay trừ actual payment. Rank 1 chủ yếu nói producer/social surplus nên không đủ cho định nghĩa được hỏi."),
        'q18': ([1], "Rank 1 trang PDF 116 nêu rõ trần cao không ràng buộc, không tác động trừ khi cân bằng vượt trần. Rank 3 thuộc chương 3 nên top-3 không tuân thủ yêu cầu phạm vi chapter=4."),
        'q19': ([1], "Rank 1 trang PDF 117 giữ nguyên việc nông dân không cần biết chi tiết và giá yến mạch tăng báo hiệu mở rộng sản xuất có lợi nhuận."),
        'q20': ([1], "Rank 1 trang PDF 119 là chú thích Figure 4.11: cầu tăng, cung giảm do nghỉ hưu, lương cao hơn và số y tá tăng/giảm so với ban đầu chưa xác định. Đây là trang nguồn hợp lệ khác gold 118."),
    },
    'B': {
        'q16': ([1, 2], "Trang PDF 88: rank 1 có hàng bảng $500 và chú thích cung 15.000/cầu 19.000, đủ tính thiếu 4.000; rank 2 có số lượng và shortage. Evidence gold bị chia, nhưng từng đoạn này hỗ trợ câu hỏi khi đọc cùng điều kiện đã nêu."),
        'q17': ([2], "Rank 2 trang PDF 90 giữ nguyên định nghĩa consumer surplus là mức sẵn lòng trả trừ mức thực trả; rank 1 chủ yếu nói producer surplus."),
        'q18': ([1], "Rank 1 trang PDF 116 chứa đầy đủ điều kiện nonbinding. Cả ba rank đều thuộc chương 4 dù B không áp dụng filter; tuân thủ ở ca này không chứng minh có bật lọc."),
        'q19': ([2], "Rank 1 trang PDF 117 có nông dân và việc không cần biết chi tiết nhưng chưa có kết luận lợi nhuận; rank 2 nêu rõ giá oats tăng và mở rộng sản xuất có lời. Top-3 đủ, tuy nguyên đoạn gold bị tách qua rank 1–2."),
        'q20': ([1], "Rank 1 trang PDF 119 đã nêu đủ tác động kết hợp: lương tăng, lượng chưa xác định so với ban đầu. Rank 2–3 trang 118 còn bổ sung nguyên nhân và relative shifts, nhưng gold đầy đủ bị tách giữa chúng."),
    },
}


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_lines(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')


def main():
    out = ROOT/'results/ai_audit'
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    pdf_path = ROOT/manifest['source_path_or_url']
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == manifest['snapshot']['sha256']
    samples = read_lines(ROOT/'results/manual/coherence_samples.jsonl')
    traces = read_lines(ROOT/'results/test_traces.jsonl')
    coherence, audits = [], []
    with pymupdf.open(pdf_path) as pdf:
        source_texts = {p['pdf_page']:normalize(pdf[p['pdf_page']-1].get_text(sort=False)) for p in manifest['pages']}
        # Independently recover chapter boundaries from the original PDF bookmarks.
        chapters = [(page, int(title.split()[1]), title.split(' ', 2)[2])
                    for level, title, page in pdf.get_toc()
                    if level == 1 and title.startswith('Chapter ') and title.split()[1].isdigit()]
        for sample in samples:
            chunk = sample['chunk']
            metadata = chunk['metadata']
            assert chunk['text'] == source_texts[metadata['page']][metadata['start_char']:metadata['end_char']]
            score, reason = COHERENCE[sample['pdf_page']][0 if sample['strategy']=='A' else 1]
            coherence.append({**sample, 'ai_coherence_0_2':score, 'ai_reason':reason,
                              'ai_reviewer':REVIEWER, 'review_status':STATUS,
                              'human_confirmed':False, 'review_date':'2026-11-14'})
        for trace in traces:
            baseline = trace['strategy'] if trace['strategy'] != 'C' else 'B'
            if trace['strategy'] == 'C':
                same = next(t for t in traces if t['strategy']=='B' and t['id']==trace['id'])
                assert trace['hits'] == same['hits']
            ranks, reason = TEST_READINGS[baseline][trace['id']]
            checks = []
            for rank, hit in enumerate(trace['hits'], 1):
                metadata = hit['metadata']
                chapter = max((c for c in chapters if c[0] <= metadata['page']), key=lambda c:c[0])
                field_checks = {
                    'document_id':metadata['document_id']==manifest['source_id'],
                    'source':metadata['source']==manifest['source_path_or_url'],
                    'page_and_text_offsets':hit['text']==source_texts[metadata['page']][metadata['start_char']:metadata['end_char']],
                    'chapter':metadata['chapter']==chapter[1],
                    'chapter_title':metadata['chapter_title']==chapter[2],
                    'language':metadata['language']=='en',
                }
                assert all(field_checks.values()), (trace['id'], rank, field_checks)
                checks.append({'rank':rank, 'chunk_id':hit['chunk_id'], 'pdf_page':metadata['page'],
                               'field_checks':field_checks, 'metadata_complete_and_correct':True,
                               'ai_sufficient_single_chunk_evidence':rank in ranks})
            requested = trace['requested_filter']
            compliant = all(h['metadata']['chapter']==requested['chapter'] for h in trace['hits']) if requested else None
            audits.append({'strategy':trace['strategy'], 'id':trace['id'], 'question':trace['question'],
                           'requested_filter':requested, 'applied_filter':trace['applied_filter'],
                           'metadata_checks':checks, 'filter_compliance':compliant,
                           'ai_grounding_0_2':2, 'ai_reason':reason,
                           'ai_equivalent_evidence_hit1':1 in ranks,
                           'ai_equivalent_evidence_hit3':bool(ranks),
                           'ai_reviewer':REVIEWER, 'review_status':STATUS, 'human_confirmed':False,
                           'review_date':'2026-11-14'})
    write_lines(out/'coherence_labels.jsonl', coherence)
    write_lines(out/'test_labels.jsonl', audits)
    summary = {'reviewer':REVIEWER, 'status':STATUS, 'human_confirmed':False,
               'method':'Case-by-case reading of sampled chunks and all test top-3; fresh original PDF extraction and bookmark checks; visual inspection of PDF 88,90,116,117,118,119. Labels are AI-authored proposals, not string-match inference or human manual grades.',
               'bias':'Same assistant authored pipeline/benchmark and has seen metrics; review is not blind or independent.',
               'raw_metrics_unchanged':True, 'strategies':[]}
    for strategy in ['A','B','C']:
        cs = [c for c in coherence if c['strategy']==strategy]
        ts = [t for t in audits if t['strategy']==strategy]
        filtered = [t for t in ts if t['requested_filter']]
        summary['strategies'].append({
            'strategy':strategy, 'coherence_n':len(cs),
            'ai_coherence_mean':sum(c['ai_coherence_0_2'] for c in cs)/len(cs),
            'ai_coherence_counts':dict(Counter(c['ai_coherence_0_2'] for c in cs)),
            'metadata_correct':sum(c['metadata_complete_and_correct'] for t in ts for c in t['metadata_checks']),
            'metadata_checked':sum(len(t['metadata_checks']) for t in ts),
            'filter_compliant_questions':sum(t['filter_compliance'] for t in filtered),
            'filter_question_count':len(filtered),
            'ai_grounding_counts':dict(Counter(t['ai_grounding_0_2'] for t in ts)),
            'ai_grounding_mean':sum(t['ai_grounding_0_2'] for t in ts)/len(ts),
            'ai_equivalent_evidence_hit1_count':sum(t['ai_equivalent_evidence_hit1'] for t in ts),
            'ai_equivalent_evidence_hit3_count':sum(t['ai_equivalent_evidence_hit3'] for t in ts),
            'test_n':len(ts)})
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

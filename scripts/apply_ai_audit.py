"""Populate audit fields with disclosed AI judgments, never human confirmation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    pending = []
    specs = [
        ('coherence_samples.jsonl', 'coherence_labels.jsonl', lambda r:(r['strategy'], r['chunk']['chunk_id'])),
        ('test_audit.jsonl', 'test_labels.jsonl', lambda r:(r['strategy'], r['id'])),
    ]
    for target_name, source_name, key in specs:
        target = ROOT/'results/manual'/target_name
        rows = read(target)
        judgments = {key(row):row for row in read(ROOT/'results/ai_audit'/source_name)}
        assert len(rows) == len(judgments)
        for row in rows:
            judgment = judgments[key(row)]
            reviewer = judgment['ai_reviewer']
            if row.get('reviewer') not in (None, reviewer) or row.get('human_confirmed'):
                raise ValueError('Existing reviewer labels detected; refusing to overwrite')
            if target_name == 'coherence_samples.jsonl':
                assert row['chunk'] == judgment['chunk']
                if row.get('reviewer') is None and row['manual_coherence_0_2'] is not None:
                    raise ValueError('Existing coherence score detected; refusing to overwrite')
                row['manual_coherence_0_2'] = judgment['ai_coherence_0_2']
            else:
                assert [h['chunk_id'] for h in row['hits']] == [h['chunk_id'] for h in judgment['metadata_checks']]
                if row.get('reviewer') is None and any(row.get(k) is not None for k in ['metadata_correct_per_hit','filter_compliance','grounding_0_2']):
                    raise ValueError('Existing test labels detected; refusing to overwrite')
                row['metadata_correct_per_hit'] = [c['metadata_complete_and_correct'] for c in judgment['metadata_checks']]
                row['filter_compliance'] = judgment['filter_compliance']
                row['grounding_0_2'] = judgment['ai_grounding_0_2']
            row.update(reason=judgment['ai_reason'], reviewer=reviewer,
                       review_method='AI-assisted source review; see results/ai_audit/REVIEW.md',
                       review_status='AI evaluation completed; not human-confirmed',
                       human_confirmed=False, review_date=judgment['review_date'])
        pending.append((target, rows))
    for target, rows in pending:
        target.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')
    print('Applied disclosed AI evaluations: 30 coherence samples and 15 test cases. Human confirmation remains false.')


if __name__ == '__main__':
    main()

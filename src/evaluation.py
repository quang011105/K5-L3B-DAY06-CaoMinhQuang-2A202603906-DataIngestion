"""Conservative evidence metrics; manual equivalence/coherence/grounding stay separate."""
from collections import defaultdict
import re


def comparable(text):
    return re.sub(r'\s+', ' ', text).strip()


def evaluate(question, hits):
    golds = [question] + question.get('alternative_gold', [])
    labels = [any(hit['metadata']['document_id'] == gold['gold_source_id']
                  and hit['metadata']['page'] == gold['gold_page']
                  and comparable(gold['evidence_quote']) in comparable(hit['text']) for gold in golds) for hit in hits]
    return {'id': question['id'], 'split': question['split'], 'question': question['question'],
            'expected_answer': question['expected_answer'],
            'gold': [{k:g[k] for k in ('gold_source_id','gold_page','evidence_quote')} for g in golds],
            'requested_filter': question.get('filter'), 'hits': hits, 'evidence_match_per_hit': labels,
            'hit1': bool(labels and labels[0]), 'hit3': any(labels[:3]), 'manual_grounding': None,
            'metric_method': 'source/page and complete evidence substring after whitespace normalization; equivalent evidence requires documented manual review'}


def summarize(traces):
    groups = defaultdict(list)
    for trace in traces:
        groups[(trace['strategy'], trace['split'])].append(trace)
    return [{'strategy': strategy, 'split': split, 'n': len(rows),
             'hit1_count': sum(r['hit1'] for r in rows), 'hit3_count': sum(r['hit3'] for r in rows),
             'hit1': sum(r['hit1'] for r in rows)/len(rows), 'hit3': sum(r['hit3'] for r in rows)/len(rows)}
            for (strategy, split), rows in sorted(groups.items())]

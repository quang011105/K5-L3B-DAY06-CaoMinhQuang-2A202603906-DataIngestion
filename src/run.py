"""Run from repository root: python -m src.run ingest|dev|freeze|test."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import logging
import os
from pathlib import Path
import statistics
import time

from .chunking import chunk_page
from .evaluation import evaluate, summarize
from .store import Store

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
LOCAL = ROOT / '.local'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def write_lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')


def fingerprint():
    paths = [ROOT/'configs/strategies.json', ROOT/'data/manifest.json', ROOT/'data/processed/pages.jsonl', ROOT/'benchmark/questions.jsonl']
    paths += sorted((ROOT/'src').glob('*.py'))
    return hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()


def ingest(config, embedder, store):
    pages = read_lines(ROOT/'data/processed/pages.jsonl')
    manifest = read_json(ROOT/'data/manifest.json')
    if len(pages) < 30 or len(pages) != manifest['content_page_count']:
        raise ValueError('Corpus page requirement failed')
    if hashlib.sha256((ROOT/manifest['source_path_or_url']).read_bytes()).hexdigest() != manifest['snapshot']['sha256']:
        raise ValueError('PDF snapshot changed; prepare and revalidate corpus/benchmark first')
    audit, chunks_by_strategy = [], {}
    for strategy, spec in config['strategies'].items():
        started = time.perf_counter()
        chunks = [chunk for page in pages for chunk in chunk_page(page, spec['chunk_size'], spec['overlap'], spec['chunking'] != 'fixed')]
        chunks_by_strategy[strategy] = chunks
        cache_key = hashlib.sha256(json.dumps([config['model'], config['revision'], [c['chunk_id'] for c in chunks]]).encode()).hexdigest()
        cache = LOCAL/'embeddings'/f'{cache_key}.json'
        cache_hit = cache.exists()
        encode_start = time.perf_counter()
        vectors = read_json(cache) if cache_hit else embedder.encode([c['text'] for c in chunks])
        encode_seconds = time.perf_counter()-encode_start
        if not cache_hit:
            write_json(cache, vectors)
        store_start = time.perf_counter()
        store.upsert(strategy, chunks, vectors)
        store_seconds = time.perf_counter()-store_start
        count_before = store.collection(strategy).count()
        store.upsert(strategy, chunks, vectors)
        count_after = store.collection(strategy).count()
        if count_before != count_after or count_after != len(chunks):
            raise RuntimeError('Reingest duplicated chunks')
        lengths = sorted(len(c['text']) for c in chunks)
        tokens = [len(ids) for ids in embedder.model.tokenizer([c['text'] for c in chunks], truncation=False)['input_ids']]
        write_lines(RESULTS/f'chunks_{strategy}.jsonl', chunks)
        audit.append({'strategy': strategy, 'chunk_count': len(chunks), 'total_characters': sum(lengths),
                      'total_tokens': sum(tokens), 'min_length': lengths[0], 'median_length': statistics.median(lengths),
                      'max_length': lengths[-1], 'p90_length': lengths[int((len(lengths)-1)*.9)],
                      'encoding_or_cache_seconds': encode_seconds, 'embedding_cache_hit': cache_hit,
                      'store_write_seconds': store_seconds, 'ingest_seconds_including_reingest_check': time.perf_counter()-started,
                      'reingest_before': count_before, 'reingest_after': count_after,
                      'paid_service_cost_usd': 0, 'local_compute_energy_cost': 'not measured'})
        print(f'{strategy}: {len(chunks)} chunks, reingest {count_before} -> {count_after}', flush=True)
    if chunks_by_strategy['B'] != chunks_by_strategy['C']:
        raise RuntimeError('B/C chunk snapshots differ')
    # Predefined source positions, independent of any retrieval scores.
    samples = []
    for page in sorted(pages, key=lambda p:p['page'])[:10]:
        position = len(page['text'])//2
        for strategy, chunks in chunks_by_strategy.items():
            covering = [c for c in chunks if c['metadata']['page'] == page['page'] and c['metadata']['start_char'] <= position < c['metadata']['end_char']]
            chosen = sorted(covering, key=lambda c:c['metadata']['start_char'])[0]
            samples.append({'strategy': strategy, 'pdf_page': page['page'], 'source_position': position,
                            'selection_rule': 'midpoint of first 10 sorted source pages; earliest covering chunk if overlap',
                            'chunk': chosen, 'manual_coherence_0_2': None, 'reason': None, 'reviewer': None})
    sample_path = RESULTS/'manual/coherence_samples.jsonl'
    if not sample_path.exists():
        write_lines(sample_path, samples)
    write_json(RESULTS/'ingest_stats.json', audit)
    write_json(LOCAL/'ingest_state.json', {'fingerprint': fingerprint(), 'dimensions': embedder.dimensions})


def retrieve(split, config, embedder, store):
    state = read_json(LOCAL/'ingest_state.json')
    if state['fingerprint'] != fingerprint():
        raise RuntimeError('Pipeline/corpus/benchmark/config changed; ingest again before evaluation')
    if split == 'test':
        freeze = read_json(RESULTS/'frozen_selection.json')
        if freeze['fingerprint'] != fingerprint():
            raise RuntimeError('Configuration changed after freeze')
    questions = [q for q in read_lines(ROOT/'benchmark/questions.jsonl') if q['split'] == split]
    vectors = embedder.encode([q['question'] for q in questions])
    traces = []
    for strategy, spec in config['strategies'].items():
        for question, vector in zip(questions, vectors):
            filters = question.get('filter') if spec['filter'] else None
            started = time.perf_counter()
            hits = store.search(strategy, vector, filters)
            trace = evaluate(question, hits)
            trace.update(strategy=strategy, applied_filter=filters, retrieval_seconds=time.perf_counter()-started)
            traces.append(trace)
    write_lines(RESULTS/f'{split}_traces.jsonl', traces)
    metrics = summarize(traces)
    write_json(RESULTS/f'{split}_metrics.json', metrics)
    log_path = ROOT/'artifacts/experiment_log.csv'
    with log_path.open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        fieldnames, experiments = reader.fieldnames, list(reader)
    for row in experiments:
        metric = next(m for m in metrics if m['strategy'] == row['strategy'])
        row[f'{split}_hit1'] = f"{metric['hit1_count']}/{metric['n']}"
        row[f'{split}_hit3'] = f"{metric['hit3_count']}/{metric['n']}"
        row['notes'] = row['notes'].replace('; no metrics yet', '').replace('no metrics yet', '')
    with log_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(experiments)
    if split == 'test':
        audit = [{'strategy': t['strategy'], 'id': t['id'], 'hits': t['hits'],
                  'requested_filter': t['requested_filter'], 'applied_filter': t['applied_filter'],
                  'metadata_correct_per_hit': None, 'filter_compliance': None,
                  'grounding_0_2': None, 'reason': None, 'reviewer': None} for t in traces]
        path = RESULTS/'manual/test_audit.jsonl'
        if not path.exists():
            write_lines(path, audit)
    print(json.dumps(metrics, indent=2), flush=True)


def freeze_selection():
    metrics = read_json(RESULTS/'dev_metrics.json')
    stats = {s['strategy']:s for s in read_json(RESULTS/'ingest_stats.json')}
    ranked = sorted(metrics, key=lambda m:(-m['hit3'], -m['hit1'], stats[m['strategy']]['ingest_seconds_including_reingest_check']))
    path = RESULTS/'frozen_selection.json'
    if path.exists():
        raise RuntimeError('Selection already frozen; keep previous test history and explicitly version new experiments')
    write_json(path, {'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'fingerprint': fingerprint(),
                      'selected_strategy': ranked[0]['strategy'], 'dev_ranking': ranked,
                      'rule': 'dev Evidence Hit@3, then dev Hit@1, then measured ingest time (cache effects disclosed in stats)',
                      'test_used_for_selection': False})
    print('Frozen selection:', ranked[0]['strategy'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['ingest','dev','freeze','test'])
    parser.add_argument('--allow-model-download', action='store_true')
    args = parser.parse_args()
    if not args.allow_model_download:
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
    RESULTS.mkdir(exist_ok=True)
    logging.basicConfig(filename=RESULTS/'pipeline_errors.log', level=logging.WARNING)
    try:
        if args.action == 'freeze':
            freeze_selection()
            return
        config = read_json(ROOT/'configs/strategies.json')
        from .embeddings import Embedder
        started = time.perf_counter()
        embedder = Embedder(config['model'], config['revision'], local_only=not args.allow_model_download)
        store = Store(LOCAL/'chroma', embedder.dimensions)
        write_json(RESULTS/'environment.json', {'utc': datetime.now(timezone.utc).isoformat(),
                   'versions': {name:version(name) for name in ['sentence-transformers','chromadb','torch','PyMuPDF']},
                   'model': config['model'], 'revision': config['revision'], 'dimensions': embedder.dimensions,
                   'model_max_seq_length': embedder.model.max_seq_length, 'device': 'cpu', 'torch_threads': 4,
                   'query_document_encoding': 'same dense encode, no prefix, L2 normalization, float32',
                   'model_store_initialization_seconds': time.perf_counter()-started,
                   'search': 'Chroma cosine HNSW ANN; ef_search=100, ef_construction=100, max_neighbors=16',
                   'paid_service_cost_usd': 0})
        if args.action == 'ingest':
            ingest(config, embedder, store)
        else:
            retrieve(args.action, config, embedder, store)
    except Exception:
        logging.exception('Pipeline failed; no mock fallback')
        raise


if __name__ == '__main__':
    main()

"""Small correctness tests. Synthetic vectors here are never benchmark embeddings."""
import unittest
from pathlib import Path
import uuid

from src.chunking import chunk_page
from src.evaluation import evaluate
from src.store import Store


class PipelineTests(unittest.TestCase):
    def test_chunk_coverage_offsets_and_stable_ids(self):
        page = {'document_id':'doc', 'source':'source.pdf', 'page':1,
                'text':('A complete sentence.\nAnother sentence with context.\n'*30),
                'metadata':{'chapter':3}}
        for structure in [False, True]:
            chunks = chunk_page(page, 100, 0 if structure else 10, structure)
            self.assertEqual(chunks, chunk_page(page, 100, 0 if structure else 10, structure))
            covered = set()
            for chunk in chunks:
                start, end = chunk['metadata']['start_char'], chunk['metadata']['end_char']
                self.assertEqual(chunk['text'], page['text'][start:end])
                self.assertLessEqual(len(chunk['text']),100)
                covered.update(range(start,end))
            self.assertEqual(covered,set(range(len(page['text']))))

    def test_evidence_requires_page_source_and_complete_quote(self):
        question = {'id':'q', 'split':'dev','question':'why','expected_answer':'a',
                    'gold_source_id':'doc', 'gold_page':2,'evidence_quote':'full evidence'}
        def hit(page, text):
            return {'text':text, 'metadata':{'document_id':'doc','page':page}}
        self.assertFalse(evaluate(question,[hit(1,'full evidence')])['hit3'])
        self.assertFalse(evaluate(question,[hit(2,'full')])['hit3'])
        self.assertTrue(evaluate(question,[hit(2,'full\nevidence')])['hit1'])
        question['alternative_gold'] = [{'gold_source_id':'doc','gold_page':3,'evidence_quote':'valid alternative'}]
        self.assertTrue(evaluate(question,[hit(3,'valid alternative')])['hit1'])

    def test_persistent_store_filter_reingest_and_obsolete_cleanup(self):
        # Isolated test-only collection, with known geometry to test cosine and filtering.
        path = Path('.local/tests')/uuid.uuid4().hex
        store = Store(path,2)
        def chunk(identifier, chapter):
            return {'chunk_id':identifier,'text':identifier,
                    'metadata':{'document_id':'test','source':'test','page':1,'chapter':chapter}}
        chunks = [chunk('a',3),chunk('b',4)]
        store.upsert('A',chunks,[[1.,0.],[0.,1.]])
        store.upsert('A',chunks,[[1.,0.],[0.,1.]])
        self.assertEqual(store.collection('A').count(),2)
        self.assertEqual(store.search('A',[1.,0.])[0]['chunk_id'],'a')
        self.assertEqual(store.search('A',[1.,0.],{'chapter':4})[0]['chunk_id'],'b')
        reopened = Store(path,2)
        self.assertEqual(reopened.collection('A').count(),2)
        reopened.upsert('A',[chunk('new',4)],[[0.,1.]])
        self.assertEqual(reopened.collection('A').get(include=[])['ids'],['new'])
        with self.assertRaises(ValueError):
            reopened.search('A',[1.,0.],{'chapter':'4'})
        with self.assertRaises(ValueError):
            reopened.upsert('A',[chunk('bad',3)],[[1.]])


if __name__ == '__main__':
    unittest.main()

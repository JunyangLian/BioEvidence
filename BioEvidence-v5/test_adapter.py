"""Risk checks, separate from real scoring parity."""
import unittest
from common import *
from adapter import *

class Risks(unittest.TestCase):
    def setUp(self):
        self.doc={'question_id':'risk','gold':'yes','chunk_order':['stable-a','stable-b'],
                  'display_to_chunk':{'E1':'stable-a','E2':'stable-b'}}
    def test_invalid_denominator(self):
        valid=score_one(self.doc,'Label: yes\nReason: evidence.\nCitations: E1\nAnswerable: yes')
        bad=score_one(self.doc,'Label: yes')
        self.assertEqual(classification([valid,bad])['accuracy'],0.5)
        self.assertEqual(classification([valid,bad])['n'],2)
    def test_maybe_not_insufficient(self):
        p=score_one(self.doc,'Label: maybe\nReason: conditional.\nCitations: E1\nAnswerable: yes')
        self.assertEqual((p['label'],p['answerable']),('maybe','yes'))
    def test_mapping_and_unchanged_raw(self):
        raw='Label: yes\nReason: x.\nCitations: E2, E1\nAnswerable: yes\n'
        p=score_one(self.doc,raw)
        self.assertEqual(p['raw_output'],raw)
        self.assertEqual({p['display_to_chunk'][f'E{i}'] for i in p['citations']},{'stable-a','stable-b'})
    def test_out_of_range_not_repaired(self):
        p=score_one(self.doc,'Label: yes\nReason: x.\nCitations: E9\nAnswerable: yes')
        self.assertEqual(p['status'],'invalid_citation')
        self.assertEqual(classification([p])['accuracy'],0)
        self.assertTrue(p['citation_issues'])
    def test_unknown_not_pass(self):
        p=score_one(self.doc,'Label: unknown\nReason: x.\nCitations: None\nAnswerable: unknown')
        self.assertEqual(p['status'],'invalid')
    def test_zero_denominator(self):
        self.assertIsNone(classification([])['accuracy'])
        self.assertIsNone(compute_metrics([]).accuracy)
    def test_historical_contradiction_not_silently_redefined(self):
        p=score_one(self.doc,'Label: yes\nReason: x.\nCitations: E1\nAnswerable: no')
        self.assertEqual(p['status'],'ok')
        self.assertEqual(len(p['citation_issues']),2)

if __name__=='__main__': unittest.main()

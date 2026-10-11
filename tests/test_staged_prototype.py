import json
import tempfile
import unittest
from staged_prototype import generate_prototype

class StagedPrototypeTests(unittest.TestCase):
    def test_combined_contract_and_checkpoint(self):
        calls=[]
        def invoke(prompt,name):
            calls.append(name)
            if name=='prototype-brief':
                return json.dumps({'needs_prototype':True,'decision_reason':'UI useful',
                    'requirements_markdown':'requirements','design_markdown':'design'})
            return json.dumps({'prototype_html':'<!doctype html><html><head></head><body></body></html>'})
        with tempfile.TemporaryDirectory() as tmp:
            data=json.loads(generate_prototype('request',tmp,invoke))
            self.assertEqual(len(data),5)
            self.assertEqual(calls,['prototype-brief','prototype-html'])
            generate_prototype('request',tmp,lambda *_:self.fail('checkpoint ignored'))
    def test_truncation_stops_at_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'invalid/truncated'):
                generate_prototype('request',tmp,lambda *_:'{')
if __name__=='__main__': unittest.main()

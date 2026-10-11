import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from prototype_output import POLICY, write_bundle


class PrototypeTests(unittest.TestCase):
    def test_csp_quotes_are_literal_and_policy_is_preserved(self):
        class Reader(HTMLParser):
            policies = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy':
                    self.policies.append(attrs['content'])
        with tempfile.TemporaryDirectory() as tmp:
            write_bundle(json.dumps(self.data()), Path(tmp))
            html = (Path(tmp) / 'index.html').read_text()
            reader = Reader()
            reader.feed(html)
            self.assertEqual(reader.policies, [POLICY])
            self.assertNotIn('&#39;', html)

    def data(self, needed=True):
        return dict(needs_prototype=needed, decision_reason='界面流程需要验证' if needed else '纯后端任务', requirements_markdown='目标用户与验收条件', design_markdown='紧凑响应式布局', prototype_html='<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'+('演示'*250)+'</body></html>' if needed else '')

    def test_bundle_and_no_prototype(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_bundle(json.dumps(self.data()), root)
            self.assertTrue((root/'index.html').is_file())
            self.assertIn('Content-Security-Policy', (root/'index.html').read_text())
            self.assertIn('connect-src', (root/'index.html').read_text())
            self.assertEqual(set(p.name for p in root.iterdir()), {'index.html','decision.json','requirements.md','design.md','README.md'})
            report=write_bundle(json.dumps(self.data(False)), root)
            self.assertFalse((root/'index.html').exists())
            self.assertIn('不需要原型', report)

    def test_invalid_outputs_do_not_write_artifacts(self):
        cases=[]
        d=self.data();d['needs_prototype']='true';cases.append(d)
        d=self.data();d['path']='../../evil';cases.append(d)
        d=self.data();d['prototype_html']='<p>placeholder</p>';cases.append(d)
        d=self.data();d['prototype_html']=d['prototype_html'].replace('<body>','<body><script src="https://example.com/a.js"></script>');cases.append(d)
        d=self.data(False);d['prototype_html']='unexpected';cases.append(d)
        for d in cases:
            with self.subTest(d=d), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):write_bundle(json.dumps(d),Path(tmp)/'output')
                self.assertFalse((Path(tmp)/'output').exists())


if __name__ == '__main__':unittest.main()

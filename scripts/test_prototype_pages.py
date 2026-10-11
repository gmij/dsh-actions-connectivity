import io
import json
import os
import unittest
import urllib.request
import zipfile
from unittest.mock import patch

from prototype_pages import SafeRedirect, assemble, member, page_base, prepare, validate_run

HTML = '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="connect-src &#39;none&#39;"></head><body>demo</body></html>'


class PagesTests(unittest.TestCase):
    def test_accepts_official_deployment_custom_domain(self):
        self.assertEqual(page_base('http://gmij.win/dsh-actions-connectivity/'), 'http://gmij.win/dsh-actions-connectivity/')
        self.assertEqual(page_base('https://gmij.github.io/dsh-actions-connectivity'), 'https://gmij.github.io/dsh-actions-connectivity/')
        for url in ['javascript:alert(1)', 'https://user:secret@gmij.win/', 'https://gmij.win/?token=secret', 'https://gmij.win/#x', 'https://gmij.win/\nmalicious']:
            with self.assertRaises(ValueError):
                page_base(url)

    def test_preserves_other_issues_and_versions(self):
        first, _, _ = assemble({}, 14, 101, HTML)
        second, latest, version = assemble(first, 16, 102, HTML)
        self.assertEqual(second['previews/issue-14/runs/101/index.html'], HTML)
        self.assertEqual(latest, 'previews/issue-16/index.html')
        self.assertEqual(version, 'previews/issue-16/runs/102/index.html')
        self.assertIn('Issue #14', second['index.html'])
        self.assertIn('Issue #16', second['index.html'])

    def test_replaying_old_run_does_not_replace_latest(self):
        first, _, _ = assemble({}, 14, 102, HTML + '<!--new-->')
        second, _, _ = assemble(first, 14, 101, HTML)
        self.assertEqual(second['previews/issue-14/index.html'], HTML + '<!--new-->')

    def test_only_allowlisted_paths_and_positive_ids(self):
        for files, issue in [({'README.md': 'private'}, 14), ({'../index.html': HTML}, 14), ({}, 0), ({}, True)]:
            with self.assertRaises(ValueError):
                assemble(files, issue, 101, HTML)
        with self.assertRaises(ValueError):
            assemble({}, 14, 101, '<!doctype html><html>missing CSP</html>')

    def test_rejects_untrusted_source_runs(self):
        run = {'repository': {'full_name': 'gmij/example'}, 'path': '.github/workflows/issue-agent.yml',
               'head_branch': 'main', 'event': 'workflow_dispatch', 'conclusion': 'success'}
        validate_run(run, 'gmij/example', 'main')
        for field, value in [('event', 'pull_request'), ('head_branch', 'feature'), ('conclusion', 'failure'), ('path', 'other.yml')]:
            with self.assertRaises(ValueError):
                validate_run(dict(run, **{field: value}), 'gmij/example', 'main')
        with self.assertRaises(ValueError):
            validate_run(run, 'gmij/other', 'main')

    def test_zip_is_not_extracted_and_duplicate_member_rejected(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('../private.txt', 'not extracted')
            archive.writestr('index.html', HTML)
        with zipfile.ZipFile(payload) as archive:
            self.assertEqual(member(archive, 'index.html'), HTML)
            with self.assertRaises(ValueError):
                member(archive, 'decision.json')

    def test_download_redirect_does_not_forward_github_token(self):
        request = urllib.request.Request('https://api.github.com/artifact', headers={'Authorization': 'Bearer dummy'})
        redirect = SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://storage.example/zip')
        self.assertIsNone(redirect.get_header('Authorization'))
        with self.assertRaises(ValueError):
            SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'http://storage.example/zip')

    def test_no_prototype_or_no_dispatch_skips_without_publishing(self):
        run = {'repository': {'full_name': 'gmij/example'}, 'path': '.github/workflows/issue-agent.yml',
               'head_branch': 'main', 'event': 'issues', 'conclusion': 'success'}
        def archive(files):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as output_zip:
                for name, content in files.items():
                    output_zip.writestr(name, json.dumps(content))
            return zipfile.ZipFile(buffer)
        for artifacts in [[None], [archive({'metadata.json': {'agent': 'prototype', 'config': {'mode': 'prototype'}, 'issue_number': 12}}),
                                  archive({'decision.json': {'needs_prototype': False}})]]:
            with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'gmij/example', 'SOURCE_RUN_ID': '101'}), \
                    patch('prototype_pages.api', side_effect=[{'default_branch': 'main'}, run]) as mocked_api, \
                    patch('prototype_pages.artifact', side_effect=artifacts), \
                    patch('prototype_pages.output') as output:
                prepare()
                output.assert_called_once_with(publish='false')
                self.assertEqual(mocked_api.call_count, 2)


if __name__ == '__main__':
    unittest.main()

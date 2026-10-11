"""Publish only validated HTML; never execute generated prototype code."""
import base64
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from issue_agent import api, comments

BRANCH = 'prototype-previews'
SAFE_PATH = re.compile(r'(?:index\.html|previews/issue-[1-9]\d*/(?:runs/[1-9]\d*/)?index\.html)\Z')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise ValueError('Artifact redirect must use HTTPS')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


def artifact(repo, run_id, name, required=True):
    found = []
    page = 1
    while True:
        batch = api('GET', f'/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100&page={page}')['artifacts']
        found.extend(a for a in batch if a['name'] == name and not a['expired'])
        if len(batch) < 100:
            break
        page += 1
    if not found and not required:
        return None
    if len(found) != 1:
        raise ValueError('Expected one unexpired ' + name + ' artifact')
    request = urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/artifacts/{found[0]["id"]}/zip',
                                    headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN']})
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=60) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError('Artifact is too large')
    return zipfile.ZipFile(io.BytesIO(payload))


def member(archive, name):
    entries = [entry for entry in archive.infolist() if entry.filename == name]
    if len(entries) != 1 or entries[0].file_size > 300_000:
        raise ValueError('Missing, duplicate or oversized artifact member: ' + name)
    return archive.read(entries[0]).decode('utf-8')


def positive(value):
    if type(value) is not int or value < 1:
        raise ValueError('Expected positive integer')
    return value


def validate_run(run, repo, default_branch):
    if (run.get('repository', {}).get('full_name') != repo or
            run.get('path') != '.github/workflows/issue-agent.yml' or
            run.get('head_branch') != default_branch or
            run.get('event') not in {'issues', 'workflow_dispatch'} or
            run.get('conclusion') != 'success'):
        raise ValueError('Source must be a successful trusted Issue DSH workflow on the default branch')


def validate_html(html):
    if len(html.encode()) > 300_000 or not re.search(r'<!doctype html', html, re.I):
        raise ValueError('Invalid prototype HTML')
    if 'Content-Security-Policy' not in html or 'connect-src &#39;none&#39;' not in html:
        raise ValueError('Prototype must include the trusted offline CSP')
    return html


def assemble(existing, issue, run_id, html):
    positive(issue)
    positive(run_id)
    if any(not SAFE_PATH.fullmatch(path) for path in existing):
        raise ValueError('Unexpected file in preview storage branch')
    latest = f'previews/issue-{issue}/index.html'
    version = f'previews/issue-{issue}/runs/{run_id}/index.html'
    updated = dict(existing)
    updated[version] = validate_html(html)
    # A manual replay of an older run must not roll the latest preview backwards.
    versions = [int(path.split('/')[3]) for path in updated
                if path.startswith(f'previews/issue-{issue}/runs/')]
    if run_id == max(versions):
        updated[latest] = html
    numbers = sorted({int(path.split('/')[1][6:]) for path in updated if path.startswith('previews/')})
    links = ''.join(f'<li><a href="previews/issue-{n}/">Issue #{n} · 在线原型</a></li>' for n in numbers)
    updated['index.html'] = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow"><title>原型预览</title>'
        '<style>body{font:16px/1.7 system-ui;background:#f7f8f6;color:#20342d;margin:0}'
        'main{max-width:720px;margin:8vh auto;padding:24px}a{color:#276b52}li{margin:18px 0}</style>'
        '</head><body><main><h1>原型预览</h1><p>演示界面，请勿输入真实或敏感数据。</p><ul>' + links + '</ul></main></body></html>')
    return updated, latest, version


def output(**values):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        for key, value in values.items():
            stream.write(f'{key}={value}\n')


def prepare():
    repo = os.environ['GITHUB_REPOSITORY']
    run_id = positive(int(os.environ['SOURCE_RUN_ID']))
    default = api('GET', f'/repos/{repo}')['default_branch']
    run = api('GET', f'/repos/{repo}/actions/runs/{run_id}')
    validate_run(run, repo, default)
    archive = artifact(repo, run_id, 'issue-agent-input', required=False)
    if archive is None:
        output(publish='false')
        return
    with archive:
        metadata = json.loads(member(archive, 'metadata.json'))
    if metadata.get('agent') != 'prototype' or metadata.get('config', {}).get('mode') != 'prototype':
        output(publish='false')
        return
    issue = positive(metadata['issue_number'])
    with artifact(repo, run_id, 'prototype-deliverable') as archive:
        decision = json.loads(member(archive, 'decision.json'))
        if type(decision.get('needs_prototype')) is not bool:
            raise ValueError('Invalid prototype decision')
        if not decision['needs_prototype']:
            output(publish='false')
            return
        html = validate_html(member(archive, 'index.html'))
    existing = {}
    parent = None
    try:
        parent = api('GET', f'/repos/{repo}/git/ref/heads/{BRANCH}')['object']['sha']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    if parent:
        tree = api('GET', f'/repos/{repo}/git/trees/{parent}?recursive=1')
        if tree.get('truncated'):
            raise ValueError('Preview tree is too large')
        for entry in tree['tree']:
            if entry['type'] == 'tree':
                continue
            if entry['mode'] != '100644' or not SAFE_PATH.fullmatch(entry['path']):
                raise ValueError('Preview branch contains unsupported files')
            blob = api('GET', f'/repos/{repo}/git/blobs/{entry["sha"]}')
            if blob['size'] > 300_000:
                raise ValueError('Stored preview is too large')
            existing[entry['path']] = base64.b64decode(blob['content']).decode('utf-8')
    updated, latest, version = assemble(existing, issue, run_id, html)
    entries = []
    for path, content in updated.items():
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'content': content})
    tree_sha = api('POST', f'/repos/{repo}/git/trees', {'tree': entries})['sha']
    commit = api('POST', f'/repos/{repo}/git/commits', {'message': f'Preview Issue #{issue} from DSH run {run_id}',
                 'tree': tree_sha, 'parents': [parent] if parent else []})['sha']
    if parent:
        api('PATCH', f'/repos/{repo}/git/refs/heads/{BRANCH}', {'sha': commit, 'force': False})
    else:
        api('POST', f'/repos/{repo}/git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': commit})
    site = Path(os.environ['RUNNER_TEMP']) / 'prototype-site'
    site.mkdir(parents=True, exist_ok=True)
    for path, content in updated.items():
        target = site / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    output(publish='true', issue_number=issue, latest=latest.removesuffix('index.html'), version=version.removesuffix('index.html'))


def page_base(url):
    # The URL comes from deploy-pages, never from a model or an Issue field.
    # GitHub supports custom domains and sites without Enforce HTTPS.
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or
            parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment or
            re.search(r'[\s<>\[\]()]', url)):
        raise ValueError('Unexpected Pages URL')
    return url.rstrip('/') + '/'


def notify():
    repo = os.environ['GITHUB_REPOSITORY']
    issue = positive(int(os.environ['ISSUE_NUMBER']))
    run_id = positive(int(os.environ['SOURCE_RUN_ID']))
    base = page_base(os.environ['PAGE_URL'])
    marker = f'<!-- dsh-pages:{run_id} -->'
    body = (marker + f'\n### 在线原型已发布\n\n[打开本次交互原型]({base}previews/issue-{issue}/runs/{run_id}/)'
            f' · [此任务最新原型]({base}previews/issue-{issue}/)\n\n'
            '无需下载压缩包。页面为公开演示预览，请勿输入真实或敏感数据。\n\n'
            f'[DSH 生成记录](https://github.com/{repo}/actions/runs/{run_id})')
    found = next((c for c in comments(repo, issue) if c['user']['login'] == 'github-actions[bot]' and marker in (c.get('body') or '')), None)
    if found:
        api('PATCH', f'/repos/{repo}/issues/comments/{found["id"]}', {'body': body})
    else:
        api('POST', f'/repos/{repo}/issues/{issue}/comments', {'body': body})


if __name__ == '__main__':
    {'prepare': prepare, 'notify': notify}[sys.argv[1]]()

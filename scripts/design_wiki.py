"""Publish trusted DSH design artifacts as navigable GitHub Wiki pages."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from issue_agent import api
from prototype_pages import artifact, positive, validate_run, output, member
from design_output import write_bundle

MARKER = '<!-- dsh-design-wiki -->'
START, END = '<!-- dsh-navigation:start -->', '<!-- dsh-navigation:end -->'
STATE = '_dsh-design-index.json'


def label(value):
    return str(value).replace('\n', ' ').replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('<', '&lt;')


def managed(existing, section):
    if START in existing or END in existing:
        if existing.count(START) != 1 or existing.count(END) != 1 or existing.index(START) > existing.index(END):
            raise ValueError('Invalid existing managed navigation markers')
        before, rest = existing.split(START, 1)
        _, after = rest.split(END, 1)
        return before + START + '\n' + section + '\n' + END + after
    return existing.rstrip() + '\n\n' + START + '\n' + section + '\n' + END + '\n'


def wiki_link(repo, page):
    if not re.fullmatch(r'[A-Za-z0-9-]+', page):
        raise ValueError('Unsafe wiki page name')
    return f'https://github.com/{repo}/wiki/{page}'


def state_validate(state):
    if not isinstance(state, dict) or len(state) > 1000:
        raise ValueError('Invalid wiki index')
    for key, entry in state.items():
        if not isinstance(entry, dict) or set(entry) != {'issue', 'role', 'latest', 'versions'} or entry['role'] not in {'overview', 'detailed'} or key != f"{positive(entry['issue'])}-{entry['role']}":
            raise ValueError('Invalid wiki index entry')
        positive(entry['latest'])
        if not isinstance(entry['versions'], list) or not entry['versions'] or len(entry['versions']) > 1000 or any(type(v) is not int or v < 1 for v in entry['versions']) or entry['latest'] != max(entry['versions']):
            raise ValueError('Invalid wiki version ordering')
    return state


def base(issue, role):
    return f'Issue-{issue}-' + ('Overview' if role == 'overview' else 'Detailed')


def rewrite(text, prefix, names):
    def replace(match):
        target = match[2].removeprefix('./')
        if target in names:
            return f'[{match[1]}]({prefix}{names[target]})'
        return match[0]
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace, text)


def assemble(existing, state, repo, issue, run_id, role, raw):
    positive(issue); positive(run_id); state_validate(state)
    if role not in {'overview', 'detailed'}:
        raise ValueError('Unsupported wiki role')
    with tempfile.TemporaryDirectory() as folder:
        bundle = Path(folder) / 'bundle'
        write_bundle(raw, bundle, role)
        current = json.loads((bundle / 'design.json').read_text()).get('schema_version') == 2
        docs = {str(p.relative_to(bundle)): p.read_text() for p in bundle.rglob('*.md') if p.name != 'README.md'}
    prefix = base(issue, role)
    names = {'design.md': '', 'task-contracts.md': '-Tasks', 'decisions.md': '-Decisions', 'overview-update.md': '-Overview-Update'}
    names.update({'milestones.md': '-Milestones', 'ui.md': '-UI', 'documentation.md': '-Documentation'})
    names.update({name: '-' + Path(name).stem for name in docs if name.startswith('modules/')})
    result = dict(existing)
    key = f'{issue}-{role}'
    entry = state.get(key, {'issue': issue, 'role': role, 'latest': run_id, 'versions': []})
    entry = {**entry, 'versions': sorted(set(entry['versions'] + [run_id]), reverse=True), 'latest': max(entry['latest'], run_id)}
    for variant in [f'{prefix}-Run-{run_id}'] + ([prefix] if run_id == entry['latest'] else []):
        for name, text in docs.items():
            filename = variant + names[name] + '.md'
            if filename in existing and MARKER not in existing[filename]:
                raise ValueError('Refusing to overwrite an unmanaged wiki page: ' + filename)
            nav = f'[文档目录]({wiki_link(repo, "DSH-Documents")}) · [本设计]({wiki_link(repo, variant)}) · [版本记录]({wiki_link(repo, prefix + "-History")})'
            provenance = f'来源：[Issue #{issue}](https://github.com/{repo}/issues/{issue}) · [DSH run {run_id}](https://github.com/{repo}/actions/runs/{run_id})'
            rendered = MARKER + '\n\n' + nav + '\n\n' + provenance + '\n\n' + rewrite(text, variant, names)
            if name == 'design.md' and not current:
                rendered += '\n\n## 阅读导航\n\n' + '\n'.join(f'- [{label(Path(n).stem)}]({wiki_link(repo, variant + names[n])})' for n in docs if n != 'design.md') + '\n'
            if '-Run-' in variant and filename in existing and existing[filename] != rendered:
                raise ValueError('Immutable wiki version differs from existing content')
            result[filename] = rendered
    state = {**state, key: entry}
    directory = '# DSH 设计文档目录\n\n按任务阅读概要设计、详细设计、任务契约、模式依据、模块文档与概要修订。\n\n| Issue | 设计 | 最新 DSH 运行 | 版本 |\n|---|---|---|---|\n'
    sidebar = '[DSH 文档目录](DSH-Documents)\n'
    for entry in sorted(state.values(), key=lambda e: (e['issue'], e['role'])):
        p = base(entry['issue'], entry['role'])
        title = '概要设计' if entry['role'] == 'overview' else '详细设计'
        directory += f"| #{entry['issue']} | [{title}]({wiki_link(repo, p)}) | {entry['latest']} | [历史]({wiki_link(repo, p + '-History')}) |\n"
        sidebar += f"\n- [#{entry['issue']} {title}]({p})\n  - [任务输入输出]({p}-Tasks)\n  - [设计决策]({p}-Decisions)\n"
        for suffix, heading in [('Milestones', 'MVP 里程碑与发布'), ('UI', '界面与交互'), ('Documentation', '文档交付')]:
            if p + '-' + suffix + '.md' in result:
                sidebar += f'  - [{heading}]({p}-{suffix})\n'
        if entry['role'] == 'detailed':
            sidebar += f'  - [概要同步修订]({p}-Overview-Update)\n'
        module_pages = sorted(set(re.findall(re.escape(p) + r'-MOD-\d{2,3}(?!\d)', result.get(p + '.md', ''))))
        for page in module_pages:
            heading = re.search(r'^# (MOD-\d{2,3} · .+)$', result.get(page + '.md', ''), re.M)
            module_title = heading[1] if heading else page.split('-MOD-')[1] + ' 模块'
            sidebar += f'  - [{label(module_title)}]({page})\n'
        history = MARKER + f'\n\n# Issue #{entry["issue"]} · {title}版本\n\n'
        history += '\n'.join(f'- [DSH run {version}]({wiki_link(repo, p + "-Run-" + str(version))})' for version in entry['versions']) + '\n'
        history_name = p + '-History.md'
        if history_name in result and MARKER not in result[history_name]:
            raise ValueError('Refusing to overwrite unmanaged version page')
        result[history_name] = history
    if 'DSH-Documents.md' in result and MARKER not in result['DSH-Documents.md']:
        raise ValueError('Refusing to overwrite unmanaged document directory')
    result['DSH-Documents.md'] = MARKER + '\n\n' + directory
    result['_Sidebar.md'] = managed(result.get('_Sidebar.md', ''), sidebar)
    result['Home.md'] = managed(result.get('Home.md', '# 项目 Wiki\n'), '## DSH 设计文档\n\n[打开文档目录](DSH-Documents)\n\n设计完成后自动同步；从侧栏选择任务、模块或历史版本。')
    return result, state


def git(directory, *args):
    env = dict(os.environ)
    token = env.get('WIKI_TOKEN') or env['GH_TOKEN']
    env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.https://github.com/.extraheader', GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode())
    completed = subprocess.run(['git', *args], cwd=directory, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if completed.returncode:
        error = completed.stderr.lower()
        reason = 'repository_unavailable' if 'not found' in error else ('access_denied' if any(s in error for s in ['403', 'permission denied', 'authentication failed']) else 'git_operation_failed')
        raise RuntimeError('Wiki Git operation failed: ' + reason + '. No credentials are included in diagnostics.')
    return completed.stdout


def publish():
    repo = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    repository = api('GET', f'/repos/{repo}')
    ids = os.environ['SOURCE_RUN_IDS'].split(',')
    if not 1 <= len(ids) <= 10 or any(not re.fullmatch(r'[1-9]\d*', v.strip()) for v in ids):
        raise ValueError('Expected 1–10 numeric source run IDs')
    sources = []
    for value in ids:
        run_id = positive(int(value))
        run = api('GET', f'/repos/{repo}/actions/runs/{run_id}')
        validate_run(run, repo, repository['default_branch'])
        archive = artifact(repo, run_id, 'issue-agent-input', required=False)
        if archive is None: continue
        with archive:
            metadata = json.loads(member(archive, 'metadata.json'))
        role = metadata.get('agent')
        if role not in {'overview', 'detailed'} or metadata.get('config', {}).get('mode') != 'design': continue
        with artifact(repo, run_id, 'design-deliverable') as archive:
            matches = [e for e in archive.infolist() if e.filename == 'design.json']
            if len(matches) != 1 or matches[0].file_size > 1_100_000: raise ValueError('Invalid design artifact')
            raw = archive.read(matches[0]).decode('utf-8')
        sources.append((positive(metadata['issue_number']), run_id, role, raw))
    if not sources:
        output(status='skipped'); return
    preview = Path(os.environ['RUNNER_TEMP']) / 'design-wiki-preview'
    preview.mkdir(parents=True, exist_ok=True)
    dry = os.environ.get('DRY_RUN') == 'true'
    ready = bool(repository['has_wiki'])
    # A reviewable preview exists even if the Wiki backend is not initialized.
    initial, initial_state = {}, {}
    for issue, run_id, role, raw in sources:
        initial, initial_state = assemble(initial, initial_state, repo, issue, run_id, role, raw)
    for filename, text in initial.items():
        (preview / filename).write_text(text)
    (preview / STATE).write_text(json.dumps(initial_state, ensure_ascii=False, indent=2))
    initialization_error = False
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        existing, state = {}, {}
        if ready and not dry:
            try:
                git(work, 'clone', '--depth=1', f'https://github.com/{repo}.wiki.git', '.')
            except RuntimeError as error:
                print(str(error))
                # Public read probe distinguishes missing initialization from token access.
                import urllib.request
                import urllib.error
                request = urllib.request.Request(f'https://github.com/{repo}.wiki.git/info/refs?service=git-upload-pack', headers={'User-Agent': 'DSH-Wiki-Publisher'})
                try:
                    with urllib.request.urlopen(request, timeout=30) as response:
                        print('Wiki anonymous Git read HTTP status:', response.status)
                except urllib.error.HTTPError as probe:
                    print('Wiki anonymous Git read HTTP status:', probe.code)
                except urllib.error.URLError:
                    print('Wiki anonymous Git read unavailable')
                ready = False
                initialization_error = True
            if ready:
                existing = {p.name: p.read_text() for p in work.glob('*.md') if p.is_file() and not p.is_symlink()}
                if (work / STATE).is_symlink(): raise ValueError('Refusing wiki index symlink')
                if (work / STATE).exists(): state = state_validate(json.loads((work / STATE).read_text()))
        for issue, run_id, role, raw in sources:
            existing, state = assemble(existing, state, repo, issue, run_id, role, raw)
        for filename, text in existing.items():
            if Path(filename).name != filename or any(c in filename for c in '/\\\r\n\0') or not filename.endswith('.md'): raise ValueError('Unsafe stored page name')
            (preview / filename).write_text(text)
            if ready and not dry:
                if (work / filename).is_symlink(): raise ValueError('Refusing wiki symlink target')
                (work / filename).write_text(text)
        (preview / STATE).write_text(json.dumps(state, ensure_ascii=False, indent=2))
        if ready and not dry:
            (work / STATE).write_text(json.dumps(state, ensure_ascii=False, indent=2))
            git(work, 'add', '--', '.')
            if git(work, 'diff', '--cached', '--name-only').strip():
                git(work, '-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', 'commit', '-m', 'Publish DSH design documents and navigation')
                git(work, 'push', 'origin', 'HEAD')
            for issue, run_id, role, raw in sources:
                marker = f'<!-- dsh-wiki:{issue}:{role}:{run_id} -->'
                body = marker + '\n📚 **设计文档已同步到 Wiki**\n\n' + f'[文档目录]({wiki_link(repo, "DSH-Documents")}) · [此任务最新设计]({wiki_link(repo, base(issue, role))}) · [本次固定版本]({wiki_link(repo, base(issue, role) + "-Run-" + str(run_id))})'
                from issue_agent import comments
                if not any(marker in c['body'] for c in comments(repo, issue)):
                    api('POST', f'/repos/{repo}/issues/{issue}/comments', {'body': body})
    status = 'preview' if dry else ('published' if ready else 'needs_wiki_initialization_or_access')
    output(status=status)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f'## DSH Wiki\n\n状态：`{status}`。已生成目录、侧栏、任务与模块页面、概要修订和历史版本。\n')
        if status == 'published': summary.write(f'\n[打开 Wiki 文档目录]({wiki_link(repo, "DSH-Documents")})\n')
        elif not ready: summary.write('\nWiki 尚未启用、初始化或发布身份缺少访问权限。请确认 Wiki 已启用并创建首个 Home 页；必要时配置 WIKI_PUBLISH_TOKEN（仅限本仓库写权限），然后重新运行 Design Wiki 补发。预览 artifact 已生成，无需再次调用模型。\n')
    if initialization_error:
        raise RuntimeError('Wiki clone failed: preview retained; initialize Home or check publishing access and rerun.')


if __name__ == '__main__':
    publish()

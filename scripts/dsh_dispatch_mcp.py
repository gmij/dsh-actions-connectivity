"""Repository-scoped MCP bridge: native custom agent -> DSH Actions.

No arbitrary URLs, workflows, models, commands, or role arguments are accepted.
The token is supplied by the Agents secret, never by tool arguments.
"""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

REPO = 'gmij/dsh-actions-connectivity'
WORKFLOW = 'issue-agent.yml'
ROOT = Path(__file__).resolve().parents[1]


def api(method, path, body=None):
    token = os.environ.get('DSH_DISPATCH_TOKEN', '')
    if not token or token.startswith('${'):
        raise ValueError('Missing Agents secret COPILOT_MCP_DSH_DISPATCH_TOKEN')
    request = urllib.request.Request('https://api.github.com' + path,
        method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        # Do not expose response bodies or credentials to the model.
        raise ValueError(f'GitHub API HTTP {error.code}; check repository-scoped Actions write and Issues read permissions') from None


def dispatch(arguments):
    if set(arguments) != {'issue_number'} or type(arguments['issue_number']) is not int or arguments['issue_number'] < 1:
        raise ValueError('Only one positive integer issue_number is accepted')
    role = os.environ.get('DSH_AGENT_ID', '')
    agents = json.loads((ROOT / 'agents/registry.json').read_text())['agents']
    if role not in agents or not agents[role]['enabled']:
        raise ValueError('Agent profile has no enabled registered DSH role')
    number = arguments['issue_number']
    issue = api('GET', f'/repos/{REPO}/issues/{number}')
    if issue.get('pull_request') or issue.get('state') != 'open':
        raise ValueError('Target must be an open Issue in the configured repository')
    repository = api('GET', f'/repos/{REPO}')
    api('POST', f'/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches', {
        'ref': repository['default_branch'],
        'inputs': {'issue_number': str(number), 'agent': role, 'force': 'false'}})
    return {'status': 'dispatch_accepted', 'engine': 'DSH', 'agent': role,
            'issue_number': number,
            'actions_url': f'https://github.com/{REPO}/actions/workflows/{WORKFLOW}',
            'issue_url': f'https://github.com/{REPO}/issues/{number}',
            'notice': 'Dispatch accepted, not task completion. DSH Actions posts its own execution result to the Issue; an identical task may be skipped.'}


def handle(message):
    method = message.get('method')
    identifier = message.get('id')
    if identifier is None:
        return None
    result = None
    if method == 'initialize':
        result = {'protocolVersion': message.get('params', {}).get('protocolVersion', '2024-11-05'),
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'dsh-actions-dispatch', 'version': '1.0.0'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': [{'name': 'dispatch_issue',
            'description': 'Dispatch the selected native agent role to the real DSH Actions engine. Does not itself solve the task.',
            'inputSchema': {'type': 'object', 'properties': {'issue_number': {'type': 'integer', 'minimum': 1}},
                            'required': ['issue_number'], 'additionalProperties': False},
            'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'openWorldHint': True}}]}
    elif method == 'tools/call':
        try:
            params = message.get('params', {})
            if params.get('name') != 'dispatch_issue':
                raise ValueError('Unknown tool')
            value = dispatch(params.get('arguments', {}))
            result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}], 'isError': False}
        except ValueError as error:
            result = {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
        except Exception:
            result = {'content': [{'type': 'text', 'text': 'Bridge failed; task has not been confirmed complete.'}], 'isError': True}
    else:
        return {'jsonrpc': '2.0', 'id': identifier, 'error': {'code': -32601, 'message': 'Method not found'}}
    return {'jsonrpc': '2.0', 'id': identifier, 'result': result}


if __name__ == '__main__':
    for line in sys.stdin:
        try:
            response = handle(json.loads(line))
        except (ValueError, TypeError):
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid request'}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)

import json
import os
import unittest
from unittest.mock import patch
import dsh_dispatch_mcp as bridge


class BridgeTests(unittest.TestCase):
    def test_dispatch_is_fixed_repo_workflow_role_and_no_force(self):
        with patch.dict(os.environ, {'DSH_AGENT_ID': 'reviewer'}), patch.object(bridge, 'api', side_effect=[{'state': 'open'}, {'default_branch': 'main'}, None]) as api:
            result = bridge.dispatch({'issue_number': 2})
        self.assertEqual(result['status'], 'dispatch_accepted')
        self.assertEqual(api.call_args.args, ('POST', '/repos/gmij/dsh-actions-connectivity/actions/workflows/issue-agent.yml/dispatches', {'ref': 'main', 'inputs': {'issue_number': '2', 'agent': 'reviewer', 'force': 'false'}}))

    def test_bad_input_never_calls_api(self):
        for args in [{}, {'issue_number': True}, {'issue_number': 0}, {'issue_number': '2'}, {'issue_number': 2, 'agent': 'other'}]:
            with patch.object(bridge, 'api') as api, self.assertRaises(ValueError):
                bridge.dispatch(args)
            api.assert_not_called()

    def test_invalid_role_never_calls_api(self):
        with patch.dict(os.environ, {'DSH_AGENT_ID': 'other'}), patch.object(bridge, 'api') as api, self.assertRaises(ValueError):
            bridge.dispatch({'issue_number': 2})
        api.assert_not_called()

    def test_pr_or_closed_never_dispatches(self):
        for issue in [{'state': 'closed'}, {'state': 'open', 'pull_request': {}}]:
            # pull_request is non-empty in GitHub's actual response.
            if 'pull_request' in issue:
                issue['pull_request'] = {'url': 'unused'}
            with patch.dict(os.environ, {'DSH_AGENT_ID': 'connectivity'}), patch.object(bridge, 'api', return_value=issue) as api, self.assertRaises(ValueError):
                bridge.dispatch({'issue_number': 2})
            self.assertEqual(api.call_count, 1)

    def test_missing_secret_returns_tool_error(self):
        with patch.dict(os.environ, {'DSH_DISPATCH_TOKEN': '', 'DSH_AGENT_ID': 'reviewer'}):
            result = bridge.handle({'id': 4, 'method': 'tools/call', 'params': {'name': 'dispatch_issue', 'arguments': {'issue_number': 2}}})
        self.assertTrue(result['result']['isError'])
        self.assertIn('Missing Agents secret', result['result']['content'][0]['text'])

    def test_initialize_and_tools(self):
        response = bridge.handle({'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26'}})
        self.assertEqual(response['result']['protocolVersion'], '2025-03-26')
        self.assertIsNone(bridge.handle({'method': 'notifications/initialized'}))
        self.assertEqual(bridge.handle({'id': 2, 'method': 'tools/list'})['result']['tools'][0]['name'], 'dispatch_issue')


if __name__ == '__main__':
    unittest.main()

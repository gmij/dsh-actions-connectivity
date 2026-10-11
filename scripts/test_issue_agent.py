import unittest
from issue_agent import select_agent, fingerprint


class RoutingTests(unittest.TestCase):
    agents = {k: {"label": "agent:" + k, "enabled": True} for k in ["reviewer", "connectivity"]}

    def test_unassigned_issue_is_not_a_task(self):
        self.assertIsNone(select_agent({"body": "ordinary question", "labels": []}, self.agents))

    def test_issue_form_selects_agent(self):
        self.assertEqual(select_agent({"body": "### Agent\n\nreviewer\n\n### Task\n\nReview code"}, self.agents), "reviewer")

    def test_label_overrides_old_form_selection(self):
        self.assertEqual(select_agent({"body": "### Agent\n\nreviewer", "labels": [{"name": "agent:connectivity"}]}, self.agents), "connectivity")

    def test_conflicting_or_unknown_labels_are_rejected(self):
        for labels in [["agent:reviewer", "agent:connectivity"], ["agent:unknown"]]:
            with self.assertRaises(ValueError):
                select_agent({"labels": [{"name": label} for label in labels]}, self.agents)

    def test_disabled_agent_is_rejected(self):
        with self.assertRaises(ValueError):
            select_agent({"labels": [{"name": "agent:reviewer"}]}, {"reviewer": {"enabled": False, "label": "agent:reviewer"}})

    def test_fingerprint_ignores_assignee_events_but_tracks_task_changes(self):
        issue = {"number": 1, "title": "Review", "body": "code"}
        key = fingerprint(issue, "reviewer", {}, "persona")
        self.assertEqual(key, fingerprint({**issue, "assignees": ["gmij"]}, "reviewer", {}, "persona"))
        self.assertNotEqual(key, fingerprint({**issue, "body": "new code"}, "reviewer", {}, "persona"))
        self.assertNotEqual(key, fingerprint(issue, "connectivity", {}, "persona"))

# Regression: native dispatcher instructions must not contaminate DSH context.
class NativeWorkerSeparationTests(unittest.TestCase):
    def test_dispatch_profiles_are_excluded_and_connectivity_gets_no_snapshot(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import issue_agent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profiles = root / '.github/agents'
            profiles.mkdir(parents=True)
            (profiles / 'dispatcher.agent.md').write_text('DISPATCHER_ONLY_INSTRUCTION')
            (root / 'business.py').write_text('BUSINESS_REVIEW_SOURCE')
            issue = {'number': 8, 'title': 'worker task', 'body': 'Please return WORKER_OK'}
            with patch.object(issue_agent, 'ROOT', root):
                reviewer = issue_agent.build_prompt(issue, 'reviewer')
                connectivity = issue_agent.build_prompt(issue, 'connectivity')
            self.assertNotIn('DISPATCHER_ONLY_INSTRUCTION', reviewer)
            self.assertIn('BUSINESS_REVIEW_SOURCE', reviewer)
            self.assertNotIn('BUSINESS_REVIEW_SOURCE', connectivity)
            self.assertIn('dispatch is complete', connectivity)
            self.assertIn('Please return WORKER_OK', connectivity)


if __name__ == "__main__":
    unittest.main()

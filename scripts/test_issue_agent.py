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


if __name__ == "__main__":
    unittest.main()

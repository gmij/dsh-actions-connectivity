import copy
import json
import unittest
from design_wiki import assemble, state_validate, managed
from test_design_output import example

REPO = 'gmij/dsh-actions-connectivity'

class WikiTests(unittest.TestCase):
    def test_navigation_modules_and_manual_pages_preserved(self):
        old = {'Home.md': '# Human home\n', '_Sidebar.md': '[Manual](Manual)\n', '中文说明.md': '人工内容'}
        pages, state = assemble(old, {}, REPO, 17, 100, 'detailed', json.dumps(example()))
        self.assertEqual(pages['中文说明.md'], '人工内容')
        self.assertIn('Human home', pages['Home.md'])
        self.assertIn('[Manual](Manual)', pages['_Sidebar.md'])
        self.assertIn('Issue-17-Detailed-MOD-01', pages['_Sidebar.md'])
        self.assertIn('](Issue-17-Detailed-MOD-01)', pages['Issue-17-Detailed.md'])
        self.assertNotIn('](modules/', pages['Issue-17-Detailed.md'])
        self.assertIn('TASK-01.batch', pages['Issue-17-Detailed-MOD-02.md'])
        self.assertIn('概要修订', pages['Issue-17-Detailed-Overview-Update.md'])
        self.assertEqual(state['17-detailed']['latest'], 100)
        repeated, again = assemble(pages, state, REPO, 17, 100, 'detailed', json.dumps(example()))
        self.assertEqual(repeated, pages)
        self.assertEqual(again, state)

    def test_history_does_not_downgrade_latest_or_show_removed_module(self):
        pages, state = assemble({}, {}, REPO, 17, 100, 'detailed', json.dumps(example()))
        changed = copy.deepcopy(example())
        changed['modules'] = [dict(changed['modules'][0], task_ids=['TASK-01', 'TASK-02'])]
        pages, state = assemble(pages, state, REPO, 17, 200, 'detailed', json.dumps(changed))
        latest = pages['Issue-17-Detailed.md']
        self.assertNotIn('](Issue-17-Detailed-MOD-02)', pages['_Sidebar.md'])
        pages, state = assemble(pages, state, REPO, 17, 99, 'detailed', json.dumps(example()))
        self.assertEqual(pages['Issue-17-Detailed.md'], latest)
        self.assertEqual(state['17-detailed']['versions'], [200, 100, 99])
        self.assertIn('Run-100', pages['Issue-17-Detailed-History.md'])

    def test_refuses_overwrites_and_invalid_state(self):
        with self.assertRaises(ValueError):
            assemble({'Issue-17-Detailed.md': 'human'}, {}, REPO, 17, 100, 'detailed', json.dumps(example()))
        pages, state = assemble({}, {}, REPO, 17, 100, 'detailed', json.dumps(example()))
        changed = example(); changed['summary_markdown'] = 'Changed'
        with self.assertRaises(ValueError):
            assemble(pages, state, REPO, 17, 100, 'detailed', json.dumps(changed))
        with self.assertRaises(ValueError): state_validate({'bad': 'text'})
        with self.assertRaises(ValueError): managed('<!-- dsh-navigation:start -->', 'new')
        with self.assertRaises(ValueError): assemble({}, {}, REPO, '../1', 1, 'detailed', json.dumps(example()))

class MvpWikiTests(unittest.TestCase):
    def test_new_mvp_pages_links_and_old_fixed_versions_survive(self):
        from test_mvp_design import example2
        pages, state = assemble({}, {}, REPO, 17, 100, 'detailed', json.dumps(example()))
        fixed = {k:v for k,v in pages.items() if '-Run-100' in k}
        pages, state = assemble(pages, state, REPO, 17, 200, 'detailed', json.dumps(example2()))
        self.assertEqual(fixed, {k:v for k,v in pages.items() if '-Run-100' in k})
        self.assertIn('](Issue-17-Detailed-Milestones)', pages['Issue-17-Detailed.md'])
        self.assertIn('界面与交互', pages['_Sidebar.md'])
        self.assertLess(pages['_Sidebar.md'].index('MVP 里程碑'), pages['_Sidebar.md'].index('MOD-01'))
        self.assertLess(pages['_Sidebar.md'].index('MOD-02'), pages['_Sidebar.md'].index('任务索引与契约'))
        self.assertIn('SyncApiContract', pages['Issue-17-Detailed-MOD-02.md'])
        self.assertIn('发布门槛', pages['Issue-17-Detailed-Milestones.md'])
        again, _ = assemble(pages, state, REPO, 17, 100, 'detailed', json.dumps(example()))
        self.assertEqual(fixed, {k:v for k,v in again.items() if '-Run-100' in k})

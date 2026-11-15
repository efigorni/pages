"""Regression checks for forward-only lesson generation; no repository writes."""
import copy
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import build_all as BA
import lessonlib as LL
import validate as V


class ForwardBuildTests(unittest.TestCase):
    def test_kicker_option_preserves_every_other_slide_field(self):
        kit = LL.Kit()
        legacy = LL.load_lesson(LL.LESSONS / 'g7-makom-baolam')
        legacy['steps'][0]['body'].extend([
            {'video': {'title': 'סרטון', 'url': 'https://example.org/video', 'before': 'מה רואים?', 'art': 'heart'}},
            {'source_slide': {'slides': [1], 'why': 'תמונה', 'art': 'heart'}},
        ])
        old = LL.derive(legacy, kit)
        clean = copy.deepcopy(legacy)
        clean['slide_kickers'] = False
        clean['pdf_backup'] = False
        new = LL.derive(clean, kit)
        self.assertTrue(any(s['kicker'] for s in old['slides']))
        self.assertTrue(all(not s['kicker'] for s in new['slides']))
        self.assertEqual([{**s, 'kicker': ''} for s in old['slides']], new['slides'])
        plan, slides, _ = LL.render_lesson(clean, kit)
        self.assertNotIn('class="kicker"', slides)
        self.assertNotIn('class="kicker"', plan)
        self.assertNotIn('href="slides.pdf"', plan)
        self.assertEqual(old['core_minutes'], new['core_minutes'])

    def run_builder(self, args, inventory=None):
        dirs = [Path('/lessons/g4-a'), Path('/lessons/g5-b'), Path('/lessons/g7-c')]
        metadata = {d: {'grade': g, 'title': d.name} for d, g in zip(dirs, [4, 5, 7])}
        report = MagicMock(errors=[], warnings=[])
        with patch.object(LL, 'lesson_dirs', return_value=dirs), \
             patch.object(LL, 'load_lesson', side_effect=metadata.__getitem__), \
             patch.object(LL, 'inventory', return_value=inventory or {}), \
             patch.object(LL, 'sync_assets') as sync, \
             patch.object(LL, 'Kit') as kit, \
             patch.object(LL, 'write_atomic') as write, \
             patch.object(BA.B, 'build_one', return_value=(report, {'L': {}})) as build, \
             patch.object(BA.subprocess, 'call') as export:
            self.assertEqual(0, BA.main(args))
        return dirs, sync, kit, write, build, export

    def test_hub_only_reads_metadata_without_build_assets_or_pdf(self):
        _, sync, kit, write, build, export = self.run_builder(['--hub-only'])
        for operation in (sync, kit, build, export):
            operation.assert_not_called()
        write.assert_called_once()
        html = write.call_args.args[1]
        for grade in (4, 5, 7):
            self.assertIn(f'data-v="{grade}"', html)
        self.assertEqual(3, html.count('<article class="card"'))

    def test_grade_scope_leaves_other_lessons_and_assets_alone(self):
        dirs, sync, _, write, build, export = self.run_builder(['--grades', '4', '5', '--no-sync-assets'])
        self.assertEqual(dirs[:2], [call.args[0] for call in build.call_args_list])
        sync.assert_not_called()
        export.assert_not_called()
        self.assertIn('g7-c/index.html', write.call_args.args[1])

    def test_fit_ignores_hidden_kicker(self):
        report = V.Report('test')
        report.slide_kickers = False
        with patch.object(LL, 'slide_fit', return_value=(0, {})) as fit:
            V.check_fit(report, 'slide', 'hidden', 'title')
        self.assertEqual('', fit.call_args.args[0])

    def test_hub_uses_inventory_for_shared_legacy_grade_associations(self):
        _, _, _, write, build, _ = self.run_builder(
            ['--hub-only'], {'g7-c': {'grades_served': [4, 5, 7]}})
        build.assert_not_called()
        html = write.call_args.args[1]
        self.assertIn('data-grade="4 5 7"', html)
        self.assertIn('כיתות ד׳, ה׳, ז׳', html)


if __name__ == '__main__':
    unittest.main()

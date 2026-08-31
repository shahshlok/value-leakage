"""Tests of substantive failure modes: joins, missing labels, paired contrasts."""
import unittest

import numpy as np

from prepare_h7 import observed_label, source_key, unique, value_status
from analyze_h7 import cell_statistics, mean_masked, summarize


def record(y, claim, threshold=10):
    return dict(estimate=y, claim=claim, threshold=threshold)


class H7Tests(unittest.TestCase):
    def test_labels_require_literal_boolean_and_successful_finish(self):
        for label in ('true', 1, 0, None, [], {}):
            self.assertIsNone(observed_label(dict(http_status='200', finish_reason='stop', parsed={'x': label}), 'x'))
        self.assertIs(observed_label(dict(http_status='200', finish_reason='stop', parsed={'x': False}), 'x'), False)
        for status, finish in [('500', 'stop'), ('200', 'length')]:
            self.assertIsNone(observed_label(dict(http_status=status, finish_reason=finish, parsed={'x': True}), 'x'))

    def test_embedded_keys_not_positions_and_duplicates_fail(self):
        rows = [dict(model_dir='m', condition='above_good', row_i=i) for i in (19, 2)]
        keyed = unique(rows, source_key)
        self.assertEqual(keyed[('m', 'above_good', 2)]['row_i'], 2)
        with self.assertRaises(ValueError):
            unique(rows + rows[:1], source_key)

    def test_value_categories_are_separate(self):
        self.assertEqual([value_status(x) for x in (None, np.inf, 0, -1, 1)],
                         ['unparseable', 'nonfinite', 'zero', 'negative', 'positive'])

    def test_threshold_ties_and_nonpositive_values(self):
        result = cell_statistics([record(10, True), record(11, True), record(0, True), record(-2, True)])
        self.assertEqual(result['binary', 'all'], .25)
        self.assertAlmostEqual(result['log', 'all'], (np.log(10) + np.log(11)) / 2)

    def test_missing_labels_do_not_become_negative(self):
        result = cell_statistics([record(100, None), record(10, True), record(1, False)])
        self.assertAlmostEqual(result['log', 'negative'], 0)
        self.assertAlmostEqual(result['log', 'known_label'], np.log(10) / 2)

    def test_all_positive_filter_is_exactly_tautological_in_every_draw(self):
        rows = [record(x, True) for x in (10, 20, 30, None)]
        indices = np.random.default_rng(12).integers(4, size=(100, 4))
        result = cell_statistics(rows, indices)
        for metric in ('log', 'binary'):
            np.testing.assert_allclose(result[metric, 'positive'], result[metric, 'all'], equal_nan=True)

    def test_paired_bootstrap_cancels_common_noise(self):
        # All-positive traces: independent resamples would wrongly inflate D variance.
        a = [record(x, True) for x in (2, 3, 17)]
        b = [record(x, True) for x in (1, 5, 11)]
        idx = np.random.default_rng(42).integers(3, size=(1000, 3))
        sa, sb = cell_statistics(a, idx), cell_statistics(b, idx)
        diff = (sa['log', 'positive'] - sb['log', 'positive']) - (sa['log', 'all'] - sb['log', 'all'])
        self.assertTrue(np.all(diff == 0))

    def test_decomposition_in_same_records(self):
        a = cell_statistics([record(100, None), record(20, True), record(3, False)])
        b = cell_statistics([record(80, None), record(10, True), record(4, False)])
        d = {s: a['log', s] - b['log', s] for s in ('all', 'known_label', 'positive')}
        self.assertAlmostEqual(d['positive'] - d['all'], (d['positive'] - d['known_label']) + (d['known_label'] - d['all']))

    def test_empty_strata_propagate_and_intervals_withheld(self):
        result = cell_statistics([record(2, True), record(3, True)])
        self.assertTrue(np.isnan(result['log', 'negative']))
        self.assertTrue(np.isnan(np.mean([1, result['log', 'negative']])))
        stats = summarize(1, np.array([1, 2, np.nan]))
        self.assertIsNone(stats['ci95_low'])
        self.assertEqual(stats['bootstrap_undefined'], 1)
        self.assertIsNotNone(stats['conditional_finite_ci95_low'])


if __name__ == '__main__':
    unittest.main()

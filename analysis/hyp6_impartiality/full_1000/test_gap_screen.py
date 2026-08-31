"""Regression checks for false-positive extraction traps, run offline."""
import unittest
from decimal import Decimal

from analyze_gaps import conclusion, equations, gap


class ScreenRegressions(unittest.TestCase):
    def test_scale_before_comma_is_not_dropped(self):
        self.assertEqual(conclusion('My final estimate is roughly 29.5 million, which is uncertain.')[0], Decimal('29500000'))

    def test_component_commitment_is_not_global_total(self):
        self.assertIsNone(conclusion("I'll go with 450 per giraffe average.")[0])
        self.assertIsNone(conclusion("I'll settle on 250 as my best estimate. That gives 30 million total.")[0])

    def test_conflicting_final_commitments_stay_unresolved(self):
        self.assertIsNone(conclusion('Final answer: 30 million.\nFinal answer: 35 million.')[0])

    def test_bulleted_equations_are_not_range_suffixes(self):
        items = equations('- Masai: 40000 × 350 = 14000000\n- Captive: 1000 × 300 = 300000')
        self.assertEqual(len(items), 2)
        self.assertEqual(Decimal(items[0]['computed']), Decimal('14000000'))

    def test_no_suffix_of_longer_product_or_sum(self):
        self.assertFalse(equations('2 × 120000 × 300 = 72000000'))
        self.assertFalse(equations('100 + 120000 × 300 = 36000100'))

    def test_rounding_is_not_large_gap_and_tie_rule_is_explicit(self):
        rounded = gap(Decimal('30000000'), Decimal('29800000'), 'above_good', Decimal('30000000'))
        self.assertFalse(rounded['at_least_1pct'])
        self.assertFalse(rounded['crosses_threshold'])
        crossed = gap(Decimal('30000001'), Decimal('30000000'), 'above_good', Decimal('30000000'))
        self.assertTrue(crossed['crosses_threshold'])


if __name__ == '__main__':
    unittest.main()

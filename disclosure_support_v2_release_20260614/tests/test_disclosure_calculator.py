import unittest

from disclosure_calculator import extract_summary_lines, inject_dynamic_borderlines


FINANCIAL_DATA = {
    "net_assets": 1_000,
    "net_sales": 2_000,
    "recurring_profit": 100,
    "net_income": 80,
    "capital_stock": 500,
}


class DisclosureCalculatorTests(unittest.TestCase):
    def test_dynamic_fraction_and_fixed_amount(self):
        text = "純資産額の100分の3未満。払込金額が1億円未満。"
        result = inject_dynamic_borderlines(text, FINANCIAL_DATA)
        self.assertIn("30百万円", result)
        self.assertIn("100百万円", result)
        self.assertEqual(len(extract_summary_lines(text, FINANCIAL_DATA)), 2)


if __name__ == "__main__":
    unittest.main()

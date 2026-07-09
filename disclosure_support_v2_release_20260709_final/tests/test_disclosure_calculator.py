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

    def test_fraction_injected_amount_is_not_reprocessed(self):
        result = inject_dynamic_borderlines("純資産額の100分の3未満。", FINANCIAL_DATA)
        self.assertEqual(result.count("判定ライン:"), 1)

    def test_extracts_more_fixed_amount_and_people_lines(self):
        text = "取得価額が500百万円以上。支出額が3000万円未満。従業員数が50名以上。"
        result = inject_dynamic_borderlines(text, FINANCIAL_DATA)
        self.assertIn("500百万円", result)
        self.assertIn("30百万円", result)
        self.assertIn("50人", result)
        self.assertEqual(len(extract_summary_lines(text, FINANCIAL_DATA)), 3)


if __name__ == "__main__":
    unittest.main()

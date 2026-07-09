import unittest
from collections import Counter

from data_service import filter_records, get_categories, load_records, regime_text


class DataServiceTests(unittest.TestCase):
    def test_reference_dataset_is_complete(self):
        records = load_records()
        self.assertEqual(len(records), 101)
        self.assertEqual(len({item["mapping_id"] for item in records}), 101)
        self.assertEqual(len(get_categories(records)), 6)
        self.assertEqual(sum(item["manual_review_flag"] for item in records), 13)
        self.assertEqual(
            Counter(item["disclosure_category"] for item in records),
            {
                "上場会社・決定事実": 40,
                "上場会社・発生事実": 28,
                "上場会社・決算情報": 2,
                "子会社等・決定事実": 16,
                "子会社等・発生事実": 14,
                "子会社等・決算情報": 1,
            },
        )

    def test_search_and_missing_regime_label(self):
        records = load_records()
        results = filter_records(records, query="自己株式")
        self.assertTrue(results)
        self.assertTrue(all("自己株式" in item["search_text"] for item in results))
        missing = next(item for item in records if not item.get("extraordinary_report_requirements", "").strip())
        self.assertIn("非該当を意味しません", regime_text(missing, "extraordinary"))


if __name__ == "__main__":
    unittest.main()

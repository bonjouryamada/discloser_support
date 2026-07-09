import io
import unittest
import zipfile
from unittest.mock import patch

import edinet_fetcher


class DummyResponse:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content

    def json(self):
        return self._payload


def make_xbrl_zip(html):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr("XBRL/PublicDoc/test.htm", html)
    return payload.getvalue()


class EdinetFetcherTests(unittest.TestCase):
    def test_sec_code_matches_exact_five_digits_and_four_digit_input(self):
        payload = {
            "results": [
                {
                    "docID": "S100BAD",
                    "docDescription": "有価証券報告書",
                    "filerName": "別会社",
                    "secCode": "17203",
                },
                {
                    "docID": "S100GOOD",
                    "docDescription": "有価証券報告書",
                    "filerName": "対象会社",
                    "secCode": "72030",
                },
            ]
        }

        with patch("edinet_fetcher.requests.get", return_value=DummyResponse(payload=payload)):
            self.assertEqual(
                edinet_fetcher.get_doc_id_for_date("2026-07-08", "7203", "https://example.test", {}),
                ("S100GOOD", "対象会社"),
            )

    def test_sec_code_does_not_use_unsafe_substring_match(self):
        payload = {
            "results": [
                {
                    "docID": "S100BAD",
                    "docDescription": "有価証券報告書",
                    "filerName": "別会社",
                    "secCode": "17203",
                }
            ]
        }

        with patch("edinet_fetcher.requests.get", return_value=DummyResponse(payload=payload)):
            self.assertIsNone(
                edinet_fetcher.get_doc_id_for_date("2026-07-08", "7203", "https://example.test", {})
            )

    def test_xbrl_excludes_abstract_and_prefers_consolidated_current_context(self):
        html = """
        <html><body>
          <ix:nonfraction name="jppfs_cor:NetAssetsAbstract"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">999999999999</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantNonConsolidatedMember" unitRef="JPY">100000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">200000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetSales"
              contextRef="PriorYearDurationConsolidatedMember" unitRef="JPY">999000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetSales"
              contextRef="CurrentYearDurationNonConsolidatedMember" unitRef="JPY">300000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetSales"
              contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">400000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:OrdinaryIncome"
              contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">50000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:ProfitLossAttributableToOwnersOfParent"
              contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">60000000</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:CapitalStock"
              contextRef="CurrentYearInstantNonConsolidatedMember" unitRef="JPY">70000000</ix:nonfraction>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(make_xbrl_zip(html))

        self.assertEqual(result["net_assets"], 200)
        self.assertEqual(result["net_sales"], 400)
        self.assertEqual(result["recurring_profit"], 50)
        self.assertEqual(result["net_income"], 60)
        self.assertEqual(result["capital_stock"], 70)
        self.assertEqual(result["missing_keys"], [])
        self.assertEqual(result["warnings"], [])

    def test_missing_financial_values_are_reported_separately_from_real_zero(self):
        html = """
        <html><body>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">0</ix:nonfraction>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(make_xbrl_zip(html))

        self.assertEqual(result["net_assets"], 0)
        self.assertIn("net_sales", result["missing_keys"])
        self.assertNotIn("net_assets", result["missing_keys"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()

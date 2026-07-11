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
        self.text = ""

    def json(self):
        return self._payload


def make_xbrl_zip(html):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr("XBRL/PublicDoc/test.htm", html)
    return payload.getvalue()


def make_zip_with_file(path, content):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr(path, content)
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
                {
                    "doc_id": "S100GOOD",
                    "filer_name": "対象会社",
                    "sec_code": "72030",
                    "doc_description": "有価証券報告書",
                    "submit_datetime": "2026-07-08",
                    "search_date": "2026-07-08",
                    "period_start": None,
                    "period_end": None,
                    "period_label": "",
                },
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
          <ix:nonfraction name="jppfs_cor:OrdinaryProfit"
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

    def test_xbrl_prefers_nonzero_value_over_stronger_current_context(self):
        html = """
        <html><body>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">0</ix:nonfraction>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstant" unitRef="JPY">250000000</ix:nonfraction>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(
            make_xbrl_zip(html)
        )

        self.assertEqual(result["net_assets"], 250)

    def test_xbrl_extracts_period_metadata_from_dei_tags(self):
        html = """
        <html><body>
          <ix:nonnumeric name="jpdei_cor:CurrentFiscalYearStartDateDEI"
              contextRef="FilingDateInstant">2025-04-01</ix:nonnumeric>
          <ix:nonnumeric name="jpdei_cor:CurrentFiscalYearEndDateDEI"
              contextRef="FilingDateInstant">2026-03-31</ix:nonnumeric>
          <ix:nonnumeric name="jpdei_cor:DocumentTitleCoverPage"
              contextRef="FilingDateInstant">有価証券報告書</ix:nonnumeric>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">200000000</ix:nonfraction>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(
            make_xbrl_zip(html),
            {"doc_id": "S100META", "filer_name": "対象会社"},
        )

        self.assertEqual(result["doc_info"]["period_start"], "2025-04-01")
        self.assertEqual(result["doc_info"]["period_end"], "2026-03-31")
        self.assertEqual(result["doc_info"]["period_label"], "2026年3月期")
        self.assertIn("有価証券報告書", result["doc_info_label"])
        self.assertIn("2026年3月期", result["doc_info_label"])
        self.assertIn("docID: S100META", result["doc_info_label"])

    def test_latest_yuho_returns_document_metadata_dict(self):
        payload = {
            "results": [
                {
                    "docID": "S100META",
                    "docDescription": "有価証券報告書",
                    "filerName": "対象会社",
                    "secCode": "72030",
                    "submitDateTime": "2026-07-08 10:30",
                    "periodStart": "2025-04-01",
                    "periodEnd": "2026-03-31",
                }
            ]
        }

        with patch("edinet_fetcher.get_api_key", return_value="dummy"), patch(
            "edinet_fetcher.requests.get", return_value=DummyResponse(payload=payload)
        ):
            result = edinet_fetcher.get_latest_yuho_doc_id("7203", max_days=1)

        self.assertEqual(result["doc_id"], "S100META")
        self.assertEqual(result["filer_name"], "対象会社")
        self.assertEqual(result["doc_description"], "有価証券報告書")
        self.assertEqual(result["submit_datetime"], "2026-07-08 10:30")
        self.assertEqual(result["period_start"], "2025-04-01")
        self.assertEqual(result["period_end"], "2026-03-31")
        self.assertEqual(result["period_label"], "2026年3月期")

    def test_documents_api_uses_subscription_key_parameter(self):
        calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
            return DummyResponse(payload={"results": []})

        with patch("edinet_fetcher.get_api_key", return_value="dummy-key"), patch(
            "edinet_fetcher.requests.get", side_effect=fake_get
        ):
            edinet_fetcher.get_latest_yuho_doc_id("7203", max_days=1)

        self.assertEqual(calls[0]["params"]["Subscription-Key"], "dummy-key")
        self.assertEqual(calls[0]["headers"]["Ocp-Apim-Subscription-Key"], "dummy-key")

    def test_documents_api_status_error_is_not_reported_as_not_found(self):
        with patch("edinet_fetcher.requests.get", return_value=DummyResponse(status_code=401)):
            with self.assertRaisesRegex(RuntimeError, "EDINET APIエラー"):
                edinet_fetcher.get_doc_id_for_date(
                    "2026-07-08",
                    "7203",
                    "https://example.test",
                    {"Ocp-Apim-Subscription-Key": "dummy-key"},
                )

    def test_extract_financial_data_from_xbrl_includes_doc_info(self):
        html = """
        <html><body>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">200000000</ix:nonfraction>
        </body></html>
        """

        with patch("edinet_fetcher.get_api_key", return_value="dummy"), patch(
            "edinet_fetcher.requests.get",
            return_value=DummyResponse(status_code=200, content=make_xbrl_zip(html)),
        ):
            result = edinet_fetcher.extract_financial_data_from_xbrl(
                "S100DOC",
                {
                    "doc_id": "S100DOC",
                    "doc_description": "有価証券報告書",
                    "period_end": "2026-03-31",
                },
            )

        self.assertEqual(result["doc_info"]["doc_id"], "S100DOC")
        self.assertEqual(result["doc_info"]["period_label"], "2026年3月期")
        self.assertIn("有価証券報告書", result["doc_info_label"])
        self.assertIn("2026年3月期", result["doc_info_label"])

    def test_xbrl_download_uses_subscription_key_parameter(self):
        html = """
        <html><body>
          <ix:nonfraction name="jppfs_cor:NetAssets"
              contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">200000000</ix:nonfraction>
        </body></html>
        """
        calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
            return DummyResponse(status_code=200, content=make_xbrl_zip(html))

        with patch("edinet_fetcher.get_api_key", return_value="dummy-key"), patch(
            "edinet_fetcher.requests.get", side_effect=fake_get
        ):
            edinet_fetcher.extract_financial_data_from_xbrl("S100DOC")

        self.assertEqual(calls[0]["params"]["Subscription-Key"], "dummy-key")
        self.assertEqual(calls[0]["headers"]["Ocp-Apim-Subscription-Key"], "dummy-key")

    def test_financial_or_insurance_ordinary_income_can_be_used_as_sales(self):
        html = """
        <html><body>
          <span name="jpcrp_cor:OrdinaryIncome"
              contextRef="CurrentYearDurationConsolidatedMember">123000000</span>
          <span name="jpcrp_cor:OrdinaryProfit"
              contextRef="CurrentYearDurationConsolidatedMember">45000000</span>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(make_xbrl_zip(html))

        self.assertEqual(result["net_sales"], 123)
        self.assertEqual(result["recurring_profit"], 45)

    def test_raw_xbrl_element_names_are_parsed_for_ifrs_insurance_filings(self):
        xbrl = """
        <xbrli:xbrl>
          <jpdei_cor:CurrentFiscalYearEndDateDEI contextRef="FilingDateInstant">2026-03-31</jpdei_cor:CurrentFiscalYearEndDateDEI>
          <jpigp_cor:EquityIFRS contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">0</jpigp_cor:EquityIFRS>
          <jpigp_cor:InsuranceRevenueIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">0</jpigp_cor:InsuranceRevenueIFRS>
          <jpigp_cor:ProfitBeforeTaxIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">0</jpigp_cor:ProfitBeforeTaxIFRS>
          <jpigp_cor:ProfitAttributableToOwnersOfParentIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">0</jpigp_cor:ProfitAttributableToOwnersOfParentIFRS>
          <jpigp_cor:EquityIFRS contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">5941000000000</jpigp_cor:EquityIFRS>
          <jpigp_cor:InsuranceRevenueIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">7229000000000</jpigp_cor:InsuranceRevenueIFRS>
          <jpigp_cor:ProfitBeforeTaxIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">1184000000000</jpigp_cor:ProfitBeforeTaxIFRS>
          <jpigp_cor:ProfitAttributableToOwnersOfParentIFRS contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">880000000000</jpigp_cor:ProfitAttributableToOwnersOfParentIFRS>
          <jppfs_cor:CapitalStock contextRef="CurrentYearInstantNonConsolidatedMember" unitRef="JPY">0</jppfs_cor:CapitalStock>
          <jppfs_cor:CapitalStock contextRef="CurrentYearInstantNonConsolidatedMember" unitRef="JPY">150000000000</jppfs_cor:CapitalStock>
        </xbrli:xbrl>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(
            make_zip_with_file("XBRL/PublicDoc/test.xbrl", xbrl)
        )

        self.assertEqual(result["net_assets"], 5_941_000)
        self.assertEqual(result["net_sales"], 7_229_000)
        self.assertEqual(result["recurring_profit"], 1_184_000)
        self.assertEqual(result["net_income"], 880_000)
        self.assertEqual(result["capital_stock"], 150_000)
        self.assertEqual(result["doc_info"]["period_label"], "2026年3月期")
        self.assertEqual(result["missing_keys"], [])

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

    def test_all_zero_result_includes_at_most_twenty_safe_debug_candidates(self):
        tags = "".join(
            '<ix:nonfraction name="jppfs_cor:NetAssets" '
            'contextRef="CurrentYearInstantConsolidatedMember" unitRef="JPY">'
            '0</ix:nonfraction>'
            for _ in range(25)
        )

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(
            make_xbrl_zip(f"<html><body>{tags}</body></html>")
        )

        self.assertEqual(len(result["debug_candidates"]), 20)
        self.assertEqual(
            set(result["debug_candidates"][0]),
            {"tag_name", "context_ref", "raw_value", "normalized_value", "candidate_key"},
        )
        self.assertEqual(result["debug_candidates"][0]["candidate_key"], "net_assets")
        self.assertEqual(result["debug_candidates"][0]["normalized_value"], 0)

        nonzero = edinet_fetcher._format_financial_data({"net_assets": (1, 1)})
        self.assertNotIn("debug_candidates", nonzero)

    def test_unmatched_nonzero_candidates_are_ranked_and_returned_without_parsed_data(self):
        zero_tags = "".join(
            f'<ix:nonfraction name="custom:UnknownMetric{index}" '
            'contextRef="CurrentYearDurationConsolidatedMember" unitRef="JPY">'
            '0</ix:nonfraction>'
            for index in range(25)
        )
        html = f"""
        <html><body>
          {zero_tags}
          <ix:nonfraction name="custom:AssetMetric"
              contextRef="CurrentYearDurationConsolidatedMember"
              unitRef="JPY">123000000</ix:nonfraction>
        </body></html>
        """

        result = edinet_fetcher._extract_financial_data_from_zip_bytes(
            make_xbrl_zip(html)
        )

        self.assertEqual(result["missing_keys"], list(edinet_fetcher.FINANCIAL_KEYS))
        self.assertTrue(all(result[key] == 0 for key in edinet_fetcher.FINANCIAL_KEYS))
        self.assertEqual(len(result["debug_candidates"]), 20)
        self.assertEqual(
            result["debug_candidates"][0]["tag_name"],
            "custom:AssetMetric",
        )
        self.assertEqual(result["debug_candidates"][0]["candidate_key"], "unmatched")
        self.assertEqual(result["debug_candidates"][0]["normalized_value"], 123)


if __name__ == "__main__":
    unittest.main()

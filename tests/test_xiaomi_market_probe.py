import unittest
from tools.xiaomi_market_probe import TARGET, parse_market_page, allowed_url

class MarketProbeTests(unittest.TestCase):
    def test_valid_store_detail(self):
        page = "<h1>Mi Fitness</h1><p>appID</p><p>1234567</p><p>版本号</p><p>3.59.9</p><p>包名</p><p>com.mi.health</p>"
        got = parse_market_page(page)
        self.assertEqual(got["app_id"], "1234567")
        self.assertEqual(got["package"], TARGET)
        self.assertEqual(got["candidate_url"], "https://app.mi.com/download/1234567")
        self.assertFalse(got["maintenance"])

    def test_international_package_must_not_match(self):
        page = "<p>appID 926314</p><p>包名 com.xiaomi.wearable</p><p>版本号 2.16.4</p>"
        self.assertIsNone(parse_market_page(page))

    def test_substring_not_identity(self):
        self.assertIsNone(parse_market_page("appID 1234567 com.mi.health.malicious"))

    def test_maintenance_blocks_candidate(self):
        page = "<p>appID 1234567</p><p>包名 com.mi.health</p><p>维护中</p>"
        self.assertTrue(parse_market_page(page)["maintenance"])

    def test_unsafe_urls(self):
        self.assertFalse(allowed_url("http://app.mi.com/download/123"))
        self.assertFalse(allowed_url("https://app.mi.com.evil.test/download/123"))
        self.assertFalse(allowed_url("https://evil.test/file.apk"))
        self.assertTrue(allowed_url("https://file.market.xiaomi.com/download/123"))

if __name__ == "__main__":
    unittest.main()

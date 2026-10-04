import asyncio
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.services.met_client import MetClient


class SearchPaginationTests(unittest.TestCase):
    def setUp(self):
        self.client = MetClient()
        self.requests = []

        def fetch(url):
            self.requests.append(url)
            params = parse_qs(urlsplit(url).query)
            offset = int(params["offset"][0])
            limit = int(params["limit"][0])
            return {"total": 14405, "objectIDs": list(range(offset, offset + limit))}

        self.client._fetch_json = fetch
        self.client.batch_fetch_objects = lambda ids: ids

        async def batch(ids):
            return ids

        self.client.batch_fetch_objects_async = batch

    def test_every_browse_path_returns_page_two_and_full_total(self):
        calls = [
            lambda: self.client.get_highlights(2, 24, "Oil on canvas"),
            lambda: self.client.get_by_medium("Paintings", 2, 24, True),
            lambda: self.client.get_by_department(11, 2, 24),
            lambda: self.client.search("Van Gogh & sunflowers", 11, "Paintings", True, 2, 24),
            lambda: asyncio.run(self.client.get_highlights_async(2, 24, "Oil on canvas")),
            lambda: asyncio.run(self.client.get_by_medium_async("Paintings", 2, 24, True)),
            lambda: asyncio.run(self.client.get_by_department_async(11, 2, 24)),
            lambda: asyncio.run(self.client.search_async("Van Gogh & sunflowers", 11, "Paintings", True, 2, 24)),
        ]
        for call in calls:
            with self.subTest(call=call):
                data = call()
                self.assertEqual(data["objects"], list(range(24, 48)))
                self.assertEqual(data["total"], 14405)
                self.assertTrue(data["has_more"])
        for url in self.requests:
            self.assertEqual(urlsplit(url).path, "/public/collection/v1.1/search")
        search = parse_qs(urlsplit(self.requests[-1]).query)
        self.assertEqual(search["q"], ["Van Gogh & sunflowers"])
        self.assertEqual(search["departmentId"], ["11"])
        self.assertEqual(search["medium"], ["Paintings"])
        self.assertEqual(search["isHighlight"], ["true"])

    def test_page_cache_does_not_repeat_previous_page(self):
        first = self.client.get_by_medium("Paintings", 1, 24)
        second = self.client.get_by_medium("Paintings", 2, 24)
        self.assertTrue(set(first["objects"]).isdisjoint(second["objects"]))
        self.client.get_by_medium("Paintings", 2, 24)
        self.assertEqual(len(self.requests), 2)

    def test_last_accessible_page_respects_met_limit(self):
        data = self.client.get_by_medium("Paintings", 209, 48)
        self.assertEqual(data["objects"], list(range(9984, 10000)))
        self.assertFalse(data["has_more"])
        past_end = self.client.get_by_medium("Paintings", 210, 48)
        self.assertEqual(past_end["objects"], [])
        self.assertFalse(past_end["has_more"])
        self.assertEqual(len(self.requests), 1)

    def test_invalid_pagination_is_rejected(self):
        for page, size in [(0, 24), (1, 0), (1, 501)]:
            with self.assertRaises(ValueError):
                self.client.get_by_medium("Paintings", page, size)


if __name__ == "__main__":
    unittest.main()

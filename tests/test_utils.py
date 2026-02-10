import unittest
from utils import format_size, get_display_width, pad_string, format_book_list_item

class TestUtils(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(512), "512B")
        self.assertEqual(format_size(1024), "1.0KB")
        self.assertEqual(format_size(1024 * 1024), "1.0MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0GB")
        self.assertEqual(format_size(None), "0B")
        self.assertEqual(format_size(-1), "0B")

    def test_display_width_and_pad(self):
        text = "中文ABC"
        width = get_display_width(text)
        self.assertTrue(width >= len(text))
        padded = pad_string(text, width + 2)
        self.assertEqual(get_display_width(padded), width + 2)

    def test_format_book_list_item_link(self):
        item_with_id = format_book_list_item(1, {"id": 123, "title": "书名", "file_name": "a.pdf", "file_size": 100})
        self.assertIn("https://t.me/", item_with_id)
        item_without_id = format_book_list_item(2, {"title": "书名", "file_name": "a.pdf", "file_size": 100})
        self.assertNotIn("https://t.me/", item_without_id)

if __name__ == "__main__":
    unittest.main()

import unittest
from keyboards import get_search_keyboard, get_book_detail_keyboard, get_filter_menu_keyboard, get_settings_keyboard

class TestKeyboards(unittest.TestCase):
    def test_search_keyboard_layout(self):
        kb = get_search_keyboard(current_page=0, total_pages=3, book_ids=list(range(10)))
        # InlineKeyboardMarkup has inline_keyboard: List[List[InlineKeyboardButton]]
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 7)
        self.assertEqual(len(rows[0]), 3)
        self.assertEqual(len(rows[1]), 4)
        self.assertEqual(len(rows[2]), 4)
        self.assertEqual(len(rows[3]), 3)
        self.assertEqual(len(rows[4]), 4)
        self.assertEqual(len(rows[5]), 3)
        self.assertEqual(len(rows[6]), 5)
        self.assertEqual(rows[6][0].text, "·")
        self.assertEqual(rows[6][2].text, ">")

    def test_search_keyboard_page_picker_layout(self):
        kb = get_search_keyboard(current_page=0, total_pages=50, book_ids=list(range(10)), mode="page_picker")
        rows = kb.inline_keyboard
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(len(rows[-1]), 5)

    def test_detail_keyboard(self):
        kb = get_book_detail_keyboard(123)
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 1)
        self.assertEqual(rows[0][0].text, "⬇️ 免费下载")

    def test_filter_menu_keyboard(self):
        kb = get_filter_menu_keyboard("format", {"format": "PDF"})
        rows = kb.inline_keyboard
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(len(rows[-1]), 5)

    def test_settings_keyboard(self):
        kb = get_settings_keyboard({"content_rating": "ALL"})
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 6)

if __name__ == "__main__":
    unittest.main()

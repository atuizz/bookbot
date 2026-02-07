import unittest
from keyboards import get_search_keyboard, get_book_detail_keyboard

class TestKeyboards(unittest.TestCase):
    def test_search_keyboard_layout(self):
        kb = get_search_keyboard(current_page=0, total_pages=3, book_ids=list(range(10)))
        # InlineKeyboardMarkup has inline_keyboard: List[List[InlineKeyboardButton]]
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(rows[0]), 3)
        self.assertEqual(len(rows[1]), 4)
        self.assertEqual(len(rows[2]), 3)
        self.assertEqual(len(rows[3]), 5)
        # First page prev disabled（noop），next enabled
        self.assertEqual(rows[3][0].text, "·")
        self.assertEqual(rows[3][2].text, ">")

    def test_detail_keyboard(self):
        kb = get_book_detail_keyboard(123)
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 1)
        self.assertEqual(rows[0][0].text, "⬇️ 免费下载")

if __name__ == "__main__":
    unittest.main()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_search_keyboard(current_page: int, total_pages: int, book_ids: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # 1-10 Number buttons (rows of 3, 4, 3)
    # Map indices 0-9 to book_ids
    # If fewer than 10 books, only show available buttons or disable them
    
    # Row 1: 1, 2, 3
    for i in range(1, 4):
        idx = i - 1
        if idx < len(book_ids):
            builder.button(text=str(i), callback_data=f"sel:{book_ids[idx]}")
        else:
            builder.button(text=" ", callback_data="noop")
    
    # Row 2: 4, 5, 6, 7
    for i in range(4, 8):
        idx = i - 1
        if idx < len(book_ids):
            builder.button(text=str(i), callback_data=f"sel:{book_ids[idx]}")
        else:
            builder.button(text=" ", callback_data="noop")
        
    # Row 3: 8, 9, 10
    for i in range(8, 11):
        idx = i - 1
        if idx < len(book_ids):
            builder.button(text=str(i), callback_data=f"sel:{book_ids[idx]}")
        else:
            builder.button(text=" ", callback_data="noop")
        
    # Row 4: Navigation & Tools (5 buttons)
    # <<, Page, >>, Settings, Close
    prev_page = max(0, current_page - 1)
    next_page = min(total_pages - 1, current_page + 1)
    
    # Prev
    if current_page > 0:
        builder.button(text="<", callback_data=f"page:{prev_page}")
    else:
        builder.button(text="·", callback_data="noop")
        
    # Page Indicator
    builder.button(text=f"{current_page + 1}/{total_pages}", callback_data="noop")
    
    # Next
    if current_page < total_pages - 1:
        builder.button(text=">", callback_data=f"page:{next_page}")
    else:
        builder.button(text="·", callback_data="noop")
        
    # Extra buttons to make it 5
    builder.button(text="⚙️", callback_data="settings")
    builder.button(text="❌", callback_data="close")

    # Adjust layout
    # 3, 4, 3, 5
    builder.adjust(3, 4, 3, 5)
    
    return builder.as_markup()

def get_book_detail_keyboard(book_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Row 1: Download (Full width or main)
    # Using book_id to avoid length limit
    builder.button(text="⬇️ 免费下载", callback_data=f"dl:{book_id}")
    
    # Row 2: Collections, Related
    builder.button(text="❤️ 收藏", callback_data=f"fav:{book_id}")
    builder.button(text="🔗 相关书籍", callback_data=f"rel:{book_id}")
    
    builder.adjust(1, 2)
    return builder.as_markup()

def get_moderation_keyboard(short_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ 通过", callback_data=f"mod_approve:{short_id}")
    builder.button(text="❌ 拒绝", callback_data=f"mod_reject:{short_id}")
    return builder.as_markup()

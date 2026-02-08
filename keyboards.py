from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_search_keyboard(current_page: int, total_pages: int, book_ids: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Generate number buttons only for available books
    # Layout: 5 buttons per row
    for i, book_id in enumerate(book_ids):
        # Display number is i + 1
        builder.button(text=str(i + 1), callback_data=f"sel:{book_id}")
    
    # Calculate how many rows of numbers we have
    # We want rows of 5
    num_books = len(book_ids)
    rows_of_5 = num_books // 5
    remainder = num_books % 5
    layout = [5] * rows_of_5
    if remainder > 0:
        layout.append(remainder)
        
    # Navigation Row
    # <<, Page, >>, Settings, Close
    
    # Prev
    if current_page > 0:
        prev_page = current_page - 1
        builder.button(text="<", callback_data=f"page:{prev_page}")
    else:
        builder.button(text=" ", callback_data="noop") # Keep spacing
        
    # Page Indicator
    builder.button(text=f"{current_page + 1}/{total_pages}", callback_data="noop")
    
    # Next
    if current_page < total_pages - 1:
        next_page = current_page + 1
        builder.button(text=">", callback_data=f"page:{next_page}")
    else:
        builder.button(text=" ", callback_data="noop") # Keep spacing

    # Tools
    # builder.button(text="⚙️", callback_data="settings")
    builder.button(text="❌", callback_data="close")

    # Add navigation row layout (4 buttons: <, P/T, >, X)
    layout.append(4)
    
    builder.adjust(*layout)
    
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

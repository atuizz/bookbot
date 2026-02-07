import unicodedata
from typing import List, Dict, Any

def get_display_width(text: str) -> int:
    """Calculate the display width of a string (East Asian Width)."""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_string(text: str, width: int) -> str:
    """Pad a string with spaces to reach the desired display width."""
    current_width = get_display_width(text)
    if current_width >= width:
        return text
    return text + ' ' * (width - current_width)

def format_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f}MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f}GB"

def format_book_list_item(index: int, book: Dict[str, Any], bot_username: str = "bookbot") -> str:
    """Format a single book item for the list view."""
    title = book.get('title') or book.get('file_name', 'Unknown')
    file_name = book.get('file_name', '')
    ext = file_name.split('.')[-1].upper() if '.' in file_name else 'FILE'
    size = format_size(book.get('file_size', 0))
    downloads = book.get('downloads', 0)
    
    # Truncate title
    display_len = get_display_width(title)
    if display_len > 30:
        # Simple truncation
        title = title[:20] + "..." 
    
    # Using specific link to trigger start with book id, assuming deep linking is implemented
    # Or just a visual link if not clickable for action
    # Based on screenshot, it looks like a blue link. Let's make it a deep link to the bot itself.
    # We will use the 'id' field which is the database primary key.
    book_id = book.get('id')
    
    # Constructing the lines
    # Line 1: 01. Title (Hyperlink)
    # Line 2:    · EXT · SIZE · DLs
    
    # We use a dummy link or a deep link
    # Deep link format: https://t.me/bookbot?start=id_123
    # But for now, let's just make it bold or use a placeholder link if we don't have bot username
    # The requirement says "Blue Link". In TG HTML, <a href="...">text</a> makes it blue.
    # We can link to the bot's start param.
    
    if book_id is None:
        line1 = f"{index:02d}. {title}"
    else:
        line1 = f"{index:02d}. <a href=\"https://t.me/{bot_username}?start=book_{book_id}\">{title}</a>"
    line2 = f"   · {ext} · {size} · {downloads}DL"
    
    return f"{line1}\n<code>{line2}</code>"

def format_book_list(
    books: List[Dict[str, Any]],
    start_index: int = 1,
    total_hits: int = 0,
    time_taken: float = 0.0,
    bot_username: str = "bookbot",
) -> str:
    """Format the entire list of books."""
    header = f"🔍 搜索结果：第 {start_index}-{start_index+len(books)-1} 条，共 {total_hits}（用时 {time_taken:.2f} 秒）\n\n"
    items = [format_book_list_item(start_index + i, book, bot_username=bot_username) for i, book in enumerate(books)]
    footer = "\n\n💎 捐赠会员: 提升等级获得书币，等级权限翻倍，优先体验新功能"
    return header + "\n".join(items) + footer

def format_book_detail(book: Dict[str, Any]) -> str:
    """Format book details for the detail view."""
    title = book.get('title') or book.get('file_name')
    author = book.get('author', 'Unknown')
    size = format_size(book.get('file_size', 0))
    tags_list = book.get('tags', [])
    tags = " ".join([f"#{t}" for t in tags_list]) if tags_list else "#无标签"
    
    return (
        f"<b>{title}</b>\n"
        f"👤 作者: {author}\n"
        f"📦 体积: {size}\n"
        f"🏷 标签: {tags}\n"
        f"⬇️ 下载: {book.get('downloads', 0)} 次"
    )

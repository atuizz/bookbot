import unicodedata
import html
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

def truncate_display(text: str, max_width: int) -> str:
    if get_display_width(text) <= max_width:
        return text
    result = ""
    width = 0
    for ch in text:
        w = 2 if unicodedata.east_asian_width(ch) in ("F", "W", "A") else 1
        if width + w > max_width - 3:
            break
        result += ch
        width += w
    return result + "..."

def format_word_count(word_count: int) -> str:
    if word_count < 10000:
        return f"{word_count}字"
    if word_count < 100000000:
        return f"{word_count/10000:.1f}万字"
    return f"{word_count/100000000:.2f}亿字"

def format_book_list_item(index: int, book: Dict[str, Any], bot_username: str = "bookbot") -> str:
    """Format a single book item for the list view."""
    raw_title = book.get("title") or book.get("file_name", "Unknown")
    title = truncate_display(str(raw_title), 30)
    file_name = str(book.get("file_name", "") or "")
    ext = (
        str(book.get("ext") or "").upper()
        or (file_name.split(".")[-1].upper() if "." in file_name else "FILE")
    )
    size = format_size(book.get('file_size', 0))
    downloads = book.get('downloads', 0)
    collections = book.get("collections", 0)
    
    word_count = (
        book.get("word_count")
        or book.get("wordCount")
        or book.get("words")
        or book.get("wordcount")
    )
    rating = book.get("rating") or book.get("score") or book.get("douban_score")

    fields: list[str] = [ext, size]
    if isinstance(word_count, (int, float)) and word_count > 0:
        fields.append(format_word_count(int(word_count)))
    if isinstance(rating, (int, float)) and rating > 0:
        fields.append(f"{float(rating):.1f}")
    if isinstance(collections, int) and isinstance(downloads, int):
        fields.append(f"{collections}/{downloads}")
    elif isinstance(downloads, int):
        fields.append(f"{downloads}DL")

    book_id = book.get("id")
    safe_title = html.escape(title)
    if book_id is None:
        line1 = f"{index:02d}. {safe_title}"
    else:
        line1 = f"{index:02d}. <a href=\"https://t.me/{bot_username}?start=book_{book_id}\">{safe_title}</a>"
    line2 = "   · " + " · ".join(fields)
    
    return f"{line1}\n<code>{line2}</code>"

def format_book_list(
    books: List[Dict[str, Any]],
    query: str = "",
    start_index: int = 1,
    total_hits: int = 0,
    time_taken: float = 0.0,
    bot_username: str = "bookbot",
) -> str:
    """Format the entire list of books."""
    end_index = start_index + len(books) - 1
    safe_query = html.escape(query or "")
    header = f"🔍 搜书关键词: <code>{safe_query}</code> Results {start_index}-{end_index} of {total_hits}（用时 {time_taken:.2f} 秒）\n\n"
    items = [format_book_list_item(start_index + i, book, bot_username=bot_username) for i, book in enumerate(books)]
    footer = "\n\n💎 捐赠会员: 提升等级获得书币，等级权限翻倍，优先体验新功能"
    return header + "\n".join(items) + footer

def format_book_detail(book: Dict[str, Any]) -> str:
    """Format book details for the detail view."""
    title = html.escape(str(book.get("title") or book.get("file_name") or "Unknown"))
    author = html.escape(str(book.get("author", "Unknown") or "Unknown"))
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

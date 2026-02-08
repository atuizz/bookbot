from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def _sort_button_text(current_sort: str, sort_key: str, label: str) -> str:
    if current_sort == sort_key:
        return f"{label}↓"
    return label

def _filter_button_text(filters: dict, key: str, label: str) -> str:
    if not filters:
        return f"{label}▾"
    value = filters.get(key)
    if not value:
        return f"{label}▾"
    if value == "ALL":
        return f"{label}▾"
    if key == "format" and isinstance(value, str):
        return f"{label}:{value}▾"
    if key == "rating" and isinstance(value, str):
        return f"{label}:{value}▾"
    if key == "size" and isinstance(value, str):
        return f"{label}:{value}▾"
    if key == "words" and isinstance(value, str):
        return f"{label}:{value}▾"
    return f"{label}▾"

def _build_page_quick_row(current_page: int, total_pages: int) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    current_display = current_page + 1
    buttons.append(InlineKeyboardButton(text=f"{current_display}▾", callback_data="pagesel"))
    for i in range(1, 6):
        p = current_page + i
        if p >= total_pages:
            break
        buttons.append(InlineKeyboardButton(text=str(p + 1), callback_data=f"page:{p}"))
    if total_pages > (current_page + 6):
        buttons.append(InlineKeyboardButton(text=f"...{total_pages}", callback_data=f"jump:{total_pages - 1}"))
    return buttons

def _build_page_picker_rows(current_page: int, total_pages: int) -> tuple[list[int], list[InlineKeyboardButton]]:
    group_size = 10
    group_start = (current_page // group_size) * group_size
    group_end = min(group_start + group_size, total_pages)
    page_buttons: list[InlineKeyboardButton] = []
    for p in range(group_start, group_end):
        label = str(p + 1)
        if p == current_page:
            label = f"·{label}·"
        page_buttons.append(InlineKeyboardButton(text=label, callback_data=f"page:{p}"))

    layout: list[int] = []
    remaining = len(page_buttons)
    if remaining > 0:
        c = min(remaining, 3)
        layout.append(c)
        remaining -= c
    if remaining > 0:
        c = min(remaining, 4)
        layout.append(c)
        remaining -= c
    if remaining > 0:
        c = min(remaining, 3)
        layout.append(c)

    nav: list[InlineKeyboardButton] = []
    prev_group = max(group_start - group_size, 0)
    next_group = min(group_start + group_size, max(total_pages - 1, 0))
    if group_start > 0:
        nav.append(InlineKeyboardButton(text="«", callback_data=f"jump:{prev_group}"))
    else:
        nav.append(InlineKeyboardButton(text="·", callback_data="noop"))
    nav.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="noop"))
    if group_end < total_pages:
        nav.append(InlineKeyboardButton(text="»", callback_data=f"jump:{next_group}"))
    else:
        nav.append(InlineKeyboardButton(text="·", callback_data="noop"))
    nav.append(InlineKeyboardButton(text="返回", callback_data="back:search"))
    nav.append(InlineKeyboardButton(text="❌", callback_data="close"))
    return layout, page_buttons + nav

def get_search_keyboard(
    current_page: int,
    total_pages: int,
    book_ids: list,
    mode: str = "default",
    sort: str = "best",
    filters: dict | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if mode == "page_picker":
        layout, items = _build_page_picker_rows(current_page, total_pages)
        for b in items:
            builder.add(b)
        builder.adjust(*layout, 5)
        return builder.as_markup()

    sizes: list[int] = []

    if total_pages > 1:
        quick = _build_page_quick_row(current_page, total_pages)
        for b in quick:
            builder.add(b)
        sizes.append(len(quick))

    for label, key in [("分级", "rating"), ("格式", "format"), ("体积", "size"), ("字数", "words")]:
        builder.button(text=_filter_button_text(filters or {}, key, label), callback_data=f"fltmenu:{key}")
    sizes.append(4)

    builder.button(text=_sort_button_text(sort, "best", "最佳"), callback_data="sort:best")
    builder.button(text=_sort_button_text(sort, "hot", "最热"), callback_data="sort:hot")
    builder.button(text=_sort_button_text(sort, "new", "最新"), callback_data="sort:new")
    builder.button(text=_sort_button_text(sort, "big", "最大"), callback_data="sort:big")
    sizes.append(4)

    for i, book_id in enumerate(book_ids):
        builder.button(text=str(i + 1), callback_data=f"sel:{book_id}")

    num_books = len(book_ids)
    layout = []
    if num_books > 0:
        count = min(num_books, 3)
        layout.append(count)
        num_books -= count
    if num_books > 0:
        count = min(num_books, 4)
        layout.append(count)
        num_books -= count
    if num_books > 0:
        count = min(num_books, 3)
        layout.append(count)
        num_books -= count

    if current_page > 0:
        builder.button(text="<", callback_data=f"page:{current_page - 1}")
    else:
        builder.button(text="·", callback_data="noop")
    builder.button(text=f"{current_page + 1}/{total_pages}", callback_data="noop")
    if current_page < total_pages - 1:
        builder.button(text=">", callback_data=f"page:{current_page + 1}")
    else:
        builder.button(text="·", callback_data="noop")
    builder.button(text="⚙️", callback_data="settings")
    builder.button(text="❌", callback_data="close")
    layout.append(5)

    builder.adjust(*sizes, *layout)
    return builder.as_markup()

def get_filter_menu_keyboard(filter_key: str, selected: dict | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected = selected or {}
    sizes: list[int] = []

    if filter_key == "format":
        options = ["ALL", "PDF", "EPUB", "TXT", "MOBI", "AZW3"]
        labels = {"ALL": "全部"}
        for v in options:
            text = labels.get(v, v)
            if selected.get("format") == v:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"flt:format:{v}")
        sizes.extend([3, 3])
    elif filter_key == "size":
        options = [("ALL", "全部"), ("<5MB", "<5MB"), ("5-20MB", "5-20MB"), ("20-50MB", "20-50MB"), (">50MB", ">50MB")]
        for v, text in options:
            if selected.get("size") == v:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"flt:size:{v}")
        sizes.extend([3, 2])
    elif filter_key == "words":
        options = [("ALL", "全部"), ("<10万", "<10万"), ("10-50万", "10-50万"), ("50-100万", "50-100万"), (">100万", ">100万")]
        for v, text in options:
            if selected.get("words") == v:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"flt:words:{v}")
        sizes.extend([3, 2])
    else:
        options = [("ALL", "全部"), ("G", "全年龄"), ("R15", "R15"), ("R18", "R18")]
        for v, text in options:
            if selected.get("rating") == v:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"flt:rating:{v}")
        sizes.extend([2, 2])

    builder.button(text="清除", callback_data=f"fltclr:{filter_key}")
    builder.button(text="·", callback_data="noop")
    builder.button(text="·", callback_data="noop")
    builder.button(text="返回", callback_data="back:search")
    builder.button(text="❌", callback_data="close")
    sizes.append(5)
    builder.adjust(*sizes)
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

def get_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="设置内容分级", callback_data="setmenu:content_rating")
    builder.button(text="搜索按钮模式", callback_data="setmenu:search_button_mode")

    builder.button(text="添加屏蔽标签", callback_data="setmenu:block_tags_add")
    builder.button(text="删除屏蔽标签", callback_data="setmenu:block_tags_del")

    builder.button(text="隐藏个人信息", callback_data="set:hide_personal_info")
    builder.button(text="隐藏上传列表", callback_data="set:hide_upload_list")

    builder.button(text="关闭上传反馈消息", callback_data="set:mute_upload_feedback")
    builder.button(text="关闭邀请反馈消息", callback_data="set:mute_invite_feedback")

    builder.button(text="关闭书籍动态消息", callback_data="set:mute_feed")

    builder.button(text="返回搜索", callback_data="back:search")
    builder.button(text="❌ 关闭", callback_data="close")

    builder.adjust(2, 2, 2, 2, 1, 2)
    return builder.as_markup()

def get_settings_menu_keyboard(menu_key: str, settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sizes: list[int] = []

    if menu_key == "content_rating":
        options = [("ALL", "全部"), ("G", "全年龄"), ("R15", "R15"), ("R18", "R18")]
        current = settings.get("content_rating", "ALL")
        for v, text in options:
            if v == current:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"setv:content_rating:{v}")
        sizes.extend([2, 2])
    elif menu_key == "search_button_mode":
        options = [("preview", "预览模式"), ("download", "极速下载")]
        current = settings.get("search_button_mode", "preview")
        for v, text in options:
            if v == current:
                text = f"·{text}·"
            builder.button(text=text, callback_data=f"setv:search_button_mode:{v}")
        sizes.append(2)
    else:
        builder.button(text="暂未开放", callback_data="noop")
        sizes.append(1)

    builder.button(text="返回设置", callback_data="back:settings")
    builder.button(text="返回搜索", callback_data="back:search")
    builder.button(text="❌ 关闭", callback_data="close")
    sizes.append(3)
    builder.adjust(*sizes)
    return builder.as_markup()

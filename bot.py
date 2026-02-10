import asyncio
import logging
import time
import json
import sys
from typing import Optional, Union

# Use uvloop on non-Windows systems for better performance
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from services import meili_service, db_service, redis_service
from utils import format_book_list, format_book_detail, format_size
from keyboards import (
    get_search_keyboard,
    get_book_detail_keyboard,
    get_moderation_keyboard,
    get_filter_menu_keyboard,
    get_settings_keyboard,
    get_settings_menu_keyboard,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot & Dispatcher
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Helpers ---

def render_settings_text(settings: dict) -> str:
    rating_label = {
        "ALL": "全部",
        "G": "全年龄",
        "R15": "R15",
        "R18": "R18",
    }.get(settings.get("content_rating", "ALL"), "全部")
    mode_label = "预览模式" if settings.get("search_button_mode", "preview") == "preview" else "极速下载"

    def yn(value: bool) -> str:
        return "是" if value else "否"

    lines = [
        f"全局内容分级:{rating_label}",
        f"搜索按钮模式:{mode_label}",
        f"隐藏个人信息:{yn(bool(settings.get('hide_personal_info', False)))}",
        f"隐藏上传列表:{yn(bool(settings.get('hide_upload_list', False)))}",
        "",
        f"关闭上传反馈消息:{yn(bool(settings.get('mute_upload_feedback', False)))}",
        f"关闭邀请反馈消息:{yn(bool(settings.get('mute_invite_feedback', False)))}",
        f"关闭书籍动态消息:{yn(bool(settings.get('mute_feed', False)))}",
    ]
    return "\n".join(lines)

async def search_and_render(
    event: Union[Message, CallbackQuery], 
    query: str, 
    page: int = 0, 
    limit: int = 10, 
    filter_type: str = None,
    keyboard_mode: str = "default",
    sort: str = "best",
    filters: dict | None = None,
):
    """
    Execute search and render results. 
    Handles both Message (new search) and CallbackQuery (pagination).
    """
    start_time = time.time()

    if isinstance(event, Message):
        chat_id = event.chat.id
        ctx_key = event.from_user.id if event.from_user else chat_id
        reply_method = event.answer
    else:
        chat_id = event.message.chat.id
        ctx_key = event.from_user.id if event.from_user else chat_id
        reply_method = event.message.edit_text

    filters = filters or {}
    if isinstance(event, Message):
        user_settings = await redis_service.get_user_settings(ctx_key)
        if user_settings.get("content_rating") and user_settings.get("content_rating") != "ALL":
            filters.setdefault("rating", user_settings.get("content_rating"))

    def to_filter_expr(filters_dict: dict) -> list[str]:
        parts: list[str] = []
        fmt = filters_dict.get("format")
        if isinstance(fmt, str) and fmt and fmt != "ALL":
            parts.append(f'ext = "{fmt}"')

        rating = filters_dict.get("rating")
        rating_map = {"G": 0, "R15": 1, "R18": 2}
        if isinstance(rating, str) and rating in rating_map:
            parts.append(f"content_rating <= {rating_map[rating]}")

        size = filters_dict.get("size")
        size_map = {
            "<5MB": (None, 5 * 1024 * 1024),
            "5-20MB": (5 * 1024 * 1024, 20 * 1024 * 1024),
            "20-50MB": (20 * 1024 * 1024, 50 * 1024 * 1024),
            ">50MB": (50 * 1024 * 1024, None),
        }
        if isinstance(size, str) and size in size_map:
            lo, hi = size_map[size]
            if lo is not None:
                parts.append(f"file_size >= {lo}")
            if hi is not None:
                parts.append(f"file_size < {hi}")

        words = filters_dict.get("words")
        words_map = {
            "<10万": (None, 100000),
            "10-50万": (100000, 500000),
            "50-100万": (500000, 1000000),
            ">100万": (1000000, None),
        }
        if isinstance(words, str) and words in words_map:
            lo, hi = words_map[words]
            if lo is not None:
                parts.append(f"word_count >= {lo}")
            if hi is not None:
                parts.append(f"word_count < {hi}")
        return parts

    meili_filter_parts: list[str] = []
    if filter_type == "tags":
        meili_filter_parts.append(f'tags = "{query}"')
    meili_filter_parts.extend(to_filter_expr(filters))
    meili_filter = " AND ".join(meili_filter_parts) if meili_filter_parts else None

    meili_sort = None
    if sort == "hot":
        meili_sort = ["downloads:desc"]
    elif sort == "new":
        meili_sort = ["created_at:desc"]
    elif sort == "big":
        meili_sort = ["file_size:desc"]
    
    try:
        search_result = await meili_service.search(
            query, 
            limit=limit, 
            offset=page * limit, 
            filter=meili_filter,
            sort=meili_sort,
        )
        hits = search_result.get('hits', [])
        total_hits = search_result.get('estimatedTotalHits', 0)
        time_taken = time.time() - start_time

        if not hits:
            text = "🔍 未找到相关书籍，请尝试更换关键词。"
            if isinstance(event, CallbackQuery):
                await event.answer(text)
            else:
                await reply_method(text)
            return

        # Prepare book IDs for keyboard
        book_ids = [hit.get('id') for hit in hits]
        
        # Calculate total pages
        total_pages = (total_hits + limit - 1) // limit
        
        text = format_book_list(
            hits,
            query=query,
            start_index=page * limit + 1,
            total_hits=total_hits,
            time_taken=time_taken,
            bot_username=config.BOT_USERNAME,
        )
        keyboard = get_search_keyboard(page, total_pages, book_ids, mode=keyboard_mode, sort=sort, filters=filters)
        
        existing_ctx = await redis_service.get_search_context(ctx_key)
        if not existing_ctx or existing_ctx.get("query") != query or existing_ctx.get("filter") != filter_type:
            await redis_service.cache_search_context(ctx_key, query, filter_type)
        await redis_service.update_search_context(ctx_key, {"page": page, "sort": sort, "filters": filters})
        
        await reply_method(text, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        err_text = "⚠️ 搜索服务暂时不可用，请稍后重试。"
        if isinstance(event, CallbackQuery):
            await event.answer(err_text)
        else:
            if isinstance(event, Message):
                await event.answer(err_text)

async def show_book_detail(chat_id: int, book_id: int, message_to_edit: Optional[Message] = None):
    try:
        book = await db_service.get_book(book_id)
        if not book:
            text = "⚠️ 书籍不存在或已被删除。"
            if message_to_edit:
                await message_to_edit.answer(text) # Can't edit to text if it was media, safe fallback
            else:
                await bot.send_message(chat_id, text)
            return

        book = dict(book)
        text = format_book_detail(book)
        # Pass book_id to keyboard, not file_id
        keyboard = get_book_detail_keyboard(book_id)
        
        if message_to_edit:
            await message_to_edit.edit_text(text, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Detail error: {e}")

# --- Handlers ---

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    if args and args.startswith("book_"):
        try:
            book_id = int(args.split("_")[1])
            await show_book_detail(message.chat.id, book_id)
            return
        except ValueError:
            await message.answer("⚠️ 链接无效，已回到首页")
            
    await message.answer(
        "📚 <b>欢迎使用搜书神器 (纯净版)</b>\n\n"
        "直接发送书名、作者或关键词即可搜索。\n"
        "支持指令：\n"
        "/s <关键词> - 搜标题/作者\n"
        "/ss <关键词> - 搜标签\n"
        "/settings - 设置\n"
        "/help - 查看帮助"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>使用帮助</b>\n\n"
        "- 直接发送书名/作者/关键词进行搜索\n"
        "- /s <关键词>：搜索标题/作者\n"
        "- /ss <关键词>：搜索标签\n\n"
        "提示：列表标题链接可直接打开书籍详情。"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    text = render_settings_text(settings)
    kb = get_settings_keyboard(settings)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

@dp.message(Command("s"))
async def cmd_search_s(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("请在指令后输入搜索关键词，例如：<code>/s 三体</code>")
        return
    await search_and_render(message, command.args)

@dp.message(Command("ss"))
async def cmd_search_ss(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("请在指令后输入标签，例如：<code>/ss 科幻</code>")
        return
    await search_and_render(message, command.args, filter_type='tags')

@dp.message(F.text & ~F.text.startswith("/"))
async def text_search(message: Message):
    if len(message.text) < 1:
        return
    await search_and_render(message, message.text)

@dp.message(F.document)
async def handle_document(message: Message):
    doc = message.document
    file_id = doc.file_id
    file_unique_id = doc.file_unique_id
    file_name = doc.file_name or "Unknown"
    file_size = doc.file_size
    
    # Deduplication
    exists = await db_service.get_book_by_file_unique_id(file_unique_id)
    if exists:
        await message.reply("⚠️ 该文件已存在于库中。")
        return

    upload_data = {
        'file_id': file_id,
        'file_unique_id': file_unique_id,
        'file_name': file_name,
        'file_size': file_size,
        'uploader_id': message.from_user.id,
        'username': message.from_user.username if message.from_user.username else "Unknown"
    }

    uploader_settings = await redis_service.get_user_settings(message.from_user.id)
    uploader_line = f"上传者: {message.from_user.full_name} ({message.from_user.id})"
    if uploader_settings.get("hide_personal_info"):
        uploader_line = "上传者: 匿名"
    
    if not config.ADMIN_IDS:
        await message.reply("⚠️ 系统未配置管理员，无法审核上传。")
        return
        
    # Create session with short ID
    short_id = await redis_service.create_upload_session(upload_data)
    
    for admin_id in config.ADMIN_IDS:
        try:
            text = (
                f"📝 <b>新文件待审核</b>\n"
                f"文件名: {file_name}\n"
                f"大小: {format_size(file_size)}\n"
                f"{uploader_line}"
            )
            kb = get_moderation_keyboard(short_id)
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    if not uploader_settings.get("mute_upload_feedback"):
        await message.reply("✅ 文件已提交审核，感谢您的贡献！")

# --- Callbacks ---

@dp.callback_query(F.data.startswith("page:"))
async def on_page_click(callback: CallbackQuery):
    _, _, page_str = callback.data.partition(":")
    if not page_str.isdigit():
        await callback.answer("无效的页码")
        return
    page = int(page_str)

    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。")
        return
        
    await search_and_render(
        callback, 
        ctx.get('query'), 
        page=page, 
        filter_type=ctx.get('filter'),
        keyboard_mode="default",
        sort=ctx.get("sort", "best"),
        filters=ctx.get("filters", {}) or {},
    )
    await callback.answer()

@dp.callback_query(F.data == "pagesel")
async def on_pagesel(callback: CallbackQuery):
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    await search_and_render(
        callback,
        ctx.get("query"),
        page=ctx.get("page", 0),
        filter_type=ctx.get("filter"),
        keyboard_mode="page_picker",
        sort=ctx.get("sort", "best"),
        filters=ctx.get("filters", {}) or {},
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("jump:"))
async def on_jump(callback: CallbackQuery):
    _, _, page_str = callback.data.partition(":")
    if not page_str.isdigit():
        await callback.answer("无效的页码")
        return
    page = int(page_str)
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    await search_and_render(
        callback,
        ctx.get("query"),
        page=page,
        filter_type=ctx.get("filter"),
        keyboard_mode="page_picker",
        sort=ctx.get("sort", "best"),
        filters=ctx.get("filters", {}) or {},
    )
    await callback.answer()

@dp.callback_query(F.data == "back:search")
async def on_back_search(callback: CallbackQuery):
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    await search_and_render(
        callback,
        ctx.get("query"),
        page=ctx.get("page", 0),
        filter_type=ctx.get("filter"),
        keyboard_mode="default",
        sort=ctx.get("sort", "best"),
        filters=ctx.get("filters", {}) or {},
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sort:"))
async def on_sort(callback: CallbackQuery):
    _, _, sort_key = callback.data.partition(":")
    if sort_key not in {"best", "hot", "new", "big"}:
        await callback.answer("无效的排序")
        return
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    await search_and_render(
        callback,
        ctx.get("query"),
        page=0,
        filter_type=ctx.get("filter"),
        keyboard_mode="default",
        sort=sort_key,
        filters=ctx.get("filters", {}) or {},
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("fltmenu:"))
async def on_filter_menu(callback: CallbackQuery):
    _, _, key = callback.data.partition(":")
    if key not in {"rating", "format", "size", "words"}:
        await callback.answer("无效的筛选项")
        return
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    kb = get_filter_menu_keyboard(key, selected=ctx.get("filters", {}) or {})
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("flt:"))
async def on_filter_set(callback: CallbackQuery):
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer("无效的筛选")
        return
    _, key, value = parts
    if key not in {"rating", "format", "size", "words"}:
        await callback.answer("无效的筛选项")
        return
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    ctx_filters = dict(ctx.get("filters", {}) or {})
    ctx_filters[key] = value
    await search_and_render(
        callback,
        ctx.get("query"),
        page=0,
        filter_type=ctx.get("filter"),
        keyboard_mode="default",
        sort=ctx.get("sort", "best"),
        filters=ctx_filters,
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("fltclr:"))
async def on_filter_clear(callback: CallbackQuery):
    _, _, key = callback.data.partition(":")
    if key not in {"rating", "format", "size", "words"}:
        await callback.answer("无效的筛选项")
        return
    ctx_key = callback.from_user.id if callback.from_user else callback.message.chat.id
    ctx = await redis_service.get_search_context(ctx_key)
    if not ctx:
        await callback.answer("⚠️ 搜索会话已过期，请重新搜索。", show_alert=True)
        return
    ctx_filters = dict(ctx.get("filters", {}) or {})
    ctx_filters.pop(key, None)
    await search_and_render(
        callback,
        ctx.get("query"),
        page=0,
        filter_type=ctx.get("filter"),
        keyboard_mode="default",
        sort=ctx.get("sort", "best"),
        filters=ctx_filters,
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sel:"))
async def on_select_book(callback: CallbackQuery):
    _, _, book_id_str = callback.data.partition(":")
    if not book_id_str.isdigit():
        await callback.answer("无效的选择")
        return
    book_id = int(book_id_str)

    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    if settings.get("search_button_mode") == "download":
        book = await db_service.get_book(book_id)
        if not book:
            await callback.answer("⚠️ 书籍不存在或已被删除")
            return
        book = dict(book)
        try:
            await bot.send_document(callback.message.chat.id, book["file_id"])
            asyncio.create_task(db_service.increment_download(book_id))
            await callback.answer()
        except Exception as e:
            logger.error(f"Send document failed: {e}")
            await callback.answer("❌ 发送失败，文件可能已失效")
        return

    await show_book_detail(callback.message.chat.id, book_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("dl:"))
async def on_download(callback: CallbackQuery):
    _, _, book_id_str = callback.data.partition(":")
    if not book_id_str.isdigit():
        await callback.answer("无效的下载请求")
        return
    book_id = int(book_id_str)

    book = await db_service.get_book(book_id)
    if not book:
        await callback.answer("⚠️ 书籍不存在或已被删除")
        return
    book = dict(book)
    
    # Send document using file_id
    try:
        await bot.send_document(callback.message.chat.id, book["file_id"])
        await callback.answer()
        # Async increment
        asyncio.create_task(db_service.increment_download(book_id))
    except Exception as e:
        logger.error(f"Send document failed: {e}")
        await callback.answer("❌ 发送失败，文件可能已失效")

@dp.callback_query(F.data.startswith("mod_approve:"))
async def on_approve(callback: CallbackQuery):
    _, _, short_id = callback.data.partition(":")
    if not short_id:
        await callback.answer("无效的审核请求")
        return
    
    # Atomic get and delete
    data = await redis_service.get_and_delete_upload_session(short_id)
    
    if not data:
        await callback.answer("⚠️ 该请求已被处理或已过期")
        # Update message to reflect status
        await callback.message.edit_text(f"{callback.message.text}\n\n[已处理/过期]")
        return
        
    try:
        title = data['file_name'].rsplit('.', 1)[0]
        data['title'] = title
        data['author'] = "Unknown"
        
        book_id = await db_service.add_book(data)
        
        book = await db_service.get_book(book_id)
        if book:
            meili_doc = dict(book)
            file_name = str(meili_doc.get("file_name") or "")
            meili_doc["ext"] = (file_name.split(".")[-1].upper() if "." in file_name else "FILE")
            meili_doc["word_count"] = int(meili_doc.get("word_count") or 0) if "word_count" in meili_doc else 0
            meili_doc["content_rating"] = int(meili_doc.get("content_rating") or 0) if "content_rating" in meili_doc else 0
            created_at = meili_doc.get("created_at")
            if created_at is not None and hasattr(created_at, "isoformat"):
                meili_doc["created_at"] = created_at.isoformat()
            await meili_service.add_documents([meili_doc])
        
        await callback.message.edit_text(f"✅ 已通过: {data['file_name']}")
        await callback.answer("审核通过")
        
        # Notify uploader (if we had stored their ID properly and bot can initiate)
        # data['uploader_id'] is available.
        try:
            await bot.send_message(data['uploader_id'], f"✅ 您的文件 {data['file_name']} 已通过审核！")
        except:
            pass # User might have blocked bot
            
    except Exception as e:
        logger.error(f"Approval error: {e}")
        await callback.answer("❌ 处理失败")

@dp.callback_query(F.data.startswith("mod_reject:"))
async def on_reject(callback: CallbackQuery):
    _, _, short_id = callback.data.partition(":")
    if not short_id:
        await callback.answer("无效的审核请求")
        return
    # Just delete session
    await redis_service.get_and_delete_upload_session(short_id)
    
    await callback.message.edit_text("❌ 已拒绝")
    await callback.answer("已拒绝")

@dp.callback_query(F.data == "settings")
async def on_settings(callback: CallbackQuery):
    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    text = render_settings_text(settings)
    kb = get_settings_keyboard(settings)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "back:settings")
async def on_back_settings(callback: CallbackQuery):
    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    text = render_settings_text(settings)
    kb = get_settings_keyboard(settings)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("setmenu:"))
async def on_settings_menu(callback: CallbackQuery):
    _, _, key = callback.data.partition(":")
    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    if key in {"content_rating", "search_button_mode"}:
        kb = get_settings_menu_keyboard(key, settings)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()
        return
    await callback.answer("该功能暂未开放", show_alert=True)

@dp.callback_query(F.data.startswith("set:"))
async def on_settings_toggle(callback: CallbackQuery):
    _, _, key = callback.data.partition(":")
    allowed = {
        "hide_personal_info",
        "hide_upload_list",
        "mute_upload_feedback",
        "mute_invite_feedback",
        "mute_feed",
    }
    if key not in allowed:
        await callback.answer("无效的设置项")
        return
    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.get_user_settings(user_id)
    new_value = not bool(settings.get(key, False))
    settings = await redis_service.update_user_settings(user_id, {key: new_value})
    text = render_settings_text(settings)
    kb = get_settings_keyboard(settings)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("setv:"))
async def on_settings_set_value(callback: CallbackQuery):
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer("无效的设置")
        return
    _, key, value = parts
    if key == "content_rating" and value not in {"ALL", "G", "R15", "R18"}:
        await callback.answer("无效的分级")
        return
    if key == "search_button_mode" and value not in {"preview", "download"}:
        await callback.answer("无效的模式")
        return
    if key not in {"content_rating", "search_button_mode"}:
        await callback.answer("无效的设置项")
        return
    user_id = callback.from_user.id if callback.from_user else callback.message.chat.id
    settings = await redis_service.update_user_settings(user_id, {key: value})
    text = render_settings_text(settings)
    kb = get_settings_keyboard(settings)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def on_fav(callback: CallbackQuery):
    await callback.answer("收藏功能暂未开放", show_alert=True)


@dp.callback_query(F.data.startswith("rel:"))
async def on_rel(callback: CallbackQuery):
    await callback.answer("相关书籍功能暂未开放", show_alert=True)

@dp.callback_query(F.data == "close")
async def on_close(callback: CallbackQuery):
    await callback.message.delete()

@dp.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery):
    await callback.answer()

# --- Startup/Shutdown ---

async def on_startup():
    await db_service.connect()
    await meili_service.init_index()
    
    # Auto-detect bot username for deep linking
    try:
        me = await bot.get_me()
        if me.username:
            config.BOT_USERNAME = me.username
            logger.info(f"Bot username detected: @{config.BOT_USERNAME}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")

    try:
        await bot.set_my_commands(
            [
                types.BotCommand(command="s", description="搜标题/作者"),
                types.BotCommand(command="ss", description="搜标签"),
                types.BotCommand(command="settings", description="设置"),
                types.BotCommand(command="help", description="帮助"),
            ],
            scope=types.BotCommandScopeDefault(),
        )
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    logger.info("Bot started")

async def on_shutdown():
    await db_service.close()
    await redis_service.close()
    await bot.session.close()
    logger.info("Bot stopped")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # 自动删除可能存在的 Webhook，防止冲突
    logger.info("Deleting webhook to enable polling mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

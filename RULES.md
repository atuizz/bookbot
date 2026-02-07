# Vibe Coding Implementation Rules

## 核心原则

1. **异步优先 (Async First)**: 
   - 全链路必须异步，严禁在主线程使用 `requests`, `time.sleep` 等阻塞操作。
   - 数据库操作使用 `asyncpg`，Redis 使用 `redis.asyncio`。

2. **数据对齐 (Neat Data)**:
   - 列表展示必须使用 `<code>` 标签包裹。
   - 使用全角/半角字符宽度计算算法，确保视觉对齐。
   - 严格遵循 `3-4-3-5` 键盘布局。

3. **模块化 (Modularity)**:
   - `bot.py`: 仅包含路由和高层逻辑。
   - `services.py`: 封装所有外部服务交互。
   - `utils.py`: 纯函数工具类。
   - `keyboards.py`: UI 组件工厂。

4. **极简主义 (Minimalism)**:
   - 不存储文件实体，只流转 file_id。
   - 搜索结果页无冗余信息，直击核心。

## 代码规范

- 使用 Type Hints。
- 关键逻辑必须有异常处理 (try-except)。
- 日志记录关键操作 (Logging)。

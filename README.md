# 搜书神器 (纯净版) - BookBot

一个基于 Telegram 的极速搜书机器人，专注于纯净体验和毫秒级响应。

## 🚀 核心特性

- **纯净共享**: 无广告、无积分、无等级，全员开放。
- **极速响应**: 基于 Meilisearch 实现 50ms 内搜索返回。
- **数据对齐**: 精心设计的 UI，确保在移动端完美对齐。
- **极简体验**: 关键词直达，一键下载。
- **筛选排序**: 支持格式/体积/字数/分级筛选与最热/最新/最大排序。
- **设置菜单**: 内容分级与搜索按钮模式可配置，支持匿名上传与静默提示。

## 🛠 技术栈 (Technical Stack)

- **Framework**: Python 3.10+, Aiogram 3.x (异步高并发)
- **Search Engine**: Meilisearch (全文检索)
- **Database**: PostgreSQL (asyncpg)
- **Cache**: Redis (搜索上下文缓存)
- **Deployment**: Docker Compose

## 📦 部署指南 (Deployment)

### 方式一：本地开发/测试 (Local)

1. **配置环境**:
   复制配置文件并填入 Token。
   ```bash
   cp .env.example .env
   ```
   *注意：如果本地需要代理才能连接 Telegram，请在 `.env` 中设置 `HTTP_PROXY`，例如 `http://host.docker.internal:7890`*。

2. **启动服务**:
   ```bash
   docker-compose up -d
   ```

### 方式二：VPS 一键部署 (推荐)

适用于 Ubuntu/Debian/CentOS 服务器。

1. **上传代码**:
   ```bash
   # 如果服务器已安装 git
   git clone https://github.com/atuizz/bookbot bookbot
   cd bookbot
   ```

2. **运行中文部署脚本**:
   ```bash
   chmod +x deploy_vps.sh
   ./deploy_vps.sh
   ```
   *脚本提供交互式中文菜单，自动完成 Docker 安装、环境配置和启动。*

   **脚本功能**:
   - 1. 安装并启动 (自动生成密钥，配置 Token)
   - 2. 更新代码并重启
   - 3. 查看实时日志
   - 4. 停止服务

## 📁 项目结构 (Project Structure)

- `bot.py`: 机器人主入口，包含路由和高层逻辑。
- `services.py`: 封装所有外部服务交互（Meilisearch, PostgreSQL, Redis）。
- `utils.py`: 纯函数工具类，处理字符串格式化等。
- `keyboards.py`: Telegram 键盘 UI 组件工厂。
- `config.py`: 配置管理（基于 pydantic-settings）。
- `tests/`: 单元测试目录。

## 🧪 运行测试 (Running Tests)

项目包含单元测试，用于验证核心逻辑和工具函数。

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m unittest discover tests
```

## 🧑‍💻 开发指南

详见 [RULES.md](RULES.md) 了解代码规范和贡献指南。

# Colorful State - Twitter 推文采集与存储系统 🎨

[![GitHub](https://img.shields.io/badge/GitHub-Colorful--State-blue?logo=github)](https://github.com/lixiansky/Colorful-State)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

一个基于 **Playwright Stealth** 技术的 Twitter 推文采集系统，自动抓取指定用户的推文，使用 **DeepSeek API** 翻译成中文，并存储到 **Neon PostgreSQL** 数据库中。

## ✨ 核心特性

- **🛡️ 强力反检测**: 使用 Playwright + Stealth 插件模拟真实浏览器，绕过 Nitter 验证
- **🌐 智能翻译**: 集成 DeepSeek API，自动将推文翻译成简体中文 (temperature=1.3)
- **💾 数据持久化**: 使用 Neon PostgreSQL 云数据库存储推文数据
- **🎨 现代化 UI**: 仿 TikTok 风格设计，支持深色/浅色模式，流畅动画体验
- **🎬 视频播放**: 内嵌视频播放器，支持封面预览、原生控制及防盗链绕过
- **🖼️ 完整内容**: 支持提取推文文本、图片、视频等完整信息
- **🔄 自动去重**: 基于 tweet_id 的唯一约束，避免重复存储
- **⚡ 灵活运行**: 支持单次运行或循环监控模式

## 📋 功能对比

| 功能 | Colorful State | 原 twitter_monitor |
|------|----------------|-------------------|
| 推文抓取 | ✅ | ✅ |
| 单条推文抓取 | ✅ | ❌ |
| 图片/视频 | ✅ (修复防盗链) | ✅ |
| 翻译 | ✅ DeepSeek API | ✅ Google Translate |
| 存储 | ✅ Neon Database | ❌ |
| 界面 | ✅ 现代化 Web UI | ❌ |
| 通知 | ❌ | ✅ 钉钉 |
| 去重 | ✅ 数据库约束 | ✅ 本地文件 |
| GitHub Actions | ✅ (自动部署 Pages) | ✅ |

## 🚀 快速开始

### 1. 安装依赖

```bash
cd colorful_state
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置 Neon 数据库

1. 访问 [Neon.tech](https://neon.tech/) 注册账号
2. 创建新项目和数据库
3. 复制连接字符串 (格式: `postgresql://user:password@host/dbname?sslmode=require`)
4. 在 Neon SQL Editor 中执行 `schema.sql` 创建表结构

### 3. 配置 DeepSeek API

1. 访问 [DeepSeek 平台](https://platform.deepseek.com/) 注册账号
2. 创建 API Key
3. 复制 API Key 备用

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Twitter 监控配置
TWITTER_USERS=elonmusk,OpenAI

# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Neon Database 配置
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

# 运行模式配置
LOOP_MODE=true
LOOP_INTERVAL=600  # 10分钟
```

### 5. 运行脚本

```bash
python colorful_state.py
```

## 📊 数据库表结构

```sql
CREATE TABLE tweets (
    id SERIAL PRIMARY KEY,
    tweet_id VARCHAR(255) UNIQUE NOT NULL,  -- 推文唯一ID
    author VARCHAR(255) NOT NULL,           -- 作者用户名
    content TEXT NOT NULL,                  -- 原文内容
    content_zh TEXT,                        -- 中文翻译
    published_at TIMESTAMP,                 -- 发布时间
    is_retweet BOOLEAN DEFAULT FALSE,       -- 是否转发
    images JSONB,                           -- 图片URL数组
    video_url TEXT,                         -- 视频URL
    source_url TEXT,                        -- 来源URL
    created_at TIMESTAMP DEFAULT NOW(),     -- 创建时间
    updated_at TIMESTAMP DEFAULT NOW()      -- 更新时间
);
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 示例 | 必填 |
|--------|------|------|------|
| `TWITTER_USERS` | 监控的 Twitter 用户名，多个用逗号分隔 | `elonmusk,OpenAI` | ❌ |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` | ✅ |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` | ❌ |
| `DATABASE_URL` | Neon 数据库连接字符串 | `postgresql://...` | ✅ |
| `LOOP_MODE` | 是否循环运行 | `true` / `false` | ❌ |
| `LOOP_INTERVAL` | 循环间隔（秒） | `600` | ❌ |

> **注意**: 单条推文抓取通过 `tweets.txt` 文件配置，无需环境变量

### DeepSeek Temperature 参数

根据 DeepSeek 官方建议，本项目使用 **temperature=1.3** 进行翻译：

| 场景 | Temperature |
|------|-------------|
| 代码生成/数学解题 | 0.0 |
| 数据抽取/分析 | 1.0 |
| 通用对话 | 1.3 |
| **翻译** | **1.3** ✅ |
| 创意类写作/诗歌 | 1.5 |

## 🔍 查询数据

连接到 Neon 数据库后，可以使用 SQL 查询推文：

```sql
-- 查询最新 10 条推文
SELECT tweet_id, author, content, content_zh, published_at 
FROM tweets 
ORDER BY created_at DESC 
LIMIT 10;

-- 查询特定作者的推文
SELECT * FROM tweets 
WHERE author = 'elonmusk' 
ORDER BY published_at DESC;

-- 查询包含图片的推文
SELECT * FROM tweets 
WHERE images IS NOT NULL AND jsonb_array_length(images) > 0;

-- 查询包含视频的推文
SELECT * FROM tweets 
WHERE video_url IS NOT NULL;
```

## 🎯 单条推文抓取

除了监控用户，还支持抓取指定的推文 URL。

### 使用 tweets.txt 文件

1. **编辑 tweets.txt**

```txt
# 添加推文 URL，每行一个
https://x.com/elonmusk/status/1234567890
https://twitter.com/OpenAI/status/9876543210

# 已抓取的推文可以注释掉
# https://x.com/user/status/111  # 已抓取 2026-02-09
```

2. **运行脚本**

```bash
python colorful_state.py
```

3. **查看状态报告**

脚本会自动检查哪些已抓取、哪些待抓取：

```
[读取配置] 从 tweets.txt 读取到 5 条推文 URL
============================================================
[状态检查] 配置了 5 条推文 URL
============================================================

✅ 已抓取: 3 条
   - https://x.com/user/status/123
     @elonmusk | 2026-02-09 10:30 | ✓ 已翻译
   - https://x.com/user/status/456
     @OpenAI | 2026-02-09 11:20 | ✓ 已翻译

⏳ 待抓取: 2 条
   - https://x.com/user/status/789
   - https://x.com/user/status/101

============================================================

[开始抓取] 抓取 2 条待抓取推文...
```

### 查询推文状态

使用独立查询脚本：

```bash
# 查询 tweets.txt 中的所有推文
python query_status.py

# 或指定推文 URL
python query_status.py "https://x.com/user/status/123,https://x.com/user/status/456"
```

输出示例：

```
推文状态查询结果：

✅ https://x.com/user/status/123
   作者: @elonmusk
   抓取时间: 2026-02-09 10:30:15
   翻译: 已完成
   图片: 2 张
   视频: 无

❌ https://x.com/user/status/456
   状态: 未抓取
```

## 🚀 GitHub Actions 部署

### 1. 配置 GitHub Secrets

在仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret Name | 说明 | 必填 |
|-------------|------|------|
| `TWITTER_USERS` | 监控用户（逗号分隔） | ❌ |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ✅ |
| `DATABASE_URL` | Neon 数据库连接 | ✅ |

### 2. 工作流说明

- **自动运行**: 每 10 分钟自动执行一次
- **手动触发**: 在 Actions 标签页点击 "Run workflow"
- **推文列表**: 通过 `tweets.txt` 文件管理

### 3. 使用流程

1. 编辑 `tweets.txt` 添加推文 URL
2. Git commit 并 push
3. GitHub Actions 自动运行
4. 查看 Actions 日志中的状态报告

### 4. 查看运行日志

进入 Actions 标签页 → 选择最新的工作流运行 → 查看详细日志，可以看到：

- 读取了多少条推文 URL
- 哪些已抓取、哪些待抓取
- 抓取进度和结果

## 📝 运行模式

### 单次运行模式

适合手动触发或定时任务：

```bash
export LOOP_MODE=false
python colorful_state.py
```

### 循环监控模式

持续运行，定期抓取：

```bash
export LOOP_MODE=true
export LOOP_INTERVAL=600  # 每10分钟
python colorful_state.py
```

> **注意**: 在 GitHub Actions 环境中，Monitor 工作流完成后会自动触发 Pages 部署工作流，确保网站内容实时更新。
```

## 🛠️ 技术架构

```
┌─────────────────┐
│  Nitter 实例    │
│  (xcancel.com)  │
└────────┬────────┘
         │
         │ Playwright + Stealth
         ↓
┌─────────────────┐
│  推文抓取模块    │
│  - 文本内容     │
│  - 图片/视频    │
│  - 元数据       │
└────────┬────────┘
         │
         │ DeepSeek API
         ↓
┌─────────────────┐
│  翻译模块       │
│  (temp=1.3)     │
└────────┬────────┘
         │
         │ psycopg2
         ↓
┌─────────────────┐
│  Neon Database  │
│  (PostgreSQL)   │
└─────────────────┘
```

## ❓ 常见问题

**Q: 为什么选择 Neon 数据库？**  
A: Neon 是一个现代化的 Serverless PostgreSQL 服务，提供免费套餐，支持自动扩缩容，非常适合这类轻量级应用。

**Q: DeepSeek API 费用如何？**  
A: DeepSeek 提供非常优惠的定价，具体请查看 [官方定价页面](https://platform.deepseek.com/pricing)。

**Q: 如何避免重复抓取？**  
A: 数据库中 `tweet_id` 字段有 UNIQUE 约束，使用 `ON CONFLICT DO UPDATE` 策略自动处理重复。

**Q: 可以同时监控多个用户吗？**  
A: 可以，在 `TWITTER_USERS` 中用逗号分隔多个用户名即可。

A: 如果 DeepSeek API 调用失败，`content_zh` 字段会保存为 NULL，不影响原文存储。

**Q: 为什么视频或图片无法显示？**  
A: Twitter 的媒体资源有防盗链保护。本项目已通过以下方式解决：
1. 添加 `<meta name="referrer" content="no-referrer">` 绕过 Referer 检查
2. 自动将不稳定的 Nitter 图片域名替换为官方 `pbs.twimg.com` 域名
3. 视频使用原生 HTML5 播放器，且配置了 `poster` 封面

## 📄 许可证

本项目采用 [MIT License](../LICENSE) 开源。

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 浏览器自动化框架
- [DeepSeek](https://www.deepseek.com/) - AI 翻译服务
- [Neon](https://neon.tech/) - Serverless PostgreSQL
- [Nitter](https://github.com/zedeus/nitter) - Twitter 前端替代品

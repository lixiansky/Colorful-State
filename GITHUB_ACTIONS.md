# GitHub Actions 部署指南

## 快速开始

### 1. 配置 GitHub Secrets

进入仓库 **Settings** → **Secrets and variables** → **Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 必填 | 示例 |
|------------|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ✅ | `sk-xxxxxxxxxxxxxxxx` |
| `DATABASE_URL` | Neon 数据库连接字符串 | ✅ | `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require` |
| `TWITTER_USERS` | 监控的用户（逗号分隔） | ❌ | `elonmusk,OpenAI` |

### 2. 数据库自动设置

**好消息**：GitHub Actions 工作流已经包含自动数据库设置步骤！

首次运行时，工作流会自动：
1. 检查 `tweets` 表是否存在
2. 如果不存在，自动执行 `schema.sql` 创建表
3. 继续运行抓取任务

**无需手动操作！**

### 3. 启用 GitHub Actions

1. 提交并推送代码到 GitHub
2. 进入仓库的 **Actions** 标签页
3. GitHub Actions 会自动启用

### 4. 工作流说明

#### 自动运行
- **频率**: 每 10 分钟运行一次
- **触发**: 自动触发，无需手动操作

#### 手动触发
1. 进入 **Actions** 标签页
2. 选择 "Colorful State Monitor"
3. 点击 "Run workflow"
4. 可选：勾选 "强制重新抓取"

### 5. 管理推文列表

#### 添加推文 URL

1. **编辑 `tweets.txt`**
   ```txt
   https://x.com/elonmusk/status/123456
   https://x.com/OpenAI/status/789012
   ```

2. **提交并推送**
   ```bash
   git add tweets.txt
   git commit -m "add new tweets"
   git push
   ```

3. **自动运行**
   - GitHub Actions 会在下次定时运行时自动抓取
   - 或手动触发立即运行

### 6. 查看运行结果

1. 进入 **Actions** 标签页
2. 点击最新的工作流运行
3. 展开 "Run scraper" 步骤
4. 查看详细日志

#### 日志示例

```
[读取配置] 从 tweets.txt 读取到 5 条推文 URL
============================================================
[状态检查] 配置了 5 条推文 URL
============================================================

✅ 已抓取: 3 条
   - https://x.com/user/status/123
     @elonmusk | 2026-02-09 10:30 | ✓ 已翻译

⏳ 待抓取: 2 条
   - https://x.com/user/status/456
   - https://x.com/user/status/789

============================================================

[开始抓取] 抓取 2 条待抓取推文...
```

## 工作流文件说明

### 完整工作流

```yaml
name: Colorful State Monitor

on:
  schedule:
    - cron: '*/10 * * * *'  # 每10分钟
  workflow_dispatch:  # 手动触发
    inputs:
      force_rescrape:
        description: '强制重新抓取已存在的推文'
        required: false
        type: boolean
        default: false

jobs:
  scrape:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      
      - name: Setup database (if needed)
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python setup_db.py || echo "Database already set up"
      
      - name: Run scraper
        env:
          TWITTER_USERS: ${{ secrets.TWITTER_USERS }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          LOOP_MODE: 'false'
        run: python colorful_state.py
```

### 关键步骤

1. **Setup database** - 自动创建数据库表（首次运行）
2. **Run scraper** - 执行推文抓取

## 常见问题

### Q: 首次运行需要手动创建数据库表吗？

A: **不需要！** 工作流会自动运行 `setup_db.py` 创建表。

### Q: 如何验证数据库设置成功？

A: 查看 Actions 日志中的 "Setup database" 步骤，应该看到：

```
✅ 数据库连接成功
✅ Schema 执行成功
✅ tweets 表已成功创建
```

### Q: 如果数据库设置失败怎么办？

A: 检查：
1. `DATABASE_URL` Secret 是否正确配置
2. 连接字符串格式是否正确
3. Neon 数据库是否可访问

手动在 Neon Dashboard 执行 `schema.sql` 作为备选方案。

### Q: 如何修改运行频率？

A: 编辑 `.github/workflows/monitor.yml`：

```yaml
schedule:
  - cron: '*/10 * * * *'  # 每10分钟
  # 改为
  - cron: '0 * * * *'     # 每小时
  # 或
  - cron: '0 */6 * * *'   # 每6小时
```

### Q: 如何停止自动运行？

A: 两种方法：
1. **禁用工作流**: Actions → Colorful State Monitor → "..." → Disable workflow
2. **删除 cron**: 从 `monitor.yml` 中删除 `schedule` 部分

### Q: 如何查看数据库中的数据？

A: 登录 Neon Dashboard：
1. 进入 SQL Editor
2. 运行查询：
   ```sql
   SELECT * FROM tweets ORDER BY created_at DESC LIMIT 10;
   ```

## 最佳实践

### 1. 监控运行状态

- 定期检查 Actions 标签页
- 关注失败的运行
- 查看错误日志

### 2. 管理推文列表

- 使用注释标记已抓取的推文
- 定期清理不需要的 URL
- 使用有意义的注释说明

### 3. 控制成本

- DeepSeek API 按使用量计费
- 合理设置运行频率
- 避免重复抓取（脚本已自动去重）

### 4. 数据备份

- 定期导出 Neon 数据库
- 保存重要推文的本地副本

## 故障排查

如果遇到问题，请查看：
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 连接问题
- [DATABASE_SETUP.md](DATABASE_SETUP.md) - 数据库设置
- Actions 日志 - 运行详情

## 下一步

1. ✅ 配置 Secrets
2. ✅ 推送代码
3. ✅ 等待自动运行（或手动触发）
4. ✅ 查看日志验证
5. ✅ 添加推文 URL 到 `tweets.txt`
6. ✅ 享受自动化！🎉

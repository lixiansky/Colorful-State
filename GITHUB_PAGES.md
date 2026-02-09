# GitHub Pages 展示说明

## 功能特点

✅ **分页显示** - 每页 20 条推文，支持翻页
✅ **实时搜索** - 搜索推文内容、作者
✅ **统计信息** - 显示总推文数、视频数、图片数、作者数
✅ **响应式设计** - 支持手机、平板、电脑
✅ **自动更新** - 每 30 分钟自动从数据库更新

## 部署步骤

### 1. 启用 GitHub Pages

1. 进入仓库 **Settings** → **Pages**
2. **Source** 选择 `Deploy from a branch`
3. **Branch** 选择 `gh-pages` 分支，目录选择 `/ (root)`
4. 点击 **Save**

### 2. 首次部署

手动触发 GitHub Actions：

1. 进入 **Actions** 标签
2. 选择 **Deploy to GitHub Pages** 工作流
3. 点击 **Run workflow**
4. 等待部署完成（约 1-2 分钟）

### 3. 访问网站

部署完成后，访问：

```
https://<你的用户名>.github.io/Colorful-State/
```

例如：`https://lixiansky.github.io/Colorful-State/`

## 文件说明

- `export_to_pages.py` - 数据导出脚本
- `docs/index.html` - 前端展示页面
- `docs/data.json` - 推文数据（自动生成）
- `docs/stats.json` - 统计信息（自动生成）
- `.github/workflows/deploy-pages.yml` - 自动部署工作流

## 本地测试

```bash
# 1. 导出数据
python export_to_pages.py

# 2. 启动本地服务器
cd docs
python -m http.server 8000

# 3. 访问 http://localhost:8000
```

## 更新频率

- **自动更新**: 每 30 分钟
- **手动更新**: 在 Actions 中手动触发
- **代码更新**: 推送代码时自动部署

## 自定义

### 修改每页显示数量

编辑 `docs/index.html`，找到：

```javascript
const TWEETS_PER_PAGE = 20;  // 改为你想要的数量
```

### 修改更新频率

编辑 `.github/workflows/deploy-pages.yml`，找到：

```yaml
cron: '*/30 * * * *'  # 改为你想要的频率
```

### 修改样式

编辑 `docs/index.html` 中的 `<style>` 部分。

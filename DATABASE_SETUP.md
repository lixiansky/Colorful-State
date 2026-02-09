# 数据库设置指南

## 问题：relation "tweets" does not exist

这个错误表明数据库中还没有创建 `tweets` 表。

## 解决方案

### 方法 1: 使用 Neon Dashboard（推荐）

1. **登录 Neon Dashboard**
   - 访问 https://console.neon.tech/
   - 选择您的项目

2. **打开 SQL Editor**
   - 点击左侧菜单的 "SQL Editor"

3. **执行 schema.sql**
   - 打开项目中的 `schema.sql` 文件
   - 复制全部内容
   - 粘贴到 SQL Editor
   - 点击 "Run" 执行

4. **验证表创建**
   ```sql
   SELECT * FROM tweets LIMIT 1;
   ```

### 方法 2: 使用 psql 命令行

```bash
# 使用您的 DATABASE_URL
psql "postgresql://user:pass@host/db?sslmode=require" -f schema.sql
```

### 方法 3: 使用 Python 脚本（自动化）

我已经创建了 `setup_db.py` 脚本来自动设置数据库：

```bash
python setup_db.py
```

## schema.sql 内容

```sql
-- 创建推文表
CREATE TABLE IF NOT EXISTS tweets (
    id SERIAL PRIMARY KEY,
    tweet_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_zh TEXT,
    published_at TIMESTAMP,
    is_retweet BOOLEAN DEFAULT FALSE,
    images JSONB,
    video_url TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tweets_tweet_id ON tweets(tweet_id);
CREATE INDEX IF NOT EXISTS idx_tweets_author ON tweets(author);
CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tweets_updated_at 
    BEFORE UPDATE ON tweets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

## 验证数据库设置

运行测试脚本：

```bash
python test_db.py
```

应该看到：

```
✅ 数据库连接成功！
✅ tweets 表已存在
   当前记录数: 0
✅ 所有检查通过！
```

## 常见问题

### Q: 执行 schema.sql 后仍然报错？

A: 确保：
1. 使用的数据库连接字符串正确
2. 数据库用户有创建表的权限
3. 重启应用程序以刷新连接

### Q: 如何重置数据库？

A: 在 SQL Editor 中执行：

```sql
DROP TABLE IF EXISTS tweets CASCADE;
```

然后重新运行 schema.sql。

### Q: 如何查看现有表？

A: 在 SQL Editor 中执行：

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

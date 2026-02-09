-- Colorful State Database Schema for Neon PostgreSQL
-- 推文数据表

CREATE TABLE IF NOT EXISTS tweets (
    id SERIAL PRIMARY KEY,
    tweet_id VARCHAR(255) UNIQUE NOT NULL,
    author VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_zh TEXT,  -- 中文翻译
    published_at TIMESTAMP,
    is_retweet BOOLEAN DEFAULT FALSE,
    images JSONB,  -- 图片URL数组 (JSON格式)
    video_url TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_tweet_id ON tweets(tweet_id);
CREATE INDEX IF NOT EXISTS idx_author ON tweets(author);
CREATE INDEX IF NOT EXISTS idx_published_at ON tweets(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_created_at ON tweets(created_at DESC);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tweets_updated_at BEFORE UPDATE ON tweets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE tweets IS '推文数据表';
COMMENT ON COLUMN tweets.tweet_id IS '推文唯一ID';
COMMENT ON COLUMN tweets.author IS '推文作者用户名';
COMMENT ON COLUMN tweets.content IS '推文原文内容';
COMMENT ON COLUMN tweets.content_zh IS '推文中文翻译';
COMMENT ON COLUMN tweets.published_at IS '推文发布时间';
COMMENT ON COLUMN tweets.is_retweet IS '是否为转发';
COMMENT ON COLUMN tweets.images IS '图片URL数组(JSON格式)';
COMMENT ON COLUMN tweets.video_url IS '视频URL';
COMMENT ON COLUMN tweets.source_url IS '推文来源URL';

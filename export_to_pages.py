"""
导出推文数据到 GitHub Pages
从 Neon 数据库读取推文，生成 JSON 文件供前端展示
"""
import os
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def export_tweets_to_json():
    """从数据库导出推文为 JSON"""
    try:
        print("=" * 80)
        print("开始导出推文数据到 GitHub Pages")
        print("=" * 80)
        print()
        
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) FROM tweets;")
        total_count = cursor.fetchone()[0]
        print(f"数据库中共有 {total_count} 条推文")
        
        # 导出所有推文（按时间倒序）
        cursor.execute("""
            SELECT 
                tweet_id,
                author,
                content,
                content_zh,
                images,
                video_url,
                published_at,
                source_url,
                created_at
            FROM tweets
            ORDER BY published_at DESC NULLS LAST, created_at DESC;
        """)
        
        tweets = []
        for row in cursor.fetchall():
            tweet = {
                'tweet_id': row[0],
                'author': row[1],
                'content': row[2],
                'content_zh': row[3],
                'images': row[4] if row[4] else [],
                'video_url': row[5],
                'published_at': row[6].isoformat() if row[6] else None,
                'source_url': row[7],
                'created_at': row[8].isoformat() if row[8] else None
            }
            tweets.append(tweet)
        
        # 创建 docs 目录
        os.makedirs('docs', exist_ok=True)
        
        # 保存完整数据
        data = {
            'updated_at': datetime.now().isoformat(),
            'total_count': len(tweets),
            'tweets': tweets
        }
        
        with open('docs/data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 成功导出 {len(tweets)} 条推文到 docs/data.json")
        
        # 生成统计信息
        stats = {
            'total_tweets': len(tweets),
            'tweets_with_video': sum(1 for t in tweets if t['video_url']),
            'tweets_with_images': sum(1 for t in tweets if t['images']),
            'unique_authors': len(set(t['author'] for t in tweets)),
            'updated_at': datetime.now().isoformat()
        }
        
        with open('docs/stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 统计信息:")
        print(f"   - 总推文数: {stats['total_tweets']}")
        print(f"   - 包含视频: {stats['tweets_with_video']}")
        print(f"   - 包含图片: {stats['tweets_with_images']}")
        print(f"   - 作者数量: {stats['unique_authors']}")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 80)
        print("导出完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    export_tweets_to_json()

import os
import sys
from colorful_state import parse_tweet_url, get_db_connection
from dotenv import load_dotenv

load_dotenv()

def query_tweet_status(urls):
    """查询推文状态"""
    parsed_tweets = [parse_tweet_url(url) for url in urls if parse_tweet_url(url)]
    
    if not parsed_tweets:
        print("未找到有效的推文 URL")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n推文状态查询结果：\n")
        
        for tweet in parsed_tweets:
            cursor.execute("""
                SELECT author, content, content_zh, created_at, images, video_url
                FROM tweets
                WHERE tweet_id = %s
            """, (tweet['tweet_id'],))
            
            row = cursor.fetchone()
            
            if row:
                print(f"✅ {tweet['url']}")
                print(f"   作者: @{row[0]}")
                print(f"   抓取时间: {row[3]}")
                print(f"   翻译: {'已完成' if row[2] else '未完成'}")
                print(f"   图片: {len(row[4]) if row[4] else 0} 张")
                print(f"   视频: {'有' if row[5] else '无'}")
            else:
                print(f"❌ {tweet['url']}")
                print(f"   状态: 未抓取")
            
            print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        urls = sys.argv[1].split(',')
    else:
        # 从 tweets.txt 读取
        if os.path.exists('tweets.txt'):
            urls = []
            with open('tweets.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
        else:
            urls = []
    
    if not urls:
        print("用法: python query_status.py 'url1,url2,...'")
        print("或在 tweets.txt 文件中配置推文 URL")
        sys.exit(1)
    
    query_tweet_status(urls)

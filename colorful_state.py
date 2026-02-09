import os
import time
import random
import json
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 配置
USERS_STR = os.environ.get('TWITTER_USERS', 'elonmusk')
USERS = [u.strip() for u in USERS_STR.split(',') if u.strip()]

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Neon Database 配置
DATABASE_URL = os.environ.get('DATABASE_URL')

# 运行模式配置
LOOP_MODE = os.environ.get('LOOP_MODE', 'false').lower() == 'true'
INTERVAL = int(os.environ.get('LOOP_INTERVAL', '600'))  # 默认 10 分钟

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_FILE = os.path.join(BASE_DIR, 'instances.json')

# Nitter 实例列表（优先使用支持视频的实例）
NITTER_INSTANCES = [
    'https://xcancel.com',  # 支持视频 (source tag)
    'https://nitter.privacyredirect.com',  # 支持视频 (data-url)
    "https://nitter.net",
    "https://nitter.catsarch.com",
    "https://nitter.tiekoetter.com",
    "https://nitter.poast.org",
    "https://nuku.trabun.org",
    "https://lightbrd.com",
    "https://nitter.space"
]

def get_random_user_agent():
    """获取随机 User-Agent"""
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    ]
    return random.choice(ua_list)

def load_instances():
    """从本地缓存加载健康的 Nitter 实例"""
    if os.path.exists(INSTANCES_FILE):
        try:
            with open(INSTANCES_FILE, 'r', encoding='utf-8') as f:
                instances = json.load(f)
                if instances and isinstance(instances, list):
                    print(f"[系统] 成功从本地缓存加载 {len(instances)} 个实例")
                    return instances
        except Exception as e:
            print(f"[系统] 加载实例缓存失败: {e}")
    
    print("[系统] 缓存不存在或损坏，采用内置兜底实例列表")
    return NITTER_INSTANCES

def get_original_image_url(nitter_url):
    """尝试从 Nitter 的代理 URL 中还原出 Twitter/X 的原始图片地址"""
    import urllib.parse
    import re
    try:
        if 'pbs.twimg.com' in nitter_url:
            return nitter_url
            
        # 处理 hex 编码
        if '/pic/enc/' in nitter_url:
            enc_part = nitter_url.split('/pic/enc/')[-1].split('?')[0]
            try:
                decoded = bytes.fromhex(enc_part).decode('utf-8')
                if 'pbs.twimg.com' in decoded:
                    return decoded
            except:
                pass

        # 处理标准 Nitter 路径
        path = urllib.parse.unquote(nitter_url)
        
        if '/media/' in path:
            media_part = path.split('/media/')[-1].split('?')[0]
            if '.' in media_part:
                media_id, ext = media_part.rsplit('.', 1)
                ext = ext.split('&')[0].split('?')[0]
                return f"https://pbs.twimg.com/media/{media_id}?format={ext}&name=large"

        if 'pbs.twimg.com' in path:
            match = re.search(r'(pbs\.twimg\.com/media/[^?&]+)', path)
            if match:
                return "https://" + match.group(1)

    except Exception as e:
        print(f"[图片解析] 还原 URL 失败 {nitter_url}: {e}")
        
    return nitter_url

def scrape_nitter_with_playwright(target, dynamic_instances=None):
    """使用 Playwright 模拟浏览器访问 Nitter 并抓取最新推文"""
    is_search = target.startswith('search:')
    keyword = target[7:] if is_search else target
    
    instances = dynamic_instances if dynamic_instances else NITTER_INSTANCES.copy()
    
    # 随机打乱实例顺序
    if len(instances) > 5:
        top_5 = instances[:5]
        random.shuffle(top_5)
        others = instances[5:]
        random.shuffle(others)
        instances = top_5 + others
    else:
        random.shuffle(instances)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for instance in instances:
            try:
                context = browser.new_context(
                    user_agent=get_random_user_agent(),
                    viewport={'width': 1280, 'height': 720}
                )
                page = context.new_page()
                stealth_sync(page)
                
                if is_search:
                    url = f"{instance.rstrip('/')}/search?f=tweets&q={requests.utils.quote(keyword)}"
                else:
                    url = f"{instance.rstrip('/')}/{keyword}"
                
                print(f"[{target}] 正在加载: {url}")
                
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=45000)
                    if response and response.status == 403:
                        print(f"[{target}] 访问 {instance} 被拒 (403 Forbidden)")
                        context.close()
                        continue
                except Exception as e:
                    print(f"[{target}] 加载 {instance} 超时或失败: {e}")
                    context.close()
                    continue
                
                # 智能等待浏览器验证
                challenge_keywords = ["Verifying your browser", "Just a moment", "Checking your browser"]
                for i in range(5):
                    content = page.content()
                    if any(kw in content for kw in challenge_keywords):
                        print(f"[{target}] 检测到浏览器验证 ({i+1}/5)，尝试等待...")
                        page.wait_for_timeout(5000)
                    else:
                        break
                
                soup = BeautifulSoup(page.content(), 'html.parser')
                items = soup.select('.timeline-item')
                
                if not items:
                    print(f"[{target}] 在实例 {instance} 上未发现推文内容")
                    context.close()
                    continue
                
                # 扫描前 8 条推文
                valid_tweets = []
                for item in items[:8]:
                    # 检查是否是置顶推文
                    is_pinned = item.select_one('.pinned') is not None
                    if is_pinned:
                        print(f"[{target}] 发现置顶推文，跳过")
                        continue
                    
                    # 检查是否是转发
                    is_retweet = item.select_one('.retweet-header') is not None

                    # 提取图片
                    images = []
                    img_els = item.select('.attachment.image img, .tweet-image img, .still-image img, .attachments img')
                    for img in img_els:
                        if any(c in str(img.parent.get('class', [])) for c in ['avatar', 'profile']):
                            continue
                            
                        src = img.get('src', '')
                        if src:
                            if src.startswith('//'):
                                full_src = 'https:' + src
                            elif src.startswith('/'):
                                full_src = instance.rstrip('/') + src
                            else:
                                full_src = src
                            
                            full_src = get_original_image_url(full_src)
                            
                            if 'emoji' in src.lower() or 'hashtag_click' in src:
                                continue
                                
                            images.append(full_src)

                    # 提取视频
                    video_url = None
                    try:
                        video_tag = item.select_one('video')
                        
                        if video_tag:
                            # 方法1: 检查 data-url 属性（Nitter 的主要方式）
                            data_url = video_tag.get('data-url', '')
                            if data_url:
                                # data-url 可能是相对路径或包含编码的 URL
                                if data_url.startswith('/video/'):
                                    # 格式: /video/ID/https%3A%2F%2F...
                                    # 提取实际的视频 URL
                                    parts = data_url.split('/', 3)
                                    if len(parts) > 3:
                                        from urllib.parse import unquote
                                        encoded_url = parts[3]
                                        video_url = unquote(encoded_url)
                                        print(f"[{target}] 找到视频 (data-url): {video_url[:80]}...")
                                elif data_url.startswith('//'):
                                    video_url = 'https:' + data_url
                                    print(f"[{target}] 找到视频 (data-url): {video_url[:80]}...")
                                elif data_url.startswith('/'):
                                    video_url = instance.rstrip('/') + data_url
                                    print(f"[{target}] 找到视频 (data-url): {video_url[:80]}...")
                                else:
                                    video_url = data_url
                                    print(f"[{target}] 找到视频 (data-url): {video_url[:80]}...")
                            
                            # 方法2: 检查 src 属性
                            if not video_url:
                                v_src = video_tag.get('src', '')
                                if v_src:
                                    if v_src.startswith('//'):
                                        video_url = 'https:' + v_src
                                    elif v_src.startswith('/'):
                                        video_url = instance.rstrip('/') + v_src
                                    else:
                                        video_url = v_src
                                    print(f"[{target}] 找到视频 (src): {video_url[:80]}...")
                            
                            # 提取封面图
                            poster = video_tag.get('poster', '')
                            if poster:
                                if poster.startswith('//'):
                                    full_poster = 'https:' + poster
                                elif poster.startswith('/'):
                                    full_poster = instance.rstrip('/') + poster
                                else:
                                    full_poster = poster
                                full_poster = get_original_image_url(full_poster)
                                if full_poster not in images:
                                    images.append(full_poster)
                        
                        # 方法3: 检查 video source 标签
                        if not video_url:
                            video_source = item.select_one('video source')
                            if video_source:
                                v_src = video_source.get('src', '')
                                if v_src:
                                    if v_src.startswith('//'):
                                        video_url = 'https:' + v_src
                                    elif v_src.startswith('/'):
                                        video_url = instance.rstrip('/') + v_src
                                    else:
                                        video_url = v_src
                                    print(f"[{target}] 找到视频 (source): {video_url[:80]}...")
                        
                        # 方法4: 查找视频链接
                        if not video_url:
                            video_links = item.select('a[href*=".mp4"], a[href*=".m3u8"]')
                            for link in video_links:
                                href = link.get('href', '')
                                if href and ('.mp4' in href or '.m3u8' in href):
                                    if href.startswith('//'):
                                        video_url = 'https:' + href
                                    elif href.startswith('/'):
                                        video_url = instance.rstrip('/') + href
                                    else:
                                        video_url = href
                                    print(f"[{target}] 找到视频 (link): {video_url[:80]}...")
                                    break
                        
                        # 如果仍未找到，记录调试信息
                        if not video_url:
                            has_video_indicator = item.select_one('.video-container, .video-overlay, video')
                            if has_video_indicator:
                                print(f"[{target}] 检测到视频但未能提取 URL")
                                
                    except Exception as e:
                        print(f"[{target}] 视频提取异常: {e}")

                    # 提取关键信息
                    content_el = item.select_one('.tweet-content')
                    link_el = item.select_one('.tweet-link')
                    date_el = item.select_one('.tweet-date a')
                    author_el = item.select_one('.username')

                    if not content_el or not link_el:
                        continue

                    # 提取推文 ID
                    link_href = link_el.get('href', '')
                    tweet_id = link_href.split('/status/')[-1].split('#')[0] if '/status/' in link_href else link_href

                    tweet_data = {
                        'content': content_el.get_text(strip=True),
                        'link': instance.rstrip('/') + link_href,
                        'published': date_el.get('title', '') if date_el else 'Unknown Time',
                        'author': author_el.get_text(strip=True) if author_el else keyword,
                        'guid': tweet_id,
                        'is_retweet': is_retweet,
                        'images': images,
                        'video_url': video_url
                    }
                    valid_tweets.append(tweet_data)
                    
                    if len(valid_tweets) >= 1:
                        break

                if valid_tweets:
                    tweet = valid_tweets[0]
                    retweet_tag = " [转发]" if tweet['is_retweet'] else ""
                    print(f"[{target}] 成功从 {instance} 抓取{retweet_tag}推文: {tweet['guid']}")
                    context.close()
                    browser.close()
                    return tweet

                print(f"[{target}] {instance} 页面上未找到符合条件的非置顶推文")
                context.close()

            except Exception as e:
                print(f"[{target}] 访问 {instance} 出错: {e}")
                continue
        
        browser.close()
    return None

def translate_with_deepseek(text):
    """使用 DeepSeek API 翻译文本为中文"""
    if not text or not text.strip():
        return ""
    
    if not DEEPSEEK_API_KEY:
        print("[翻译] DeepSeek API Key 未配置，跳过翻译")
        return None
    
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        
        print(f"[翻译] 正在翻译文本...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译助手，请将用户提供的文本翻译成简体中文。只返回翻译结果，不要添加任何解释或额外内容。"},
                {"role": "user", "content": f"请将以下文本翻译成简体中文：\n\n{text}"}
            ],
            temperature=1.3,  # 官方推荐翻译场景参数
            max_tokens=2000
        )
        
        translated = response.choices[0].message.content.strip()
        print(f"[翻译] 翻译成功")
        return translated
        
    except Exception as e:
        print(f"[翻译] DeepSeek API 调用失败: {e}")
        return None

def get_db_connection():
    """获取数据库连接"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 环境变量未配置")
    
    return psycopg2.connect(DATABASE_URL)

def save_tweet_to_db(tweet):
    """保存推文到数据库"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 翻译推文内容
        content_zh = translate_with_deepseek(tweet['content'])
        
        # 解析发布时间
        published_at = None
        if tweet.get('published') and tweet['published'] != 'Unknown Time':
            try:
                # 尝试解析时间格式
                published_at = datetime.strptime(tweet['published'], '%b %d, %Y · %I:%M %p %Z')
            except:
                try:
                    published_at = datetime.fromisoformat(tweet['published'])
                except:
                    print(f"[数据库] 无法解析时间格式: {tweet['published']}")
        
        # 插入或更新推文
        cursor.execute("""
            INSERT INTO tweets (tweet_id, author, content, content_zh, published_at, is_retweet, images, video_url, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tweet_id) 
            DO UPDATE SET
                content = EXCLUDED.content,
                content_zh = EXCLUDED.content_zh,
                images = EXCLUDED.images,
                video_url = EXCLUDED.video_url,
                source_url = EXCLUDED.source_url,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (
            tweet['guid'],
            tweet['author'],
            tweet['content'],
            content_zh,
            published_at,
            tweet.get('is_retweet', False),
            Json(tweet.get('images', [])),
            tweet.get('video_url'),
            tweet.get('link')
        ))
        
        tweet_db_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"[数据库] 推文已保存 (ID: {tweet_db_id}, Tweet ID: {tweet['guid']})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[数据库] 保存推文失败: {e}")
        return False

def parse_tweet_url(url):
    """
    解析推文 URL 提取用户名和推文 ID
    支持格式:
    - https://x.com/user/status/123456
    - https://twitter.com/user/status/123456
    """
    import re
    pattern = r'(?:x\.com|twitter\.com)/([^/]+)/status/(\d+)'
    match = re.search(pattern, url)
    if match:
        return {
            'username': match.group(1),
            'tweet_id': match.group(2),
            'url': url
        }
    return None

def load_tweet_urls_from_file(filepath='tweets.txt'):
    """从文件读取推文 URL 列表"""
    if not os.path.exists(filepath):
        return []
    
    urls = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith('#'):
                    urls.append(line)
        
        if urls:
            print(f"[读取配置] 从 {filepath} 读取到 {len(urls)} 条推文 URL")
        return urls
    except Exception as e:
        print(f"[读取配置] 读取文件失败: {e}")
        return []

def check_tweet_status(tweet_urls):
    """
    检查推文列表的抓取状态
    返回: (已抓取列表, 待抓取列表)
    """
    if not tweet_urls:
        return [], []
    
    parsed_tweets = []
    for url in tweet_urls:
        parsed = parse_tweet_url(url)
        if parsed:
            parsed_tweets.append(parsed)
        else:
            print(f"[URL解析] 无效的推文 URL: {url}")
    
    if not parsed_tweets:
        return [], []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tweet_ids = [t['tweet_id'] for t in parsed_tweets]
        placeholders = ','.join(['%s'] * len(tweet_ids))
        
        cursor.execute(f"""
            SELECT tweet_id, author, created_at, content_zh IS NOT NULL as has_translation
            FROM tweets
            WHERE tweet_id IN ({placeholders})
        """, tweet_ids)
        
        scraped_dict = {row[0]: {'author': row[1], 'scraped_at': row[2], 'has_translation': row[3]} for row in cursor.fetchall()}
        
        scraped = []
        pending = []
        
        for tweet in parsed_tweets:
            if tweet['tweet_id'] in scraped_dict:
                info = scraped_dict[tweet['tweet_id']]
                scraped.append({
                    **tweet,
                    'scraped_at': info['scraped_at'],
                    'has_translation': info['has_translation']
                })
            else:
                pending.append(tweet)
        
        cursor.close()
        conn.close()
        
        return scraped, pending
        
    except Exception as e:
        print(f"[状态检查] 数据库查询失败: {e}")
        # 失败时，全部视为待抓取
        return [], parsed_tweets

def print_status_report(scraped, pending):
    """打印状态报告"""
    total = len(scraped) + len(pending)
    
    print(f"\n{'='*60}")
    print(f"[状态检查] 配置了 {total} 条推文 URL")
    print(f"{'='*60}")
    
    if scraped:
        print(f"\n✅ 已抓取: {len(scraped)} 条")
        for tweet in scraped:
            trans_status = "✓ 已翻译" if tweet['has_translation'] else "✗ 未翻译"
            scraped_time = tweet['scraped_at'].strftime('%Y-%m-%d %H:%M') if tweet['scraped_at'] else '未知时间'
            print(f"   - {tweet['url']}")
            print(f"     @{tweet['username']} | {scraped_time} | {trans_status}")
    
    if pending:
        print(f"\n⏳ 待抓取: {len(pending)} 条")
        for tweet in pending:
            print(f"   - {tweet['url']}")
    
    print(f"\n{'='*60}\n")

def scrape_tweet_by_id(username, tweet_id, dynamic_instances=None):
    """根据用户名和推文 ID 抓取指定推文"""
    instances = dynamic_instances if dynamic_instances else NITTER_INSTANCES.copy()
    random.shuffle(instances)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for instance in instances:
            try:
                context = browser.new_context(
                    user_agent=get_random_user_agent(),
                    viewport={'width': 1280, 'height': 720}
                )
                page = context.new_page()
                stealth_sync(page)
                
                # 构造推文 URL: instance/username/status/tweet_id
                url = f"{instance.rstrip('/')}/{username}/status/{tweet_id}"
                
                print(f"[{username}/{tweet_id}] 正在加载: {url}")
                
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=45000)
                    if response and response.status == 403:
                        print(f"[{username}/{tweet_id}] 访问 {instance} 被拒 (403 Forbidden)")
                        context.close()
                        continue
                except Exception as e:
                    print(f"[{username}/{tweet_id}] 加载 {instance} 超时或失败: {e}")
                    context.close()
                    continue
                
                # 智能等待浏览器验证
                challenge_keywords = ["Verifying your browser", "Just a moment", "Checking your browser"]
                for i in range(5):
                    content = page.content()
                    if any(kw in content for kw in challenge_keywords):
                        print(f"[{username}/{tweet_id}] 检测到浏览器验证 ({i+1}/5)，尝试等待...")
                        page.wait_for_timeout(5000)
                    else:
                        break
                
                soup = BeautifulSoup(page.content(), 'html.parser')
                
                # 查找主推文内容
                main_tweet = soup.select_one('.main-tweet')
                if not main_tweet:
                    print(f"[{username}/{tweet_id}] 在 {instance} 上未找到推文")
                    context.close()
                    continue
                
                print(f"[{username}/{tweet_id}] ✅ 使用实例: {instance}")
                
                # 提取推文信息（复用原有逻辑）
                content_el = main_tweet.select_one('.tweet-content')
                date_el = main_tweet.select_one('.tweet-date a')
                author_el = main_tweet.select_one('.username')
                
                if not content_el:
                    print(f"[{username}/{tweet_id}] 推文内容为空")
                    context.close()
                    continue
                
                # 提取图片
                images = []
                img_els = main_tweet.select('.attachment.image img, .tweet-image img, .still-image img, .attachments img')
                for img in img_els:
                    if any(c in str(img.parent.get('class', [])) for c in ['avatar', 'profile']):
                        continue
                    src = img.get('src', '')
                    if src:
                        if src.startswith('//'):
                            full_src = 'https:' + src
                        elif src.startswith('/'):
                            full_src = instance.rstrip('/') + src
                        else:
                            full_src = src
                        full_src = get_original_image_url(full_src)
                        if 'emoji' not in src.lower():
                            images.append(full_src)
                
                # 提取视频
                video_url = None
                try:
                    video_tag = main_tweet.select_one('video')
                    
                    if video_tag:
                        # 方法1: 检查 data-url 属性（Nitter 的主要方式）
                        data_url = video_tag.get('data-url', '')
                        if data_url:
                            # data-url 可能是相对路径或包含编码的 URL
                            if data_url.startswith('/video/'):
                                # 格式: /video/ID/https%3A%2F%2F...
                                # 提取实际的视频 URL
                                parts = data_url.split('/', 3)
                                if len(parts) > 3:
                                    from urllib.parse import unquote
                                    encoded_url = parts[3]
                                    video_url = unquote(encoded_url)
                                    print(f"[{username}/{tweet_id}] 找到视频 (data-url): {video_url[:80]}...")
                            elif data_url.startswith('//'):
                                video_url = 'https:' + data_url
                                print(f"[{username}/{tweet_id}] 找到视频 (data-url): {video_url[:80]}...")
                            elif data_url.startswith('/'):
                                video_url = instance.rstrip('/') + data_url
                                print(f"[{username}/{tweet_id}] 找到视频 (data-url): {video_url[:80]}...")
                            else:
                                video_url = data_url
                                print(f"[{username}/{tweet_id}] 找到视频 (data-url): {video_url[:80]}...")
                        
                        # 方法2: 检查 src 属性
                        if not video_url:
                            v_src = video_tag.get('src', '')
                            if v_src:
                                if v_src.startswith('//'):
                                    video_url = 'https:' + v_src
                                elif v_src.startswith('/'):
                                    video_url = instance.rstrip('/') + v_src
                                else:
                                    video_url = v_src
                                print(f"[{username}/{tweet_id}] 找到视频 (src): {video_url[:80]}...")
                        
                        # 提取封面图
                        poster = video_tag.get('poster', '')
                        if poster:
                            if poster.startswith('//'):
                                full_poster = 'https:' + poster
                            elif poster.startswith('/'):
                                full_poster = instance.rstrip('/') + poster
                            else:
                                full_poster = poster
                            full_poster = get_original_image_url(full_poster)
                            if full_poster not in images:
                                images.append(full_poster)
                    
                    # 方法3: 检查 video source 标签
                    if not video_url:
                        video_source = main_tweet.select_one('video source')
                        if video_source:
                            v_src = video_source.get('src', '')
                            if v_src:
                                if v_src.startswith('//'):
                                    video_url = 'https:' + v_src
                                elif v_src.startswith('/'):
                                    video_url = instance.rstrip('/') + v_src
                                else:
                                    video_url = v_src
                                print(f"[{username}/{tweet_id}] 找到视频 (source): {video_url[:80]}...")
                    
                    # 方法4: 查找视频链接
                    if not video_url:
                        video_links = main_tweet.select('a[href*=".mp4"], a[href*=".m3u8"]')
                        for link in video_links:
                            href = link.get('href', '')
                            if href and ('.mp4' in href or '.m3u8' in href):
                                if href.startswith('//'):
                                    video_url = 'https:' + href
                                elif href.startswith('/'):
                                    video_url = instance.rstrip('/') + href
                                else:
                                    video_url = href
                                print(f"[{username}/{tweet_id}] 找到视频 (link): {video_url[:80]}...")
                                break
                    
                    if not video_url:
                        # 检查是否有视频指示器
                        has_video = main_tweet.select_one('.video-container, .video-overlay, video')
                        if has_video:
                            print(f"[{username}/{tweet_id}] 检测到视频但未能提取 URL")
                            
                except Exception as e:
                    print(f"[{username}/{tweet_id}] 视频提取异常: {e}")
                
                tweet_data = {
                    'content': content_el.get_text(strip=True),
                    'link': url,
                    'published': date_el.get('title', '') if date_el else 'Unknown Time',
                    'author': author_el.get_text(strip=True) if author_el else username,
                    'guid': tweet_id,
                    'is_retweet': False,
                    'images': images,
                    'video_url': video_url
                }
                
                print(f"[{username}/{tweet_id}] 成功从 {instance} 抓取推文")
                context.close()
                browser.close()
                return tweet_data
                
            except Exception as e:
                print(f"[{username}/{tweet_id}] 访问 {instance} 出错: {e}")
                continue
        
        browser.close()
    return None

def main():
    print(f"[{datetime.now()}] 启动 Colorful State 监控系统...")
    
    # 从本地缓存加载可用实例
    instances = load_instances()

    while True:
        cycle_start = time.time()
        print(f"\n--- 启动新一轮监控轮询 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---")
        
        # 优先处理文件中的推文 URL
        tweet_urls = load_tweet_urls_from_file('tweets.txt')
        
        if tweet_urls:
            print(f"\n[模式] 单条推文抓取模式")
            
            # 检查状态
            scraped, pending = check_tweet_status(tweet_urls)
            
            # 打印报告
            print_status_report(scraped, pending)
            
            # 仅抓取待抓取的推文
            if pending:
                print(f"[开始抓取] 抓取 {len(pending)} 条待抓取推文...\n")
                for tweet_info in pending:
                    try:
                        tweet = scrape_tweet_by_id(
                            tweet_info['username'],
                            tweet_info['tweet_id'],
                            instances
                        )
                        if tweet:
                            save_tweet_to_db(tweet)
                    except Exception as e:
                        print(f"[{tweet_info['url']}] 处理异常: {e}")
            else:
                print("[完成] 所有配置的推文都已抓取，无需重复抓取。")
        
        # 处理用户监控模式
        if USERS:
            print(f"\n[模式] 用户监控模式 ({len(USERS)} 个用户)")
            for target in USERS:
                try:
                    tweet = scrape_nitter_with_playwright(target, instances)
                    if tweet:
                        save_tweet_to_db(tweet)
                    else:
                        print(f"[{target}] 未能抓取到推文")
                except Exception as e:
                    print(f"[{target}] 处理异常: {e}")

        if not LOOP_MODE:
            print("\n[系统] 非循环模式，任务结束。")
            break
        
        # 计算需要 sleep 的时间
        elapsed = time.time() - cycle_start
        sleep_time = max(10, INTERVAL - elapsed)
        print(f"--- 轮询结束。耗时 {elapsed:.1f}s，准备休眠 {sleep_time:.1f}s ---\n")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL 环境变量未设置")
    exit(1)

print("=" * 60)
print("数据库自动设置脚本")
print("=" * 60)
print()

# 读取 schema.sql
schema_file = 'schema.sql'
if not os.path.exists(schema_file):
    print(f"❌ 找不到 {schema_file} 文件")
    exit(1)

with open(schema_file, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

print(f"✅ 已读取 {schema_file}")
print()

try:
    print("正在连接数据库...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    print("✅ 数据库连接成功")
    print()
    
    print("正在执行 schema.sql...")
    cursor.execute(schema_sql)
    print("✅ Schema 执行成功")
    print()
    
    # 验证表是否创建
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'tweets'
        );
    """)
    table_exists = cursor.fetchone()[0]
    
    if table_exists:
        print("✅ tweets 表已成功创建")
        
        # 获取表结构
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'tweets'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print()
        print("表结构:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")
        
        # 获取索引
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'tweets';
        """)
        indexes = cursor.fetchall()
        
        print()
        print("索引:")
        for idx in indexes:
            print(f"  - {idx[0]}")
    else:
        print("⚠️  tweets 表创建失败")
    
    cursor.close()
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ 数据库设置完成！")
    print("=" * 60)
    print()
    print("现在可以运行: python colorful_state.py")
    
except psycopg2.Error as e:
    print(f"❌ 数据库错误: {e}")
    print()
    print("请检查:")
    print("1. DATABASE_URL 是否正确")
    print("2. 数据库用户是否有创建表的权限")
    print("3. 网络连接是否正常")
    
except Exception as e:
    print(f"❌ 发生错误: {e}")

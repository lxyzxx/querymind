import os

from querymind.client import QueryMindClient

# 连接服务
client = QueryMindClient("localhost", 50051)

# 创建 session
sid = client.open_session()

# 执行用户提供的 Python 代码
code = """
import pandas as pd
import psycopg2 as pg

engine = pg.connect(
    dbname=os.getenv("QUERYMIND_PG_DATABASE", "postgres"),
    user=os.getenv("QUERYMIND_PG_USER", "postgres"),
    host=os.getenv("QUERYMIND_PG_HOST", "localhost"),
    port=os.getenv("QUERYMIND_PG_PORT", "5432"),
    password=os.getenv("QUERYMIND_PG_PASSWORD", ""),
)
df = pd.read_sql('select * from users', con=engine)
print(df.head())
"""
out = client.execute(sid, code)
print("执行输出:\n", out)

# 关闭 session
client.close_session(sid)
client.close()

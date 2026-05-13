from querymind.client import QueryMindClient

# 连接服务
client = QueryMindClient("localhost", 50051)

# 创建 session
sid = client.open_session()

# 执行简单代码
client.execute(sid, "x = 100")

# 执行用户提供的 Python 代码
code = """
import pandas as pd
numbers = [1, 2, 3, 4, 5]
print("原始列表:", numbers)
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
# 计算平方
squares = [x**2 for x in numbers]
print("平方值:", squares)

# 计算和
total = sum(squares)
print("总和:", total)

# 返回结果
result = {"squares": squares, "total": total}
"""
out = client.execute(sid, code)
print("执行输出:\n", out)

# 通过 get_variable 获取执行结果
squares_val = client.get_variable(sid, "squares")
total_val = client.get_variable(sid, "total")
result_val = client.get_variable(sid, "result")
df_val = client.get_variable(sid, "df")
not_exist = client.get_variable(sid, "not_exist")

print("squares:", squares_val)
print("total:", total_val)
print("result:", result_val)
print("df:", df_val)
print("not_exist:", not_exist)

# 关闭 session
client.close_session(sid)
client.close()

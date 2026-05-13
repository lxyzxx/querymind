import grpc
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../generated'))
import cli_pb2, cli_pb2_grpc
import pickle

class QueryMindClient:
    """
    QueryMind Python SDK Client

    负责：
    - 建立 gRPC 连接
    - 管理 session
    - 执行 Python 代码
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        self.address = f"{host}:{port}"
        self.channel = grpc.insecure_channel(self.address)

        self.cli_stub = cli_pb2_grpc.CliStub(self.channel)
        self.exec_stub = cli_pb2_grpc.ExecutorStub(self.channel)
        self.var_stub = cli_pb2_grpc.VariableGetterStub(self.channel)

    # ---------------- Session ----------------

    def open_session(self) -> str:
        """创建一个新的 session"""
        resp = self.cli_stub.OpenSession(
            cli_pb2.OpenSessionReq()
        )
        return resp.session_id

    def close_session(self, session_id: str) -> None:
        """关闭 session"""
        self.cli_stub.CloseSession(
            cli_pb2.CloseSessionReq(session_id=session_id)
        )

    # ---------------- Execute ----------------

    def execute(
        self,
        session_id: str,
        code: str,
        raise_on_error: bool = True
    ) -> str:
        """
        在指定 session 中执行 Python 代码

        :param session_id: session id
        :param code: Python code string
        :param raise_on_error: 是否在执行失败时抛异常
        :return: stdout 输出
        """
        resp = self.exec_stub.ExecuteCode(
            cli_pb2.ExecuteCodeReq(
                session_id=session_id,
                code=code
            )
        )

        if not resp.success and raise_on_error:
            return resp.error

        return resp.output

    def get_variable(
            self,
            session_id: str,
            variable_name: str,
            raise_on_error: bool = True,
    ) -> dict:
        """
        在指定 session 中获取变量值
        """
        resp = self.var_stub.GetVariable(
            cli_pb2.GetVariableReq(
                session_id=session_id,
                variable_name=variable_name,
            )
        )

        result = {
            "type": "get_variable",
            "found": False,
            "var_name": variable_name,
            "var_type": "",
            "var_value": None
        }

        if not resp.success:
            result.update({
                "found": False,
                "error": resp.error
            })
            return result

        try:
            value = pickle.loads(resp.value)
            result.update({
                "found": True,
                "var_value": value,
                "var_type": type(value).__name__
            })
        except Exception as e:
            # 如果反序列化失败，也返回失败结构
            result.update({
                "found": False,
                "error": f"Failed to deserialize variable: {e}"
            })
        return result

    # ---------------- Lifecycle ----------------

    def close(self):
        """关闭 gRPC 连接"""
        self.channel.close()

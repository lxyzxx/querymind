import traceback
from concurrent import futures
import grpc
import logging
import threading
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../generated'))
import cli_pb2,cli_pb2_grpc


class CliServicer(cli_pb2_grpc.CliServicer):
    def __init__(self, scheduler):
        self.scheduler = scheduler

    def OpenSession(self, request, context):
        # 在 Scheduler 中分配 Worker
        sid = self.scheduler.open_session()

        return cli_pb2.OpenSessionResp(session_id=sid)

    def CloseSession(self, request, context):
        sid = request.session_id

        if sid in self.scheduler.sessions:
            self.scheduler.close_session(sid)

        return cli_pb2.CloseSessionResp()
class ExecutorServicer(cli_pb2_grpc.ExecutorServicer):
    def __init__(self, scheduler):
        self.scheduler = scheduler

    def ExecuteCode(self, request, context):
        if request.session_id not in self.scheduler.sessions:
            return cli_pb2.ExecuteCodeResp(output="", error="unknown session", success=False)
        # Phase2: session绑定Worker
        resp = self.scheduler.submit_task(request.code, session_id=request.session_id)
        return cli_pb2.ExecuteCodeResp(
            output=resp["output"],
            error=resp["error"],
            success=resp["success"]
        )

class VariableGetterServicer(cli_pb2_grpc.VariableGetterServicer):
    def __init__(self, scheduler):
        self.scheduler = scheduler

    def GetVariable(self, request, context):
        session_id = request.session_id
        var_name = request.variable_name
        worker = self.scheduler.sessions[session_id].assigned_worker
        # Use worker.get_variable to support both in-thread and subprocess sessions
        try:
            res = worker.get_variable(session_id, var_name)
        except Exception:
            return cli_pb2.GetVariableResp(value=b"", error=traceback.format_exc(), success=False)

        if not res.get('success'):
            return cli_pb2.GetVariableResp(value=b"", error=res.get('error', ''), success=False)

        # prefer serialized value when available, otherwise fall back to repr
        if 'value' in res and res.get('value') is not None:
            try:
                return cli_pb2.GetVariableResp(value=res.get('value'), error="", success=True)
            except Exception:
                return cli_pb2.GetVariableResp(value=res.get('repr', ''), error="", success=True)
        else:
            return cli_pb2.GetVariableResp(value=res.get('repr', ''), error="", success=True)

def start_metrics_logger(scheduler, interval=2):
    def run():
        while True:
            metrics = scheduler.get_metrics()
            logging.debug(f"[Metrics] Total tasks: {metrics['tasks_total']}, "
                         f"Available workers: {metrics['workers_available']}, "
                         f"Active workers: {metrics['workers_active']}, "
                         f"Sessions active: {metrics['sessions_active']}")
            time.sleep(interval)
    t = threading.Thread(target=run, daemon=True)
    t.start()

def serve(scheduler, host, port, max_workers):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers)
    )

    cli_pb2_grpc.add_CliServicer_to_server(
        CliServicer(scheduler), server
    )
    cli_pb2_grpc.add_ExecutorServicer_to_server(
        ExecutorServicer(scheduler), server
    )
    cli_pb2_grpc.add_VariableGetterServicer_to_server(
        VariableGetterServicer(scheduler), server
    )

    addr = f"{host}:{port}"
    server.add_insecure_port(addr)
    server.start()
    logging.info(f"gRPC server started on {addr}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Shutting down server")
        server.stop(0)

import contextlib
import io
import logging
import queue
import threading
import time
import traceback
import multiprocessing
import pickle


def _exec_in_process(code, ns,  resp_q):
    """Helper target for an isolated process that executes `code` and posts result to `resp_q`."""
    #try:
    buf = io.StringIO()
    start_ts = time.time()
    print("Executing code in subprocess...")
    print(code)
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, ns)
        success = True
        error_text = ""
    except Exception:
        success = False
        error_text = traceback.format_exc()
    stdout_buf = buf.getvalue()
    end_ts = time.time()
    print("Subprocess execution complete.")
    try:
        resp_q.put({
            "output": stdout_buf,
            "error": error_text,
            "success": success,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "ns": ns
        })
    except Exception:
        pass
    #finally:
    #    # Ensure the subprocess exits
    #    try:
    #        import os
    #        os._exit(0)
    #    except Exception:
    #        pass


class Worker:
    def __init__(self, worker_id, use_subprocess=False, subprocess_timeout=None):
        """Worker can either execute code in-thread or spawn an independent subprocess per exec.

        - `use_subprocess`: if True, `submit_task` will run each EXEC in a new process (no session persistence).
        - `subprocess_timeout`: optional timeout (seconds) to wait for subprocess result before killing it.
        """
        self.worker_id = worker_id
        self.use_subprocess = use_subprocess
        self.subprocess_timeout = subprocess_timeout
        self.executing = False
        # thread-based queue and ctx map for session-persistent mode
        self.req_q = queue.Queue()
        self.exec_ctx_map = {}
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while True:
            task = self.req_q.get()
            t = task["type"]
            session_id = task.get("session_id")
            if t == "EXEC":
                code = task.get("code")
                # if using subprocess mode, the `submit_task` shortcut handles separate processes,
                # but the run loop still supports running code in-process for compatibility.
                ctx = self.exec_ctx_map.setdefault(session_id, {})
                start_ts = time.time()
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf):
                        exec(code, ctx)
                    success = True
                    error_text = ""
                except Exception as e:
                    success = False
                    error_text = f"{type(e).__name__}:{str(e)}"
                    logging.error(traceback.format_exc())
                stdout_buf = buf.getvalue()
                end_ts = time.time()
                self.executing = False
                try:
                    task["resp_q"].put({
                        "output": stdout_buf,
                        "error": error_text,
                        "success": success,
                        "start_ts": start_ts,
                        "end_ts": end_ts
                    })
                except Exception:
                    pass
            elif t == "RESET":
                if session_id and session_id in self.exec_ctx_map:
                    del self.exec_ctx_map[session_id]

    def submit_task(self, code, session_id):
        """提交任务并阻塞等待结果

        If `use_subprocess` is True, run `code` in an independent process and return its result.
        Note: subprocess mode does NOT preserve session execution context between runs.
        """
        self.executing = True
        if self.use_subprocess:
            ns = self.exec_ctx_map.setdefault(session_id, {})
            ctx = multiprocessing.get_context("spawn")
            resp_q = ctx.Queue()
            p = ctx.Process(target=_exec_in_process, args=(code, ns, resp_q))
            p.start()
            result = None
            try:
                if self.subprocess_timeout is None:
                    result = resp_q.get()
                else:
                    result = resp_q.get(timeout=self.subprocess_timeout)
                    self.exec_ctx_map[session_id] = result.get("ns", {})
            except Exception:
                # timeout or other error: ensure process is terminated
                try:
                    if p.is_alive():
                        p.terminate()
                except Exception:
                    pass
                result = {
                    "output": "",
                    "error": "subprocess execution timeout or error",
                    "success": False,
                    "start_ts": time.time(),
                    "end_ts": time.time(),
                }
            finally:
                try:
                    p.join(0.1)
                except Exception:
                    pass
                self.executing = False
                return result

        resp_q = queue.Queue()
        self.req_q.put({
            "type": "EXEC",
            "session_id": session_id,
            "code": code,
            "resp_q": resp_q
        })
        return resp_q.get()


    def get_variable(self, session_id, var_name):
        """获取指定 session 中的变量值"""
        if session_id not in self.exec_ctx_map:
            return {"success": False, "error": f"unknown session {session_id}"}
        ctx = self.exec_ctx_map[session_id]
        if var_name not in ctx:
            return {"success": False, "error": f"variable '{var_name}' not found in session {session_id}"}
        value = ctx[var_name]
        value = pickle.dumps(value)
        try:
            return {"success": True, "value": value}
        except Exception:
            return {"success": True, "repr": repr(value)}

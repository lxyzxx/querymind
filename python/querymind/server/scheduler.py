import threading
import time
import uuid
import logging

from querymind.server.worker import Worker

class Session:
    """只负责生命周期管理"""
    def __init__(self, session_id):
        self.session_id = session_id
        self.session_start_ts = time.time()
        self.last_active_ts = time.time()
        self.assigned_worker = None  # 绑定 Worker，保持 namespace


class Scheduler:
    """重构后的 Scheduler"""
    def __init__(self, num_workers=3, idle_timeout=30, max_life_timeout=300):
        self.lock = threading.Lock()
        self.workers = [Worker(i) for i in range(num_workers)]
        self.sessions = {}  # session_id -> Session
        self.tasks_total = 0

        self.idle_timeout = idle_timeout
        self.max_life_timeout = max_life_timeout

        self._start_cleaner()

    # ---------------- Session 生命周期 ----------------
    def open_session(self):
        sid = str(uuid.uuid4())
        with self.lock:
            session = Session(sid)
            self.sessions[sid] = session
        logging.info("Session opened: %s", sid)
        return sid

    def close_session(self, session_id, reason='Closed by client'):
        with self.lock:
            session = self.sessions.pop(session_id, None)
        if session:
            if session.assigned_worker:
                session.assigned_worker.req_q.put({
                    "type": "RESET",
                    "session_id": session_id
                })
                session.assigned_worker = None
            logging.info("Session closed: %s reason=%s", session_id, reason)

    # ---------------- Worker / Task ----------------
    def _get_free_worker(self):
        """获取空闲 Worker 阻塞等待"""
        while True:
            with self.lock:
                for w in self.workers:
                    if not w.executing:
                        return w
            time.sleep(0.05)

    def submit_task(self, code, session_id):
        with self.lock:
            if session_id not in self.sessions:
                raise RuntimeError(f"session {session_id} not opened")
            session = self.sessions[session_id]

            worker = session.assigned_worker

        # 如果已有 assigned_worker，等待它空闲
        if worker:
            while worker.executing:
                time.sleep(0.05)
        else:
            # 为 session 分配一个空闲 Worker
            while True:
                with self.lock:
                    free_worker = next((w for w in self.workers if not w.executing), None)
                    if free_worker:
                        worker = free_worker
                        session.assigned_worker = worker
                        break
                time.sleep(0.05)

        # 提交任务
        resp = worker.submit_task(code, session_id)

        # 更新 session 活跃时间
        session.last_active_ts = time.time()
        with self.lock:
            self.tasks_total += 1

        return resp

    # ---------------- Cleaner ----------------
    def _start_cleaner(self):
        t = threading.Thread(target=self._cleaner_loop, daemon=True)
        t.start()

    def _cleaner_loop(self):
        while True:
            now = time.time()
            to_close = []

            with self.lock:
                for sid, session in self.sessions.items():
                    # max life timeout
                    if (self.max_life_timeout and
                        now - session.session_start_ts > self.max_life_timeout):
                        to_close.append((sid, "max_life", now - session.session_start_ts))
                        continue

                    # idle timeout
                    if (self.idle_timeout and
                        now - session.last_active_ts > self.idle_timeout):
                        to_close.append((sid, "idle", now - session.last_active_ts))

            for sid, reason, duration in to_close:
                self.close_session(sid, reason=reason)
            time.sleep(1)

    # ---------------- Metrics ----------------
    def get_metrics(self):
        with self.lock:
            workers_active = sum(1 for w in self.workers if w.executing)
            return {
                "tasks_total": self.tasks_total,
                "workers_active": workers_active,
                "workers_available": len(self.workers) - workers_active,
                "sessions_active": len(self.sessions)
            }

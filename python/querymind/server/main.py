import argparse
import logging
import os

from querymind.server.config import load_config, setup_logging_simple
from querymind.server.scheduler import Scheduler
from querymind.server.server import serve
from querymind.server.server import start_metrics_logger


def main():
    # 1. 读取配置
    parser = argparse.ArgumentParser(description="QueryMind gRPC Server")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.yaml"
    )
    args = parser.parse_args()
    if args.config:
        cfg_path = args.config
    else:
        # 默认路径：同目录下的 config.yaml
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    cfg = load_config(cfg_path)

    # 2. 初始化日志
    log_file = cfg.get("logging", {}).get("log_file", None)
    setup_logging_simple(cfg["logging"]["level"], log_file)

    logging.info(f"Loaded config from {cfg_path}: {cfg}")


    # 3. 初始化核心组件
    scheduler = Scheduler(
        num_workers=cfg["scheduler"]["num_workers"],
        idle_timeout=cfg["scheduler"]["idle_timeout_sec"],
        max_life_timeout=cfg["scheduler"]["max_life_timeout_sec"]
    )

    # 4. 启动 metrics logger
    start_metrics_logger(scheduler, interval=2)

    # 5. 启动 gRPC server
    serve(
        scheduler=scheduler,
        host=cfg["server"]["host"],
        port=cfg["server"]["port"],
        max_workers=cfg["server"]["grpc_max_workers"],
    )


if __name__ == "__main__":
    main()

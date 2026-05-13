import yaml
import logging


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    return cfg

def setup_logging_simple(level="INFO", log_file=None):
    if log_file:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(message)s",
            filename=log_file
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(message)s"
        )
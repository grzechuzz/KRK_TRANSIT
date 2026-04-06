import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the entire application. Call once at process startup."""
    root = logging.getLogger()
    root.setLevel(level)

    if any(getattr(handler, "name", "") == "mpk_stdout" for handler in root.handlers):
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name("mpk_stdout")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

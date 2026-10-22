import json
import logging


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        # Security events pass structured fields (ids only, never secrets).
        if hasattr(record, "event"):
            log_record["event"] = record.event
        if hasattr(record, "fields"):
            log_record["fields"] = record.fields
        return json.dumps(log_record, default=str)


def setup_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)


def security_event(event: str, request_id: str | None = None, **fields: object) -> None:
    """Log a security-relevant event (login failed, token reuse, ...).
    Pass ids only. Never pass passwords, tokens or email bodies."""
    logging.getLogger("security").info(
        event, extra={"event": event, "request_id": request_id, "fields": fields}
    )
    from app.audit.service import persist_access_event  # imported here: the audit module needs the database

    persist_access_event(event, request_id, fields)

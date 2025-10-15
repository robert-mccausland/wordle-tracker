import logging
import json
from datetime import datetime

FORWARDED_FIELDS = ["user_id", "guild_id", "channel_id", "name"]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }

        for field in FORWARDED_FIELDS:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)

        if record.exc_info:
            log_record["error"] = self.formatException(record.exc_info)

        return json.dumps(log_record)

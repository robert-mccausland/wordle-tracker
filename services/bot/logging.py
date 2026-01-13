import logging
import os
import sys
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogRecordExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry._logs import set_logger_provider

FORWARDED_FIELDS = ["user_id", "guild_id", "channel_id", "name"]


def setup_logging() -> None:
    if os.getenv("DEBUG") == "TRUE":
        debug_handler = logging.StreamHandler(sys.stdout)
        debug_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.basicConfig(level=logging.INFO, handlers=[debug_handler])
    else:
        provider = LoggerProvider(Resource.create(get_attributes()))
        provider.add_log_record_processor(BatchLogRecordProcessor(ConsoleLogRecordExporter()))
        provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(provider)

        handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
        logging.basicConfig(level=logging.INFO, handlers=[handler])


def get_attributes() -> dict[str, str]:
    attributes = {"service.name": "wordle-tracker"}
    version = os.getenv("VERSION")
    if version is not None:
        attributes["service.versin"] = version

    return attributes

from unittest import TestCase

from rasa_integration_testing.logging_provider import get_logger

LOGGER_NAME = "test_logging_provider"


class TestLoggingProvider(TestCase):
    def test_session_id_logging(self):
        with self.assertLogs(LOGGER_NAME, level="INFO") as context_manager:
            logger = get_logger(LOGGER_NAME)
            logger.info("This is a test")
            logger.info("This is a test", session_id="abc123")
            self.assertEqual(
                context_manager.output,
                [
                    "INFO:test_logging_provider:This is a test",
                    "INFO:test_logging_provider:[SID:abc123]:This is a test",
                ],
            )

    def test_double_quote_logging(self):
        with self.assertLogs(LOGGER_NAME, level="INFO") as context_manager:
            logger = get_logger(LOGGER_NAME)
            logger.info('This is a "test"')
            self.assertEqual(
                context_manager.output, ['INFO:test_logging_provider:This is a "test"']
            )

    def test_invalid_log_format(self):
        log_name = "rasa_integration_testing.logging_provider"
        level = "ERROR"
        error_message = "Unable to parse logging format \"Invalid {test}\". \
Error: name 'test' is not defined."

        with self.assertLogs(log_name, level=level) as context_manager:
            logger = get_logger(__name__)
            logger.info("Invalid {test}")
            logger.info("Invalid {test}", session_id="abc123")
            self.assertEqual(
                context_manager.output,
                [
                    f"{level}:{log_name}:{error_message}",
                    f"{level}:{log_name}:[SID:abc123]:{error_message}",
                ],
            )

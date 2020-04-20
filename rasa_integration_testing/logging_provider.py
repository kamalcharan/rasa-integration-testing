import logging
import os

from coloredlogs import StandardErrorHandler

DEFAULT_LOGGING_LEVEL = "INFO"
ENVIRONMENT_VARIABLE_NAME = "LOGGING_LEVEL"
LOGGING_FORMAT = "%(asctime)s %(levelname)-8s %(name)s.%(funcName)-20s - %(message)s"
SESSION_ID_KEY = "session_id"

# NOTE:
# In the logging_provider, we are not using the customAdapter capability to process
# extra variables but are using plain "f" strings. This is because this customAdapter
# capability is only available once the module is fully initialized.


def get_logger(logger_name):
    return _adapt_logging_format(logging.getLogger(logger_name))


class _CustomAdapter(logging.LoggerAdapter):
    def process(self, message, kwargs):
        # use session_id from kwargs or the default given on instantiation
        session_id = kwargs.pop(SESSION_ID_KEY, self.extra[SESSION_ID_KEY])

        if kwargs is not None:
            # Publish the content of the dictionnary as local variables.
            locals().update(kwargs)
            # Make sure to remove all but the "session_id" keys from the dictionary
            # otherwise, the logger will complain that extra variables are not
            # specified in the logging format.
            delete = [key for key in kwargs if key is not SESSION_ID_KEY]
            for key in delete:
                del kwargs[key]

        # Resolve the fString using the newly added "local" variables.
        try:
            resolved_message = eval('f"' + message.replace('"', '\\"') + '"')
            # Only add the session ID if specified on the logging statement ...
            if session_id:
                return f"[SID:{session_id}]:{resolved_message}", kwargs

            return f"{resolved_message}", kwargs
        except Exception as error:
            logger = logging.getLogger(__name__)
            if session_id:
                logger.error(
                    f'[SID:{session_id}]:Unable to parse logging format "{message}". \
Error: {error}.'
                )
            else:
                logger.error(
                    f'Unable to parse logging format "{message}". Error: {error}.'
                )

            return message, kwargs


def _initialize_module():
    logger = logging.getLogger(__name__)

    # process root logger ...
    root_logger = logging.getLogger()
    _set_logging_level(root_logger)
    logger.info("Setting root logger ...")
    _set_log_formatter_for_handler(logger, root_logger)
    logger.info("Setting root logger done.")

    # process Sanic loggers from the list of all loggers ...
    logger.info("Setting Sanic loggers ...")
    for name in logging.root.manager.loggerDict:
        if name.startswith("sanic"):
            sanic_logger = logging.getLogger(name)
            _set_log_formatter_for_handler(logger, sanic_logger)
    logger.info("Setting Sanic loggers done.")


def _set_logging_level(logger):

    logging_level = DEFAULT_LOGGING_LEVEL
    try:
        logging_level = os.environ[ENVIRONMENT_VARIABLE_NAME]
        logger.info(f'Setting logging level to "{logging_level}".')
    except Exception:
        logger.info(
            f'Environment variable "{ENVIRONMENT_VARIABLE_NAME}" is not defined, setting \
logging level to default value "{logging_level}".'
        )

    # Translate the logLevel input string to one of the accepted values of the logging
    # module. Change it to upper to allow calling module to use lowercase. If it
    # doesn't translate default to something like DEBUG which is 10
    numeric_level = getattr(logging, logging_level.upper(), logging.DEBUG)
    logging.basicConfig(level=numeric_level)

    logger.setLevel(numeric_level)
    for handler in logger.handlers:
        handler.setLevel(level=numeric_level)


def _set_log_formatter_for_handler(logger, logger_object):
    formatter = logging.Formatter(LOGGING_FORMAT, datefmt="%Y-%m-%d,%H:%M:%S")

    # Update the console formatter
    if len(logger_object.handlers) > 0:
        for handler in logger_object.handlers:
            if isinstance(handler, StandardErrorHandler):
                logger.info(
                    f'Setting formatter for logger "{logger_object.name}"\
, handler "{handler.__class__.__name__}"'
                )
                handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.info(
            f'No handler for logger "{logger_object.name}"\
, adding "{console_handler.__class__.__name__}"'
        )
        logger_object.addHandler(console_handler)


def _adapt_logging_format(logger):
    # Default session ID is empty, unless explicitely passed on the
    # logging statement.
    adapter = _CustomAdapter(logger, {SESSION_ID_KEY: ""})
    return adapter


_initialize_module()

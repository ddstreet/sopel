# coding=utf-8
from __future__ import unicode_literals, absolute_import, print_function, division

import logging
import os
from logging.config import dictConfig

from sopel import tools


class IrcLoggingHandler(logging.Handler):
    def __init__(self, bot, level, lines_split=False, lines_leading=0, lines_trailing=0):
        super(IrcLoggingHandler, self).__init__(level)
        self._bot = bot
        self._channel = bot.config.core.logging_channel
        self._lines_split = lines_split
        self._lines_leading = max(lines_leading, 0)
        self._lines_trailing = max(lines_trailing, 0)

    def emit(self, record):
        try:
            for msg in self.split_msg(self.format(record)):
                self._bot.say(msg, self._channel)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:  # TODO: Be specific
            self.handleError(record)

    def split_msg(self, msg):
        if not self._lines_split:
            return [msg]

        leading = self._lines_leading
        trailing = self._lines_trailing
        lines = msg.splitlines()

        # don't cut any if neither are specified
        if leading == 0 and trailing == 0:
            return lines

        # remove lines if the 'lines cut' line will replace > a single line
        if len(lines) > leading + trailing + 1:
            cut = len(lines) - leading - trailing
            parts = lines[:leading]
            parts += ['...<%s lines cut>...' % cut]
            if trailing > 0:
                parts += lines[-(trailing):]
            lines = parts
        return lines


class ChannelOutputFormatter(logging.Formatter):
    def __init__(self, fmt='[%(filename)s] %(message)s', datefmt=None):
        super(ChannelOutputFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def formatException(self, exc_info):
        # logging will through a newline between the message and this, but
        # that's fine because Sopel will strip it back out anyway
        return ' - ' + repr(exc_info[1])


def setup_logging(settings):
    log_directory = settings.core.logdir
    base_level = settings.core.logging_level or 'WARNING'
    base_format = settings.core.logging_format
    base_datefmt = settings.core.logging_datefmt

    logging_config = {
        'version': 1,
        'formatters': {
            'sopel': {
                'format': base_format,
                'datefmt': base_datefmt,
            },
            'raw': {
                'format': '%(asctime)s %(message)s',
                'datefmt': base_datefmt,
            },
        },
        'loggers': {
            # all purpose, sopel root logger
            'sopel': {
                'level': base_level,
                'handlers': ['console', 'logfile', 'errorfile'],
            },
            # raw IRC log
            'sopel.raw': {
                'level': 'DEBUG',
                'propagate': False,
                'handlers': ['raw'],
            },
            # asynchat exception logger
            'sopel.exceptions': {
                'level': 'INFO',
                'propagate': False,
                'handlers': ['exceptionfile'],
            },
        },
        'handlers': {
            # output on stderr
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'sopel',
            },
            # generic purpose log file
            'logfile': {
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': os.path.join(
                    log_directory, settings.basename + '.sopel.log'),
                'when': 'midnight',
                'formatter': 'sopel',
            },
            # catched error log file
            'errorfile': {
                'level': 'ERROR',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': os.path.join(
                    log_directory, settings.basename + '.error.log'),
                'when': 'midnight',
                'formatter': 'sopel',
            },
            # uncaught error file
            'exceptionfile': {
                'level': 'ERROR',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': os.path.join(
                    log_directory, settings.basename + '.exceptions.log'),
                'when': 'midnight',
                'formatter': 'sopel',
            },
            # raw IRC log file
            'raw': {
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': os.path.join(
                    log_directory, settings.basename + '.raw.log'),
                'when': 'midnight',
                'formatter': 'raw',
            },
        },
    }
    dictConfig(logging_config)


def get_logger(name=None):
    """Return a logger for a module, if the name is given.

    .. deprecated:: 7.0

        Use ``logging.getLogger(__name__)`` in Sopel's code instead, and
        :func:`sopel.tools.get_logger` for external plugins.

        This will warn a deprecation warning in Sopel 8.0 then removed in 9.0.

    """
    if not name:
        return logging.getLogger('sopel')

    parts = name.strip().split('.')
    if len(parts) > 1 or parts[0] in ['sopel', 'sopel_modules']:
        return logging.getLogger(name)

    # assume it's a plugin name, as intended by the original get_logger
    return tools.get_logger(name)

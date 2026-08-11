from argparse import ArgumentParser
import sys
import logging
import traceback
from logging import getLogger

from .base import BaseParser
from .restapi import RestapiParser

from ai4copsec.restapi.app_settings import AppSettings

from ai4copsec.restapi.version import __version__
from ai4copsec.restapi.config import (
    LOG_FORMAT,
    LOG_STYLE,
    LOG_DATE_FORMAT
)

logging.basicConfig(
    format=LOG_FORMAT,
    style=LOG_STYLE,
    datefmt=LOG_DATE_FORMAT,
)

logger = getLogger(__name__)
logger.setLevel(logging.INFO)


class MainParser(ArgumentParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.description = "ai4copsec-restapi - starting the restapi for AI4COPSEC"
        self.add_argument("--log-level", type=str, default="INFO", help="Logging level")
        self.add_argument("--version", "-i", action="store_true", help="Show version")
        self.add_argument("--verbose", action="store_true", help="Show verbose information")

        # This is mainly here to provide documentation,
        # the actual loading need to be done in AppSettings, since this
        # will be initialized before the parser is parsing the arguments
        self.add_argument("--env-file",
                          type=str,
                          default=".env",
                          help="Set the env-file"
        )

    def attach_subcommand_parser(
        self, subcommand: str, help: str, parser_klass: BaseParser
    ):
        if not hasattr(self, 'subparsers'):
            # lazy initialization, since it cannot be part of the __init__ function
            # otherwise random errors
            self.subparsers = self.add_subparsers(help="sub-command help")

        subparser = self.subparsers.add_parser(subcommand)
        parser_klass(parser=subparser)

def run():
    AppSettings.initialize(env_file_required=False)

    main_parser = MainParser()

    main_parser.attach_subcommand_parser(
        subcommand="start",
        help="Start the restapi",
        parser_klass=RestapiParser
    )

    args, unknown_args = main_parser.parse_known_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    for current_logger in [logging.getLogger(x) for x in logging.root.manager.loggerDict]:
        if current_logger.name.startswith("ai4copsec.restapi"):
            current_logger.setLevel(logging.getLevelName(args.log_level))

    if hasattr(args, "active_subparser"):
        try:
            active_subparser = getattr(args, "active_subparser")
            active_subparser.unknown_args  = unknown_args
            active_subparser.execute(args)
        except Exception as e:
            if args.verbose:
                traceback.print_tb(e.__traceback__)
            print(f"Error: {e}")
            sys.exit(-1)
    else:
        main_parser.print_help()

if __name__ == "__main__":
    run()

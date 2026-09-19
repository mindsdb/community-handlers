from collections import OrderedDict

from mindsdb.integrations.libs.const import HANDLER_CONNECTION_ARG_TYPE, HANDLER_TYPE

from .__about__ import __description__ as description
from .__about__ import __version__ as version

name = "adanos"
title = "Adanos"
type = HANDLER_TYPE.DATA
icon_path = "icon.svg"
connection_args = OrderedDict(
    api_key={
        "type": HANDLER_CONNECTION_ARG_TYPE.STR,
        "description": "Your Adanos API key.",
        "required": True,
        "secret": True,
    }
)
connection_args_example = {"api_key": "placeholder"}

__all__ = [
    "Handler",
    "name",
    "title",
    "type",
    "description",
    "version",
    "icon_path",
    "connection_args",
    "connection_args_example",
    "import_error",
]

try:
    from .adanos_handler import AdanosHandler as Handler

    import_error = None
except ImportError as exc:
    Handler = None
    import_error = exc

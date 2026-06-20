"""Base RPC Provider."""

from typing import TypeVar

from ..core import JsonRPCRequestSerializer, JsonRPCResponseParserType

T = TypeVar("T")


class BaseProvider:
    """Base class for RPC providers to implement."""

    def make_request(self, body: JsonRPCRequestSerializer, parser: JsonRPCResponseParserType[T]) -> T:
        """Make a request to the rpc endpoint."""
        raise NotImplementedError("Providers must implement this method")

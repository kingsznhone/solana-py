"""Async base RPC Provider."""

from collections.abc import Coroutine
from typing import Any, TypeVar

from ..core import JsonRPCRequestSerializer, JsonRPCResponseParserType

T = TypeVar("T")


class AsyncBaseProvider:
    """Base class for async RPC providers to implement."""

    def make_request(
        self,
        body: JsonRPCRequestSerializer,
        parser: JsonRPCResponseParserType[T],
    ) -> Coroutine[Any, Any, T]:
        """Make a request to the rpc endpoint."""
        raise NotImplementedError("Providers must implement this method")

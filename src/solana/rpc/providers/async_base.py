"""Async base RPC Provider."""

from collections.abc import Coroutine
from typing import Any

from ..core import JsonRPCRequestSerializer


class AsyncBaseProvider:
    """Base class for async RPC providers to implement."""

    def send(self, body: JsonRPCRequestSerializer) -> Coroutine[Any, Any, str]:
        """Send a JSON-RPC request body and return the raw response string."""
        raise NotImplementedError("Providers must implement this method")

"""Base RPC Provider."""

from ..core import JsonRPCRequestSerializer


class BaseProvider:
    """Base class for RPC providers to implement."""

    def send(self, body: JsonRPCRequestSerializer) -> str:
        """Send a JSON-RPC request body and return the raw response string."""
        raise NotImplementedError("Providers must implement this method")

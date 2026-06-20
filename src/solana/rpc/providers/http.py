"""HTTP RPC Provider."""

from __future__ import annotations

from typing import Dict, Optional

import httpx2

from ...exceptions import SolanaRpcException, handle_exceptions
from ..core import JsonRPCRequestSerializer
from .base import BaseProvider
from .core import (
    DEFAULT_LIMITS,
    DEFAULT_TIMEOUT,
    _after_request_unparsed,
    _HTTPProviderCore,
)


class HTTPProvider(BaseProvider, _HTTPProviderCore):
    """HTTP provider to interact with the http rpc endpoint."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        proxy: Optional[str] = None,
    ):
        """Init HTTPProvider."""
        super().__init__(endpoint, extra_headers)
        if proxy is None:
            self.session = httpx2.Client(
                timeout=timeout,
                limits=DEFAULT_LIMITS,
            )
        else:
            self.session = httpx2.Client(timeout=timeout, proxy=proxy, limits=DEFAULT_LIMITS)

    def __str__(self) -> str:
        """String definition for HTTPProvider."""
        return f"HTTP RPC connection {self.endpoint_uri}"

    @handle_exceptions(SolanaRpcException, httpx2.HTTPError)
    def send(self, body: JsonRPCRequestSerializer) -> str:
        """Send a JSON-RPC request and return the raw response string."""
        request_kwargs = self._before_request(body=body)
        try:
            raw_response = self.session.post(**request_kwargs)
        except (httpx2.RemoteProtocolError, httpx2.ReadError):
            # httpcore2 does not auto-retry stale keepalive connections (unlike httpcore 1.x).
            # Also retry on ReadError (ECONNRESET) which occurs when the server forcibly
            # closes the connection mid-response under load.
            raw_response = self.session.post(**request_kwargs)
        return _after_request_unparsed(raw_response)

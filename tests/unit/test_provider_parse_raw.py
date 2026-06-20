"""Tests for provider-level transport and response decoding."""

import pytest
from solders.rpc.responses import GetHealthResp

from solana.rpc.core import RPCException, RPCNoResultException, _decode_rpc_response
from solana.rpc.providers.async_http import AsyncHTTPProvider
from solana.rpc.providers.http import HTTPProvider


class _EchoParser:
    @classmethod
    def from_json(cls, raw: str):
        return raw


class _BrokenParser:
    @classmethod
    def from_json(cls, raw: str):
        assert raw
        raise ValueError("decode boom")


def test_decode_with_solders_parser_success():
    """Solders response classes should decode through _decode_rpc_response."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    parsed = _decode_rpc_response(raw, GetHealthResp)
    assert parsed.value == "ok"


def test_decode_with_custom_parser_class_success():
    """Custom parser classes with from_json should be accepted."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    parsed = _decode_rpc_response(raw, _EchoParser)
    assert parsed == raw


def test_decode_rejects_callable_parser():
    """Plain parser functions are not supported."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'

    def decode(raw_text: str) -> str:
        return raw_text

    with pytest.raises(TypeError):
        _decode_rpc_response(raw, decode)  # type: ignore[arg-type]


def test_decode_raises_on_rpc_error_envelope():
    """Error envelope should be mapped to RPCException."""
    raw = '{"jsonrpc":"2.0","error":{"code":-32000,"message":"boom"},"id":1}'
    with pytest.raises(RPCException):
        _decode_rpc_response(raw, GetHealthResp)


def test_decode_raises_on_missing_result_and_error():
    """Missing result and error should map to RPCNoResultException."""
    raw = '{"jsonrpc":"2.0","id":1}'
    with pytest.raises(RPCNoResultException):
        _decode_rpc_response(raw, GetHealthResp)


def test_decode_maps_decode_failure_to_rpc_exception():
    """Parser decode failures should be normalized as RPCException."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    with pytest.raises(RPCException):
        _decode_rpc_response(raw, _BrokenParser)


def test_http_providers_expose_send():
    """HTTP providers should expose send() but not deprecated methods."""
    for provider in (HTTPProvider, AsyncHTTPProvider):
        assert hasattr(provider, "send")
        assert not hasattr(provider, "make_request")
        assert not hasattr(provider, "make_request_unparsed")
        assert not hasattr(provider, "make_batch_request")
        assert not hasattr(provider, "make_batch_request_unparsed")

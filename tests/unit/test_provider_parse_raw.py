"""Tests for provider-level raw response parsing."""

import pytest
from solders.rpc.responses import GetHealthResp

from solana.rpc.core import RPCException, RPCNoResultException
from solana.rpc.providers.async_http import AsyncHTTPProvider
from solana.rpc.providers.core import _parse_raw
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


def test_parse_raw_with_solders_parser_success():
    """Solders response classes should parse through provider helper."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    parsed = _parse_raw(raw, GetHealthResp)
    assert parsed.value == "ok"


def test_parse_raw_with_custom_parser_class_success():
    """Custom parser classes with from_json should be accepted."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    parsed = _parse_raw(raw, _EchoParser)
    assert parsed == raw


def test_parse_raw_rejects_callable_parser():
    """Plain parser functions are not supported by provider parsing."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'

    def decode(raw_text: str) -> str:
        return raw_text

    with pytest.raises(TypeError):
        _parse_raw(raw, decode)  # type: ignore[arg-type]


def test_parse_raw_raises_on_rpc_error_envelope():
    """Error envelope should be mapped to RPCException."""
    raw = '{"jsonrpc":"2.0","error":{"code":-32000,"message":"boom"},"id":1}'
    with pytest.raises(RPCException):
        _parse_raw(raw, GetHealthResp)


def test_parse_raw_raises_on_missing_result_and_error():
    """Missing result and error should map to RPCNoResultException."""
    raw = '{"jsonrpc":"2.0","id":1}'
    with pytest.raises(RPCNoResultException):
        _parse_raw(raw, GetHealthResp)


def test_parse_raw_maps_decode_failure_to_rpc_exception():
    """Parser decode failures should be normalized as RPCException."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    with pytest.raises(RPCException):
        _parse_raw(raw, _BrokenParser)


def test_http_providers_do_not_expose_batch_requests():
    """Deprecated HTTP batch request APIs should be removed."""
    for provider in (HTTPProvider, AsyncHTTPProvider):
        assert not hasattr(provider, "make_batch_request")
        assert not hasattr(provider, "make_batch_request_unparsed")

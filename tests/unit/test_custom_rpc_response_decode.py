"""Tests for JSON-RPC response decoding."""

import pytest
from solders.rpc.errors import SendTransactionPreflightFailureMessage
from solders.rpc.responses import GetHealthResp, SendTransactionResp

from solana.rpc.core import RPCException, RPCNoResultException, _decode_rpc_response


def test_decode_rpc_response_with_solders_parser():
    """Solders response classes should work as built-in parsers."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'
    resp = _decode_rpc_response(raw, GetHealthResp)
    assert resp.value == "ok"


def test_decode_rpc_response_rejects_callable_parser():
    """Parser functions are not supported; parser classes must define from_json."""
    raw = '{"jsonrpc":"2.0","result":"ok","id":1}'

    def decode(raw_text: str) -> str:
        return raw_text

    with pytest.raises(TypeError):
        _decode_rpc_response(raw, decode)  # type: ignore[arg-type]


def test_decode_rpc_response_raises_rpc_exception_on_error_envelope():
    """JSON-RPC error envelopes should be mapped to RPCException."""
    raw = '{"jsonrpc":"2.0","error":{"code":-32000,"message":"boom"},"id":1}'

    with pytest.raises(RPCException, match="boom"):
        _decode_rpc_response(raw, GetHealthResp)


def test_decode_rpc_response_preserves_solders_rpc_error_type():
    """Structured solders RPC errors should remain strongly typed."""
    raw = (
        '{"jsonrpc":"2.0","error":{"code":-32002,'
        '"message":"Transaction simulation failed: Error processing Instruction 0: custom program error: 0x1",'
        '"data":{"err":{"InstructionError":[0,{"Custom":1}]},'
        '"logs":["Program 11111111111111111111111111111111 invoke [1]"],'
        '"accounts":null,"unitsConsumed":150,"returnData":null,"innerInstructions":null}},"id":1}'
    )

    with pytest.raises(RPCException) as exc_info:
        _decode_rpc_response(raw, SendTransactionResp)

    assert isinstance(exc_info.value.args[0], SendTransactionPreflightFailureMessage)
    assert exc_info.value.args[0].data.logs


def test_decode_rpc_response_raises_no_result_when_missing_result_and_error():
    """Missing both result and error should map to RPCNoResultException."""
    raw = '{"jsonrpc":"2.0","id":1}'

    with pytest.raises(RPCNoResultException):
        _decode_rpc_response(raw, GetHealthResp)

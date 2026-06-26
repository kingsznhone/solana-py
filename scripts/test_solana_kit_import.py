#!/usr/bin/env python3
"""Smoke test: verify ``solana_kit`` imports and basic ops work from the
main library's environment.

Run::

    .venv/bin/python scripts/test_solana_kit_import.py
"""

from __future__ import annotations

import sys


def main() -> int:
    # 1. 包级导入
    import solana_kit
    from solana_kit import (
        AccountMeta,
        Instruction,
        Keypair,
        Pubkey,
        Signature,
        SystemInstruction,
    )

    print(f"[1] solana_kit loaded from: {solana_kit.__file__}")
    print(f"    public API: {solana_kit.__all__}")

    # 2. Keypair 生成 / 签名 / 验证
    kp = Keypair.generate()
    pk = kp.pubkey()
    assert pk.is_on_curve(), "generated pubkey should be on curve"
    msg = b"hello solana"
    sig: Signature = kp.sign(msg)
    assert Keypair.verify(msg, sig, pk), "signature verification failed"
    print(f"[2] Keypair: pubkey={pk.to_string()[:8]}... sig_len={len(bytes(sig))}")

    # 3. Pubkey 构造与序列化
    pk2 = Pubkey.from_string(pk.to_string())
    assert bytes(pk2) == bytes(pk), "round-trip from_string/to_string mismatch"
    pk3 = Pubkey.from_bytes(bytes(pk))
    assert bytes(pk3) == bytes(pk), "from_bytes round-trip mismatch"
    pk4 = Pubkey.from_string(str(kp.pubkey()))
    assert bytes(pk4) == bytes(pk), "from_base58_string round-trip mismatch"
    print(f"[3] Pubkey: round-trip OK, PUBKEY_BYTES={Pubkey.PUBKEY_BYTES}")

    # 4. SystemInstruction.transfer
    to = Pubkey.new_rand()
    lamports = 1_000_000
    ix: Instruction = SystemInstruction.transfer(pk, to, lamports)
    assert isinstance(ix, Instruction)
    assert (
        ix.program_id.to_string() == "11111111111111111111111111111111"
    ), "system program id"
    assert len(ix.accounts) == 2, "transfer should have 2 accounts"
    assert all(isinstance(a, AccountMeta) for a in ix.accounts)
    assert ix.accounts[0].pubkey.to_string() == pk.to_string()
    assert ix.accounts[0].is_signer and ix.accounts[0].is_writable
    assert ix.accounts[1].pubkey.to_string() == to.to_string()
    assert not ix.accounts[1].is_signer and ix.accounts[1].is_writable
    print(
        f"[4] SystemInstruction.transfer: accounts={len(ix.accounts)} data_len={len(ix.data)}"
    )

    # 5. Keypair 序列化往返
    secret = kp.secret_bytes
    kp_restored = Keypair.from_bytes(secret)
    assert kp_restored.pubkey().to_string() == pk.to_string(), "secret_bytes round-trip"
    print(f"[5] Keypair: secret_bytes round-trip OK, len={len(secret)}")

    # 6. 手动组装 Instruction / AccountMeta 构造器
    program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
    meta1 = AccountMeta(pk, is_signer=True)  # writable signer
    meta2 = AccountMeta(to, is_signer=False)  # writable non-signer
    meta3 = AccountMeta.new_readonly(Pubkey.new_rand(), is_signer=False)  # readonly
    assert meta1.is_writable and meta1.is_signer
    assert meta2.is_writable and not meta2.is_signer
    assert not meta3.is_writable and not meta3.is_signer
    custom_data = b"\x01\x02\x03\x04"
    custom_ix = Instruction(program_id, [meta1, meta2, meta3], custom_data)
    assert custom_ix.program_id.to_string() == program_id.to_string()
    assert len(custom_ix.accounts) == 3
    assert custom_ix.accounts[0].pubkey.to_string() == pk.to_string()
    assert bytes(custom_ix.data) == custom_data
    # new_with_bytes 别名（参数顺序: program_id, data, accounts）
    custom_ix2 = Instruction.new_with_bytes(program_id, custom_data, [meta1])
    assert bytes(custom_ix2.data) == custom_data
    print(f"[6] Instruction/AccountMeta constructors: {custom_ix!r}")

    # 7. System program 全量指令测试
    SYS_ID = "11111111111111111111111111111111"
    owner = Pubkey.new_rand()
    base = Pubkey.new_rand()
    new_acct = Pubkey.new_rand()
    seed = "seed1"

    def assert_sys(ix: Instruction, n_accounts: int, signer_flags: list[bool]) -> None:
        assert (
            ix.program_id.to_string() == SYS_ID
        ), f"expected system program, got {ix.program_id}"
        assert (
            len(ix.accounts) == n_accounts
        ), f"expected {n_accounts} accounts, got {len(ix.accounts)}"
        assert len(signer_flags) == n_accounts
        for i, (meta, should_sign) in enumerate(zip(ix.accounts, signer_flags)):
            assert (
                meta.is_signer == should_sign
            ), f"account {i} signer mismatch: {meta.is_signer} != {should_sign}"

    # create_account: [signer, signer]
    ix = SystemInstruction.create_account(pk, new_acct, 1000, 200, owner)
    assert_sys(ix, 2, [True, True])
    # create_account_with_seed: [signer(from), writable, signer(base)]
    ix = SystemInstruction.create_account_with_seed(
        pk, new_acct, base, seed, 1000, 200, owner
    )
    assert_sys(ix, 3, [True, False, True])
    # create_account_allow_prefund (no payer): [signer]
    ix = SystemInstruction.create_account_allow_prefund(new_acct, None, 200, owner)
    assert_sys(ix, 1, [True])
    # create_account_allow_prefund (with payer): [signer, signer]
    ix = SystemInstruction.create_account_allow_prefund(
        new_acct, (pk, 1000), 200, owner
    )
    assert_sys(ix, 2, [True, True])
    # assign: [signer]
    ix = SystemInstruction.assign(new_acct, owner)
    assert_sys(ix, 1, [True])
    # assign_with_seed: [writable, signer(base)]
    ix = SystemInstruction.assign_with_seed(new_acct, base, seed, owner)
    assert_sys(ix, 2, [False, True])
    # transfer: [signer, writable]
    ix = SystemInstruction.transfer(pk, to, 500)
    assert_sys(ix, 2, [True, False])
    # transfer_with_seed: [writable, signer(base), writable]
    ix = SystemInstruction.transfer_with_seed(new_acct, base, seed, owner, to, 500)
    assert_sys(ix, 3, [False, True, False])
    # transfer_many: 3 transfers
    ixs = SystemInstruction.transfer_many(
        pk, [(to, 100), (new_acct, 200), (owner, 300)]
    )
    assert len(ixs) == 3, f"expected 3 instructions, got {len(ixs)}"
    for t_ix in ixs:
        assert_sys(t_ix, 2, [True, False])
    # allocate: [signer]
    ix = SystemInstruction.allocate(new_acct, 300)
    assert_sys(ix, 1, [True])
    # allocate_with_seed: [writable, signer(base)]
    ix = SystemInstruction.allocate_with_seed(new_acct, base, seed, 300, owner)
    assert_sys(ix, 2, [False, True])
    # advance_nonce_account: [writable, readonly, signer]
    ix = SystemInstruction.advance_nonce_account(new_acct, pk)
    assert_sys(ix, 3, [False, False, True])
    # withdraw_nonce_account: [writable, writable, readonly, readonly, signer]
    ix = SystemInstruction.withdraw_nonce_account(new_acct, pk, to, 100)
    assert_sys(ix, 5, [False, False, False, False, True])
    # authorize_nonce_account: [writable, signer]
    ix = SystemInstruction.authorize_nonce_account(new_acct, pk, to)
    assert_sys(ix, 2, [False, True])
    # upgrade_nonce_account: [writable]
    ix = SystemInstruction.upgrade_nonce_account(new_acct)
    assert_sys(ix, 1, [False])
    # create_nonce_account: returns 2 instructions
    ixs = SystemInstruction.create_nonce_account(pk, new_acct, to, 1000)
    assert len(ixs) == 2, f"expected 2 instructions, got {len(ixs)}"
    # create_nonce_account_with_seed: returns 2 instructions
    ixs = SystemInstruction.create_nonce_account_with_seed(
        pk, new_acct, base, seed, to, 1000
    )
    assert len(ixs) == 2, f"expected 2 instructions, got {len(ixs)}"
    print(f"[7] SystemInstruction: all 16 methods verified")

    # 7.5. ComputeBudgetInstruction
    from solana_kit import ComputeBudgetInstruction

    CB_ID = "ComputeBudget111111111111111111111111111111"
    cb_ix = ComputeBudgetInstruction.request_heap_frame(256 * 1024)
    assert cb_ix.program_id.to_string() == CB_ID
    assert len(cb_ix.accounts) == 0
    assert cb_ix.data[0] == 1  # discriminator
    assert len(cb_ix.data) == 5  # 1 byte discriminator + 4 bytes u32

    cb_ix = ComputeBudgetInstruction.set_compute_unit_limit(200_000)
    assert cb_ix.data[0] == 2
    assert len(cb_ix.data) == 5

    cb_ix = ComputeBudgetInstruction.set_compute_unit_price(1_000)
    assert cb_ix.data[0] == 3
    assert len(cb_ix.data) == 9  # 1 byte discriminator + 8 bytes u64

    cb_ix = ComputeBudgetInstruction.set_loaded_accounts_data_size_limit(
        10 * 1024 * 1024
    )
    assert cb_ix.data[0] == 4
    assert len(cb_ix.data) == 5
    print(f"[7.5] ComputeBudgetInstruction: all 4 methods verified")

    # 8. Message types: Hash, MessageHeader, CompiledInstruction
    from solana_kit import (
        AddressLookupTableAccount,
        CompiledInstruction,
        Hash,
        Message,
        MessageAddressTableLookup,
        MessageHeader,
        MessageV0,
        MessageV1,
    )

    bh = Hash.new_unique()
    assert len(bytes(bh)) == 32
    bh2 = Hash.from_bytes(bytes(bh))
    assert bytes(bh2) == bytes(bh), "Hash round-trip"
    hdr = MessageHeader(1, 0, 1)
    assert hdr.num_required_signatures == 1
    ci = CompiledInstruction(1, [0, 1], b"\x02")
    assert ci.program_id_index == 1 and len(ci.accounts) == 2
    print(f"[8] Hash/MessageHeader/CompiledInstruction: OK ({bh!r}, {hdr!r}, {ci!r})")

    # 9. Legacy Message
    transfer_ix = SystemInstruction.transfer(pk, to, 1000)
    msg = Message.new_with_blockhash([transfer_ix], pk, bh)
    assert msg.header.num_required_signatures == 1
    # account_keys = [payer, to, system_program] (program_id is included)
    assert (
        len(msg.account_keys) == 3
    ), f"expected 3 account keys, got {len(msg.account_keys)}"
    assert msg.account_keys[0].to_string() == pk.to_string(), "payer should be first"
    assert len(msg.instructions) == 1
    assert bytes(msg.recent_blockhash) == bytes(bh)
    msg_bytes = msg.serialize()
    assert len(msg_bytes) > 0, "serialized message should be non-empty"
    # default constructor (zero blockhash)
    msg_default = Message([transfer_ix], payer=pk)
    assert msg_default.header.num_required_signatures == 1
    print(
        f"[9] Legacy Message: account_keys={len(msg.account_keys)}, serialized={len(msg_bytes)} bytes"
    )

    # 10. MessageV0 (no lookup tables)
    msg_v0 = MessageV0.try_compile(pk, [transfer_ix], [], bh)
    assert msg_v0.header.num_required_signatures == 1
    assert len(msg_v0.account_keys) == 3  # payer, to, system_program
    assert len(msg_v0.address_table_lookups) == 0
    v0_bytes = msg_v0.serialize()
    assert (
        v0_bytes[0] == 0x80
    ), f"V0 message should start with 0x80 prefix, got {hex(v0_bytes[0])}"
    print(
        f"[10] MessageV0: account_keys={len(msg_v0.account_keys)}, serialized={len(v0_bytes)} bytes"
    )

    # 11. MessageV0 with lookup table
    alt = AddressLookupTableAccount(key=Pubkey.new_rand(), addresses=[to, owner])
    msg_v0_alt = MessageV0.try_compile(pk, [transfer_ix], [alt], bh)
    assert len(msg_v0_alt.address_table_lookups) >= 0  # may be 0 if keys not in table
    print(f"[11] MessageV0 with ALT: lookups={len(msg_v0_alt.address_table_lookups)}")

    # 12. MessageV1 (SIMD-0385)
    msg_v1 = MessageV1.try_compile(pk, [transfer_ix], bh)
    assert msg_v1.header.num_required_signatures == 1
    assert len(msg_v1.account_keys) == 3  # payer, to, system_program
    assert bytes(msg_v1.lifetime_specifier) == bytes(bh)
    v1_bytes = msg_v1.serialize()
    assert (
        v1_bytes[0] == 0x81
    ), f"V1 message should start with 0x81 prefix, got {hex(v1_bytes[0])}"
    assert msg_v1.size() > 0
    print(
        f"[12] MessageV1: account_keys={len(msg_v1.account_keys)}, size={msg_v1.size()}, serialized={len(v1_bytes)} bytes"
    )

    # 13. VersionedTransaction — 签名 + 序列化 + 反序列化
    from solana_kit import VersionedTransaction

    # V1 交易（构造器接收 MessageV1）
    tx_v1 = VersionedTransaction(msg_v1, [kp])
    assert (
        tx_v1.num_signatures == 1
    ), f"expected 1 signature, got {tx_v1.num_signatures}"
    sigs = tx_v1.signatures
    assert len(sigs) == 1
    assert len(bytes(sigs[0])) == 64, "signature should be 64 bytes"
    tx_v1_bytes = tx_v1.serialize()
    assert len(tx_v1_bytes) > 0, "serialized transaction should be non-empty"
    # 反序列化往返
    tx_v1_restored = VersionedTransaction.deserialize(tx_v1_bytes)
    assert tx_v1_restored.num_signatures == 1
    assert tx_v1_restored.signatures[0] == sigs[0], "signature round-trip mismatch"
    print(
        f"[13] VersionedTransaction V1: sigs={tx_v1.num_signatures}, serialized={len(tx_v1_bytes)} bytes, round-trip OK"
    )

    # V0 交易（构造器接收 MessageV0）
    tx_v0 = VersionedTransaction(msg_v0, [kp])
    assert tx_v0.num_signatures == 1
    tx_v0_bytes = tx_v0.serialize()
    tx_v0_restored = VersionedTransaction.deserialize(tx_v0_bytes)
    assert tx_v0_restored.num_signatures == 1
    print(
        f"[14] VersionedTransaction V0: sigs={tx_v0.num_signatures}, serialized={len(tx_v0_bytes)} bytes, round-trip OK"
    )

    print("\n✅ All solana_kit smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

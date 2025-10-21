#!/usr/bin/env python3
"""Generate chaoschain_wallets.json from environment variables."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def error(message: str) -> None:
    """Print an error message and exit."""
    print(f"ERROR: {message}")
    raise SystemExit(1)


def main() -> None:
    try:
        from eth_account import Account
    except ImportError as exc:  # pragma: no cover - dependency check
        error("eth-account is not installed. Run 'make install' first.")  # noqa: B904

    agent_name = os.getenv("CHAOS_AGENT_NAME", "FilecoinPinDemoAgent")
    private_key = os.getenv("BASE_SEPOLIA_PRIVATE_KEY")
    address_override = os.getenv("BASE_SEPOLIA_ADDRESS")

    if not private_key or private_key == "your-base-sepolia-private-key":
        error("BASE_SEPOLIA_PRIVATE_KEY is not configured in the environment.")

    account = Account.from_key(private_key)
    wallet_address = (
        address_override
        if address_override and address_override != "your-base-sepolia-address"
        else account.address
    )

    wallet_data = {
        agent_name: {
            "address": wallet_address,
            "private_key": private_key,
        }
    }

    output_path = Path(__file__).resolve().parents[1] / "chaoschain_wallets.json"
    output_path.write_text(json.dumps(wallet_data, indent=2), encoding="utf-8")

    print(f"ChaosChain wallet created for {agent_name} at {wallet_address}")
    print(f"Wrote wallet data to {output_path}")


if __name__ == "__main__":
    main()


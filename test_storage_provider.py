#!/usr/bin/env python3
"""Standalone verification for the Filecoin Pin storage provider."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from storage.filecoin_pin_provider import FilecoinPinStorageProvider


def test_storage_provider() -> bool:
    """Exercise the storage provider end-to-end with representative data."""
    print("=" * 50)
    print("Filecoin Pin Storage Provider Diagnostic")
    print("=" * 50)

    try:
        print("Initialising storage provider...")
        provider = FilecoinPinStorageProvider(
            auto_fund=True,
            verbose=True,
            private_key=os.getenv("FILECOIN_CALIBRATION_PRIVATE_KEY"),
        )
        print("Storage provider initialised.")

        print("\nUploading sample payload...")
        test_data = (
            b'{"test": "ChaosChain Filecoin Pin Integration",'
            b'"message": "Verification payload for filecoin-pin CLI",'
            b'"source": "test_storage_provider.py"}'
        )

        result = provider.put(
            test_data,
            mime="application/json",
            tags={"test": "true", "source": "chaoschain-demo"},
        )

        if not result.success:
            print(f"Upload failed: {result.error}")
            return False

        print("Upload succeeded.")
        print(f"CID: {result.cid}")
        print(f"View URL: {result.view_url}")
        print(f"Metadata: {result.metadata}")

        print("\nRetrieving content through public gateway...")
        retrieved_data, metadata = provider.get(result.uri)
        print(f"Retrieved {len(retrieved_data)} bytes via {metadata.get('gateway')}.")
        print(f"Content matches original: {retrieved_data == test_data}")

        print("\nVerifying CID integrity...")
        verified = provider.verify(result.uri, result.cid)
        print(f"Verification result: {verified}")

        return verified

    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"Diagnostic run failed: {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test_storage_provider() else 1)

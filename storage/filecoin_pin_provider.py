#!/usr/bin/env python3
"""Filecoin Pin storage provider used by the ChaosChain SDK demo."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass
class StorageResult:
    """Container returned to the ChaosChain SDK when storing content."""

    success: bool
    uri: str = ""
    hash: str = ""
    provider: str = ""
    cid: str = ""
    view_url: str = ""
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


class FilecoinPinStorageProvider:
    """
    Storage provider that uses filecoin-pin CLI directly.

    This provider stores data by calling the filecoin-pin CLI, which handles:
    - IPFS encoding and CAR creation
    - Filecoin upload via Synapse SDK
    - Automatic funding if needed
    """

    def __init__(
        self,
        filecoin_pin_path: str = "filecoin-pin",
        auto_fund: bool = True,
        bare: bool = False,
        verbose: bool = False,
        private_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the Filecoin Pin storage provider.

        Args:
            filecoin_pin_path: Path to filecoin-pin CLI (default: "filecoin-pin")
            auto_fund: Automatically ensure minimum runway before upload
            bare: Add file without directory wrapper
            verbose: Enable verbose output from filecoin-pin
            private_key: Private key for authentication (can also use PRIVATE_KEY env)
        """
        self.filecoin_pin_path: str = filecoin_pin_path
        self.auto_fund: bool = auto_fund
        self.bare: bool = bare
        self.verbose: bool = verbose
        self.private_key: Optional[str] = private_key

        self._verify_filecoin_pin()

    def _verify_filecoin_pin(self) -> None:
        """Ensure the filecoin-pin CLI is available before continuing."""
        try:
            result = subprocess.run(
                [self.filecoin_pin_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"filecoin-pin CLI returned non-zero exit code: {result.stderr.strip()}"
                )
            print(f"filecoin-pin detected: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(f"filecoin-pin not found at path: {self.filecoin_pin_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("filecoin-pin version command timed out")

    @staticmethod
    def _filename_for_mime(mime: Optional[str]) -> str:
        """Return a user-friendly filename based on MIME type."""
        if mime == "application/json":
            return "chaoschain_proof.json"
        if mime and mime.startswith("text/"):
            return "chaoschain_payload.txt"
        return "chaoschain_payload.bin"

    def _build_command(self, temp_path: str) -> list[str]:
        """Build the CLI command used to store the provided file."""
        command = [self.filecoin_pin_path, "add", temp_path]

        if self.auto_fund:
            command.append("--auto-fund")

        if self.bare:
            command.append("--bare")

        if self.verbose:
            command.append("--verbose")

        if self.private_key:
            command.extend(["--private-key", self.private_key])

        return command

    @staticmethod
    def _parse_cli_output(output: str) -> Dict[str, Optional[str]]:
        """Extract relevant metadata from the filecoin-pin CLI output."""
        root_cid: Optional[str] = None
        piece_cid: Optional[str] = None
        data_set_id: Optional[str] = None
        transaction_hash: Optional[str] = None
        file_size: Optional[str] = None

        for line in output.splitlines():
            if "Root CID:" in line:
                root_cid = line.split("Root CID:")[1].strip()
            elif "Piece CID:" in line:
                piece_cid = line.split("Piece CID:")[1].strip()
            elif "Data Set ID:" in line:
                data_set_id = line.split("Data Set ID:")[1].strip()
            elif line.strip().startswith("│ Hash:"):
                transaction_hash = line.split("Hash:")[1].strip()
            elif "IPFS content loaded (" in line:
                match = re.search(r"IPFS content loaded \(([^)]+)\)", line)
                if match:
                    file_size = match.group(1)

        return {
            "root_cid": root_cid,
            "piece_cid": piece_cid,
            "data_set_id": data_set_id,
            "transaction_hash": transaction_hash,
            "file_size_display": file_size,
        }

    def put(
        self,
        blob: bytes,
        *,
        mime: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> StorageResult:
        """
        Store data using filecoin-pin CLI.

        Args:
            blob: Data to store
            mime: MIME type (stored in metadata)
            tags: Optional metadata tags
            idempotency_key: Ignored (filecoin-pin handles deduplication)

        Returns:
            StorageResult with IPFS URI and CID
        """
        try:
            payload_filename = self._filename_for_mime(mime)
            temp_dir = Path(tempfile.mkdtemp(prefix="chaoschain_filecoin_pin_"))
            temp_path = temp_dir / payload_filename
            temp_path.write_bytes(blob)

            try:
                command = self._build_command(str(temp_path))
                print(f"Uploading {len(blob)} bytes via filecoin-pin...")
                result = subprocess.run(  # noqa: S603 - external CLI is intentional
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    metadata = self._parse_cli_output(result.stdout)
                    root_cid = metadata.get("root_cid")

                    if not root_cid:
                        print("filecoin-pin completed but no Root CID was found in the output.")
                        print("stdout:\n", result.stdout)
                        print("stderr:\n", result.stderr)
                        return StorageResult(
                            success=False,
                            provider="filecoin-pin",
                            error="filecoin-pin completed without returning a Root CID",
                        )

                    print(f"Upload successful. Root CID: {root_cid}")
                    dweb_url = f"https://{root_cid}.ipfs.dweb.link/{payload_filename}"
                    return StorageResult(
                        success=True,
                        uri=f"ipfs://{root_cid}",
                        hash=root_cid,
                        provider="filecoin-pin",
                        cid=root_cid,
                        view_url=dweb_url,
                        size=len(blob),
                        metadata={
                            "piece_cid": metadata.get("piece_cid"),
                            "data_set_id": metadata.get("data_set_id"),
                            "transaction_hash": metadata.get("transaction_hash"),
                            "file_size_display": metadata.get("file_size_display"),
                            "mime_type": mime,
                            "tags": tags or {},
                            "filecoin_pin": True,
                            "payload_filename": payload_filename,
                            "dweb_gateway_url": dweb_url,
                        },
                    )

                print("filecoin-pin returned a non-zero exit code.")
                print("stdout:\n", result.stdout)
                print("stderr:\n", result.stderr)
                return StorageResult(
                    success=False,
                    provider="filecoin-pin",
                    error=result.stderr.strip() or "filecoin-pin command failed",
                )

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except subprocess.TimeoutExpired:
            return StorageResult(
                success=False,
                provider="filecoin-pin",
                error="filecoin-pin command timed out after 5 minutes",
            )
        except Exception as e:
            return StorageResult(
                success=False,
                provider="filecoin-pin",
                error=f"Storage error: {e}",
            )

    def get(self, uri: str) -> Tuple[bytes, Optional[Dict]]:
        """
        Retrieve data from IPFS using public gateways.

        Args:
            uri: IPFS URI (ipfs://Qm... or just the CID)

        Returns:
            Tuple of (data bytes, metadata dict)
        """
        # Extract CID from URI
        cid = uri.replace("ipfs://", "")

        try:
            # Try multiple IPFS gateways
            gateways = [
                f"https://ipfs.io/ipfs/{cid}",
                f"https://gateway.pinata.cloud/ipfs/{cid}",
                f"https://cloudflare-ipfs.com/ipfs/{cid}",
                f"https://dweb.link/ipfs/{cid}"
            ]

            import requests  # Local import keeps dependency optional for callers.

            for gateway_url in gateways:
                try:
                    print(f"Attempting retrieval from: {gateway_url}")
                    response = requests.get(gateway_url, timeout=30)

                    if response.status_code == 200:
                        metadata = {
                            "content-type": response.headers.get("Content-Type"),
                            "content-length": response.headers.get("Content-Length"),
                            "gateway": gateway_url,
                        }
                        print(f"Successfully retrieved content from: {gateway_url}")
                        return response.content, metadata
                    print(f"Gateway returned HTTP {response.status_code}: {gateway_url}")
                except Exception as e:
                    print(f"Failed to retrieve from {gateway_url}: {e}")
                    continue

            raise Exception("Failed to retrieve from any IPFS gateway")

        except Exception as e:
            raise Exception(f"Error retrieving from IPFS: {str(e)}")

    def verify(self, uri: str, expected_hash: str) -> bool:
        """
        Verify data integrity.

        For IPFS, the CID IS the hash, so we just compare CIDs.

        Args:
            uri: IPFS URI
            expected_hash: Expected CID

        Returns:
            True if CIDs match
        """
        cid = uri.replace("ipfs://", "")
        expected_cid = expected_hash.replace("ipfs://", "")
        return cid == expected_cid

    def delete(self, uri: str) -> bool:
        """
        Delete/unpin data from Filecoin.

        Note: This is not supported by filecoin-pin CLI.
        Once data is on Filecoin, it cannot be easily removed.

        Args:
            uri: IPFS URI

        Returns:
            False (not supported)
        """
        print("Delete not supported: Filecoin data cannot be removed once stored.")
        return False

    def upload_json(self, data: dict, filename: str = None) -> Optional[str]:
        """
        Upload JSON data to Filecoin via filecoin-pin CLI.
        This method is expected by the ChaosChain SDK.

        Args:
            data: Dictionary to upload as JSON
            filename: Optional filename for the data

        Returns:
            CID if successful, None otherwise
        """
        try:
            json_data = json.dumps(data, indent=2).encode("utf-8")
            result = self.put(
                json_data,
                mime="application/json",
                tags={"filename": filename or "data.json"},
            )

            if result.success:
                return result.cid
            print(f"Failed to upload JSON to Filecoin: {result.error}")
            return None

        except Exception as e:
            print(f"Exception during JSON upload: {e}")
            return None


# For testing
if __name__ == "__main__":
    # Test the provider
    provider = FilecoinPinStorageProvider()

    # Test with some sample data
    test_data = b"Hello, Filecoin! This is a test from ChaosChain SDK."

    print("Testing Filecoin Pin Storage Provider...")
    result = provider.put(test_data, mime="text/plain", tags={"test": "true"})

    if result.success:
        print(f"Success. CID: {result.cid}")
        print(f"URI: {result.uri}")
        print(f"View URL: {result.view_url}")
        print(f"Metadata: {result.metadata}")

        # Test retrieval
        print("\nTesting retrieval...")
        try:
            data, metadata = provider.get(result.uri)
            print(f"Retrieved {len(data)} bytes")
            print(f"Content: {data.decode('utf-8')}")
            print(f"Metadata: {metadata}")
        except Exception as e:
            print(f"Retrieval failed: {e}")
    else:
        print(f"Upload failed: {result.error}")

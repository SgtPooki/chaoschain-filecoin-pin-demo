#!/usr/bin/env python3
"""ChaosChain demo agent that persists proofs on Filecoin via filecoin-pin."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import requests
except ImportError as exc:  # pragma: no cover - guard for missing dependency
    print("Error: The 'requests' package is required. Install it with 'pip install requests'.")
    raise SystemExit(1) from exc

# Make local modules importable when executing as a script.
sys.path.append(str(Path(__file__).parent.parent))

try:
    from chaoschain_sdk import ChaosChainAgentSDK
    from storage.filecoin_pin_provider import FilecoinPinStorageProvider
except ImportError as exc:
    print(f"Error: required dependencies not installed: {exc}")
    print("Ensure 'chaoschain-sdk' is installed and the repository's root is on PYTHONPATH.")
    raise SystemExit(1) from exc


NETWORK = os.getenv("CHAOS_NETWORK", "base-sepolia")
AGENT_NAME = os.getenv("CHAOS_AGENT_NAME", "FilecoinPinDemoAgent")
AGENT_DOMAIN = os.getenv("CHAOS_AGENT_DOMAIN", "demo.chaoscha.in")
AGENT_ROLE = os.getenv("CHAOS_AGENT_ROLE", "server")
RECEIPTS_DIR = Path(__file__).parent.parent / "receipts"

RPC_ENV_MAPPINGS = {
    "BASE_SEPOLIA_RPC_URL": "BASE-SEPOLIA_RPC_URL",
    "FILECOIN_CALIBRATION_RPC_URL": "FILECOIN-CALIBRATION_RPC_URL",
}

for underscore_key, hyphen_key in RPC_ENV_MAPPINGS.items():
    value = os.getenv(underscore_key)
    if value and hyphen_key not in os.environ:
        os.environ[hyphen_key] = value


def create_sdk() -> ChaosChainAgentSDK:
    """Instantiate the ChaosChain SDK configured for Filecoin Pin storage."""
    print("Initialising Filecoin Pin storage provider...")
    try:
        storage_provider = FilecoinPinStorageProvider(
            filecoin_pin_path=os.getenv("FILECOIN_PIN_PATH", "filecoin-pin"),
            auto_fund=os.getenv("FILECOIN_PIN_AUTO_FUND", "true").lower() == "true",
            bare=os.getenv("FILECOIN_PIN_BARE", "false").lower() == "true",
            verbose=os.getenv("FILECOIN_PIN_VERBOSE", "false").lower() == "true",
            private_key=os.getenv("FILECOIN_CALIBRATION_PRIVATE_KEY"),
        )
        print("Storage provider initialised.")
    except Exception as exc:  # pragma: no cover - CLI validation
        print(f"Failed to initialise Filecoin Pin storage provider: {exc}")
        print("Confirm the filecoin-pin CLI is installed and accessible.")
        raise SystemExit(1) from exc

    return ChaosChainAgentSDK(
        agent_name=AGENT_NAME,
        agent_domain=AGENT_DOMAIN,
        agent_role=AGENT_ROLE,
        network=NETWORK,
        enable_process_integrity=True,
        enable_storage=True,
        storage_provider=storage_provider,
    )


def verify_ipfs_content(cid: str) -> bool:
    """Verify CID reachability via filecoinpin.contact."""
    if not cid:
        return False

    contact_url = f"https://filecoinpin.contact/cid/{cid}"

    print("Verifying IPFS content availability...")

    try:
        print(f"Checking: {contact_url}")
        response = requests.get(contact_url, timeout=10)
        if response.status_code == 200:
            print("IPFS content is reachable via filecoinpin.contact.")
            return True
        print(f"filecoinpin.contact returned status {response.status_code}.")
    except requests.exceptions.RequestException as exc:
        print(f"Could not verify IPFS content via filecoinpin.contact: {exc}")

    return False


async def demo_function(
    hello: str = "world",
    demo: str = "chaoschain-filecoin-pin-integration",
    timestamp: Optional[str] = None,
) -> Dict[str, str]:
    """Sample workload executed under ChaosChain process integrity."""
    payload = {
        "hello": hello,
        "demo": demo,
        "timestamp": timestamp or datetime.now().isoformat(),
    }
    print(f"Executing demo function with payload: {payload}")

    digest_input = json.dumps(payload, sort_keys=True).encode("utf-8")
    computation_hash = hashlib.sha256(digest_input).hexdigest()

    result = {
        "echo": payload,
        "timestamp": datetime.now().isoformat(),
        "agent": AGENT_NAME,
        "network": NETWORK,
        "computation_hash": computation_hash,
    }

    print(f"Function result: {result}")
    return result


async def main() -> Tuple[str, bool]:
    """Run the demo workflow end-to-end."""
    print("=" * 60)
    print("ChaosChain Filecoin Pin Demo Agent")
    print("=" * 60)
    print(f"Network: {NETWORK}")
    print(f"Agent: {AGENT_NAME}")
    print(f"Domain: {AGENT_DOMAIN}")
    print()

    try:
        print("Initialising ChaosChain SDK...")
        sdk = create_sdk()

        print("Registering agent identity...")
        sdk.register_identity()
        print("Agent identity registered.")

        print("Registering demo function...")
        sdk.process_integrity.register_function(demo_function)
        print("Demo function registered.")

        print("\nExecuting function with integrity proof...")
        payload = {
            "hello": "world",
            "demo": "chaoschain-filecoin-pin-integration",
            "timestamp": datetime.now().isoformat(),
        }

        result, proof = await sdk.execute_with_integrity_proof("demo_function", payload)
        print("Function executed with integrity proof.")
        print(f"Result: {result}")
        print(f"Proof: {proof}")

        proof_cid = proof.ipfs_cid if hasattr(proof, "ipfs_cid") else str(proof)

        print("\n" + "=" * 60)
        print("Proof automatically pinned to Filecoin")
        print("=" * 60)
        print(f"PROOF_CID={proof_cid}")
        print(f"IPFS_URI=ipfs://{proof_cid}")
        print(f"VIEW_URL=https://{proof_cid}.ipfs.dweb.link/chaoschain_proof.json")

        is_accessible = False
        contact_url: Optional[str] = None
        if proof_cid and proof_cid != "None":
            contact_url = f"https://filecoinpin.contact/cid/{proof_cid}"
            is_accessible = verify_ipfs_content(proof_cid)
            print(f"BROWSER_LINK=https://inbrowser.link/ipfs/{proof_cid}")
            if is_accessible:
                print("Content verified as accessible.")
            else:
                print("Content may require a few minutes to propagate to public gateways.")
        else:
            print("No CID available; proof was not stored.")

        print("=" * 60)

        proof_data: Dict[str, object] = {
            "proof_cid": proof_cid,
            "result": result,
            "proof": str(proof),
            "timestamp": datetime.now().isoformat(),
            "agent": AGENT_NAME,
            "network": NETWORK,
            "storage_provider": "filecoin-pin",
            "automatically_pinned": True,
            "urls": {
                "ipfs_uri": f"ipfs://{proof_cid}",
                "view_url": f"https://{proof_cid}.ipfs.dweb.link/chaoschain_proof.json",
                "dweb_gateway": f"https://{proof_cid}.ipfs.dweb.link/chaoschain_proof.json",
                "browser_link": f"https://inbrowser.link/ipfs/{proof_cid}",
                "filecoinpin_contact": contact_url,
            },
            "verification": {
                "accessible": is_accessible,
                "verified_at": datetime.now().isoformat(),
            },
        }

        RECEIPTS_DIR.mkdir(exist_ok=True)
        proof_file = RECEIPTS_DIR / f"chaos_proof_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with proof_file.open("w", encoding="utf-8") as handle:
            json.dump(proof_data, handle, indent=2)

        print(f"Proof data saved to: {proof_file}")
        print("\nThe proof is now durably stored via Filecoin Pin.")
        print("Copy-ready inspection commands:")
        if proof_cid and proof_cid != "None":
            print(f'  curl -s "https://{proof_cid}.ipfs.dweb.link/chaoschain_proof.json" | jq')
        print(f"  jq '.' {proof_file.as_posix()}")

        return proof_cid, is_accessible

    except Exception as exc:  # pragma: no cover - orchestration level
        print(f"Error: {exc}")
        print("Verify that:")
        print("1. chaoschain-sdk is installed (pip install chaoschain-sdk)")
        print("2. filecoin-pin CLI is installed and on PATH")
        print("3. Wallet credentials are set in .env")
        print("4. Required RPC endpoints are reachable")
        print("5. Filecoin pinning credentials are valid")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    proof_cid, accessible = asyncio.run(main())
    print(f"\nDemo agent completed. Proof CID: {proof_cid}")
    print(f"Accessible via gateway: {accessible}")

"""
SIL — sil_setup.py
Initialise un canal SIL entre deux agents
Usage : python3 sil_setup.py
"""

import json
import os

def setup():
    print("=" * 55)
    print("SIL — Setup canal agent")
    print("=" * 55)

    print("\nAgent ID (ex: moise@travelagentix) : ", end="")
    agent_id = input().strip()

    print("Recipient ID (ex: offers@airfrance) : ", end="")
    recipient_id = input().strip()

    print("Shared secret (même valeur des deux côtés) : ", end="")
    shared_secret = input().strip()

    config = {
        "agent_id": agent_id,
        "recipient_id": recipient_id,
        "shared_secret": shared_secret,
        "sil_version": "1.3"
    }

    with open(".sil-config", 'w') as f:
        json.dump(config, f, indent=2)

    os.makedirs("sil_inbox", exist_ok=True)

    print(f"\n✓ Config créée : .sil-config")
    print(f"✓ Dossier inbox : sil_inbox/")
    print(f"\nPour envoyer :")
    print(f"  python3 sil_send.py \"VOTRE MESSAGE\" --intent OFFER")
    print(f"\nPour recevoir :")
    print(f"  python3 sil_receive.py")

if __name__ == "__main__":
    setup()

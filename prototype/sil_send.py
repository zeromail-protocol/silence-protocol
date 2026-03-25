"""
SIL — sil_send.py
Agent A — Envoie un message SIL à Agent B
Usage : python3 sil_send.py "MON MESSAGE" --intent OFFER
"""

import json
import os
import sys
import argparse
import hashlib
import hmac as hmac_lib
from datetime import datetime, timezone

# Import du cipher
sys.path.insert(0, os.path.dirname(__file__))
from zmp_v13 import encode, gkl, LANG_NAMES

# ============================================================
# CONFIG
# ============================================================

CONFIG_FILE = ".sil-config"
INBOX_DIR = "sil_inbox"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"✗ Fichier de config manquant : {CONFIG_FILE}")
        print("  Crée-le avec : python3 sil_setup.py")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

# ============================================================
# PAYLOAD ZMF
# ============================================================

def build_zmf(message, intent, sender, recipient):
    """Construit un payload ZMF structuré."""
    return {
        "sil_version": "1.3",
        "message_id": hashlib.sha256(
            f"{sender}{message}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16],
        "sender": sender,
        "recipient": recipient,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "payload": {
            "message": message
        }
    }

# ============================================================
# ENCODE + ÉCRIRE FICHIER .sil
# ============================================================

def send(message, intent, config):
    sender    = config["agent_id"]
    recipient = config["recipient_id"]
    secret    = config["shared_secret"]

    # 1. Construire le payload ZMF
    zmf = build_zmf(message, intent, sender, recipient)

    # 2. Encoder le message
    enc = encode(message, secret)

    # 3. Construire le fichier .sil
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}_{zmf['message_id']}_{intent}.sil"

    sil_content = {
        "header": {
            "sil_version": "1.3",
            "message_id": zmf["message_id"],
            "sender": sender,
            "recipient": recipient,
            "sent_at": zmf["sent_at"],
            "intent": intent,
            "scripts_used": enc["langs_used"],
            "gkl_checksum": enc["gkl_global"]
        },
        "encoded": enc["encoded"],
        "signature": hashlib.sha256(
            f"{secret}{enc['encoded']}".encode()
        ).hexdigest()
    }

    # 4. Écrire dans le dossier inbox
    inbox = os.path.join(INBOX_DIR, f"from_{sender.split('@')[0]}")
    os.makedirs(inbox, exist_ok=True)
    filepath = os.path.join(inbox, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sil_content, f, ensure_ascii=False, indent=2)

    # 5. Affichage
    print("=" * 55)
    print("SIL — MESSAGE ENVOYÉ")
    print("=" * 55)
    print(f"\nDe       : {sender}")
    print(f"À        : {recipient}")
    print(f"Intent   : {intent}")
    print(f"Message  : {message}")
    print(f"\nEncodé   : {enc['encoded']}")
    print(f"Scripts  : {' · '.join([LANG_NAMES[l] for l in enc['langs_used']])}")
    print(f"Checksum : GKL = {enc['gkl_global']}")
    print(f"\nFichier  : {filepath}")
    print(f"\n{'─'*55}")
    print("Détail par token :")
    print(f"{'Tok':<4} {'Script':<18} {'Symboles':<10} {'9?'}")
    print("─" * 38)
    for r in enc['results']:
        print(f"{r['token']:<4} {r['lang_name']:<18} {r['symbols']:<10} {'✓' if r['ok'] else '✗'}")

    print(f"\n✓ Prêt pour git push (ou test local)")
    return filepath

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SIL — Envoyer un message')
    parser.add_argument('message', help='Message à envoyer')
    parser.add_argument('--intent', default='INFO',
                        choices=['OFFER', 'REQUEST', 'INFO', 'ALERT', 'NEGOTIATION'],
                        help='Intent du message')
    args = parser.parse_args()

    config = load_config()
    send(args.message, args.intent, config)

"""
SIL — sil_receive.py
Agent B — Reçoit et décode les messages SIL
Usage : python3 sil_receive.py
"""

import json
import os
import sys
import hashlib
import glob

sys.path.insert(0, os.path.dirname(__file__))
from zmp_v13 import decode, gkl, LANG_NAMES

CONFIG_FILE = ".sil-config"
INBOX_DIR   = "sil_inbox"
DONE_FILE   = ".sil-processed"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"✗ Config manquante : {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_processed():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE) as f:
        return set(f.read().splitlines())

def mark_processed(filepath):
    with open(DONE_FILE, 'a') as f:
        f.write(filepath + "\n")

def verify_signature(sil_content, secret):
    """Vérifie la signature du message."""
    expected = hashlib.sha256(
        f"{secret}{sil_content['encoded']}".encode()
    ).hexdigest()
    return sil_content.get("signature") == expected

def receive(config):
    secret    = config["shared_secret"]
    agent_id  = config["agent_id"]
    processed = load_processed()

    # Chercher tous les fichiers .sil dans inbox
    pattern = os.path.join(INBOX_DIR, "**", "*.sil")
    files = sorted(glob.glob(pattern, recursive=True))

    # Filtrer les messages pour cet agent et non traités
    new_messages = []
    for f in files:
        if f not in processed:
            try:
                with open(f, encoding='utf-8') as fp:
                    content = json.load(fp)
                if content["header"]["recipient"] == agent_id or True:
                    new_messages.append((f, content))
            except Exception:
                pass

    if not new_messages:
        print("SIL — Aucun nouveau message.")
        return

    print("=" * 55)
    print(f"SIL — {len(new_messages)} NOUVEAU(X) MESSAGE(S)")
    print("=" * 55)

    for filepath, sil_content in new_messages:
        header  = sil_content["header"]
        encoded = sil_content["encoded"]

        print(f"\n{'─'*55}")
        print(f"Fichier  : {os.path.basename(filepath)}")
        print(f"De       : {header['sender']}")
        print(f"À        : {header['recipient']}")
        print(f"Intent   : {header['intent']}")
        print(f"Envoyé   : {header['sent_at']}")
        print(f"Scripts  : {' · '.join([LANG_NAMES.get(l,l) for l in header.get('scripts_used',[])])}")
        print(f"\nEncodé   : {encoded}")

        # 1. Vérifier signature
        sig_ok = verify_signature(sil_content, secret)
        print(f"Signature: {'✓ valide' if sig_ok else '✗ INVALIDE'}")

        if not sig_ok:
            print("⚠️  Message rejeté — signature invalide")
            mark_processed(filepath)
            continue

        # 2. Vérifier intégrité (preuve par 9) sans clé
        pairs = [encoded[i:i+2] for i in range(0, len(encoded), 2)]
        from zmp_v13 import integrity_check, symbols_to_sigma_reduced, detect_lang
        integrity_ok = True
        for pair in pairs:
            if len(pair) < 2:
                continue
            lang = detect_lang(pair[0])
            if lang:
                s = symbols_to_sigma_reduced(pair[0], pair[1], lang)
                a, b, ok9 = integrity_check(s)
                if not ok9:
                    integrity_ok = False
                    break

        print(f"Intégrité: {'✓ preuve par 9 OK' if integrity_ok else '✗ ERREUR'}")

        if not integrity_ok:
            print("⚠️  Message rejeté — intégrité compromise")
            mark_processed(filepath)
            continue

        # 3. Déchiffrer
        dec = decode(encoded, secret)
        decoded_msg = dec["decoded"]
        certain = dec["certain"]
        total = dec["total"]

        print(f"\nDécodé   : {decoded_msg}")
        print(f"Certain  : {certain}/{total} tokens")
        print(f"GKL      : {header.get('gkl_checksum', '?')}")

        if dec["integrity"]:
            print(f"\n✓ MESSAGE AUTHENTIFIÉ ET DÉCHIFFRÉ")
        else:
            print(f"\n⚠️  Quelques ambiguïtés ({total - certain} tokens incertains)")

        mark_processed(filepath)

    print(f"\n{'='*55}")

if __name__ == "__main__":
    config = load_config()
    receive(config)

"""
SIL — Agent Loop v1.0
Loop autonome pour agents SIL
Écoute les messages entrants, traite, répond automatiquement
"""

import json
import os
import sys
import time
import hashlib
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from zmp_v14 import encode, decode, gkl, LANG_NAMES

# ============================================================
# CONFIG
# ============================================================

CONFIG_FILE  = ".sil-config"
INBOX_DIR    = "sil_inbox"
DONE_FILE    = ".sil-processed"
AGENT_FILE   = ".sil-agent"    # Capacités déclarées de l'agent

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("✗ Pas de config. Lance : python3 sil_setup.py")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_agent_profile():
    """Charge le profil de l'agent — ses capacités."""
    if not os.path.exists(AGENT_FILE):
        return {"name": "agent", "capabilities": [], "auto_respond": True}
    with open(AGENT_FILE) as f:
        return json.load(f)

# ============================================================
# SEND — réponse de l'agent
# ============================================================

def send_response(message, intent, config, original_msg_id=None):
    """Envoie une réponse SIL encodée."""
    secret = config["shared_secret"]
    sender = config["agent_id"]
    recipient = config["recipient_id"]

    enc = encode(message, secret)

    msg_id = hashlib.sha256(
        f"{sender}{message}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}_{msg_id}_{intent}.sil"

    sil_content = {
        "header": {
            "sil_version": "1.4",
            "message_id": msg_id,
            "response_to": original_msg_id,
            "sender": sender,
            "recipient": recipient,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "scripts_used": enc["langs_used"],
            "gkl_checksum": enc["gkl_global"]
        },
        "encoded": enc["encoded"],
        "signature": hashlib.sha256(
            f"{secret}{enc['encoded']}".encode()
        ).hexdigest()
    }

    inbox = os.path.join(INBOX_DIR, f"from_{sender.split('@')[0]}")
    os.makedirs(inbox, exist_ok=True)
    filepath = os.path.join(inbox, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sil_content, f, ensure_ascii=False, indent=2)

    return filepath, enc

# ============================================================
# HANDLER — logique de réponse de l'agent
# ============================================================

def build_response(decoded_msg, intent, agent_profile, config):
    """
    Construit la réponse de l'agent selon l'intent et ses capacités.
    C'est ici que l'agent "réfléchit".
    
    En production : appel au LLM (Claude API)
    Ici : logique de base + hooks extensibles
    """
    agent_name = config["agent_id"].split("@")[0].upper()
    caps = agent_profile.get("capabilities", [])

    # ---- ACCEPT / REFUSE selon les capacités ----

    # Détecter le type de tâche demandée
    msg_lower = decoded_msg.lower()

    if intent == "REQUEST":
        # Vérifier si l'agent peut traiter cette demande
        task_detected = None

        if any(w in msg_lower for w in ["finance", "compte", "solde", "paiement", "trésorerie"]):
            task_detected = "financial_analysis"
        elif any(w in msg_lower for w in ["score", "scoring", "locataire", "dossier"]):
            task_detected = "scoring"
        elif any(w in msg_lower for w in ["linkedin", "campagne", "post", "publication", "réseau"]):
            task_detected = "social_media"
        elif any(w in msg_lower for w in ["analyser", "analyse", "analyser", "rapport"]):
            task_detected = "analysis"
        elif any(w in msg_lower for w in ["développement", "code", "architecture", "technique"]):
            task_detected = "technical"

        if task_detected and (not caps or task_detected in caps):
            return "ACCEPT", f"TACHE ACCEPTEE PAR {agent_name} TRAITEMENT EN COURS RESULTAT SOUS 60 SECONDES"
        elif task_detected and caps and task_detected not in caps:
            return "REFUSE", f"CAPACITE {task_detected.upper()} NON DISPONIBLE CHEZ {agent_name} REDIRIGER VERS AGENT COMPETENT"
        else:
            return "ACCEPT", f"MESSAGE RECU PAR {agent_name} TRAITEMENT EN COURS"

    elif intent == "OFFER":
        # Évaluer l'offre
        if any(w in msg_lower for w in ["eur", "euro", "prix", "tarif", "cout"]):
            return "COUNTER", f"OFFRE RECUE PAR {agent_name} ANALYSE TARIFICATION EN COURS CONTRE PROPOSITION DANS 30 SECONDES"
        return "ACCEPT", f"OFFRE ACCEPTEE PAR {agent_name}"

    elif intent == "INFO":
        return "ACCEPT", f"INFORMATION RECUE ET ENREGISTREE PAR {agent_name}"

    elif intent == "ALERT":
        return "ESCALATE", f"ALERTE RECUE PAR {agent_name} ESCALADE VERS PRINCIPAL HUMAIN"

    elif intent == "NEGOTIATION":
        return "COUNTER", f"NEGOCIATION OUVERTE PAR {agent_name} ANALYSE DES TERMES EN COURS"

    return "ACCEPT", f"MESSAGE TRAITE PAR {agent_name}"

# ============================================================
# VERIFY
# ============================================================

def verify_message(sil_content, secret):
    expected = hashlib.sha256(
        f"{secret}{sil_content['encoded']}".encode()
    ).hexdigest()
    return sil_content.get("signature") == expected

# ============================================================
# LOOP PRINCIPAL
# ============================================================

def agent_loop(config, agent_profile, poll_interval=10, git_sync=False, verbose=True):
    """
    Loop principal de l'agent.
    
    poll_interval : secondes entre chaque vérification
    git_sync      : git pull avant chaque vérification
    verbose       : affichage détaillé
    """
    agent_id = config["agent_id"]
    secret   = config["shared_secret"]

    processed = set()
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE) as f:
            processed = set(f.read().splitlines())

    print(f"\n{'='*56}")
    print(f"SIL — Agent Loop v1.0")
    print(f"{'='*56}")
    print(f"Agent     : {agent_id}")
    print(f"Recipient : {config['recipient_id']}")
    print(f"Sync      : {'git pull toutes les ' + str(poll_interval) + 's' if git_sync else 'local'}")
    print(f"Capacités : {', '.join(agent_profile.get('capabilities', ['généraliste']))}")
    print(f"\n→ En écoute... (Ctrl+C pour arrêter)\n")

    iteration = 0

    while True:
        iteration += 1

        # Git pull optionnel
        if git_sync:
            try:
                result = subprocess.run(
                    ["git", "pull", "--quiet"],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip() and verbose:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] git pull: {result.stdout.strip()}")
            except Exception as e:
                if verbose:
                    print(f"[git pull] {e}")

        # Scanner les nouveaux fichiers .sil
        import glob
        pattern = os.path.join(INBOX_DIR, "**", "*.sil")
        files = sorted(glob.glob(pattern, recursive=True))
        new_files = [f for f in files if f not in processed]

        for filepath in new_files:
            try:
                with open(filepath, encoding='utf-8') as fp:
                    sil_content = json.load(fp)

                header  = sil_content["header"]
                encoded = sil_content["encoded"]
                sender  = header.get("sender", "?")
                intent  = header.get("intent", "INFO")
                msg_id  = header.get("message_id", "?")

                # Ignorer nos propres messages
                if sender == agent_id:
                    processed.add(filepath)
                    with open(DONE_FILE, 'a') as f:
                        f.write(filepath + "\n")
                    continue

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ─── NOUVEAU MESSAGE ───")
                print(f"  De      : {sender}")
                print(f"  Intent  : {intent}")

                # Vérifier signature
                sig_ok = verify_message(sil_content, secret)
                print(f"  Sig     : {'✓' if sig_ok else '✗ INVALIDE — rejeté'}")

                if not sig_ok:
                    processed.add(filepath)
                    with open(DONE_FILE, 'a') as f:
                        f.write(filepath + "\n")
                    continue

                # Décoder
                dec = decode(encoded, secret)
                decoded_msg = dec["decoded"]
                certain = dec["certain"]
                total = dec["total"]

                print(f"  Décodé  : {decoded_msg}")
                print(f"  Certain : {certain}/{total} tokens")

                # Construire et envoyer la réponse
                response_intent, response_msg = build_response(
                    decoded_msg, intent, agent_profile, config
                )

                filepath_resp, enc_resp = send_response(
                    response_msg,
                    response_intent,
                    config,
                    original_msg_id=msg_id
                )

                print(f"\n  → Réponse : {response_intent}")
                print(f"    Message : {response_msg}")
                print(f"    Encodé  : {enc_resp['encoded'][:40]}...")
                print(f"    Fichier : {os.path.basename(filepath_resp)}")

                # Git push optionnel
                if git_sync:
                    try:
                        subprocess.run(
                            ["git", "add", "."],
                            capture_output=True, timeout=5
                        )
                        subprocess.run(
                            ["git", "commit", "-m",
                             f"SIL {response_intent} {agent_id}→{sender}"],
                            capture_output=True, timeout=5
                        )
                        subprocess.run(
                            ["git", "push", "--quiet"],
                            capture_output=True, timeout=15
                        )
                        print(f"    Git     : ✓ pushed")
                    except Exception as e:
                        print(f"    Git     : ⚠ {e}")

                processed.add(filepath)
                with open(DONE_FILE, 'a') as f:
                    f.write(filepath + "\n")

            except Exception as e:
                print(f"  ✗ Erreur : {e}")
                processed.add(filepath)

        # Attendre avant la prochaine vérification
        if verbose and iteration % 6 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] En écoute... ({len(processed)} messages traités)")

        time.sleep(poll_interval)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SIL Agent Loop')
    parser.add_argument('--interval', type=int, default=10,
                        help='Secondes entre chaque vérification (défaut: 10)')
    parser.add_argument('--git', action='store_true',
                        help='Activer git pull/push automatique')
    parser.add_argument('--quiet', action='store_true',
                        help='Mode silencieux')
    args = parser.parse_args()

    config = load_config()
    agent_profile = load_agent_profile()

    try:
        agent_loop(
            config,
            agent_profile,
            poll_interval=args.interval,
            git_sync=args.git,
            verbose=not args.quiet
        )
    except KeyboardInterrupt:
        print(f"\n\nAgent {config['agent_id']} arrêté.")

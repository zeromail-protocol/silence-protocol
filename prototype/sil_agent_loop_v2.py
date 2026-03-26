"""
SIL — Agent Loop v2.0
Avec Claude API dans build_response()
Karine répond avec les vraies données Scorent
"""

import json
import os
import sys
import time
import hashlib
import subprocess
import glob
import urllib.request
import urllib.error
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from zmp_v14 import encode, decode, gkl, LANG_NAMES

CONFIG_FILE  = ".sil-config"
INBOX_DIR    = "sil_inbox"
DONE_FILE    = ".sil-processed"
AGENT_FILE   = ".sil-agent"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("✗ Pas de config. Lance : python3 sil_setup.py")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_agent_profile():
    if not os.path.exists(AGENT_FILE):
        return {"name": "agent", "capabilities": [], "auto_respond": True}
    with open(AGENT_FILE) as f:
        return json.load(f)

# ============================================================
# CLAUDE API — réponse intelligente
# ============================================================

def call_claude(system_prompt, user_message, api_key):
    """
    Appel direct à l'API Claude via urllib (pas de dépendance externe).
    """
    url = "https://api.anthropic.com/v1/messages"

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-api-key', api_key)
    req.add_header('anthropic-version', '2023-06-01')

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['content'][0]['text']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return f"ERREUR API {e.code}: {body[:100]}"
    except Exception as e:
        return f"ERREUR: {str(e)[:100]}"

def build_sil_response(text):
    """
    Convertit une réponse Claude en format SIL pur.
    Zéro ponctuation émotionnelle. Majuscules. Mots clés uniquement.
    """
    # Supprimer ponctuation et caractères non-SIL
    import re
    text = text.upper()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Limiter à 200 caractères pour rester dans les capacités SIL
    if len(text) > 200:
        text = text[:200].rsplit(' ', 1)[0]
    return text

def build_response(decoded_msg, intent, agent_profile, config):
    """
    Construit la réponse de l'agent.
    Avec Claude API si clé disponible, sinon réponse de base.
    """
    agent_name = config["agent_id"].split("@")[0].upper()
    api_key = config.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")

    # Système prompt selon l'agent
    agent_persona = agent_profile.get("persona", "")
    capabilities   = agent_profile.get("capabilities", [])
    data_context   = agent_profile.get("data_context", "")

    if api_key:
        system = f"""Tu es {agent_name}, un agent IA spécialisé en {', '.join(capabilities)}.

{agent_persona}

Contexte de tes données : {data_context}

RÈGLES ABSOLUES :
- Tu réponds en moins de 150 mots
- Réponse factuelle et directe, zéro formule de politesse
- Pas de ponctuation sauf espaces
- Chiffres et faits uniquement
- Tu es un agent qui parle à un autre agent, pas à un humain
- Format : SUJET VALEUR UNITE si possible"""

        response_text = call_claude(system, decoded_msg, api_key)
        response_sil  = build_sil_response(response_text)

        # Déterminer l'intent de réponse
        msg_lower = decoded_msg.lower()
        if intent == "REQUEST":
            response_intent = "INFO"
        elif intent == "OFFER":
            response_intent = "COUNTER"
        elif intent == "ALERT":
            response_intent = "ESCALATE"
        else:
            response_intent = "ACCEPT"

        return response_intent, response_sil

    else:
        # Fallback sans API key
        msg_lower = decoded_msg.lower()
        if "finance" in msg_lower or "compte" in msg_lower:
            return "INFO", f"ANALYSE FINANCIERE EN ATTENTE DONNEES SCORENT NON ACCESSIBLES SANS CLE API"
        elif "score" in msg_lower:
            return "INFO", f"SCORING EN COURS RESULTAT DISPONIBLE SOUS 60 SECONDES"
        elif "linkedin" in msg_lower or "campagne" in msg_lower:
            return "ACCEPT", f"CAMPAGNE LINKEDIN PRISE EN CHARGE PAR {agent_name} PREPARATION EN COURS"
        else:
            return "ACCEPT", f"MESSAGE RECU PAR {agent_name} TRAITEMENT EN COURS"

# ============================================================
# SEND
# ============================================================

def send_response(message, intent, config, original_msg_id=None):
    secret    = config["shared_secret"]
    sender    = config["agent_id"]
    recipient = config["recipient_id"]

    enc = encode(message, secret)

    msg_id = hashlib.sha256(
        f"{sender}{message}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    filename  = f"{timestamp}_{msg_id}_{intent}.sil"

    sil_content = {
        "header": {
            "sil_version":  "1.4",
            "message_id":   msg_id,
            "response_to":  original_msg_id,
            "sender":       sender,
            "recipient":    recipient,
            "sent_at":      datetime.now(timezone.utc).isoformat(),
            "intent":       intent,
            "scripts_used": enc["langs_used"],
            "gkl_checksum": enc["gkl_global"]
        },
        "encoded":   enc["encoded"],
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

def verify_message(sil_content, secret):
    expected = hashlib.sha256(
        f"{secret}{sil_content['encoded']}".encode()
    ).hexdigest()
    return sil_content.get("signature") == expected

# ============================================================
# LOOP
# ============================================================

def agent_loop(config, agent_profile, poll_interval=10, git_sync=False, verbose=True):
    agent_id = config["agent_id"]
    secret   = config["shared_secret"]
    api_key  = config.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")

    processed = set()
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE) as f:
            processed = set(f.read().splitlines())

    print(f"\n{'='*56}")
    print(f"SIL — Agent Loop v2.0")
    print(f"{'='*56}")
    print(f"Agent     : {agent_id}")
    print(f"Recipient : {config['recipient_id']}")
    print(f"Claude    : {'✓ connecté' if api_key else '✗ pas de clé — mode fallback'}")
    print(f"Capacités : {', '.join(agent_profile.get('capabilities', ['généraliste']))}")
    print(f"\n→ En écoute... (Ctrl+C pour arrêter)\n")

    iteration = 0

    while True:
        iteration += 1

        if git_sync:
            try:
                result = subprocess.run(
                    ["git", "pull", "--quiet"],
                    capture_output=True, text=True, timeout=10
                )
                if "Already up to date" not in result.stdout and result.stdout.strip():
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] git pull: {result.stdout.strip()}")
            except Exception:
                pass

        pattern  = os.path.join(INBOX_DIR, "**", "*.sil")
        files    = sorted(glob.glob(pattern, recursive=True))
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

                if sender == agent_id:
                    processed.add(filepath)
                    with open(DONE_FILE, 'a') as f:
                        f.write(filepath + "\n")
                    continue

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ─── NOUVEAU MESSAGE ───")
                print(f"  De      : {sender}")
                print(f"  Intent  : {intent}")

                sig_ok = verify_message(sil_content, secret)
                print(f"  Sig     : {'✓' if sig_ok else '✗ INVALIDE — rejeté'}")

                if not sig_ok:
                    processed.add(filepath)
                    with open(DONE_FILE, 'a') as f:
                        f.write(filepath + "\n")
                    continue

                dec = decode(encoded, secret)
                decoded_msg = dec["decoded"]
                print(f"  Décodé  : {decoded_msg}")
                print(f"  Certain : {dec['certain']}/{dec['total']} tokens")

                # Réponse via Claude si disponible
                if api_key:
                    print(f"  Claude  : ⟳ génération réponse...")

                response_intent, response_msg = build_response(
                    decoded_msg, intent, agent_profile, config
                )

                filepath_resp, enc_resp = send_response(
                    response_msg, response_intent, config, original_msg_id=msg_id
                )

                print(f"\n  → Réponse : {response_intent}")
                print(f"    Message : {response_msg[:80]}{'...' if len(response_msg) > 80 else ''}")
                print(f"    Scripts : {' · '.join([LANG_NAMES[l] for l in enc_resp['langs_used']])}")
                print(f"    Fichier : {os.path.basename(filepath_resp)}")

                if git_sync:
                    try:
                        subprocess.run(["git", "add", "."], capture_output=True, timeout=5)
                        subprocess.run(
                            ["git", "commit", "-m", f"SIL {response_intent} {agent_id}"],
                            capture_output=True, timeout=5
                        )
                        subprocess.run(["git", "push", "--quiet"], capture_output=True, timeout=15)
                        print(f"    Git     : ✓ pushed")
                    except Exception as e:
                        print(f"    Git     : ⚠ {e}")

                processed.add(filepath)
                with open(DONE_FILE, 'a') as f:
                    f.write(filepath + "\n")

            except Exception as e:
                print(f"  ✗ Erreur : {e}")
                processed.add(filepath)

        if verbose and iteration % 6 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] En écoute... ({len(processed)} traités)")

        time.sleep(poll_interval)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SIL Agent Loop v2.0')
    parser.add_argument('--interval', type=int, default=10)
    parser.add_argument('--git', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    config        = load_config()
    agent_profile = load_agent_profile()

    try:
        agent_loop(config, agent_profile,
                   poll_interval=args.interval,
                   git_sync=args.git,
                   verbose=not args.quiet)
    except KeyboardInterrupt:
        print(f"\nAgent {config['agent_id']} arrêté.")

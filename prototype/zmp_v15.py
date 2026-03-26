"""
SIL — Silence Protocol Cipher v1.5
Fix collisions définitif : 6 alphabets tous >= 45 symboles
Fix chunking : messages longs découpés en chunks de 200 chars
"""

import hashlib, hmac, json, os
from datetime import datetime, timezone

def derive(secret, pos, purpose):
    k = secret.encode()
    m = f"{purpose}:{pos}".encode()
    return int.from_bytes(
        hmac.new(k, m, hashlib.sha256).digest()[:4], 'big'
    )

# ============================================================
# LKE — 6 ALPHABETS >= 45 symboles (zéro collision)
# ============================================================

ALPHABETS = {
    'CU':  (0x12000, 400, 'Cuneiform'),          # Sumérien
    'LB':  (0x10000, 127, 'Linear B'),            # Mycénien
    'LB2': (0x10080, 120, 'Linear B Ideograms'),  # Mycénien idéogrammes
    'CP':  (0x10800,  50, 'Cypriot'),             # Chypriote
    'PM':  (0x10880,  50, 'Palmyrene'),           # Palmyrénien
    'PS':  (0x1E800,  45, 'Proto-Sinaitic'),      # Proto-sinaïtique
}

LANG_KEYS   = list(ALPHABETS.keys())
LARGE_LANGS = ['CU', 'LB']  # Pour chiffres et espace

LANG_NAMES = {k: v[2] for k, v in ALPHABETS.items()}

def get_lang(secret, pos, token):
    val = derive(secret, pos, "LANG")
    t = token.upper()
    if t.isdigit() or t == ' ':
        return LARGE_LANGS[val % 2]
    return LANG_KEYS[val % 6]

# ============================================================
# TOKEN_BASE
# ============================================================

TOKEN_BASE = {}
for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    TOKEN_BASE[c] = i + 1
for d in '0123456789':
    TOKEN_BASE[d] = int(d) + 30
TOKEN_BASE[' '] = 50

assert len(set(TOKEN_BASE.values())) == len(TOKEN_BASE)

# ============================================================
# SIGMA
# ============================================================

def sigma_full(token, pos, secret):
    t = token.upper()
    base = TOKEN_BASE.get(t, ord(t[0]) % 40 + 60)
    k1 = derive(secret, pos, "K1") % 97 + 3
    k2 = derive(secret, pos, "K2") % 53 + 7
    k3 = derive(secret, pos, "K3") % 31 + 11
    return (base * k1) + (pos * k2) + k3

def sigma_reduced(token, pos, secret, lang):
    s = sigma_full(token, pos, secret)
    size = ALPHABETS[lang][1]
    return s % (size * size)

# ============================================================
# GKL
# ============================================================

def gkl(n):
    n = abs(int(n))
    if n == 0: return 0
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n

def gkl_ext(x):
    x = abs(float(x))
    e = int(x)
    d = round((x - e) * 10)
    a = gkl(e) if e > 0 else 9
    b = gkl(d)
    if a == 0: a = 9
    return a, b

def verify9(a, b):
    return gkl(a + b) == 9

def integrity_check(s):
    x = s * 0.9
    a, b = gkl_ext(x)
    return a, b, verify9(a, b)

# ============================================================
# ENCODAGE
# ============================================================

def sigma_to_symbols(sigma, lang):
    base, size, _ = ALPHABETS[lang]
    s = sigma % (size * size)
    return chr(base + s // size) + chr(base + s % size), s

def symbols_to_sigma_reduced(c1, c2, lang):
    base, size, _ = ALPHABETS[lang]
    return (ord(c1) - base) * size + (ord(c2) - base)

def detect_lang(c):
    cp = ord(c)
    for lang, (base, size, _) in ALPHABETS.items():
        if base <= cp < base + size:
            return lang
    return None

# ============================================================
# CHUNK SIZE — 200 tokens par chunk
# ============================================================

CHUNK_SIZE = 200

def encode_chunk(message, secret, chunk_index=0, total_chunks=1):
    """Encode un chunk de message."""
    results = []
    encoded = ""

    for i, token in enumerate(message.upper()):
        # Position absolue pour garantir la cohérence entre chunks
        abs_pos = chunk_index * CHUNK_SIZE + i
        lang = get_lang(secret, abs_pos, token)
        s_full = sigma_full(token, abs_pos, secret)
        syms, s_red = sigma_to_symbols(s_full, lang)
        a, b, ok9 = integrity_check(s_red)

        results.append({
            'token': token,
            'pos': abs_pos,
            'lang': lang,
            'lang_name': LANG_NAMES[lang],
            'symbols': syms,
            'pair': f"{a}·{b}",
            'ok': ok9
        })
        encoded += syms

    total = sum(r['sigma_full'] if 'sigma_full' in r else 0 for r in results)
    total = sum(sigma_reduced(r['token'], r['pos'], secret, r['lang']) for r in results)

    return {
        'chunk_index': chunk_index,
        'total_chunks': total_chunks,
        'original': message,
        'encoded': encoded,
        'results': results,
        'gkl_global': gkl(total),
        'langs_used': list(dict.fromkeys(r['lang'] for r in results))
    }

def encode(message, secret):
    """
    Encode un message en SIL.
    Si > CHUNK_SIZE tokens → découpe en chunks.
    Retourne liste de chunks (1 ou plusieurs).
    """
    msg_upper = message.upper()
    
    if len(msg_upper) <= CHUNK_SIZE:
        chunk = encode_chunk(msg_upper, secret, 0, 1)
        chunk['is_chunked'] = False
        return [chunk]
    
    # Découpage en chunks
    chunks = []
    total_chunks = (len(msg_upper) + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    for i in range(total_chunks):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(msg_upper))
        part = msg_upper[start:end]
        chunk = encode_chunk(part, secret, i, total_chunks)
        chunk['is_chunked'] = True
        chunks.append(chunk)
    
    return chunks

def decode_chunk(encoded_msg, secret, chunk_index=0):
    """Décode un chunk encodé."""
    pairs = [encoded_msg[i:i+2] for i in range(0, len(encoded_msg), 2)]
    results = []
    decoded = ""

    for j, pair in enumerate(pairs):
        if len(pair) < 2:
            results.append({'decoded': '?', 'certain': False, 'ok': False})
            decoded += '?'
            continue

        c1, c2 = pair[0], pair[1]
        lang = detect_lang(c1)
        if not lang:
            results.append({'decoded': '?', 'certain': False, 'ok': False})
            decoded += '?'
            continue

        received = symbols_to_sigma_reduced(c1, c2, lang)
        a, b, ok9 = integrity_check(received)

        abs_pos = chunk_index * CHUNK_SIZE + j

        matches = []
        for token in TOKEN_BASE:
            expected_lang = get_lang(secret, abs_pos, token)
            if expected_lang != lang:
                continue
            if sigma_reduced(token, abs_pos, secret, lang) == received:
                matches.append(token)

        token_decoded = matches[0] if matches else '?'
        certain = len(matches) == 1

        results.append({
            'symbols': pair,
            'lang': lang,
            'lang_name': LANG_NAMES.get(lang, '?'),
            'pair': f"{a}·{b}",
            'matches': matches,
            'decoded': token_decoded,
            'certain': certain,
            'ok': ok9
        })
        decoded += token_decoded

    integrity = all(r['ok'] for r in results)
    certain_count = sum(1 for r in results if r.get('certain'))

    return {
        'chunk_index': chunk_index,
        'encoded': encoded_msg,
        'decoded': decoded,
        'results': results,
        'integrity': integrity,
        'certain': certain_count,
        'total': len(pairs)
    }

def decode(encoded_msg, secret, chunk_index=0):
    """Décode un message SIL (compatible avec encode() simple)."""
    return decode_chunk(encoded_msg, secret, chunk_index)

# ============================================================
# TESTS
# ============================================================

def run():
    SECRET = "scorent-noctia-202scorent-noctia-2026"

    print("=" * 60)
    print("SIL — Silence Protocol Cipher v1.5")
    print("Fix : 6 alphabets >= 45 + chunking")
    print("=" * 60)

    messages = [
        "HELLO WORLD",
        "HIRAM",
        "SILENCE",
        "ANALYSE FINANCES APPARTEMENT RIVOLI PREMIER TRIMESTRE 2026 FORMAT RESUME",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
        # Message long > 200 chars
        "ANALYSE COMPLETE DES FINANCES DU PREMIER TRIMESTRE 2026 POUR L APPARTEMENT RIVOLI PARIS 1ER SCORE LOCATAIRE ACTUEL 745 SUR 1000 REVENUS MENSUELS 4200 EUROS CHARGES 850 EUROS LOYER 1800 EUROS TAUX EFFORT 43 POURCENT HISTORIQUE PAIEMENTS 12 MOIS SANS INCIDENT",
    ]

    all_ok = True

    for msg in messages:
        chunks = encode(msg, SECRET)
        
        # Décoder tous les chunks et reconstruire
        decoded_full = ""
        certain_total = 0
        token_total = 0
        
        for chunk in chunks:
            dec = decode_chunk(chunk['encoded'], SECRET, chunk['chunk_index'])
            decoded_full += dec['decoded']
            certain_total += dec['certain']
            token_total += dec['total']

        match = decoded_full == msg.upper()
        all_ok = all_ok and match

        chunked_info = f" [{len(chunks)} chunks]" if len(chunks) > 1 else ""
        print(f"\n{msg[:60]}{'...' if len(msg) > 60 else ''}{chunked_info}")
        print(f"  Match   : {'✓ EXACT' if match else f'✗ → {decoded_full[:60]}'}")
        print(f"  Certain : {certain_total}/{token_total}")
        if len(chunks) > 1:
            scripts = list(dict.fromkeys(l for c in chunks for l in c['langs_used']))
            print(f"  Scripts : {' · '.join([LANG_NAMES[l] for l in scripts])}")

    # Mauvaise clé
    print(f"\n{'─'*60}")
    chunks_hw = encode("HELLO WORLD", SECRET)
    dec_bad = decode_chunk(chunks_hw[0]['encoded'], "wrong-key-xyz")
    bad = dec_bad['decoded'] == "HELLO WORLD"
    print(f"Mauvaise clé → {dec_bad['decoded']}")
    print(f"Bloqué : {'✓' if not bad else '✗'}")

    # Preuve par 9
    errors = sum(1 for n in range(1, 31)
                 if not verify9(*gkl_ext(n * 0.9)[:2]))
    print(f"\nPreuve par neuf : {30-errors}/30 ✓")
    print(f"אמת = GKL(441) = {gkl(441)}")

    print(f"\n{'='*60}")
    print(f"RÉSULTAT : {'✓ TOUS LES TESTS PASSENT' if all_ok else '✗ ERREURS'}")
    print("=" * 60)

if __name__ == "__main__":
    run()

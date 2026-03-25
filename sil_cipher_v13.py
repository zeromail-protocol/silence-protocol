"""
SIL — Silence Protocol Cipher v1.3
LKE — Linguistic Key Exchange
6 alphabets anciens — fix round-trip
"""

import hashlib, hmac

def derive(secret, pos, purpose):
    k = secret.encode()
    m = f"{purpose}:{pos}".encode()
    return int.from_bytes(
        hmac.new(k, m, hashlib.sha256).digest()[:4], 'big'
    )

# ============================================================
# LKE — 6 ALPHABETS ANCIENS
# ============================================================

ALPHABETS = {
    'CU': (0x12000, 400),  # Cunéiforme
    'LB': (0x10000, 127),  # Linéaire B
    'PH': (0x10900,  27),  # Phénicien
    'AR': (0x10840,  32),  # Araméen
    'UG': (0x10380,  31),  # Ougaritique
    'PS': (0x1E800,  45),  # Proto-sinaïtique
}

LANG_KEYS = list(ALPHABETS.keys())
LANG_NAMES = {
    'CU': 'Cunéiforme',
    'LB': 'Linéaire B',
    'PH': 'Phénicien',
    'AR': 'Araméen',
    'UG': 'Ougaritique',
    'PS': 'Proto-sinaïtique',
}

def get_lang(secret, pos):
    val = derive(secret, pos, "LANG")
    return LANG_KEYS[val % 6]

def sigma_to_symbols(sigma, lang):
    """
    Encode SIGMA en 2 symboles.
    On encode SIGMA modulo (size²) pour garantir le round-trip.
    """
    base_cp, size = ALPHABETS[lang]
    max_val = size * size
    s = sigma % max_val  # Réduction garantissant l'encodabilité
    q = s // size
    r = s % size
    c1 = chr(base_cp + q)
    c2 = chr(base_cp + r)
    return c1 + c2, s  # Retourne aussi la valeur réduite

def symbols_to_sigma_reduced(c1, c2, lang):
    """Décode 2 symboles en SIGMA réduit."""
    base_cp, size = ALPHABETS[lang]
    q = ord(c1) - base_cp
    r = ord(c2) - base_cp
    return q * size + r

def detect_lang(c):
    cp = ord(c)
    for lang, (base, size) in ALPHABETS.items():
        if base <= cp < base + size:
            return lang
    return None

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

def sigma_full(token, pos, secret):
    t = token.upper()
    base = TOKEN_BASE.get(t, ord(t[0]) % 40 + 60)
    k1 = derive(secret, pos, "K1") % 97 + 3
    k2 = derive(secret, pos, "K2") % 53 + 7
    k3 = derive(secret, pos, "K3") % 31 + 11
    return (base * k1) + (pos * k2) + k3

def sigma_reduced(token, pos, secret, lang):
    """SIGMA réduit à la capacité de l'alphabet."""
    s = sigma_full(token, pos, secret)
    _, size = ALPHABETS[lang]
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
# ENCODE / DECODE
# ============================================================

def encode(message, secret):
    results = []
    encoded = ""

    for i, token in enumerate(message.upper()):
        lang = get_lang(secret, i)
        s_full = sigma_full(token, i, secret)
        syms, s_red = sigma_to_symbols(s_full, lang)
        a, b, ok9 = integrity_check(s_red)

        results.append({
            'token': token,
            'pos': i,
            'lang': lang,
            'lang_name': LANG_NAMES[lang],
            'sigma_full': s_full,
            'sigma_reduced': s_red,
            'symbols': syms,
            'pair': f"{a}·{b}",
            'ok': ok9
        })
        encoded += syms

    total = sum(r['sigma_reduced'] for r in results)
    return {
        'original': message,
        'encoded': encoded,
        'results': results,
        'sigma_total': total,
        'gkl_global': gkl(total),
        'langs_used': list(dict.fromkeys(r['lang'] for r in results))
    }

def decode(encoded_msg, secret):
    results = []
    decoded = ""
    pairs = [encoded_msg[i:i+2] for i in range(0, len(encoded_msg), 2)]

    for i, pair in enumerate(pairs):
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

        # Comparer le SIGMA réduit de chaque token possible
        matches = []
        for token in TOKEN_BASE:
            expected = sigma_reduced(token, i, secret, lang)
            if expected == received:
                matches.append(token)

        token_decoded = matches[0] if matches else '?'
        certain = len(matches) == 1

        results.append({
            'symbols': pair,
            'lang': lang,
            'lang_name': LANG_NAMES.get(lang, '?'),
            'sigma': received,
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
        'encoded': encoded_msg,
        'decoded': decoded,
        'results': results,
        'integrity': integrity,
        'certain': certain_count,
        'total': len(pairs)
    }

# ============================================================
# TESTS
# ============================================================

def run():
    SECRET = "sil-shared-secret-march-2026"

    print("=" * 62)
    print("SIL — Silence Protocol Cipher v1.3")
    print("LKE — Linguistic Key Exchange — 6 scripts anciens")
    print("=" * 62)

    messages = [
        "HELLO WORLD",
        "HIRAM",
        "SILENCE",
        "AUDIT FISCAL",
        "ZMP 2026",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
    ]

    all_ok = True

    for msg in messages:
        enc = encode(msg, SECRET)
        dec = decode(enc['encoded'], SECRET)
        match = dec['decoded'] == msg.upper()
        all_ok = all_ok and match

        print(f"\n{msg}")
        print(f"  Encodé  : {enc['encoded']}")
        print(f"  Scripts : {' · '.join([LANG_NAMES[l] for l in enc['langs_used']])}")
        print(f"  Décodé  : {dec['decoded']}")
        print(f"  Match   : {'✓ EXACT' if match else '✗ ERREUR'}")
        print(f"  Certain : {dec['certain']}/{dec['total']}")

    # Détail HIRAM
    print(f"\n{'─'*62}")
    print("HIRAM — détail LKE :\n")
    enc_h = encode("HIRAM", SECRET)
    print(f"{'Tok':<4} {'Script':<18} {'Symboles':<10} {'9?'}")
    print("─" * 38)
    for r in enc_h['results']:
        print(f"{r['token']:<4} {r['lang_name']:<18} {r['symbols']:<10} {'✓' if r['ok'] else '✗'}")
    print(f"\nHIRAM = {enc_h['encoded']}")

    # Mauvaise clé
    print(f"\n{'─'*62}")
    enc_hw = encode("HELLO WORLD", SECRET)
    dec_bad = decode(enc_hw['encoded'], "wrong-key-xyz")
    bad = dec_bad['decoded'] == "HELLO WORLD"
    print(f"Mauvaise clé → {dec_bad['decoded']}")
    print(f"Bloqué : {'✓' if not bad else '✗'}")

    # Preuve par 9
    errors = sum(1 for n in range(1, 31)
                 if not verify9(*gkl_ext(n * 0.9)[:2]))
    print(f"\nPreuve par neuf : {30-errors}/30 ✓")
    print(f"אמת = GKL(441) = {gkl(441)}")

    # Démo visuelle
    print(f"\n{'─'*62}")
    print("SILENCE PROTOCOL — mélange de 6 scripts :\n")
    enc_demo = encode("SILENCE PROTOCOL", SECRET)
    print(f"Encodé : {enc_demo['encoded']}")
    print()
    langs_count = {}
    for r in enc_demo['results']:
        n = r['lang_name']
        langs_count[n] = langs_count.get(n, 0) + 1
    for lang, count in langs_count.items():
        bar = '█' * count
        print(f"  {lang:<18} {bar} ({count})")

    print(f"\n{'='*62}")
    print(f"RÉSULTAT : {'✓ TOUS LES TESTS PASSENT' if all_ok else '✗ ERREURS'}")
    print("=" * 62)

if __name__ == "__main__":
    run()

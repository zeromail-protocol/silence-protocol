"""
SIL — Silence Protocol Cipher v1.4
Fix collisions : alphabets segmentés par type de token
"""

import hashlib, hmac

def derive(secret, pos, purpose):
    k = secret.encode()
    m = f"{purpose}:{pos}".encode()
    return int.from_bytes(
        hmac.new(k, m, hashlib.sha256).digest()[:4], 'big'
    )

# ============================================================
# LKE — 6 ALPHABETS avec capacités réelles
# ============================================================

ALPHABETS = {
    'CU': (0x12000, 400),
    'LB': (0x10000, 127),
    'PH': (0x10900,  27),
    'AR': (0x10840,  32),
    'UG': (0x10380,  31),
    'PS': (0x1E800,  45),
}

LANG_KEYS = list(ALPHABETS.keys())
LANG_NAMES = {
    'CU': 'Cuneiform',
    'LB': 'Linear B',
    'PH': 'Phoenician',
    'AR': 'Aramaic',
    'UG': 'Ugaritic',
    'PS': 'Proto-Sinaitic',
}

# Alphabets capables d'encoder sans collision :
# On a 37 tokens max (26 + 10 + 1 espace)
# size² doit être > max(sigma_reduced) pour tous les tokens
# Petits alphabets (PH=27, AR=32, UG=31) → max 961
# Certains sigma_reduced peuvent dépasser 961 → collision

# SOLUTION : pour les tokens chiffres et espace,
# forcer un grand alphabet (CU ou LB)
LARGE_LANGS = ['CU', 'LB']  # size >= 127 → 16129 max → pas de collision
SMALL_LANGS = ['PH', 'AR', 'UG', 'PS']  # petits alphabets

def get_lang(secret, pos, token):
    """
    Dérive la langue selon le token :
    - Chiffres et espace → toujours grand alphabet
    - Lettres → tous alphabets possibles
    """
    val = derive(secret, pos, "LANG")
    t = token.upper()
    if t.isdigit() or t == ' ':
        # Chiffres et espace → grand alphabet uniquement
        return LARGE_LANGS[val % 2]
    else:
        # Lettres → tous les 6 alphabets
        return LANG_KEYS[val % 6]

# ============================================================
# TOKEN_BASE — valeurs uniques
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
# ENCODAGE
# ============================================================

def sigma_to_symbols(sigma, lang):
    base_cp, size = ALPHABETS[lang]
    max_val = size * size
    s = sigma % max_val
    q = s // size
    r = s % size
    return chr(base_cp + q) + chr(base_cp + r), s

def symbols_to_sigma_reduced(c1, c2, lang):
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
# ENCODE / DECODE
# ============================================================

def encode(message, secret):
    results = []
    encoded = ""

    for i, token in enumerate(message.upper()):
        lang = get_lang(secret, i, token)
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

        # Chercher le token par comparaison
        # Tenir compte de la contrainte langue par type de token
        matches = []
        for token in TOKEN_BASE:
            expected_lang = get_lang(secret, i, token)
            if expected_lang != lang:
                continue  # Ce token ne peut pas être encodé dans cette langue
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
    SECRET = "scorent-noctia-202scorent-noctia-2026"

    print("=" * 58)
    print("SIL — Silence Protocol Cipher v1.4")
    print("Fix collisions — alphabets segmentés")
    print("=" * 58)

    messages = [
        "BESOIN CAMPAGNE LINKEDIN SILENCE PROTOCOL CE SOIR 23H",
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

        status = "✓ EXACT" if match else f"✗ → {dec['decoded']}"
        print(f"\n{msg[:50]}")
        print(f"  Match   : {status}")
        print(f"  Certain : {dec['certain']}/{dec['total']}")
        print(f"  Scripts : {' · '.join([LANG_NAMES[l] for l in enc['langs_used']])}")

    # Mauvaise clé
    print(f"\n{'─'*58}")
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

    print(f"\n{'='*58}")
    print(f"RÉSULTAT : {'✓ TOUS LES TESTS PASSENT' if all_ok else '✗ ERREURS'}")
    print("=" * 58)

if __name__ == "__main__":
    run()

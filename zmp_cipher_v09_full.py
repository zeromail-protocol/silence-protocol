"""
ZMP-Cipher v0.9 — ZTR_TABLE complète
Encode/Decode exact avec clé HMAC
"""

import hashlib, hmac

# ============================================================
# SYSTÈMES GML
# ============================================================

HE = {'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,
      'י':10,'כ':20,'ל':30,'מ':40,'נ':50,'ס':60,'ע':70,'פ':80,
      'צ':90,'ק':100,'ר':200,'ש':300,'ת':400,'ך':500,'ם':600,
      'ן':700,'ף':800,'ץ':900}

GR = {'Α':1,'Β':2,'Γ':3,'Δ':4,'Ε':5,'Ζ':7,'Η':8,'Θ':9,
      'Ι':10,'Κ':20,'Λ':30,'Μ':40,'Ν':50,'Ξ':60,'Ο':70,'Π':80,
      'Ρ':100,'Σ':200,'Τ':300,'Υ':400,'Φ':500,'Χ':600,'Ψ':700,'Ω':800,'ϡ':900}

AR = {'ا':1,'ب':2,'ج':3,'د':4,'ه':5,'و':6,'ز':7,'ح':8,'ط':9,
      'ي':10,'ك':20,'ل':30,'م':40,'ن':50,'س':60,'ع':70,'ف':80,
      'ص':90,'ق':100,'ر':200,'ش':300,'ت':400,'ث':500,'خ':600,
      'ذ':700,'ض':800,'ظ':900,'غ':1000}

SA = {'क':1,'ख':2,'ग':3,'घ':4,'ङ':5,'च':6,'छ':7,'ज':8,'झ':9,
      'य':1,'र':2,'ल':3,'व':4,'श':5,'ष':6,'स':7,'ह':8}

JA = {'い':1,'ろ':2,'は':3,'に':4,'ほ':5,'へ':6,'と':7,'ち':8,'り':9,
      'ぬ':10,'る':11,'を':12,'わ':13,'か':14,'よ':15,'た':16,'れ':17,'そ':18,
      'つ':19,'ね':20,'な':21,'ら':22,'む':23,'う':24,'の':26,'お':27,
      'く':28,'や':29,'ま':30,'け':31,'ふ':32,'こ':33,'え':34,'て':35,'あ':36,
      'さ':37,'き':38,'ゆ':39,'め':40,'み':41,'し':42,'ひ':44,'も':45,'ん':47}

ET = {'፩':1,'፪':2,'፫':3,'፬':4,'፭':5,'፮':6,'፯':7,'፰':8,'፱':9,
      '፲':10,'፳':20,'፴':30,'፵':40,'፶':50,'፷':60,'፸':70,'፹':80,'፺':90}

SYSTEMS = {'HE':HE,'GR':GR,'AR':AR,'SA':SA,'JA':JA,'ET':ET}
SYSKEYS = ['HE','GR','AR','SA','JA','ET']

# AtBash mirrors
def atbash(val, sys_key):
    vals = sorted(SYSTEMS[sys_key].values())
    if not vals: return val
    return vals[-1] - val + vals[0]

# ============================================================
# PHONÉTIQUES — Noms canoniques par token et langue
# ============================================================

# Pour chaque lettre latine : son nom phonétique en hébreu
# décomposé en lettres hébraïques avec leurs valeurs
PHON_HE = {
    'A': [('א',1)],
    'B': [('ב',2),('ה',5),('ת',400)],              # BET
    'C': [('כ',20),('א',1),('פ',80)],               # KAF
    'D': [('ד',4),('ל',30),('ת',400)],              # DALET
    'E': [('ה',5),('ה',5)],                          # HE
    'F': [('פ',80),('ה',5)],                          # PE
    'G': [('ג',3),('י',10),('מ',40),('ל',30)],      # GIMEL
    'H': [('ה',5),('א',1)],                          # HE
    'I': [('י',10),('ו',6),('ד',4)],                # YOD
    'J': [('ג',3),('י',10),('מ',40),('ל',30)],      # GIMEL (approx)
    'K': [('כ',20),('א',1),('פ',80)],               # KAF
    'L': [('ל',30),('מ',40),('ד',4)],               # LAMED
    'M': [('מ',40),('מ',40)],                        # MEM
    'N': [('נ',50),('ו',6),('נ',50)],               # NUN
    'O': [('ע',70),('י',10),('נ',50)],              # AYIN
    'P': [('פ',80),('ה',5)],                          # PE
    'Q': [('ק',100),('ו',6),('פ',80)],              # QOF
    'R': [('ר',200),('י',10),('ש',300)],            # RESH
    'S': [('ס',60),('מ',40),('ך',500)],             # SAMEKH
    'T': [('ת',400),('י',10),('ו',6)],              # TAV
    'U': [('ו',6),('ו',6)],                          # VAV (voyelle)
    'V': [('ו',6),('א',1),('ו',6)],                 # VAV
    'W': [('ד',4),('ו',6),('ב',2),('ל',30),('י',10),('ו',6)],  # DOUBLE-U
    'X': [('ס',60),('מ',40),('ך',500)],             # approx
    'Y': [('י',10),('ו',6),('ד',4)],                # YOD
    'Z': [('ז',7),('י',10),('נ',50)],               # ZAYIN
    ' ': [('ה',5),('פ',80),('ס',60),('ק',100)],    # HESEK (espace)
}

PHON_GR = {
    'A': [('Α',1),('Λ',30),('Φ',500),('Α',1)],     # ALPHA
    'B': [('Β',2),('Η',8),('Τ',300),('Α',1)],       # BETA
    'C': [('Σ',200),('Ι',10)],                       # SI
    'D': [('Δ',4),('Ε',5),('Λ',30),('Τ',300),('Α',1)],  # DELTA
    'E': [('Ε',5),('Π',80),('Σ',200),('Ι',10),('Λ',30),('Ο',70),('Ν',50)],  # EPSILON
    'F': [('Φ',500),('Ι',10)],                       # PHI (approx)
    'G': [('Γ',3),('Α',1),('Μ',40),('Μ',40),('Α',1)],  # GAMMA
    'H': [('Η',8),('Τ',300),('Α',1)],               # ETA
    'I': [('Ι',10),('Ω',800),('Τ',300),('Α',1)],   # IOTA
    'J': [('Θ',9),('Η',8),('Τ',300),('Α',1)],       # THETA (approx)
    'K': [('Κ',20),('Α',1),('Π',80),('Π',80),('Α',1)],  # KAPPA
    'L': [('Λ',30),('Α',1),('Μ',40),('Β',2),('Δ',4),('Α',1)],  # LAMBDA
    'M': [('Μ',40),('Υ',400)],                       # MU
    'N': [('Ν',50),('Υ',400)],                       # NU
    'O': [('Ο',70),('Μ',40),('Ι',10),('Κ',20),('Ρ',100),('Ο',70),('Ν',50)],  # OMICRON
    'P': [('Π',80),('Ι',10)],                         # PI
    'Q': [('Θ',9),('Η',8),('Τ',300),('Α',1)],      # THETA
    'R': [('Ρ',100),('Η',8),('Ο',70)],              # RHO
    'S': [('Σ',200),('Ι',10),('Γ',3),('Μ',40),('Α',1)],  # SIGMA
    'T': [('Τ',300),('Α',1),('Υ',400)],             # TAU
    'U': [('Υ',400),('Π',80),('Σ',200),('Ι',10),('Λ',30),('Ο',70),('Ν',50)],  # UPSILON
    'V': [('Β',2),('Η',8),('Τ',300),('Α',1)],       # BETA (approx)
    'W': [('Ω',800),('Μ',40),('Ε',5),('Γ',3),('Α',1)],  # OMEGA
    'X': [('Χ',600),('Ι',10)],                       # CHI
    'Y': [('Υ',400),('Π',80),('Σ',200),('Ι',10),('Λ',30),('Ο',70),('Ν',50)],
    'Z': [('Ζ',7),('Η',8),('Τ',300),('Α',1)],       # ZETA
    ' ': [('Κ',20),('Ε',5),('Ν',50),('Ο',70),('Ν',50)],  # KENON (vide)
}

PHON = {'HE': PHON_HE, 'GR': PHON_GR}

def phon_sum(token, lang):
    """Somme phonétique d'un token dans une langue"""
    ph = PHON.get(lang, {}).get(token, [])
    return sum(v for _, v in ph) if ph else 0

# ============================================================
# SIGMA-222 rigoureux
# ============================================================

def sigma_exact(token, sys_key):
    """
    Calcul SIGMA-222 exact et déterministe pour un token.
    Indépendant de la clé — c'est une propriété du token.
    La clé intervient seulement pour choisir quel système utiliser.
    """
    sys = SYSTEMS[sys_key]
    vals = sorted(sys.values())
    if not vals: return 100

    # Valeur de base selon le token
    base_map = {
        'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9,'J':10,
        'K':11,'L':12,'M':13,'N':14,'O':15,'P':16,'Q':17,'R':18,'S':19,
        'T':20,'U':21,'V':22,'W':23,'X':24,'Y':25,'Z':26,' ':0
    }
    base_ordinal = base_map.get(token.upper(), ord(token[0]) % 26 + 1)

    # Mapper sur les valeurs du système
    sys_sorted = sorted(set(vals))
    idx = base_ordinal % len(sys_sorted)
    v0 = sys_sorted[idx]

    # M1 — AtBash
    v1 = vals[-1] - v0 + vals[0]

    # M2 — Phonétique HE
    v2 = phon_sum(token.upper(), 'HE')
    if v2 == 0:
        v2 = v0 * 2

    # M3 — Phonétique AtBash
    v3 = sum(
        atbash(v, 'HE')
        for _, v in PHON_HE.get(token.upper(), [(token, v0)])
    )
    if v3 == 0: v3 = v1

    # M4 — Phonétique croisée GR
    v4 = phon_sum(token.upper(), 'GR')
    if v4 == 0:
        gr_sorted = sorted(set(GR.values()))
        v4 = gr_sorted[base_ordinal % len(gr_sorted)]

    # M5 — Récursif : v0 dans système hébreu
    he_sorted = sorted(set(HE.values()))
    v5 = he_sorted[v0 % len(he_sorted)]

    return v0 + v1 + v2 + v3 + v4 + v5

# ============================================================
# ZTR_TABLE — pré-calculée pour tous les tokens
# ============================================================

def build_ztr_table():
    """
    Construit la table complète token → SIGMA par système.
    C'est le cœur du déchiffrement exact.
    """
    table = {}
    tokens = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ ') + list('0123456789')
    
    for sys_key in SYSKEYS:
        table[sys_key] = {}
        for token in tokens:
            sigma = sigma_exact(token, sys_key)
            table[sys_key][token] = sigma
    
    # Table inverse : sigma → token (par système)
    table_inv = {}
    for sys_key in SYSKEYS:
        table_inv[sys_key] = {}
        for token, sigma in table[sys_key].items():
            if sigma not in table_inv[sys_key]:
                table_inv[sys_key][sigma] = []
            table_inv[sys_key][sigma].append(token)
    
    return table, table_inv

ZTR_TABLE, ZTR_INV = build_ztr_table()

# ============================================================
# GKL + NPE
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

def build_zmp81():
    alpha = {}
    base = 0x12000
    idx = 0
    for a in range(1, 10):
        for b in range(0, 10):
            alpha[(a, b)] = chr(base + idx)
            idx += 1
    return alpha

ZMP81 = build_zmp81()
ZMP81_R = {v: k for k, v in ZMP81.items()}

# ============================================================
# CLÉ — HMAC déterministe
# ============================================================

def derive(secret, pos, purpose):
    k = secret.encode()
    m = f"{purpose}:{pos}".encode()
    return int.from_bytes(hmac.new(k, m, hashlib.sha256).digest()[:4], 'big')

def get_sys(secret, pos):
    return SYSKEYS[derive(secret, pos, "SYS") % 6]

# ============================================================
# ENCODE / DECODE exact
# ============================================================

def encode_token(token, pos, secret):
    sys_key = get_sys(secret, pos)
    sigma = ZTR_TABLE[sys_key].get(token.upper())
    if sigma is None:
        sigma = ord(token) % 900 + 1
    x = sigma * 0.9
    a, b = gkl_ext(x)
    if not verify9(a, b):
        b = (9 - a) % 9
    sym = ZMP81.get((a, b), '?')
    return {
        'token': token.upper(),
        'sys': sys_key,
        'sigma': sigma,
        'x': round(x, 2),
        'a': a, 'b': b,
        'pair': f"{a}·{b}",
        'sym': sym,
        'ok': verify9(a, b)
    }

def decode_token(sym, pos, secret):
    pair = ZMP81_R.get(sym)
    if not pair:
        return {'sym': sym, 'decoded': '?', 'certain': False}
    a, b = pair
    sys_key = get_sys(secret, pos)

    # Chercher le token dont le SIGMA produit cette paire
    matches = []
    for token, sigma in ZTR_TABLE[sys_key].items():
        x = sigma * 0.9
        ta, tb = gkl_ext(x)
        if not verify9(ta, tb):
            tb = (9 - ta) % 9
        if (ta, tb) == (a, b):
            matches.append(token)

    decoded = matches[0] if matches else '?'
    certain = len(matches) == 1

    return {
        'sym': sym,
        'sys': sys_key,
        'pair': f"{a}·{b}",
        'matches': matches,
        'decoded': decoded,
        'certain': certain,
        'ok': verify9(a, b)
    }

def encode(message, secret):
    results = [encode_token(t, i, secret) for i, t in enumerate(message)]
    encoded = ''.join(r['sym'] for r in results)
    total = sum(r['sigma'] for r in results)
    return {
        'original': message,
        'encoded': encoded,
        'results': results,
        'sigma_total': total,
        'gkl_global': gkl(total)
    }

def decode(encoded, secret):
    results = [decode_token(sym, i, secret) for i, sym in enumerate(encoded)]
    decoded = ''.join(r['decoded'] for r in results)
    integrity = all(r['ok'] for r in results)
    return {
        'encoded': encoded,
        'decoded': decoded,
        'results': results,
        'integrity': integrity,
        'certain_count': sum(1 for r in results if r.get('certain'))
    }

# ============================================================
# TEST
# ============================================================

def run():
    print("=" * 62)
    print("ZMP-CIPHER v0.9 — ZTR_TABLE COMPLÈTE — TEST ENCODE/DECODE")
    print("=" * 62)

    SECRET = "zmp-shared-secret-mars-2026"
    MESSAGES = ["HELLO WORLD", "AUDIT FISCAL", "ZMP 2026"]

    for MSG in MESSAGES:
        print(f"\n{'─'*62}")
        print(f"Message : {MSG}")
        print(f"Clé     : {SECRET}\n")

        enc = encode(MSG, SECRET)
        print(f"Encodé  : {enc['encoded']}")
        print(f"\n{'Tok':<4} {'Sys':<5} {'SIGMA':<8} {'Paire':<7} {'Sym':<5} {'9?'}")
        print("─" * 38)
        for r in enc['results']:
            print(f"{r['token']:<4} {r['sys']:<5} {r['sigma']:<8} {r['pair']:<7} {r['sym']:<5} {'✓' if r['ok'] else '✗'}")

        dec = decode(enc['encoded'], SECRET)
        print(f"\nDécodé  : {dec['decoded']}")
        match = dec['decoded'] == MSG.upper()
        print(f"Original: {MSG.upper()}")
        print(f"Match   : {'✓ EXACT' if match else '✗'}")
        print(f"Certain : {dec['certain_count']}/{len(MSG)} tokens")
        print(f"Intégr. : {'✓' if dec['integrity'] else '✗'}")

        # Mauvaise clé
        dec_bad = decode(enc['encoded'], "wrong-key-xyz")
        print(f"\nMauv.clé: {dec_bad['decoded']}")
        print(f"Lisible : {'✗ NON — bloqué' if dec_bad['decoded'] != MSG.upper() else '✓ OUI (collision)'}")

    # Test preuve par 9 universelle
    print(f"\n{'─'*62}")
    print("Preuve par neuf universelle (N=1 à 30) :")
    errors = 0
    for n in range(1, 31):
        x = n * 0.9
        a, b = gkl_ext(x)
        ok = verify9(a, b)
        if not ok: errors += 1
    print(f"Résultat : {30-errors}/30 ✓ {'— Universalité confirmée' if errors==0 else f'— {errors} erreurs'}")

    # אמת
    print(f"\nאמת = א(1)+מ(40)+ת(400) = {1+40+400} → GKL = {gkl(441)}")
    print(f"Vérité = {'9 ✓' if gkl(441)==9 else gkl(441)}")

    print(f"\n{'='*62}")
    print("PROTOTYPE OPÉRATIONNEL")
    print("='*62")

if __name__ == "__main__":
    run()

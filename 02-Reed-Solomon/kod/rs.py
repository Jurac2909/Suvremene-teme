#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reed-Solomon kodovi nad poljem GF(2^m).

Implementacija prati izlaganje iz seminarskog rada:
sistematsko kodiranje dijeljenjem generirajucim polinomom, te dekodiranje
kroz sindrome, Berlekamp-Masseyev algoritam, Chienovu pretragu i
Forneyev algoritam.

Polinomi su liste koeficijenata u rastucem poretku po stupnju, dakle
p[0] je slobodni clan, a p[i] koeficijent uz x^i.

Pokretanje:  python rs.py
"""


class GF:
    """Konacno polje GF(2^m) zadano primitivnim polinomom prim."""

    def __init__(self, m, prim):
        self.m = m
        self.n = (1 << m) - 1          # broj elemenata razlicitih od nule
        self.exp = [0] * (2 * self.n + 1)
        self.log = [0] * (self.n + 1)
        x = 1
        for i in range(self.n):
            self.exp[i] = x
            self.log[x] = i
            x <<= 1
            if x & (1 << m):
                x ^= prim
        for i in range(self.n, 2 * self.n + 1):
            self.exp[i] = self.exp[i - self.n]

    def mul(self, a, b):
        if a == 0 or b == 0:
            return 0
        return self.exp[self.log[a] + self.log[b]]

    def div(self, a, b):
        if b == 0:
            raise ZeroDivisionError("dijeljenje nulom u GF(2^m)")
        if a == 0:
            return 0
        return self.exp[(self.log[a] - self.log[b]) % self.n]

    def inv(self, a):
        return self.exp[(self.n - self.log[a]) % self.n]

    def pow(self, a, k):
        if a == 0:
            return 0
        return self.exp[(self.log[a] * k) % self.n]


# ---------------------------------------------------------------- polinomi

def p_trim(a):
    a = list(a)
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    return a


def p_add(a, b):
    r = [0] * max(len(a), len(b))
    for i, c in enumerate(a):
        r[i] ^= c
    for i, c in enumerate(b):
        r[i] ^= c
    return p_trim(r)


def p_mul(gf, a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            if bj == 0:
                continue
            r[i + j] ^= gf.mul(ai, bj)
    return p_trim(r)


def p_eval(gf, a, x):
    """Hornerova shema."""
    y = 0
    for c in reversed(a):
        y = gf.mul(y, x) ^ c
    return y


def p_mod(gf, a, b):
    """Ostatak pri dijeljenju a s b."""
    a = list(a)
    db = len(b) - 1
    inv_vodeci = gf.inv(b[-1])
    while len(a) - 1 >= db:
        pomak = (len(a) - 1) - db
        koef = gf.mul(a[-1], inv_vodeci)
        if koef != 0:
            for i, bc in enumerate(b):
                a[i + pomak] ^= gf.mul(koef, bc)
        a.pop()
        if not a:
            return [0]
    return p_trim(a)


def p_derivacija(a):
    """Formalna derivacija. U karakteristici 2 prezive samo neparni stupnjevi."""
    d = [0] * max(1, len(a) - 1)
    for i in range(1, len(a)):
        if i % 2 == 1:
            d[i - 1] = a[i]
    return p_trim(d)


# ------------------------------------------------------------- kodiranje

def rs_generirajuci(gf, nsym, fcr=1):
    """g(x) = (x + a^fcr)(x + a^(fcr+1)) ... (x + a^(fcr+nsym-1))."""
    g = [1]
    for i in range(nsym):
        g = p_mul(gf, g, [gf.exp[(fcr + i) % gf.n], 1])
    return g


def rs_kodiraj(gf, poruka, nsym, fcr=1):
    """Sistematsko kodiranje: c(x) = x^nsym m(x) + (x^nsym m(x) mod g(x))."""
    g = rs_generirajuci(gf, nsym, fcr)
    pomaknuta = [0] * nsym + list(poruka)
    ostatak = p_mod(gf, pomaknuta, g)
    ostatak = ostatak + [0] * (nsym - len(ostatak))
    return ostatak + list(poruka)


# ------------------------------------------------------------ dekodiranje

def rs_sindromi(gf, primljeno, nsym, fcr=1):
    return [p_eval(gf, primljeno, gf.exp[(fcr + i) % gf.n]) for i in range(nsym)]


def berlekamp_massey(gf, sindromi):
    """Vraca polinom lokatora pogresaka Lambda(x) i broj pogresaka L."""
    C = [1]
    B = [1]
    L = 0
    m = 1
    b = 1
    for i in range(len(sindromi)):
        d = sindromi[i]
        for j in range(1, L + 1):
            if j < len(C):
                d ^= gf.mul(C[j], sindromi[i - j])
        if d == 0:
            m += 1
        else:
            koef = gf.div(d, b)
            pomak = [0] * m + [gf.mul(koef, v) for v in B]
            if 2 * L <= i:
                T = list(C)
                C = p_add(C, pomak)
                L = i + 1 - L
                B = T
                b = d
                m = 1
            else:
                C = p_add(C, pomak)
                m += 1
    return C, L


def chien(gf, lam, n):
    """Pozicije i za koje je Lambda(a^-i) = 0."""
    return [i for i in range(n) if p_eval(gf, lam, gf.inv(gf.exp[i % gf.n])) == 0]


def forney(gf, sindromi, lam, pozicije, fcr=1):
    """Vrijednosti pogresaka na zadanim pozicijama."""
    omega = p_trim(p_mul(gf, sindromi, lam)[:len(sindromi)])
    lam_d = p_derivacija(lam)
    pogreske = {}
    for p in pozicije:
        X = gf.exp[p % gf.n]
        Xinv = gf.inv(X)
        v = gf.div(p_eval(gf, omega, Xinv), p_eval(gf, lam_d, Xinv))
        if fcr != 1:
            v = gf.mul(v, gf.pow(X, 1 - fcr))
        pogreske[p] = v
    return omega, pogreske


def rs_dekodiraj(gf, primljeno, nsym, fcr=1):
    """Vraca (ispravljena_rijec, pozicije, sindromi, lambda, omega)."""
    n = len(primljeno)
    sindromi = rs_sindromi(gf, primljeno, nsym, fcr)
    if not any(sindromi):
        return list(primljeno), [], sindromi, [1], [0]

    lam, L = berlekamp_massey(gf, sindromi)
    pozicije = chien(gf, lam, n)
    if len(pozicije) != L:
        raise ValueError("previse pogresaka, dekodiranje nije moguce")

    omega, pogreske = forney(gf, sindromi, lam, pozicije, fcr)
    ispravljeno = list(primljeno)
    for p, v in pogreske.items():
        ispravljeno[p] ^= v
    return ispravljeno, pozicije, sindromi, lam, omega


# --------------------------------------------------------------- prikazi

def a_zapis(gf, v):
    """Element polja kao potencija primitivnog elementa."""
    return "0" if v == 0 else ("1" if gf.log[v] == 0 else f"a^{gf.log[v]}")


def polinom_zapis(gf, p):
    clanovi = []
    for i in range(len(p) - 1, -1, -1):
        if p[i] == 0:
            continue
        k = a_zapis(gf, p[i])
        if i == 0:
            clanovi.append(k)
        elif k == "1":
            clanovi.append(f"x^{i}" if i > 1 else "x")
        else:
            clanovi.append(f"{k} x^{i}" if i > 1 else f"{k} x")
    return " + ".join(clanovi) if clanovi else "0"


# --------------------------------------------------------------- primjeri

def primjer_gf8():
    """RS(7,3) nad GF(8), isti primjer koji je u radu proveden rucno."""
    gf = GF(3, 0b1011)                 # x^3 + x + 1
    n, k = 7, 3
    nsym = n - k

    print("=" * 70)
    print("RS(7,3) nad GF(8), primitivni polinom x^3 + x + 1")
    print("=" * 70)
    print("tablica polja:")
    for i in range(gf.n):
        print(f"   a^{i} = {gf.exp[i]:>2}  = {gf.exp[i]:03b}")
    print()

    g = rs_generirajuci(gf, nsym)
    print(f"generirajuci polinom g(x) = {polinom_zapis(gf, g)}")

    poruka = [0, 0, 1]                 # m(x) = x^2
    c = rs_kodiraj(gf, poruka, nsym)
    print(f"poruka        m(x) = {polinom_zapis(gf, poruka)}")
    print(f"kodna rijec   c(x) = {polinom_zapis(gf, c)}")
    provjera = [a_zapis(gf, p_eval(gf, c, gf.exp[j])) for j in range(1, nsym + 1)]
    print(f"provjera      c(a^j) za j=1..4: {provjera}")
    print()

    primljeno = list(c)
    primljeno[5] ^= gf.exp[2]          # pogreska a^2 na poziciji x^5
    primljeno[2] ^= gf.exp[3]          # pogreska a^3 na poziciji x^2
    print(f"primljeno     r(x) = {polinom_zapis(gf, primljeno)}")

    ispravljeno, poz, sind, lam, omega = rs_dekodiraj(gf, primljeno, nsym)
    print(f"sindromi      S1..S4 = {[a_zapis(gf, s) for s in sind]}")
    print(f"lokator       L(x) = {polinom_zapis(gf, lam)}")
    print(f"evaluator     O(x) = {polinom_zapis(gf, omega)}")
    print(f"pozicije      {poz}")
    for p in poz:
        print(f"   pogreska na x^{p} iznosi {a_zapis(gf, ispravljeno[p] ^ primljeno[p])}")
    print(f"ispravljeno   c(x) = {polinom_zapis(gf, ispravljeno)}")
    print(f"jednako izvornoj kodnoj rijeci: {ispravljeno == c}")
    print()


def primjer_gf256():
    """RS nad GF(256), skracen na 17 podatkovnih + 10 paritetnih (27 simbola)."""
    gf = GF(8, 0x11D)                  # x^8 + x^4 + x^3 + x^2 + 1
    nsym = 10                          # ispravlja do 5 pogresnih simbola
    poruka = [ord(z) for z in "Reed-Solomon 1960"]

    print("=" * 70)
    print(f"RS nad GF(256), {len(poruka)} podatkovnih i {nsym} paritetnih simbola")
    print("=" * 70)

    c = rs_kodiraj(gf, poruka, nsym)
    print(f"kodna rijec ({len(c)} simbola): {c}")

    primljeno = list(c)
    for pozicija, vrijednost in [(3, 0x5A), (7, 0x01), (11, 0xFF), (19, 0x2C), (24, 0x88)]:
        primljeno[pozicija] ^= vrijednost
    print(f"ostecena rijec:            {primljeno}")
    print(f"broj ostecenih simbola:    {sum(1 for a, b in zip(c, primljeno) if a != b)}")

    ispravljeno, poz, _, lam, _ = rs_dekodiraj(gf, primljeno, nsym)
    print(f"pronadene pozicije:        {sorted(poz)}")
    print(f"potpuni oporavak:          {ispravljeno == c}")
    tekst = "".join(chr(z) for z in ispravljeno[nsym:])
    print(f"oporavljena poruka:        {tekst!r}")
    print()

    print("granica ispravljivosti: uz nsym = 10 ispravlja se najvise 5 pogresaka")
    losije = list(c)
    for pozicija in [1, 4, 6, 9, 13, 17]:
        losije[pozicija] ^= 0x3B
    try:
        rs_dekodiraj(gf, losije, nsym)
        print("   6 pogresaka: dekoder je vratio rezultat")
    except ValueError as e:
        print(f"   6 pogresaka: {e}")


if __name__ == "__main__":
    primjer_gf8()
    primjer_gf256()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demonstracija SQL injection napada u kontroliranom okruzenju.

Skripta ne zahtijeva posluzitelj baze podataka. Koristi sqlite3 iz
standardne biblioteke i bazu u radnoj memoriji, pa se izvodi naredbom:

    python demo_sqli.py

Sve se odvija unutar procesa koji ste sami pokrenuli. Nijedan dio koda
ne salje promet prema vanjskim sustavima.
"""

import sqlite3


SHEMA = """
CREATE TABLE korisnici (
    id              INTEGER PRIMARY KEY,
    korisnicko_ime  TEXT NOT NULL,
    lozinka_hash    TEXT NOT NULL,
    uloga           TEXT NOT NULL
);

CREATE TABLE kartice (
    id      INTEGER PRIMARY KEY,
    vlasnik TEXT NOT NULL,
    broj    TEXT NOT NULL
);

INSERT INTO korisnici VALUES
    (1, 'ana',   'e9d71f5ee7c92d6dc9e92ffdad17b8bd49418f98', 'korisnik'),
    (2, 'marko', '7c4a8d09ca3762af61e59520943dc26494f8941b', 'korisnik'),
    (3, 'admin', '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', 'administrator');

INSERT INTO kartice VALUES
    (1, 'ana',   '4111 1111 1111 1111'),
    (2, 'marko', '5500 0000 0000 0004'),
    (3, 'admin', '3400 0000 0000 009');
"""


def nova_baza():
    """Stvara bazu u radnoj memoriji i puni je testnim podacima."""
    veza = sqlite3.connect(":memory:")
    veza.executescript(SHEMA)
    return veza


def prijava_ranjiva(veza, ime, lozinka):
    """Ranjiva inacica. Ulaz se spaja u tekst upita, pa ga moze mijenjati."""
    upit = (
        "SELECT id, korisnicko_ime, uloga FROM korisnici "
        f"WHERE korisnicko_ime = '{ime}' AND lozinka_hash = '{lozinka}'"
    )
    print("    upit koji baza vidi:")
    print("      " + upit)
    return veza.execute(upit).fetchall()


def prijava_sigurna(veza, ime, lozinka):
    """Sigurna inacica. Vrijednosti se predaju odvojeno od teksta upita."""
    upit = (
        "SELECT id, korisnicko_ime, uloga FROM korisnici "
        "WHERE korisnicko_ime = ? AND lozinka_hash = ?"
    )
    print("    upit koji baza vidi:")
    print("      " + upit)
    print(f"      parametri: {(ime, lozinka)}")
    return veza.execute(upit, (ime, lozinka)).fetchall()


def ispisi(naslov, redci):
    print(f"    rezultat ({len(redci)} redaka):")
    if not redci:
        print("      prijava odbijena")
    for redak in redci:
        print(f"      {redak}")
    print()


def main():
    veza = nova_baza()

    print("=" * 68)
    print("1. Ispravna prijava korisnika 'ana'")
    print("=" * 68)
    ispisi("ok", prijava_ranjiva(
        veza, "ana", "e9d71f5ee7c92d6dc9e92ffdad17b8bd49418f98"))

    print("=" * 68)
    print("2. Napad na ranjivu inacicu: zaobilazenje provjere lozinke")
    print("=" * 68)
    ispisi("napad", prijava_ranjiva(veza, "admin' -- ", "bilo sto"))

    print("=" * 68)
    print("3. Napad koji vraca sve korisnike odjednom")
    print("=" * 68)
    ispisi("napad", prijava_ranjiva(veza, "' OR '1'='1", "' OR '1'='1"))

    print("=" * 68)
    print("4. UNION napad: citanje tablice koja nije dio upita")
    print("=" * 68)
    ispisi("napad", prijava_ranjiva(
        veza, "' UNION SELECT id, vlasnik, broj FROM kartice -- ", "x"))

    print("=" * 68)
    print("5. Isti ulazi protiv pripremljenog upita")
    print("=" * 68)
    ispisi("obrana", prijava_sigurna(veza, "admin' -- ", "bilo sto"))
    ispisi("obrana", prijava_sigurna(
        veza, "' UNION SELECT id, vlasnik, broj FROM kartice -- ", "x"))

    veza.close()


if __name__ == "__main__":
    main()

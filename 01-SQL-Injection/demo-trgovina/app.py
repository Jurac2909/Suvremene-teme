#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bajt - web trgovina (namjerno ranjiva, za demonstraciju SQL injectiona).

Ovo NIJE nastavni demo s prikazom upita i prekidacem. Ovo je "prava"
stranica koja izgleda kao obicna mala web trgovina. Nigdje ne pise da je
ranjiva i nigdje se ne prikazuje SQL upit. Napad se radi rucno, kao pravi
napadac: u polju za prijavu, u trazilici i kroz id proizvoda u adresi.

Ranjive tocke (namjerno, spajanjem niza znakova u upit):
  1. Prijava        /prijava        -> zaobilazenje prijave
  2. Trazilica      /trazi?q=...     -> UNION citanje tudih tablica
  3. Proizvod       /proizvod?id=... -> UNION citanje tudih tablica (bez navodnika)

Pokretanje:
    python3 app.py
pa u pregledniku otvori  http://127.0.0.1:8000

Sve radi lokalno, baza je u radnoj memoriji, posluzitelj slusa samo na
127.0.0.1. Nista ne izlazi iz racunala i nista se ne sprema na disk.
Zaustavi s Ctrl+C.
"""

import hashlib
import html
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST, PORT = "127.0.0.1", 8000


def sha1(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- baza (u memoriji)

db = sqlite3.connect(":memory:", check_same_thread=False)
db.executescript("""
CREATE TABLE korisnici (
    id INTEGER PRIMARY KEY,
    korisnicko_ime TEXT,
    lozinka_hash   TEXT,
    uloga          TEXT,
    prikaz         TEXT);

CREATE TABLE kartice (
    id INTEGER PRIMARY KEY,
    vlasnik TEXT,
    broj    TEXT,
    istek   TEXT);

CREATE TABLE proizvodi (
    id INTEGER PRIMARY KEY,
    naziv     TEXT,
    kategorija TEXT,
    cijena    REAL,
    slika     TEXT,
    opis      TEXT);

CREATE TABLE narudzbe (
    id INTEGER PRIMARY KEY,
    kupac    TEXT,
    stavka   TEXT,
    iznos    REAL,
    datum    TEXT);
""")

# Admin lozinka je namjerno jaka - ne moze se pogoditi, mora se zaobici.
db.executemany(
    "INSERT INTO korisnici (korisnicko_ime, lozinka_hash, uloga, prikaz) VALUES (?,?,?,?)",
    [
        ("ana",   sha1("ljeto2025"),        "kupac",         "Ana Anić"),
        ("marko", sha1("marko123"),         "kupac",         "Marko Marić"),
        ("admin", sha1("V3lika!Tajna#2026"), "administrator", "Administrator sustava"),
    ],
)

db.executemany(
    "INSERT INTO kartice (vlasnik, broj, istek) VALUES (?,?,?)",
    [
        ("Ana Anić",              "4111 1111 1111 1111", "08/27"),
        ("Marko Marić",           "5500 0000 0000 0004", "11/26"),
        ("Administrator sustava", "3400 0000 0000 009",  "03/28"),
    ],
)

db.executemany(
    "INSERT INTO proizvodi (naziv, kategorija, cijena, slika, opis) VALUES (?,?,?,?,?)",
    [
        ("Prijenosnik Bajt Pro 14",     "Računala",   899.00, "💻",
         "Lagano prijenosno računalo, 14 inča, 16 GB RAM, 512 GB SSD."),
        ("Stolno računalo Bajt Tower",  "Računala",  1149.00, "🖥️",
         "Snažno kućište za posao i igru, 32 GB RAM, brzi NVMe disk."),
        ("Mehanička tipkovnica Klik 87","Periferija",  79.90, "⌨️",
         "Kompaktna mehanička tipkovnica s crvenim prekidačima."),
        ("Bežični miš Sjena M2",        "Periferija",  29.90, "🖱️",
         "Tihi bežični miš s dva Bluetooth kanala."),
        ("Monitor Vid 27Q",            "Periferija",  219.00, "🖵",
         "27 inča, 2560×1440, 165 Hz, tanki okvir."),
        ("Web kamera Oko 1080",         "Periferija",  39.90, "📷",
         "Full HD kamera s ugrađenim mikrofonom i poklopcem."),
        ("Usmjerivač Mreža AX3000",     "Mreža",       89.00, "📶",
         "Wi-Fi 6 usmjerivač, do 3000 Mbps, četiri antene."),
        ("Mrežni preklopnik 8 vrata",   "Mreža",       34.90, "🔀",
         "Gigabitni switch s osam priključaka, metalno kućište."),
        ("SSD disk 1 TB",              "Komponente",   74.90, "💾",
         "NVMe SSD, do 3500 MB/s čitanja, pet godina jamstva."),
        ("Radna memorija 16 GB DDR5",   "Komponente",   54.90, "🧠",
         "Modul 16 GB DDR5 5600 MHz s hladnjakom."),
        ("Napajanje 650W",             "Komponente",   69.90, "🔌",
         "Modularno napajanje, 80+ Bronze, tihi ventilator."),
        ("Grafička kartica Piksel 3060","Komponente",  329.00, "🎮",
         "8 GB GDDR6, dobra za 1080p i 1440p igranje."),
    ],
)

db.executemany(
    "INSERT INTO narudzbe (kupac, stavka, iznos, datum) VALUES (?,?,?,?)",
    [
        ("Ana Anić",    "Prijenosnik Bajt Pro 14", 899.00, "2026-07-14"),
        ("Ana Anić",    "Bežični miš Sjena M2",     29.90, "2026-07-14"),
        ("Marko Marić", "Monitor Vid 27Q",         219.00, "2026-08-02"),
        ("Marko Marić", "SSD disk 1 TB",            74.90, "2026-08-02"),
    ],
)
db.commit()


# --------------------------------------------------------------- pomocno

def eur(v):
    try:
        return "{:,.2f} €".format(float(v)).replace(",", ".")
    except (TypeError, ValueError):
        return html.escape(str(v))


def q1(params, key, default=""):
    return params.get(key, [default])[0]


def get_session(handler):
    raw_cookie = handler.headers.get("Cookie", "")
    for part in raw_cookie.split(";"):
        part = part.strip()
        if part.startswith("sesija="):
            raw = urllib.parse.unquote(part[len("sesija="):])
            bits = raw.split("|")
            if len(bits) == 3:
                return {"ime": bits[0], "uloga": bits[1], "prikaz": bits[2]}
    return None


def get_mode(handler):
    """Nacin rada: 'vulnerable' (zadano) ili 'safe'. Cita se iz kolacica."""
    raw_cookie = handler.headers.get("Cookie", "") if handler else ""
    for part in raw_cookie.split(";"):
        part = part.strip()
        if part.startswith("mode="):
            v = part[len("mode="):]
            if v in ("safe", "vulnerable"):
                return v
    return "vulnerable"


# --------------------------------------------------------------- izgled (CSS)

CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1c2530; background: #f3f5f8;
}
a { color: #14618a; text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { max-width: 1060px; margin: 0 auto; padding: 0 20px; }

header.top { background: #0f2740; color: #fff; }
.top .wrap { display: flex; align-items: center; gap: 20px; padding: 14px 20px; }
.brand { font-size: 1.4rem; font-weight: 800; letter-spacing: .5px; color: #fff; }
.brand span { color: #7fd1ff; }
.top form { flex: 1; display: flex; }
.top input[type=search] {
  flex: 1; padding: 10px 14px; border: 0; border-radius: 8px 0 0 8px; font-size: 1rem;
}
.top button {
  border: 0; background: #2f9bd6; color: #fff; padding: 10px 18px;
  border-radius: 0 8px 8px 0; font-size: 1rem; cursor: pointer;
}
.top .acct { color: #cfe3f2; font-size: .92rem; white-space: nowrap; }
.top .acct a { color: #fff; font-weight: 600; }

nav.cats { background: #14395c; }
nav.cats .wrap { display: flex; gap: 18px; padding: 9px 20px; flex-wrap: wrap; }
nav.cats a { color: #d6e6f3; font-size: .92rem; }

main { padding: 26px 0 60px; }
.hero {
  background: linear-gradient(120deg, #123a5c, #2f9bd6); color: #fff;
  border-radius: 14px; padding: 30px 34px; margin-bottom: 26px;
}
.hero h1 { margin: 0 0 6px; font-size: 1.7rem; }
.hero p { margin: 0; opacity: .9; }

h2.section { font-size: 1.15rem; margin: 6px 0 16px; color: #33475b; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; }
.card {
  background: #fff; border: 1px solid #e4e9ef; border-radius: 12px; overflow: hidden;
  display: flex; flex-direction: column; transition: box-shadow .15s, transform .15s;
}
.card:hover { box-shadow: 0 8px 22px rgba(20,40,70,.12); transform: translateY(-2px); }
.thumb {
  font-size: 3.4rem; text-align: center; padding: 26px 0 18px;
  background: #eef3f8; border-bottom: 1px solid #e4e9ef;
}
.card .body { padding: 14px 16px 18px; display: flex; flex-direction: column; flex: 1; }
.card .kat { font-size: .72rem; text-transform: uppercase; letter-spacing: .6px; color: #7a8ba0; }
.card .naziv { font-weight: 650; margin: 3px 0 10px; line-height: 1.3; }
.card .cijena { font-size: 1.2rem; font-weight: 800; color: #0f2740; margin-top: auto; }
.card .buy {
  margin-top: 12px; text-align: center; background: #2f9bd6; color: #fff;
  padding: 9px 0; border-radius: 8px; font-weight: 600;
}

.panel { background: #fff; border: 1px solid #e4e9ef; border-radius: 12px; padding: 24px 26px; }
.panel.detail { display: grid; grid-template-columns: 180px 1fr; gap: 26px; align-items: start; }
.detail .big { font-size: 6rem; text-align: center; background: #eef3f8; border-radius: 12px; padding: 24px 0; }
.detail h1 { margin: 0 0 4px; }
.detail .price { font-size: 1.7rem; font-weight: 800; color: #0f2740; margin: 14px 0; }

table.data { width: 100%; border-collapse: collapse; margin-top: 4px; }
table.data th, table.data td { text-align: left; padding: 9px 12px; border-bottom: 1px solid #e9edf2; font-size: .95rem; }
table.data th { background: #f5f8fb; color: #4a5c70; font-weight: 650; }

form.login { max-width: 360px; }
form.login label { display: block; font-size: .9rem; color: #4a5c70; margin: 14px 0 4px; }
form.login input {
  width: 100%; padding: 10px 12px; border: 1px solid #cdd6e0; border-radius: 8px; font-size: 1rem;
}
form.login button {
  margin-top: 20px; width: 100%; background: #2f9bd6; color: #fff; border: 0;
  padding: 11px 0; border-radius: 8px; font-size: 1rem; font-weight: 650; cursor: pointer;
}
.msg { padding: 11px 14px; border-radius: 8px; margin-bottom: 14px; font-size: .95rem; }
.msg.err { background: #fdecea; color: #96271b; border: 1px solid #f4c7c1; }
.msg.ok  { background: #e8f5ec; color: #1d6b34; border: 1px solid #bfe3c9; }
.muted { color: #7a8ba0; font-size: .9rem; }
.crumbs { font-size: .88rem; color: #7a8ba0; margin-bottom: 14px; }

footer { border-top: 1px solid #e4e9ef; background: #fff; color: #7a8ba0; font-size: .85rem; }
footer .wrap { padding: 22px 20px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.foot-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.modeflag { font-size: .78rem; padding: 3px 10px; border-radius: 20px; font-weight: 700; letter-spacing: .3px; }
.modeflag.v { background: #fdecea; color: #96271b; }
.modeflag.s { background: #e8f5ec; color: #1d6b34; }
.modeflag a { font-weight: 600; }
"""


def layout(title, body, session, aktivna_kat=""):
    kategorije = ["Računala", "Periferija", "Mreža", "Komponente"]
    cat_links = "".join(
        '<a href="/?kat={0}">{1}</a>'.format(urllib.parse.quote(k), html.escape(k))
        for k in kategorije
    )
    if session:
        admin = ' &nbsp;·&nbsp; <a href="/admin">Administracija</a>' if session["uloga"] == "administrator" else ""
        acct = 'Pozdrav, <a href="/racun">{0}</a>{1} &nbsp;·&nbsp; <a href="/odjava">Odjava</a>'.format(
            html.escape(session["prikaz"]), admin)
    else:
        acct = '<a href="/prijava">Prijava</a> &nbsp;·&nbsp; <a href="/prijava">Registracija</a>'

    mode = get_mode(HANDLER_REF[0]) if HANDLER_REF[0] is not None else "vulnerable"
    if mode == "safe":
        prekidac = ('<span class="modeflag s">zaštita: UKLJUČENA '
                    '<a href="/mode?set=vulnerable">isključi</a></span>')
    else:
        prekidac = ('<span class="modeflag v">zaštita: ISKLJUČENA '
                    '<a href="/mode?set=safe">uključi</a></span>')

    return """<!doctype html>
<html lang="hr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Bajt trgovina</title>
<style>{css}</style></head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="/">Bajt<span>.</span></a>
  <form action="/trazi" method="get">
    <input type="search" name="q" placeholder="Pretraži proizvode..." autocomplete="off">
    <button type="submit">Traži</button>
  </form>
  <div class="acct">{acct}</div>
</div></header>
<nav class="cats"><div class="wrap">
  <a href="/">Sve</a>{cats}
</div></nav>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
  <div>© 2026 Bajt d.o.o. · Ilica 1, Zagreb · OIB 12345678901</div>
  <div class="foot-right"><span>Dostava · Reklamacije · Uvjeti kupnje</span>{prekidac}</div>
</div></footer>
</body></html>""".format(title=html.escape(title), css=CSS, acct=acct, cats=cat_links, body=body, prekidac=prekidac)


# --------------------------------------------------------------- stranice

def stranica_pocetna(params):
    kat = q1(params, "kat")
    if kat:
        # ispravno: parametrizirani upit (obicno pregledavanje nije napadacka tocka)
        redovi = db.execute(
            "SELECT id, naziv, kategorija, cijena, slika FROM proizvodi WHERE kategorija = ? ORDER BY id",
            (kat,),
        ).fetchall()
        naslov = "Kategorija: " + html.escape(kat)
    else:
        redovi = db.execute(
            "SELECT id, naziv, kategorija, cijena, slika FROM proizvodi ORDER BY id"
        ).fetchall()
        naslov = "Izdvojeno iz ponude"

    kartice = []
    for pid, naziv, kategorija, cijena, slika in redovi:
        kartice.append(
            '<a class="card" href="/proizvod?id={id}">'
            '<div class="thumb">{slika}</div>'
            '<div class="body"><div class="kat">{kat}</div>'
            '<div class="naziv">{naziv}</div>'
            '<div class="cijena">{cijena}</div>'
            '<div class="buy">Detalji</div></div></a>'.format(
                id=pid, slika=slika or "📦", kat=html.escape(kategorija),
                naziv=html.escape(naziv), cijena=eur(cijena))
        )

    hero = ""
    if not kat:
        hero = (
            '<div class="hero"><h1>Sve za tvoje sklopove</h1>'
            '<p>Računala, periferija i komponente uz dostavu u 48 sati.</p></div>'
        )
    body = hero + '<h2 class="section">' + naslov + '</h2><div class="grid">' + "".join(kartice) + "</div>"
    return layout("Početna", body, get_session(HANDLER_REF[0]), kat)


def stranica_proizvod(params):
    pid = q1(params, "id", "1")
    mode = get_mode(HANDLER_REF[0])
    try:
        if mode == "safe":
            # ISPRAVNO: vrijednost ide kao parametar, odvojeno od naredbe.
            redovi = db.execute(
                "SELECT id, naziv, kategorija, cijena, opis FROM proizvodi WHERE id = ?",
                (pid,)).fetchall()
        else:
            # RANJIVO: id se lijepi izravno u upit, bez navodnika (brojcani kontekst).
            redovi = db.execute(
                "SELECT id, naziv, kategorija, cijena, opis FROM proizvodi WHERE id = " + pid
            ).fetchall()
    except sqlite3.Error as e:
        body = ('<div class="crumbs"><a href="/">Početna</a> › Greška</div>'
                '<div class="panel"><h1>Nešto je pošlo po zlu</h1>'
                '<p class="muted">Detalji: ' + html.escape(str(e)) + "</p></div>")
        return layout("Greška", body, get_session(HANDLER_REF[0]))

    if not redovi:
        body = ('<div class="panel"><h1>Proizvod nije pronađen</h1>'
                '<p class="muted"><a href="/">Natrag na početnu</a></p></div>')
        return layout("Nema proizvoda", body, get_session(HANDLER_REF[0]))

    # prvi red kao "glavni" proizvod, ostali (npr. iz UNION-a) ispod kao povezano
    r = redovi[0]
    slika = db.execute("SELECT slika FROM proizvodi WHERE id = ?", (r[0],)).fetchone()
    ikona = (slika[0] if slika else None) or "📦"
    glavni = (
        '<div class="crumbs"><a href="/">Početna</a> › {kat} › {naziv}</div>'
        '<div class="panel detail"><div class="big">{ikona}</div><div>'
        '<div class="kat muted">{kat}</div><h1>{naziv}</h1>'
        '<div class="price">{cijena}</div>'
        '<p>{opis}</p>'
        '<div class="buy" style="max-width:220px">Dodaj u košaricu</div>'
        '</div></div>'.format(
            kat=html.escape(str(r[2])), naziv=html.escape(str(r[1])),
            cijena=eur(r[3]), opis=html.escape(str(r[4])), ikona=ikona)
    )

    ostali = ""
    if len(redovi) > 1:
        red_html = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(str(x[0])), html.escape(str(x[1])), html.escape(str(x[2])),
                eur(x[3]), html.escape(str(x[4])))
            for x in redovi[1:]
        )
        ostali = ('<h2 class="section" style="margin-top:26px">Povezani artikli</h2>'
                  '<div class="panel"><table class="data">'
                  '<tr><th>#</th><th>Naziv</th><th>Kategorija</th><th>Cijena</th><th>Opis</th></tr>'
                  + red_html + "</table></div>")

    return layout(str(r[1]), glavni + ostali, get_session(HANDLER_REF[0]))


def stranica_trazi(params):
    q = q1(params, "q")
    mode = get_mode(HANDLER_REF[0])
    greska = None
    redovi = []
    try:
        if mode == "safe":
            # ISPRAVNO: unos ide kao parametar LIKE uzorka.
            redovi = db.execute(
                "SELECT naziv, kategorija, cijena FROM proizvodi "
                "WHERE naziv LIKE ? ORDER BY naziv", ("%" + q + "%",)).fetchall()
        else:
            # RANJIVO: unos se lijepi izravno u LIKE dio upita.
            redovi = db.execute(
                "SELECT naziv, kategorija, cijena FROM proizvodi "
                "WHERE naziv LIKE '%" + q + "%' ORDER BY naziv").fetchall()
    except sqlite3.Error as e:
        greska = str(e)

    head = ('<div class="crumbs"><a href="/">Početna</a> › Pretraga</div>'
            '<h2 class="section">Rezultati za: „' + html.escape(q) + "”</h2>")

    if greska:
        body = head + '<div class="msg err">Pretraga trenutno nije dostupna. (' + html.escape(greska) + ")</div>"
        return layout("Pretraga", body, get_session(HANDLER_REF[0]))

    if not redovi:
        body = head + '<div class="panel"><p class="muted">Nema proizvoda koji odgovaraju upitu.</p></div>'
        return layout("Pretraga", body, get_session(HANDLER_REF[0]))

    red_html = "".join(
        "<tr><td>{}</td><td>{}</td><td style='text-align:right'>{}</td></tr>".format(
            html.escape(str(a)), html.escape(str(b)), eur(c))
        for (a, b, c) in redovi
    )
    body = (head + '<div class="panel"><table class="data">'
            '<tr><th>Naziv</th><th>Kategorija</th><th style="text-align:right">Cijena</th></tr>'
            + red_html + "</table></div>"
            + '<p class="muted" style="margin-top:10px">Pronađeno: ' + str(len(redovi)) + " rezultat(a).</p>")
    return layout("Pretraga", body, get_session(HANDLER_REF[0]))


def stranica_prijava(params, poruka=None, ok=False):
    ime = q1(params, "ime")
    banner = ""
    if poruka:
        banner = '<div class="msg {0}">{1}</div>'.format("ok" if ok else "err", html.escape(poruka))
    body = (
        '<div class="crumbs"><a href="/">Početna</a> › Prijava</div>'
        '<div class="panel"><h1>Prijava</h1>'
        '<p class="muted">Prijavi se u svoj Bajt račun.</p>'
        + banner +
        '<form class="login" action="/prijava" method="post">'
        '<label>Korisničko ime</label>'
        '<input name="ime" value="' + html.escape(ime) + '" autocomplete="off" autofocus>'
        '<label>Lozinka</label>'
        '<input name="lozinka" type="password" autocomplete="off">'
        '<button type="submit">Prijavi se</button>'
        '</form></div>'
    )
    return layout("Prijava", body, get_session(HANDLER_REF[0]))


def obradi_prijavu(params):
    """Vraca (html_or_None, cookie_or_None). Ako je cookie postavljen, radi se redirect."""
    ime = q1(params, "ime")
    lozinka = q1(params, "lozinka")
    if not ime:
        return stranica_prijava(params), None
    mode = get_mode(HANDLER_REF[0])
    try:
        if mode == "safe":
            # ISPRAVNO: ime i lozinka idu kao parametri, odvojeno od naredbe.
            red = db.execute(
                "SELECT id, korisnicko_ime, uloga, prikaz FROM korisnici "
                "WHERE korisnicko_ime = ? AND lozinka_hash = ?",
                (ime, sha1(lozinka))).fetchone()
        else:
            # RANJIVO: i ime i lozinka se lijepe u upit.
            upit = ("SELECT id, korisnicko_ime, uloga, prikaz FROM korisnici "
                    "WHERE korisnicko_ime = '" + ime + "' AND lozinka_hash = '" + sha1(lozinka) + "'")
            red = db.execute(upit).fetchone()
    except sqlite3.Error as e:
        return stranica_prijava(params, "Prijava trenutno nije dostupna. (" + str(e) + ")"), None
    if red:
        cookie = "{0}|{1}|{2}".format(red[1], red[2], red[3])
        return None, urllib.parse.quote(cookie)
    return stranica_prijava(params, "Neispravno korisničko ime ili lozinka."), None


def stranica_racun():
    s = get_session(HANDLER_REF[0])
    if not s:
        return stranica_prijava({}, "Za pristup računu prijavi se.")
    narudzbe = db.execute(
        "SELECT stavka, iznos, datum FROM narudzbe WHERE kupac = ? ORDER BY datum DESC",
        (s["prikaz"],),
    ).fetchall()
    if narudzbe:
        red_html = "".join(
            "<tr><td>{}</td><td>{}</td><td style='text-align:right'>{}</td></tr>".format(
                html.escape(st), html.escape(dat), eur(iz))
            for (st, iz, dat) in narudzbe)
        tablica = ('<table class="data"><tr><th>Stavka</th><th>Datum</th>'
                   '<th style="text-align:right">Iznos</th></tr>' + red_html + "</table>")
    else:
        tablica = '<p class="muted">Nemaš još nijednu narudžbu.</p>'
    body = ('<div class="crumbs"><a href="/">Početna</a> › Moj račun</div>'
            '<div class="panel"><h1>Moj račun</h1>'
            '<p class="muted">Prijavljen kao <b>' + html.escape(s["prikaz"]) +
            "</b> (" + html.escape(s["uloga"]) + ")</p>"
            '<h2 class="section" style="margin-top:20px">Moje narudžbe</h2>' + tablica + "</div>")
    return layout("Moj račun", body, s)


def stranica_admin():
    s = get_session(HANDLER_REF[0])
    if not s or s["uloga"] != "administrator":
        body = ('<div class="panel"><h1>Pristup odbijen</h1>'
                '<p class="muted">Ova stranica dostupna je samo administratorima.</p></div>')
        return layout("Pristup odbijen", body, s)

    korisnici = db.execute("SELECT id, korisnicko_ime, uloga, prikaz, lozinka_hash FROM korisnici").fetchall()
    kartice = db.execute("SELECT vlasnik, broj, istek FROM kartice").fetchall()
    narudzbe = db.execute("SELECT kupac, stavka, iznos, datum FROM narudzbe ORDER BY datum DESC").fetchall()

    k_html = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><code>{}</code></td></tr>".format(
            i, html.escape(ki), html.escape(u), html.escape(p), h)
        for (i, ki, u, p, h) in korisnici)
    c_html = "".join(
        "<tr><td>{}</td><td><code>{}</code></td><td>{}</td></tr>".format(
            html.escape(v), html.escape(b), html.escape(ist))
        for (v, b, ist) in kartice)
    n_html = "".join(
        "<tr><td>{}</td><td>{}</td><td style='text-align:right'>{}</td><td>{}</td></tr>".format(
            html.escape(ku), html.escape(st), eur(iz), html.escape(da))
        for (ku, st, iz, da) in narudzbe)

    body = (
        '<div class="crumbs"><a href="/">Početna</a> › Administracija</div>'
        '<h1>Administracija</h1>'
        '<h2 class="section" style="margin-top:18px">Korisnici</h2>'
        '<div class="panel"><table class="data">'
        '<tr><th>#</th><th>Korisničko ime</th><th>Uloga</th><th>Ime</th><th>SHA-1 lozinke</th></tr>'
        + k_html + "</table></div>"
        '<h2 class="section" style="margin-top:22px">Pohranjene kartice</h2>'
        '<div class="panel"><table class="data">'
        '<tr><th>Vlasnik</th><th>Broj kartice</th><th>Istek</th></tr>'
        + c_html + "</table></div>"
        '<h2 class="section" style="margin-top:22px">Sve narudžbe</h2>'
        '<div class="panel"><table class="data">'
        '<tr><th>Kupac</th><th>Stavka</th><th style="text-align:right">Iznos</th><th>Datum</th></tr>'
        + n_html + "</table></div>"
    )
    return layout("Administracija", body, s)


# --------------------------------------------------------------- HTTP

HANDLER_REF = [None]  # trenutni handler, da stranice mogu procitati sesiju (cookie)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # tise za demo

    def _send_html(self, tekst, status=200, extra_headers=None):
        data = tekst.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, mjesto, cookie=None):
        self.send_response(303)
        self.send_header("Location", mjesto)
        if cookie is not None:
            self.send_header("Set-Cookie", "sesija=" + cookie + "; Path=/")
        self.end_headers()

    def do_GET(self):
        HANDLER_REF[0] = self
        u = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(u.query, keep_blank_values=True)

        if u.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if u.path in ("/", "/index.html"):
            self._send_html(stranica_pocetna(params))
        elif u.path == "/proizvod":
            self._send_html(stranica_proizvod(params))
        elif u.path == "/trazi":
            self._send_html(stranica_trazi(params))
        elif u.path == "/prijava":
            # dozvoljavamo i GET prijavu (payload u adresi je zgodan za demo)
            if "ime" in params:
                html_out, cookie = obradi_prijavu(params)
                if cookie is not None:
                    self._redirect("/", cookie)
                    return
                self._send_html(html_out)
            else:
                self._send_html(stranica_prijava(params))
        elif u.path == "/racun":
            self._send_html(stranica_racun())
        elif u.path == "/admin":
            self._send_html(stranica_admin())
        elif u.path == "/mode":
            novi = q1(params, "set", "vulnerable")
            if novi not in ("safe", "vulnerable"):
                novi = "vulnerable"
            natrag = self.headers.get("Referer") or "/"
            self.send_response(303)
            self.send_header("Location", natrag)
            self.send_header("Set-Cookie", "mode=" + novi + "; Path=/")
            self.end_headers()
        elif u.path == "/odjava":
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "sesija=; Path=/; Max-Age=0")
            self.end_headers()
        else:
            self._send_html(layout("Nije pronađeno",
                                   '<div class="panel"><h1>Stranica ne postoji</h1>'
                                   '<p class="muted"><a href="/">Natrag na početnu</a></p></div>',
                                   get_session(self)), status=404)

    def do_POST(self):
        HANDLER_REF[0] = self
        u = urllib.parse.urlparse(self.path)
        duljina = int(self.headers.get("Content-Length", 0) or 0)
        tijelo = self.rfile.read(duljina).decode("utf-8") if duljina else ""
        params = urllib.parse.parse_qs(tijelo, keep_blank_values=True)

        if u.path == "/prijava":
            html_out, cookie = obradi_prijavu(params)
            if cookie is not None:
                self._redirect("/", cookie)
                return
            self._send_html(html_out)
        else:
            self._redirect("/")


def main():
    srv = HTTPServer((HOST, PORT), Handler)
    print("Bajt trgovina radi na http://{}:{}   (Ctrl+C za kraj)".format(HOST, PORT))
    print("Baza je u radnoj memoriji, nista ne izlazi iz racunala.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nZaustavljeno.")


if __name__ == "__main__":
    main()

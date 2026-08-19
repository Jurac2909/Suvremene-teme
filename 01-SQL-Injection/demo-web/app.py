#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web demonstracija SQL injection napada za seminar.

Mala trgovina s dvije ranjive tocke: prijava i pretraga proizvoda.
Gore desno je prekidac izmedu RANJIVE i SIGURNE inacice, pa se isti
napad moze pokazati uzivo i onda pokazati da na ispravljenoj verziji
vise ne radi.

Pokretanje:
    python app.py
pa u pregledniku otvori  http://127.0.0.1:8000

Sve radi lokalno, baza je u radnoj memoriji, posluzitelj slusa samo na
127.0.0.1. Nista ne izlazi iz racunala i nista se ne sprema na disk.
"""

import hashlib
import html
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST, PORT = "127.0.0.1", 8000


def sha1(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- baza

db = sqlite3.connect(":memory:", check_same_thread=False)
db.executescript("""
CREATE TABLE korisnici (
    id INTEGER PRIMARY KEY, korisnicko_ime TEXT, lozinka_hash TEXT, uloga TEXT);
CREATE TABLE kartice (
    id INTEGER PRIMARY KEY, vlasnik TEXT, broj TEXT);
CREATE TABLE proizvodi (
    id INTEGER PRIMARY KEY, naziv TEXT, cijena INTEGER);
""")
db.executemany("INSERT INTO korisnici VALUES (?,?,?,?)", [
    (1, "ana",   sha1("ljeto2025"),      "korisnik"),
    (2, "marko", sha1("marko123"),       "korisnik"),
    (3, "admin", sha1("SuperTajna2026!"), "administrator"),
])
db.executemany("INSERT INTO kartice VALUES (?,?,?)", [
    (1, "ana",   "4111 1111 1111 1111"),
    (2, "marko", "5500 0000 0000 0004"),
    (3, "admin", "3400 0000 0000 009"),
])
db.executemany("INSERT INTO proizvodi VALUES (?,?,?)", [
    (1, "Tipkovnica", 249),
    (2, "Mis",        149),
    (3, "Monitor",    1299),
    (4, "Web kamera", 399),
])
db.commit()


# ----------------------------------------------------------- pomocno

def mark(s):
    """HTML-siguran prikaz korisnickog unosa, istaknut zutom bojom."""
    return "<mark>" + html.escape(s) + "</mark>"


def sql_box(text_html):
    return '<pre class="sql">' + text_html + "</pre>"


def rows_table(rows, headers):
    if not rows:
        return '<p class="muted">Upit nije vratio nijedan redak.</p>'
    out = ["<table class='res'><tr>"]
    for h in headers:
        out.append("<th>" + html.escape(h) + "</th>")
    out.append("</tr>")
    for r in rows:
        out.append("<tr>")
        for c in r:
            out.append("<td>" + html.escape(str(c)) + "</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def looks_injected(s):
    low = s.lower()
    return ("'" in s) or ("--" in s) or (" or " in low) or ("union" in low)


# ----------------------------------------------------------- scenariji

def scenarij_prijava(mode, params):
    ime = params.get("ime", [""])[0]
    lozinka = params.get("lozinka", [""])[0]
    poslano = "ime" in params

    body = ["<h2>1. Prijava</h2>",
            "<form method='get' action='/login'>",
            "<label>Korisnicko ime</label>",
            "<input name='ime' value='%s' autocomplete='off'>" % html.escape(ime),
            "<label>Lozinka</label>",
            "<input name='lozinka' value='%s' autocomplete='off'>" % html.escape(lozinka),
            "<button type='submit'>Prijavi se</button>",
            "</form>"]

    primjeri = [
        ("admin' -- ", "bilo sto", "Zaobilazenje lozinke za tocno odredenog korisnika"),
        ("' OR '1'='1' -- ", "bilo sto", "Prijava bez ijednog valjanog podatka"),
    ]
    body.append("<p class='muted'>Primjeri napada (klikni):</p><ul class='ex'>")
    for i, l, opis in primjeri:
        qs = urllib.parse.urlencode({"ime": i, "lozinka": l})
        body.append("<li><a href='/login?%s'><code>%s</code></a> &mdash; %s</li>"
                    % (qs, html.escape(i), opis))
    body.append("</ul>")
    body.append("<p class='muted'>Ispravna prijava: <code>admin</code> / "
                "<code>SuperTajna2026!</code></p>")

    if not poslano:
        return "".join(body)

    if mode == "safe":
        upit = ("SELECT id, korisnicko_ime, uloga FROM korisnici\n"
                "WHERE korisnicko_ime = ? AND lozinka_hash = ?")
        disp = (upit + "\n-- parametri: [" + mark(ime) + ", " + mark(sha1(lozinka)) + "]")
        try:
            rows = db.execute(upit, (ime, sha1(lozinka))).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)
    else:
        upit = ("SELECT id, korisnicko_ime, uloga FROM korisnici\n"
                "WHERE korisnicko_ime = '%s' AND lozinka_hash = '%s'"
                % (ime, sha1(lozinka)))
        disp = ("SELECT id, korisnicko_ime, uloga FROM korisnici\n"
                "WHERE korisnicko_ime = '" + mark(ime)
                + "' AND lozinka_hash = '" + mark(sha1(lozinka)) + "'")
        try:
            rows = db.execute(upit).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)

    body.append("<h3>Upit koji baza izvrsava</h3>")
    body.append(sql_box(disp))

    if err:
        body.append("<div class='banner err'>Greska baze: " + html.escape(err) + "</div>")
    elif rows:
        bypass = (mode != "safe") and looks_injected(ime + lozinka)
        klasa = "bad" if bypass else "ok"
        poruka = ("AUTENTIKACIJA ZAOBIDENA bez ispravne lozinke"
                  if bypass else "Prijava uspjesna")
        body.append("<div class='banner %s'>%s. Prijavljeno kao: %s</div>"
                    % (klasa, poruka,
                       ", ".join("%s (%s)" % (r[1], r[2]) for r in rows)))
        body.append(rows_table(rows, ["id", "korisnicko_ime", "uloga"]))
    else:
        body.append("<div class='banner ok'>Prijava odbijena.</div>")

    return "".join(body)


def scenarij_pretraga(mode, params):
    q = params.get("q", [""])[0]
    order = params.get("order", ["ASC"])[0]
    poslano = "q" in params

    body = ["<h2>2. Pretraga proizvoda</h2>",
            "<form method='get' action='/search'>",
            "<label>Trazi naziv</label>",
            "<input name='q' value='%s' autocomplete='off'>" % html.escape(q),
            "<input type='hidden' name='order' value='%s'>" % html.escape(order),
            "<button type='submit'>Trazi</button>",
            "</form>"]

    primjeri = [
        ("' UNION SELECT korisnicko_ime, lozinka_hash FROM korisnici -- ",
         "Ispis korisnickih imena i hashova lozinki"),
        ("' UNION SELECT vlasnik, broj FROM kartice -- ",
         "Ispis brojeva kartica iz potpuno druge tablice"),
        ("Mis", "Obicna, bezopasna pretraga"),
    ]
    body.append("<p class='muted'>Primjeri (klikni):</p><ul class='ex'>")
    for payload, opis in primjeri:
        qs = urllib.parse.urlencode({"q": payload, "order": "ASC"})
        body.append("<li><a href='/search?%s'><code>%s</code></a> &mdash; %s</li>"
                    % (qs, html.escape(payload), opis))
    body.append("</ul>")

    if not poslano:
        return "".join(body)

    if mode == "safe":
        dozvoljeni = {"asc": "ASC", "desc": "DESC"}
        smjer = dozvoljeni.get(order.lower(), "ASC")
        upit = ("SELECT naziv, cijena FROM proizvodi\n"
                "WHERE naziv LIKE ? ORDER BY cijena " + smjer)
        disp = ("SELECT naziv, cijena FROM proizvodi\n"
                "WHERE naziv LIKE ? ORDER BY cijena " + smjer
                + "\n-- parametar: [" + mark("%" + q + "%") + "]")
        try:
            rows = db.execute(upit, ("%" + q + "%",)).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)
    else:
        upit = ("SELECT naziv, cijena FROM proizvodi\n"
                "WHERE naziv LIKE '%%%s%%' ORDER BY cijena %s" % (q, order))
        disp = ("SELECT naziv, cijena FROM proizvodi\n"
                "WHERE naziv LIKE '%" + mark(q) + "%' ORDER BY cijena "
                + mark(order))
        try:
            rows = db.execute(upit).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)

    body.append("<h3>Upit koji baza izvrsava</h3>")
    body.append(sql_box(disp))

    if err:
        body.append("<div class='banner err'>Greska baze: " + html.escape(err) + "</div>")
    else:
        if mode != "safe" and looks_injected(q):
            body.append("<div class='banner bad'>Upit je promijenjen. "
                        "Rezultati ispod ne dolaze nuzno iz tablice proizvoda.</div>")
        body.append(rows_table(rows, ["naziv / procitani podatak", "cijena / procitani podatak"]))

    return "".join(body)


def scenarij_provjera(mode, params):
    ime = params.get("ime", [""])[0]
    poslano = "ime" in params

    body = ["<h2>3. Provjera korisnickog imena (slijepi napad)</h2>",
            "<p class='muted'>Kao kod registracije: stranica kaze samo je li ime "
            "<b>zauzeto</b> ili <b>slobodno</b>. Nikakav podatak se ne prikazuje. "
            "Ipak se kroz taj da/ne odgovor moze ukrasti tajni podatak, znak po znak.</p>",
            "<form method='get' action='/provjera'>",
            "<label>Korisnicko ime</label>",
            "<input name='ime' value='%s' autocomplete='off'>" % html.escape(ime),
            "<button type='submit'>Provjeri</button>",
            "</form>"]

    primjeri = [
        ("admin", "Postojece ime -> ZAUZETO"),
        ("nepostojeci", "Nepostojece ime -> SLOBODNO"),
        ("admin' AND '1'='1", "Uvijek istinit uvjet -> ZAUZETO (orakl kaze DA)"),
        ("admin' AND '1'='2", "Uvijek lazan uvjet -> SLOBODNO (orakl kaze NE)"),
        ("admin' AND substr((SELECT broj FROM kartice WHERE vlasnik='admin'),1,1)='3' -- ",
         "Pitanje: je li prvi znak admin kartice '3'? ZAUZETO znaci da."),
    ]
    body.append("<p class='muted'>Primjeri (klikni):</p><ul class='ex'>")
    for payload, opis in primjeri:
        qs = urllib.parse.urlencode({"ime": payload})
        body.append("<li><a href='/provjera?%s'><code>%s</code></a> &mdash; %s</li>"
                    % (qs, html.escape(payload), opis))
    body.append("</ul>")
    body.append("<p class='muted'>Za punu krađu pokreni "
                "<code>python blind_extract.py</code> dok je verzija RANJIVA. "
                "Skripta rekonstruira cijeli broj kartice samo iz da/ne odgovora.</p>")

    if not poslano:
        return "".join(body)

    if mode == "safe":
        upit = "SELECT id FROM korisnici WHERE korisnicko_ime = ?"
        disp = upit + "\n-- parametar: [" + mark(ime) + "]"
        try:
            rows = db.execute(upit, (ime,)).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)
    else:
        upit = "SELECT id FROM korisnici WHERE korisnicko_ime = '%s'" % ime
        disp = "SELECT id FROM korisnici WHERE korisnicko_ime = '" + mark(ime) + "'"
        try:
            rows = db.execute(upit).fetchall()
            err = None
        except sqlite3.Error as e:
            rows, err = [], str(e)

    body.append("<h3>Upit koji baza izvrsava</h3>")
    body.append(sql_box(disp))

    if err:
        body.append("<div class='banner err'>Greska baze: " + html.escape(err) + "</div>")
        body.append("<!--[[ORACLE:FALSE]]-->")
    elif rows:
        body.append("<div class='banner bad'>ZAUZETO</div>")
        body.append("<!--[[ORACLE:TRUE]]-->")
    else:
        body.append("<div class='banner ok'>SLOBODNO</div>")
        body.append("<!--[[ORACLE:FALSE]]-->")
    body.append("<p class='muted'>Primijeti: prikazan je samo da/ne, nijedan podatak "
                "iz baze. Napad ipak prolazi.</p>")
    return "".join(body)


# ----------------------------------------------------------- stranica

def stranica(mode, sadrzaj):
    drugi = "safe" if mode == "vulnerable" else "vulnerable"
    oznaka = ("RANJIVA VERZIJA" if mode == "vulnerable" else "SIGURNA VERZIJA")
    boja = "vuln" if mode == "vulnerable" else "safe-mode"
    return """<!doctype html>
<html lang="hr"><head><meta charset="utf-8">
<title>SQL injection demo</title>
<style>
 body {{ font-family: system-ui, Arial, sans-serif; max-width: 820px;
        margin: 0 auto; padding: 1rem 1.2rem 4rem; color:#1a1a1a; }}
 header {{ display:flex; justify-content:space-between; align-items:center;
          border-bottom:2px solid #ddd; padding-bottom:.6rem; }}
 header h1 {{ font-size:1.15rem; margin:0; }}
 .mode {{ font-weight:700; padding:.35rem .7rem; border-radius:6px; text-decoration:none; }}
 .mode.vuln {{ background:#fde2e1; color:#8a1c14; }}
 .mode.safe-mode {{ background:#e2f0e4; color:#1c5a2a; }}
 .switch {{ font-size:.85rem; }}
 h2 {{ margin-top:2rem; }}
 form {{ display:flex; flex-wrap:wrap; gap:.5rem; align-items:end;
        background:#f6f6f6; padding:.9rem; border-radius:8px; }}
 label {{ display:block; font-size:.78rem; color:#555; width:100%; margin-bottom:-.3rem; }}
 input {{ padding:.45rem .5rem; border:1px solid #bbb; border-radius:5px;
         font-family:monospace; min-width:16rem; }}
 button {{ padding:.5rem .9rem; border:0; border-radius:5px; background:#2b5cff;
          color:#fff; font-weight:600; cursor:pointer; }}
 pre.sql {{ background:#0f1220; color:#e6e6e6; padding:.8rem; border-radius:8px;
           overflow-x:auto; font-size:.85rem; line-height:1.4; }}
 pre.sql mark {{ background:#ffd23f; color:#000; padding:0 .1rem; border-radius:2px; }}
 table.res {{ border-collapse:collapse; margin:.6rem 0; width:100%; }}
 table.res th, table.res td {{ border:1px solid #ccc; padding:.35rem .6rem;
                              text-align:left; font-family:monospace; font-size:.9rem; }}
 table.res th {{ background:#eee; }}
 .banner {{ padding:.7rem .9rem; border-radius:8px; font-weight:600; margin:.6rem 0; }}
 .banner.bad {{ background:#fde2e1; color:#8a1c14; }}
 .banner.ok {{ background:#e2f0e4; color:#1c5a2a; }}
 .banner.err {{ background:#fff3cd; color:#7a5b00; font-family:monospace; }}
 .muted {{ color:#666; font-size:.9rem; }}
 ul.ex {{ padding-left:1.1rem; }}
 ul.ex li {{ margin:.3rem 0; }}
 code {{ background:#eee; padding:.05rem .3rem; border-radius:3px; }}
 nav a {{ margin-right:1rem; }}
</style></head><body>
<header>
  <h1>Trgovina &mdash; demo</h1>
  <div class="switch">
    <span class="mode {boja}">{oznaka}</span>
    &nbsp; <a href="/mode?set={drugi}">prebaci na {drugi}</a>
  </div>
</header>
<nav><a href="/">Pocetna</a><a href="/login">Prijava</a><a href="/search">Pretraga</a><a href="/provjera">Provjera imena</a></nav>
{sadrzaj}
</body></html>""".format(boja=boja, oznaka=oznaka, drugi=drugi, sadrzaj=sadrzaj)


POCETNA = """
<h2>O demonstraciji</h2>
<p>Ova trgovina ima dvije ranjive tocke. Gore desno prebaci izmedu
<b>ranjive</b> i <b>sigurne</b> verzije da vidis razliku na istom napadu.</p>
<ul>
  <li><a href="/login">Prijava</a> &mdash; zaobilazenje prijave.</li>
  <li><a href="/search">Pretraga proizvoda</a> &mdash; citanje tudih tablica preko UNION.</li>
  <li><a href="/provjera">Provjera imena</a> &mdash; slijepi napad, krada podatka bez ijednog prikazanog retka.</li>
</ul>
<p class="muted">Sve radi lokalno na 127.0.0.1, baza je u radnoj memoriji.</p>
"""


# ----------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    def _mode(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            if part.strip().startswith("mode="):
                v = part.strip()[5:]
                if v in ("safe", "vulnerable"):
                    return v
        return "vulnerable"

    def _send(self, html_text, extra_headers=None):
        data = html_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(u.query, keep_blank_values=True)
        mode = self._mode()

        if u.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if u.path == "/mode":
            novi = params.get("set", ["vulnerable"])[0]
            if novi not in ("safe", "vulnerable"):
                novi = "vulnerable"
            data = b"redirect"
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "mode=%s; Path=/" % novi)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if u.path == "/login":
            self._send(stranica(mode, scenarij_prijava(mode, params)))
        elif u.path == "/search":
            self._send(stranica(mode, scenarij_pretraga(mode, params)))
        elif u.path == "/provjera":
            self._send(stranica(mode, scenarij_provjera(mode, params)))
        else:
            self._send(stranica(mode, POCETNA))

    def log_message(self, *args):
        pass  # tiho, bez sumnog ispisa u konzoli


def main():
    srv = HTTPServer((HOST, PORT), Handler)
    print("Demo radi na  http://%s:%d" % (HOST, PORT))
    print("Zaustavi s Ctrl+C.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nZaustavljeno.")
        srv.server_close()


if __name__ == "__main__":
    main()

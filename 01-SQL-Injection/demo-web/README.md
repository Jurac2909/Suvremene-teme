# Web demo za prezentaciju

Mala trgovina s tri ranjive tocke. Napad se pokaze uzivo u pregledniku, a
prekidacem gore desno prebacis na ispravljenu verziju da vidi kako isti napad
vise ne prolazi.

## Pokretanje

```
python app.py
```

Zatim otvori http://127.0.0.1:8000 . Treba samo Python 3, bez instalacije
ikakvih paketa. Posluzitelj slusa samo na 127.0.0.1, baza je u radnoj
memoriji, nista ne izlazi iz racunala. Zaustavi s Ctrl+C.

Ako je port 8000 zauzet, promijeni `PORT` na vrhu `app.py`.

## Tijek prezentacije

Drzi verziju na **RANJIVA** (pise gore desno).

1. **Normalna prijava.** Otvori Prijava, upisi `admin` / `SuperTajna2026!`.
   Zelena traka, prijava radi. Ovo je ocekivano ponasanje.

2. **Zaobilazenje prijave.** Klikni primjer `admin' -- `. Crvena traka:
   prijavljen si kao admin bez ispravne lozinke. Pokazi crni okvir s upitom.
   Zuto je oznaceno ono sto je korisnik upisao. Objasni: `--` zapocinje
   komentar, pa baza preskoci provjeru lozinke.

3. **Uvijek istinit uvjet.** Klikni `' OR '1'='1' -- ` i pokazi da uvjet
   koji je uvijek istinit vrati korisnika bez ijednog valjanog podatka.

4. **Citanje tudih tablica.** Otvori Pretraga, prvo utipkaj `Mis` da pokazes
   normalnu pretragu. Zatim klikni `' UNION SELECT vlasnik, broj FROM kartice`.
   Umjesto proizvoda ispisu se brojevi kartica iz potpuno druge tablice.
   Ponovi s `' UNION SELECT korisnicko_ime, lozinka_hash FROM korisnici` za
   korisnicka imena i hashove lozinki.

5. **Slijepi napad (najjaci dio).** Otvori Provjera imena. Ova stranica
   ne prikazuje nikakav podatak, samo kaze **ZAUZETO** ili **SLOBODNO**.
   - Klikni `admin' AND '1'='1` -> ZAUZETO, pa `admin' AND '1'='2` -> SLOBODNO.
     Ovo je orakl: baza odgovara na tvoje da/ne pitanje.
   - Klikni zadnji primjer koji pita je li prvi znak admin kartice `3`.
     ZAUZETO znaci da.
   - Sad u terminalu pokreni `python blind_extract.py`. Skripta postavlja
     desetke da/ne pitanja i pred publikom slaze cijeli broj kartice
     (`3400 0000 0000 009`), znak po znak, iako stranica nikad nije
     prikazala nijedan podatak. Poanta: skrivanje ispisa nije zastita.

6. **Popravak.** Gore desno klikni "prebaci na safe". Ponovi tocke 2 do 5
   istim primjerima. Prijava se odbija, pretraga vraca prazno, a na Provjeri
   imena injektirani uvjet vise ne mijenja odgovor (`admin' AND '1'='1` daje
   SLOBODNO). Na kraju pokazi da `admin` / `SuperTajna2026!` i pretraga
   `Monitor` i dalje rade. Poanta: parametrizirani upiti razdvajaju naredbu
   od podatka.

## Sto reci kod razlike ranjivo/sigurno

U ranjivoj verziji upit se gradi lijepljenjem niza znakova, pa unos moze
promijeniti znacenje naredbe. U sigurnoj se salje predlozak upita s `?` na
mjestu vrijednosti, a vrijednost ide odvojeno. Vidljivo je i u prikazu upita:
u sigurnom nacinu unos je izvan same naredbe, pod `parametri`.

## Napomene

- Obrazac za prijavu ovdje koristi GET da bi se payload vidio u adresnoj
  traci i da primjeri rade kao poveznice. Prave aplikacije koriste POST. To
  ne mijenja ranjivost.
- Ovaj sqlite driver ne dopusta vise naredbi u jednom `execute`, pa napadi
  tipa `; DROP TABLE` ne rade. UNION i komentari rade. Dobar trenutak da se
  spomene da razliciti sustavi dopustaju razlicite napade.

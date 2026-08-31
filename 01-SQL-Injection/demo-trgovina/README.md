# Bajt trgovina — realistična ranjiva stranica

Ovo je "prava" mala web trgovina za **ručni** SQL injection na prezentaciji.
Ovdje se **nigdje ne prikazuje SQL upit** —
stranica izgleda kao obična trgovina, a napad se izvodi rukom, kao pravi
napadač: kroz polje za prijavu, tražilicu i `id` proizvoda u adresi. Sitni
prekidač zaštite skriven je u podnožju (footer): nakon što napadi prođu, klikom
se uključe parametrizirani upiti i pokaže da isti napadi više ne prolaze.

## Pokretanje

```
python3 app.py
```

Otvori http://127.0.0.1:8000 . Treba samo Python 3, bez ijednog paketa.
Poslužitelj sluša samo na `127.0.0.1`, baza je u radnoj memoriji, ništa ne
izlazi iz računala i ništa se ne sprema na disk. Ako je port 8000 zauzet,
promijeni `PORT` na vrhu `app.py`. Zaustavi s Ctrl+C.

> Namjerno ranjivo, isključivo za lokalnu demonstraciju. Ne izlagati na mrežu.

## Legitimne prijave (za usporedbu)

| korisnik | lozinka            | uloga         |
|----------|--------------------|---------------|
| `ana`    | `ljeto2025`        | kupac         |
| `marko`  | `marko123`         | kupac         |
| `admin`  | `V3lika!Tajna#2026` | administrator |

Admin lozinka je namjerno jaka — ne može se pogoditi, mora se **zaobići**.

---

## Šalabahter napada (redoslijed za prezentaciju)

Prvo pokaži da stranica radi normalno: klikaj po kategorijama, otvori proizvod,
utipkaj `miš` u tražilicu. Tek onda kreni s napadom.

### 1. Zaobilaženje prijave (`/prijava`)

Upit iza prijave je otprilike:
`... WHERE korisnicko_ime = '<ime>' AND lozinka_hash = '<hash>'`

U polje **Korisničko ime** upiši, lozinku ostavi praznu:

```
admin' --
```

(iza `--` mora biti razmak). Komentar poništi provjeru lozinke → prijavljen si
kao **admin**. Gore desno se pojavi **Administracija** → klikni i pokaži da sada
vidiš sve korisnike, **hasheve lozinki** i **brojeve kartica**. To je cilj.

Varijanta bez pogađanja imena — vrati prvog korisnika u tablici:

```
' OR 1=1 --
```

### 2. Čitanje tuđih tablica iz tražilice (`/trazi`)

Upit je: `... WHERE naziv LIKE '%<q>%' ...` (3 stupca: naziv, kategorija, cijena).
Zato UNION mora vratiti 3 stupca. U tražilicu upiši:

Brojevi kartica ispisani kao "proizvodi":
```
' UNION SELECT vlasnik, 'KARTICA', broj FROM kartice --
```

Korisnička imena, uloge i hashevi lozinki:
```
' UNION SELECT korisnicko_ime, uloga, lozinka_hash FROM korisnici --
```

Prvo utipkaj nešto normalno (npr. `disk`) da se vidi obična pretraga, pa onda
zalijepi payload — u istoj tablici osvanu podaci iz sasvim druge tablice.

### 3. Čitanje tuđih tablica preko id-a proizvoda (`/proizvod?id=`)

Ovdje je `id` broj bez navodnika: `... WHERE id = <id>`. Upit ima 5 stupaca
(id, naziv, kategorija, cijena, opis). U adresnu traku:

```
http://127.0.0.1:8000/proizvod?id=0 UNION SELECT id, vlasnik, 'Kartica', broj, istek FROM kartice --
```

(id `0` ne postoji, pa se prikažu samo redovi iz UNION-a, pod „Povezani artikli”.)
Preglednik će razmake pretvoriti u `%20` — to je u redu.

Klasična provjera da je točka ranjiva (uvijek istinito):
```
http://127.0.0.1:8000/proizvod?id=1 OR 1=1
```

### 4. Poanta / obrana

Uzrok je isti u sve tri točke: **podatak i naredba u istom nizu znakova**.
Rješenje je parametrizirani (pripremljeni) upit — `?` na mjestu vrijednosti, a
vrijednost ide odvojeno. U podnožju stranice klikni **„zaštita: uključi”** i
ponovi ista tri napada: prijava se odbija, tražilica i `id` proizvoda više ne
vraćaju tuđe podatke, a obična kupnja (`ana`/`ljeto2025`, pretraga `disk`) i
dalje radi. Ista se usporedba, uz vidljiv SQL upit, vidi i u
`../kod/demo_sqli.py` te `../kod/ranjivo.php` / `../kod/sigurno.php`.

> Način rada pamti se u kolačiću `mode`. Prekidač se vraća na Referer stranicu,
> pa ako zaštitu uključiš dok gledaš rezultat napada, ista se stranica odmah
> ponovno učita s parametriziranim upitom.

## Napomene

- SQLite driver ne dopušta više naredbi u jednom upitu, pa `; DROP TABLE ...`
  ne radi. UNION i komentari (`--`) rade — što je i realno: različiti sustavi
  dopuštaju različite napade.
- Obrazac za prijavu radi i preko GET-a (`/prijava?ime=...&lozinka=...`), pa
  payload možeš staviti i u poveznicu za bržu demonstraciju.

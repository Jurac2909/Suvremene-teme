# Suvremene teme informacijske sigurnosti — seminarski radovi

Dva seminarska rada s pripadajućim kodom za primjere. Autor: Jurica Jurčević,
Odjel za matematiku, Sveučilište Josipa Jurja Strossmayera u Osijeku, 2026.

| Mapa | Tema | Rad | Kod |
|------|------|-----|-----|
| [`01-SQL-Injection`](01-SQL-Injection) | OWASP Top 10: SQL Injection napadi i zaštita | [`SQL-Injection.pdf`](01-SQL-Injection/SQL-Injection.pdf) | web demo + skripte |
| [`02-Reed-Solomon`](02-Reed-Solomon) | Reed-Solomonovi kodovi za ispravljanje pogrešaka | [`Reed-Solomon.pdf`](02-Reed-Solomon/Reed-Solomon.pdf) | `rs.py` |

Ispisi i slike u radovima dolaze iz stvarnog izvođenja priloženih skripti.

## Pokretanje primjera

Treba samo Python 3. Nijedna skripta ne instalira pakete, ne piše na disk i ne
šalje promet izvan računala. Baze su u radnoj memoriji, web demo sluša samo na
`127.0.0.1`.

### SQL injection, konzolni prikaz

```
python 01-SQL-Injection/kod/demo_sqli.py
```

 Redom pokaže ispravnu prijavu, zaobilaženje lozinke, `OR '1'='1'`, UNION napad,
pa iste ulaze protiv pripremljenog upita gdje napad više ne prolazi.

### SQL injection, web demo za prezentaciju

```
python 01-SQL-Injection/demo-trgovina/app.py
```

Zatim otvori <http://127.0.0.1:8000>. Realistična web trgovina s tri ranjive
točke (prijava, tražilica, `id` proizvoda u adresi) na kojoj se SQL injection
izvodi ručno, kao pravi napadač. Sitni prekidač zaštite u podnožju prebacuje na
parametrizirane upite, pa se isti napad pokaže uživo i onda pokaže da na
zaštićenoj verziji više ne prolazi. Tijek prezentacije korak po korak i gotovi
payloadi su u [`demo-trgovina/README.md`](01-SQL-Injection/demo-trgovina/README.md).

Datoteke [`kod/ranjivo.php`](01-SQL-Injection/kod/ranjivo.php) i
[`kod/sigurno.php`](01-SQL-Injection/kod/sigurno.php) su isječci iz rada za
usporedbu spajanja niza i pripremljenog upita. Ne pokreću se, služe za čitanje.

### Reed-Solomon, kodiranje i dekodiranje

```
python 02-Reed-Solomon/kod/rs.py
```

Implementacija nad poljem `GF(2^m)`: sistematsko kodiranje, sindromi,
Berlekamp-Masseyev algoritam, Chienova pretraga i Forneyev algoritam. Ispisuje
razrađeni `RS(7,3)` primjer nad `GF(8)` i `RS` nad `GF(256)` koji oporavi pet
oštećenih simbola, a kod šest pogrešaka odbije dekodiranje jer je izvan granice.

## Gradnja PDF-a iz izvora

PDF-ovi su već u repozitoriju. Za ponovnu gradnju iz `.tex` izvora vidi
[`BUILD.md`](BUILD.md). Potreban je LaTeX (MiKTeX ili TeX Live), a `mathos.cls`
i `MathosLogo.png` su priloženi uz svaki rad.

## Napomena

Ranjivi primjeri postoje isključivo radi demonstracije u kontroliranom,
lokalnom okruženju za potrebe seminara. Nisu namijenjeni izlaganju prema mreži.

# Gradnja radova

MiKTeX je instaliran i oba rada su već prevedena u PDF:
- `01-SQL-Injection/SQL-Injection.pdf` (23 stranice)
- `02-Reed-Solomon/Reed-Solomon.pdf` (23 stranice)

## Ponovna gradnja
U mapi rada pokreni `pdflatex` dvaput (drugi put zbog sadržaja i unakrsnih referenci):
```
pdflatex SQL-Injection.tex
pdflatex SQL-Injection.tex
```
Isto za `Reed-Solomon.tex`. U VS Code-u je lakše koristiti proširenje LaTeX Workshop, koje to radi automatski na spremanje.

Napomena: MiKTeX pri gradnji ispisuje upozorenje "major issue: So far, you have not checked for MiKTeX updates". To je samo upozorenje i ne prekida gradnju. Ukloni ga tako da u MiKTeX Console jednom pokreneš Check for updates.

## Prije predaje
- Upiši ime mentora umjesto `Ime i prezime mentora` na naslovnici (oba rada).
- Napiši životopis na kraju svakog rada (sada stoji zamjenski tekst).
- Provjeri smjer studija na naslovnici ako nije Matematika i računarstvo.

## Priloženi kod
Ispisi u radovima dolaze iz stvarnog izvođenja ovih skripti:
```
python 01-SQL-Injection/kod/demo_sqli.py
python 02-Reed-Solomon/kod/rs.py
```
`demo_sqli.py` treba samo Python 3 (koristi `sqlite3` iz standardne biblioteke, baza je u radnoj memoriji, ništa ne izlazi iz procesa).

## Pomoćne datoteke
`.aux`, `.log`, `.out`, `.toc` su međurezultati gradnje. Mogu se obrisati, LaTeX ih ponovno stvori pri sljedećoj gradnji.

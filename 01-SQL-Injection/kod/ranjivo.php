<?php
// RANJIV KOD. Sluzi samo kao primjer u seminarskom radu.
// Ne koristiti ni u kakvom sustavu koji je dostupan izvana.

$veza = new mysqli("localhost", "webapp", "tajna", "trgovina");

// Ulaz stize izravno iz HTTP zahtjeva i spaja se u tekst upita.
$kategorija = $_GET["kategorija"];
$poredak    = $_GET["poredak"];

$upit = "SELECT naziv, cijena FROM proizvodi
         WHERE kategorija = '" . $kategorija . "'
         ORDER BY cijena " . $poredak;

$rezultat = $veza->query($upit);

while ($redak = $rezultat->fetch_assoc()) {
    echo htmlspecialchars($redak["naziv"]) . ": " . $redak["cijena"] . "\n";
}

// Zahtjev oblika
//   ?kategorija=knjige' UNION SELECT korisnicko_ime, lozinka FROM korisnici -- &poredak=ASC
// mijenja znacenje upita i vraca sadrzaj tablice korisnici.

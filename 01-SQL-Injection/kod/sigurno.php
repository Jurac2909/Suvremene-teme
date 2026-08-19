<?php
// Ispravljena inacica istog koda.

$veza = new mysqli("localhost", "webapp_ro", "tajna", "trgovina");
$veza->set_charset("utf8mb4");

$kategorija = $_GET["kategorija"];
$poredak    = $_GET["poredak"];

// Smjer sortiranja nije vrijednost nego dio sintakse upita i ne moze se
// predati kao parametar. Zato se preslikava kroz bijelu listu.
$dozvoljeni_poredak = ["asc" => "ASC", "desc" => "DESC"];
$smjer = $dozvoljeni_poredak[strtolower($poredak)] ?? "ASC";

$upit = "SELECT naziv, cijena FROM proizvodi
         WHERE kategorija = ?
         ORDER BY cijena " . $smjer;

$izjava = $veza->prepare($upit);
$izjava->bind_param("s", $kategorija);   // "s" = vrijednost tipa string
$izjava->execute();

$rezultat = $izjava->get_result();
while ($redak = $rezultat->fetch_assoc()) {
    echo htmlspecialchars($redak["naziv"]) . ": " . $redak["cijena"] . "\n";
}

$izjava->close();

// Isti zahtjev kao u prethodnom primjeru sada trazi kategoriju ciji je
// naziv doslovno
//   knjige' UNION SELECT korisnicko_ime, lozinka FROM korisnici --
// Takva kategorija ne postoji, pa upit vraca prazan skup.

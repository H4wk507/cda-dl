# cda-dl

CLI downloader do filmów i folderów z [cda.pl](https://www.cda.pl/)

## Instalacja z PyPI

```
pip install cda-dl
```

## Instalacja manualna

1. Sklonuj repozytorium

```
git clone https://github.com/H4wk507/cda-dl.git
```

2. Wejdź do katalogu i zainstaluj

```
cd cda-dl && pip install .
```

## Opcje

```
$ cda-dl --help
usage: cda-dl [OPCJE] URL [URL...]

Downloader do filmów i folderów z cda.pl

positional arguments:
  URL                   URL(y) do filmu(ów)/folder(ów) do pobrania

options:
  -h, --help            Wyświetl tę pomoc i wyjdź
  --version             Wyświetl wersję programu
  -q, --quiet           Wyświetlaj tylko błędy i ostrzeżenia
  -l, --login USER      Zaloguj się do konta
  -d, --directory PATH  Ustaw docelowy katalog (domyślnie '.')
  -R, --resolutions     Wyświetl dostępne rozdzielczości (dla filmu)
  -r, --resolution RES  Pobierz film w podanej rozdzielczości (domyślnie
                        'najlepsza')
  -o, --overwrite       Nadpisz pliki, jeśli istnieją
  -t, --threads N       Ustaw liczbę wątków (domyślnie 3)
```

## Licencja

Licencjonowany pod [MIT License](./LICENSE).

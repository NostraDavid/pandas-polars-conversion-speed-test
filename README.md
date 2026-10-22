# Pandas <-> Polars Conversion Speed Test

I want to know if pandas 3 is faster than pandas 2, when converting between
pandas and polars DataFrames.

De benchmarkimplementatie staat één keer in `benchmark/`. De mappen `p2p/` en
`p3p/` leveren afzonderlijke uv-omgevingen met respectievelijk pandas 2 en
pandas 3; beide roepen exact dezelfde gedeelde code aan.

Installeer Nix, devenv en direnv. Laad de Python 3.14-omgeving met:

```bash
direnv allow
just sync
just benchmark
just benchmark-with 100000 5 1 42
just benchmark-p2p
just benchmark-p3p
just compare
just compare-with 100000 5 1 42
just check
```

Iedere run meet de volledige gemengde dataset en twee gecontroleerde
pandas→Polars-scenario's:

- zonder `category`, met `nan_to_null=False`;
- alleen `id`, `value` en `active`, met `nan_to_null=False`.

`just compare` draait beide pandas-omgevingen in afzonderlijke processen en
rapporteert per conversie de mediane tijd, absolute delta, speedupfactor,
tijdsreductie en theoretische throughputwinst van pandas 3 ten opzichte van
pandas 2.

`just update` vernieuwt beide Python-locks en de Nix-omgeving. Pandas blijft in
`p2p` binnen versie 2 en in `p3p` binnen versie 3. Gewone runs gebruiken de
vastgelegde locks. De Nix-omgeving levert ook de native C++- en zlib-libraries.

Gebruik `just check` voor een kleine functionele controle. De korte runs dienen
om de conversies en gegevenscontroles te verifiëren. Ze onderbouwen geen algemene
uitspraak over welke pandas-versie sneller is.

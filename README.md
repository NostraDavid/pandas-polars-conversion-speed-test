# Pandas <-> Polars Conversion Speed Test

I want to know if pandas 3 is faster than pandas 2, when converting between
pandas and polars DataFrames.

De benchmarkimplementatie staat één keer in `benchmark/`. De mappen `p2p/` en
`p3p/` leveren afzonderlijke uv-omgevingen met respectievelijk pandas 2 en
pandas 3; beide roepen exact dezelfde gedeelde code aan.

```bash
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

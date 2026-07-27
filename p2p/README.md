# Gedeelde pandas ↔ Polars benchmark

De gedeelde benchmark genereert reproduceerbare random data, bouwt daarmee een pandas
`DataFrame` met expliciete dtypes en meet vervolgens vier conversiepaden:

- pandas → Polars `DataFrame`;
- pandas → Polars `LazyFrame`;
- Polars `DataFrame` → pandas;
- Polars `LazyFrame` → pandas.

De dataset bevat integers, nullable integers, floats, booleans, nullable
booleans, strings, categorische waarden, timestamps en timedeltas. Het genereren
van de data en het voorbereiden van de Polars-bronframes vallen buiten de
gemeten tijd. Na afloop worden in beide richtingen de shape en het aantal
null-waarden gecontroleerd.

## Uitvoeren

Voer alle commando's uit vanuit de root van het project.

Installeer of synchroniseer beide omgevingen:

```bash
just sync
```

Start dezelfde benchmark met pandas 2 en pandas 3:

```bash
just benchmark
```

Gebruik voor een andere datasetgrootte of meetconfiguratie:

```bash
just benchmark-with 100000 5 1 42
```

Alleen een specifieke pandas-versie draaien kan met:

```bash
just benchmark-p2p
just benchmark-p3p
just compare
```

Voer de korte compile- en end-to-endcontrole uit met:

```bash
just check
```

De standaardinstellingen zijn 10.000.000 rijen, zeven metingen, twee warmups en
seed 42. Per doel worden mediaan, minimum en maximum gerapporteerd.

## DataFrame versus LazyFrame

`pl.from_pandas(...)` converteert een pandas `DataFrame` altijd direct naar een
Polars `DataFrame`. Er bestaat voor een reeds in het geheugen aanwezige pandas
`DataFrame` geen lazy reader. De LazyFrame-meting meet daarom:

```python
pl.from_pandas(pandas_df).lazy()
```

Die meting omvat dus de eager conversie plus het maken van het lazy queryplan.

Voor de omgekeerde richting kan een `LazyFrame` niet rechtstreeks naar pandas.
De twee terugconversies zijn daarom:

```python
polars_df.to_pandas(use_pyarrow_extension_array=True)
polars_lf.collect().to_pandas(use_pyarrow_extension_array=True)
```

Bij `Polars LazyFrame → pandas` valt `.collect()` dus bewust binnen de meting.
De pandas-uitvoer gebruikt Arrow-backed extension-dtypes om nullable en andere
rijke datatypes zo goed mogelijk te behouden.

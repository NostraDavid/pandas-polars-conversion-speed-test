# pandas 3 benchmarkomgeving

Deze omgeving voert dezelfde gedeelde benchmarkcode uit als `p2p`, maar met
pandas 3. Gebruik de `just`-commando's vanuit de root van het project:

```bash
just sync
just benchmark-p3p
just benchmark-with 100000 5 1 42
just compare
just check
```

default:
    @just --list

# Synchroniseer beide benchmarkomgevingen.
sync:
    just sync-p2p
    just sync-p3p

# Synchroniseer de pandas 2-omgeving.
sync-p2p:
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv sync

# Synchroniseer de pandas 3-omgeving.
sync-p3p:
    cd p3p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv sync

# Draai dezelfde benchmark met pandas 2 en pandas 3.
benchmark:
    just benchmark-p2p
    just benchmark-p3p

# Draai de benchmark met pandas 2.
benchmark-p2p:
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run p2p

# Draai de benchmark met pandas 3.
benchmark-p3p:
    cd p3p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run p3p

# Draai beide benchmarks met dezelfde configuratie.
benchmark-with rows="10000000" repeats="7" warmups="2" seed="42":
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run p2p --rows {{rows}} --repeats {{repeats}} --warmups {{warmups}} --seed {{seed}}
    cd p3p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run p3p --rows {{rows}} --repeats {{repeats}} --warmups {{warmups}} --seed {{seed}}

# Vergelijk pandas 2 en pandas 3 en bereken speedups.
compare:
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run python -m conversion_benchmark.compare

# Vergelijk beide pandas-versies met dezelfde configuratie.
compare-with rows="10000000" repeats="7" warmups="2" seed="42":
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run python -m conversion_benchmark.compare --rows {{rows}} --repeats {{repeats}} --warmups {{warmups}} --seed {{seed}}

# Draai de korte controles met beide pandas-versies.
check:
    cd p2p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run python -m compileall -q ../benchmark/src src
    cd p3p && env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV uv run python -m compileall -q ../benchmark/src src
    just compare-with 10000 3 1 42

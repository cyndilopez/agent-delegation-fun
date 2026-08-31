# Casino

Blackjack simulator used as demo/test data in this repo. Not part of the GitHub agent layer.

## Run

```bash
python -m casino.simulate
```

Simulates 100 rounds by default and writes results to `outcomes.jsonl`.

## Layout

| Module | Purpose |
|---|---|
| `cards.py` | Card representation |
| `hand.py` | Hand value, bust, blackjack, soft/hard detection |
| `strategies.py` | Player and dealer hit/stand strategies |
| `table.py` | Round logic |
| `monitor.py` | Records outcomes |
| `simulate.py` | CLI entrypoint |

## Tests

```bash
pytest tests/test_hand.py
```

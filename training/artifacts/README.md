# Trained link-finder artifacts

One folder per training run, written by `uv run python -m training.train`
(ADR-0125, ADR-0126). Only `ripple_artifact.json` is tracked; the weights
(`model.safetensors`, about 600 MB for ModernBERT-base) and tokenizer files are
ignored and are rebuilt by re-running the command recorded in the manifest's
`train_config` (deterministic for a seed on one machine, ADR-0126 point 6).

| Folder | Command |
|---|---|
| `modernbert-base_seed20261031` | `uv run python -m training.train --validation-persona p2_harsh --seed 20261031` |
| `modernbert-base_seed20261032` | `uv run python -m training.train --validation-persona p2_harsh --seed 20261032` |
| `modernbert-base_seed20261033` | `uv run python -m training.train --validation-persona p2_harsh --seed 20261033` |

Serve one: `RIPPLE_LINKER=trained RIPPLE_TRAINED_LINKER_MODEL=training/artifacts/<folder>`
once the API wiring calls `ripple.linking.trained.select_linker` (ADR-0128). Score one:
`uv run python -m training.evaluate --linker trained --model training/artifacts/<folder>`.

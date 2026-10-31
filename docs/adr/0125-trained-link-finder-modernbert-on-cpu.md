# ADR-0125: The trained link finder fine-tunes ModernBERT-base on CPU; torch and transformers in a `linkfinder` group
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-19)
Builds on ADR-0009 (a small encoder pair classifier) and ADR-0094 (the training
interface). The author asked on 2026-10-31 for the [human] training loop to be
implemented by the collaborator.

## Context
ADR-0009 names ModernBERT or DeBERTa-v3 as the encoder. Nothing in the project could
load either: no model library was a dependency. The machine that trains and serves the
model has no GPU, so the choice must download and fine-tune on CPU in minutes, and add
as little as possible to the dependency tree. Checked on this machine on 2026-10-31:
- `answerdotai/ModernBERT-base` (149.6M parameters) downloads as safetensors with a
  `tokenizer.json`, so torch + transformers load it with nothing else. A forward and
  backward pass over one batch of short pairs took seconds on this CPU, fast enough to
  fine-tune on the jobs train split in minutes (measured times are in the artifacts).
- `microsoft/deberta-v3-small` ships only `spm.model` and a pickled
  `pytorch_model.bin`; transformers 5.22.1 refused to build its tokenizer without
  `sentencepiece` or `tiktoken` (the fallback), two dependencies more.

## Decision
1. Base model: `answerdotai/ModernBERT-base`, fine-tuned end to end with a linear head
   over the label space (ADR-0126 has the recipe). The hub commit hash the run loaded
   is recorded in the artifact.
2. Dependencies, exact pins, in a new dependency group `linkfinder`, which
   `[tool.uv] default-groups` installs with `dev` on `uv sync`:
   `torch==2.15.0` (from the PyTorch CPU index, `explicit = true`, on every platform:
   the PyPI Linux wheel pulls CUDA), `transformers==5.22.1`, and `tokenizers==0.23.3`
   (a transformers dependency, declared because the offline test model imports it
   directly, ADR-0126 point 10). Other transitive dependencies (safetensors,
   huggingface-hub, numpy, ...) come from the lock and are not imported.
3. `ripple.linking.trained` imports torch and transformers inside the functions that
   need them, so the API and worker import nothing heavy unless the trained linker is
   selected (ADR-0128).
4. The production image (`uv sync --no-dev`) still installs the `linkfinder` group,
   because `--no-dev` drops only `dev`. Whether the image should carry it is the
   coordinator's call (handover request: add `--no-group linkfinder` to
   infra/Dockerfile while the LLM linker is the default).

## Alternatives considered
- DeBERTa-v3-small (ADR-0009's other option) — about a third of ModernBERT-base's
  compute per token, but needs sentencepiece or tiktoken on top; lost on the
  "only what they strictly need" rule. Worth revisiting if CPU training time becomes the
  bottleneck.
- A frozen encoder with a trained head, or a dependency-free model (logistic
  regression on hand features) — cheaper, but not what ADR-0009 decided, and the
  fine-tune works here; kept as fallbacks, not taken.
- Main `[project] dependencies` — every install, the container included, would pull
  torch even though serving does not need it by default; lost.
- An optional extra (`ripple[linkfinder]`) — `uv sync` and CI would skip it, so the
  training tests would never run; lost.

## Consequences
- `uv sync` downloads about 200 MB of CPU torch wheels. The first training run downloads
  the base model (about 600 MB) into the Hugging Face cache; unit tests download nothing.
- Fine-tuning ModernBERT-base on the jobs v0 train split takes minutes per seed on this
  CPU (times are recorded in each artifact manifest).

## Revisit if
GPU training becomes available, a larger pair set makes CPU fine-tuning too slow, or the
trained linker becomes the default (then the image must carry the group).

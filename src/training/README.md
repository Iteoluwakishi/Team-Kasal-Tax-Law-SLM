# Team Kasai — Training Environment

Reproducible GPU environment for fine-tuning Gemma 3 4B Instruct on the Kasai
Nigerian tax law SFT dataset. This is Step 2 of the project plan — environment
only. Training code itself lives elsewhere under `training/` (see repo root
README for the full folder layout).

## Primary platform

Google Colab, GPU runtime. Stack: Python → PyTorch → Transformers → TRL → PEFT
→ bitsandbytes.

## Setup

1. Open `training/setup.ipynb` in Google Colab (upload it, or open directly
   from GitHub via Colab's "Open notebook → GitHub" if the repo is public/you're
   authenticated).
2. **Runtime → Change runtime type → GPU** (T4 is enough for a 4B model in
   4-bit; use a bigger GPU if Colab offers one and you have compute units).
3. Run every cell top to bottom. The last cell writes
   `training/environment_report.md` and loads Gemma 3 4B Instruct as a smoke
   test to confirm the whole stack works before anyone writes real training
   code against it.
4. Copy the values from `environment_report.md` into the table below and
   commit both files — this table is what makes a teammate's "it doesn't work
   on my machine" debuggable against a known-good baseline.

## Recorded environment

*(Fill in after running `setup.ipynb` once — these are placeholders, not
guesses, until someone on the team actually runs it and records the real
values.)*

| Field | Value |
|---|---|
| GPU type | <!-- e.g. Tesla T4 --> |
| VRAM | <!-- e.g. 15360 MiB --> |
| Python version | <!-- e.g. 3.11.x --> |
| PyTorch version | <!-- e.g. 2.4.x --> |
| Transformers version | <!-- e.g. 4.5x.x --> |
| TRL version | <!-- e.g. 0.1x.x --> |
| PEFT version | <!-- e.g. 0.1x.x --> |
| bitsandbytes version | <!-- e.g. 0.4x.x --> |
| Date recorded | <!-- date this was actually run --> |

## Why versions are pinned with lower bounds, not exact pins

`requirements.txt` uses `>=` rather than `==` for now, because **Transformers
4.50.0 is the minimum version that recognizes the `gemma3` architecture at
all** — anything older fails to load the model outright with a "model type
`gemma3` not recognized" error. Once the team has a known-working combination
recorded in the table above, consider switching to exact `==` pins so a
future `pip install --upgrade` from anyone on the team can't silently break
training with an incompatible newer release.

## If you hit a "model type not recognized" error

That almost always means `transformers` is below 4.50.0. Run:
```
pip install --upgrade transformers
```
then re-run the import cell in `setup.ipynb`. This exact failure mode is
common enough with Gemma 3 (a fairly recent model generation) that it's
worth checking first before assuming anything else is wrong.

## Local (non-Colab) setup

If a teammate wants to run this locally instead of in Colab:
```bash
cd training
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook setup.ipynb
```
A local GPU with at least ~8GB VRAM should handle the 4-bit Gemma 3 4B smoke
test; less than that, stick to Colab.

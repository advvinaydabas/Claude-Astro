# Six-culture chart engine

Parameterized builder for the `six-culture-verified-chart` skill (`.claude/skills/six-culture-verified-chart/SKILL.md`).
It reads a `BIRTH_INPUT.json`, computes facts only, verifies them, and then a separate synthesis step projects them
through a predeclared mapping registry. No personal data is hard-coded.

## Setup (Python 3.12 + Node 22)

```sh
cd engine
uv venv -p python3.12 .venv && uv pip install -p .venv/bin/python -r requirements.lock
npm ci                      # canonical iztro
mkdir -p ephe && cd ephe
for f in sepl_18.se1 semo_18.se1 seas_18.se1; do curl -LO https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/$f; done
curl -LO https://raw.githubusercontent.com/skyfielders/python-skyfield/master/ci/de421.bsp   # or DE440 from JPL/NAIF
```

## Run

```sh
.venv/bin/python build.py path/to/BIRTH_INPUT.json      # INPUT_AUDIT, MANIFEST, MASTER_DATASET, VERIFICATION_REPORT
.venv/bin/python synth.py path/to/MASTER_DATASET.json   # MAPPING_REGISTRY, SYNTHESIS, FINAL_READING
```

Outputs are written next to the input file. `charts/` is git-ignored so birth data stays local.

## Layout

| File | Role |
|---|---|
| `sixc/astro.py` | civil-time audit, Swiss Ephemeris primary, Skyfield/JPL validator, boundary search |
| `sixc/jyotisha.py` | sidereal D1/D9/D10, dignity, FN-1 functional natures, Y-1 yoga whitelist, Vimshottari |
| `sixc/bazi.py` | pillars (lunar_python), hidden stems, Ten Gods, WEC-1 strength, interactions, Da Yun |
| `sixc/western.py` | tropical whole-sign, Egyptian bounds, Dorothean triplicity, faces, Lots, profections |
| `sixc/calendars.py` | Maya (own arithmetic + convertdate), Tibetan element-animal, Zi Wei (iztro + py-iztro check) |
| `js/ziwei.mjs` | canonical iztro runner |
| `synth.py` | mapping registry MR-1, cluster voting, temperament, chronology windows |
| `sixc/render.py`, `sixc/reading.py` | Markdown renderers |

# us-grad-program-db

A structured, source-traceable database of application requirements for US graduate programs. Version 1 covers roughly 100 master's programs in data science, statistics, and business analytics. Every value is tied to a primary source (a university page or a federal dataset) and reviewed by a person before release. Phase 1 builds the reference-data layer: the DHS STEM Designated Degree Program List, CIP 2020, IPEDS Completions, and College Scorecard Field of Study. It uses them to produce a list of candidate institution × CIP pairs.

## Running

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # install dependencies
uv run pytest           # run the test suite (offline, fixtures only)
```

Environment variables (never commit these):

- `GRADPROG_CONTACT_EMAIL`: contact address sent in the downloader's User-Agent
- `SCORECARD_API_KEY`: optional; the College Scorecard API is used only as a supplement to the bulk files

See `docs/spec/` for the design and data rules. Raw downloads go to `data/raw/` (git-ignored). Provenance for every file is in `data/manifest/`.

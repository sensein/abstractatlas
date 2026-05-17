# CLLM Claims Plan

## Goal

Add a resumable `cllm`-based claim extraction pass for every abstract and expose
the results in the static UI detail panel without making the right-hand reading
experience overwhelming.

## Decisions

- [x] Keep claim extraction as its own cache file: `data/claim_analyses_cllm.json`
- [x] Default the `cllm` integration to `LLM_PROVIDER=openai` so the existing repo
  `.env` works without adding Anthropic credentials
- [x] Fall back to `gpt-4o-2024-08-06` as the default OpenAI claim-extraction model
  while GPT-5-family behavior is investigated
- [x] Build the `cllm` manuscript from core abstract sections only, excluding
  references and acknowledgements
- [x] Include cached figure-analysis text in the `cllm` manuscript when local
  assets have already been analyzed
- [x] Merge cached claim output into `data/primary/abstracts_enriched.json`
- [x] Flow claim output into `abstracts.detail.json`
- [x] Render abstract sections, claims, figure notes, and references as collapsible
  blocks in the UI
- [x] Tighten reference spacing and font sizing for denser reading

## Execution

1. Run `ohbmcli analyze-figures` first if you want cached figure notes included in
   the claim manuscript.
2. Run `ohbmcli extract-claims` to populate or resume the claim cache.
3. Run `ohbmcli enrich` to merge claim extraction into the enriched abstract data.
4. Run `scripts/build_ui_data.py` (Stage 6) so the SvelteKit site's data package picks up the new fields. (The legacy `ohbmcli export-ui` / `build-ui` commands have been removed; this plan predates Stage 2.1 + Stage 6 and is kept for historical reference only.)

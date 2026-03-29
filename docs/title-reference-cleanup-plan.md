# Title And Reference Cleanup Plan

## Goals

- clean obviously malformed abstract titles for downstream UI/export use without mutating the original raw input
- write an audit artifact that records every title normalization against the original dataset
- improve reference resolution by discovering DOI candidates from external scholarly search APIs before querying OpenAlex for normalized metadata

## Title Cleanup

- add a shared title-normalization helper
- keep the raw source JSON untouched
- write `data/outputs/experiments/title_audit/title_modifications.json` with:
  - abstract id
  - original title
  - cleaned title
  - normalization reasons
- apply cleaned titles in places where titles are shown or passed downstream:
  - UI export
  - claim extraction prompts/cache titles
  - embedding/title lookup helpers

## Reference Resolution

- keep the existing exact-match stages:
  - DOI -> OpenAlex
  - PMID -> OpenAlex
- add a DOI-discovery stage for unmatched references with title guesses:
  - Semantic Scholar title search to look for `externalIds.DOI`
  - Crossref title/bibliographic search as a fallback DOI source
  - once a DOI is found, look up final metadata in OpenAlex
- keep OpenAlex title search as a later fallback when DOI discovery fails

## Guardrails

- avoid Google Scholar scraping because there is no stable official API for this workflow
- require title similarity checks before accepting external DOI candidates
- persist progress in the existing reference metadata cache so long runs remain resumable

## Verification

- add unit tests for title normalization and audit generation
- add unit tests for DOI discovery helpers and cache updates
- generate `data/outputs/experiments/title_audit/title_modifications.json`

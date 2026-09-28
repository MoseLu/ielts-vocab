# Submit Log — 2026-09-28 — ielts-vocab PRD refresh

- Repository: products/ielts-vocab
- Branch: dev
- Date: 2026-09-28
- Operator: routine products/workbench L1+ dirty submit executor (audit-pass)

## Scope

Fourth of five commits closing the remaining L1+ dirty on
`products/ielts-vocab` after the port-fix commit
`42260192 fix(ports): source TTS/ASR URLs from AXI_*_URL env with
safe fallback` landed. This commit adds the project PRD.

## Commit

- Subject: `docs: PRD refresh`
- Paths: `PRD.md`

### Diff stat

- 1 file created, 172 lines added (untracked)

### What changed

`PRD.md` (new file, 172 lines) is added. The PRD is the L2
project document for the IELTS Vocabulary product. Header
covers:

- 文档编号 PRD-IELTS-VOCAB, L2 project PRD
- Active (promoted AXI product)
- Owner: AxiomaticWorld solo owner (libu), created 2026-06-07,
  last updated 2026-09-25
- Product line: Axi Spun-out Product (axiomaticworld.com)
- Audience: maintainer / next agent / dev / prod ops / end user

Section 1 starts the定位, boundaries, and section 3 covers
用户与核心场景. The full doc lives under the
`products/ielts-vocab/PRD.md` file.

## Verification

- Tested: `git status --short` after the deps commit shows
  only `?? PRD.md`.
- Tested: `wc -l PRD.md` → 172 lines, plain Markdown.
- Tested: `.gitignore` does not exclude `PRD.md` (verified by
  grepping `PRD|prd` in `.gitignore` → no exclusion).
- Not-tested: `pnpm build` (no code change, doc-only).

## Risks

- Low. New PRD markdown only. No code, config, schema, or
  contract change.

## Directive

Owner-directed L1+ dirty closure on `products/ielts-vocab`
following the port-fix commit (`42260192`). Fourth of five
commits (proxy endpoint done, test done, deps done; PRD now;
HANDOFF pending). Satisfies the AR-BOOTSTRAP-002 minimum-files
rule for a promoted AXI product.

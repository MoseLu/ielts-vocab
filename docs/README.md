# Docs Architecture
Last updated: 2026-04-19 00:00:00 +08:00

This directory is the project's durable documentation layer.

Use it for materials that should stay useful across sessions, contributors, and future feature work. Do not drop ad-hoc notes into `docs/` without choosing the right domain folder first.

## Structure

```text
docs/
- README.md                        # This index and placement rules
- agents/                          # Child AGENTS/index docs when local guidance is needed
- architecture/
  - audits/                        # Architecture and risk audits
  - specs/                         # Technical design specs
- governance/                      # Product and UI governance logs
- milestones/                      # Cross-release milestones and completion snapshots
- operations/                      # Tooling, automation, and operator runbooks
- planning/
  - implementation/                # Concrete implementation plans
- todo/                            # Child TODO breakdowns when root TODO needs detail
- logs/
  - submit/                        # Append-only submit records
```

## Placement Rules

- Put long-lived technical decisions in `architecture/specs/`.
- Put child scope guidance under `agents/` only when root `AGENTS.md` would otherwise become noisy.
- Put structural or risk reviews in `architecture/audits/`.
- Put tooling setup and operational runbooks in `operations/`.
- Put product requirement baselines, phased feature plans, and rollout checklists in `planning/`.
- Put governance history and cross-cutting UI cleanup logs in `governance/`.
- Put cross-feature delivery checkpoints and release snapshots in `milestones/`.
- Put detailed child task breakdowns in `todo/` when a root TODO item needs its own checklist.
- Put append-only execution records in `logs/submit/`.

## Naming Rules

- Prefer lowercase kebab-case file names.
- Use a date prefix when chronology matters.
- Keep one topic per document.
- Split plan, spec, and execution history into separate files instead of one mixed note.

## Current Index

### Architecture

- [architecture-audit.md](./architecture/audits/architecture-audit.md)
- [2026-03-28-tts-batch-generation-design.md](./architecture/specs/2026-03-28-tts-batch-generation-design.md)
- [architecture-spec-template.md](./architecture/specs/templates/architecture-spec-template.md)

### Governance

- [ui-governance-log.md](./governance/ui-governance-log.md)

### Milestones

- [README.md](./milestones/README.md)
- [2026-q1-platform-foundation.md](./milestones/2026-q1-platform-foundation.md)
- [milestone-template.md](./milestones/templates/milestone-template.md)

### Operations

- [agent-browser-guide.md](./operations/agent-browser-guide.md)
- [release-closeout-checklist.md](./operations/release-closeout-checklist.md)
- [frontend-automation-setup.md](./operations/frontend-automation-setup.md)

### Planning

- [product-requirements-document.md](./planning/product-requirements-document.md)
- [ui-redesign-plan.md](./planning/ui-redesign-plan.md)
- [2026-03-28-tts-batch-generation-plan.md](./planning/implementation/2026-03-28-tts-batch-generation-plan.md)
- [implementation-plan-template.md](./planning/implementation/templates/implementation-plan-template.md)

### Logs

- [20260331-084123-batch-submit.md](./logs/submit/20260331-084123-batch-submit.md)

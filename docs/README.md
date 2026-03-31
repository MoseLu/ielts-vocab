# Docs Architecture

This directory is the project's durable documentation layer.

Use it for materials that should stay useful across sessions, contributors, and future feature work. Do not drop ad-hoc notes into `docs/` without choosing the right domain folder first.

## Structure

```text
docs/
- README.md                        # This index and placement rules
- architecture/
  - audits/                        # Architecture and risk audits
  - specs/                         # Technical design specs
- governance/                      # Product and UI governance logs
- milestones/                      # Cross-release milestones and completion snapshots
- operations/                      # Tooling, automation, and operator runbooks
- planning/
  - implementation/                # Concrete implementation plans
- logs/
  - submit/                        # Append-only submit records
```

## Placement Rules

- Put long-lived technical decisions in `architecture/specs/`.
- Put structural or risk reviews in `architecture/audits/`.
- Put tooling setup and operational runbooks in `operations/`.
- Put phased feature plans and rollout checklists in `planning/`.
- Put governance history and cross-cutting UI cleanup logs in `governance/`.
- Put cross-feature delivery checkpoints and release snapshots in `milestones/`.
- Put append-only execution records in `logs/submit/`.

## Naming Rules

- Prefer lowercase kebab-case file names.
- Use a date prefix when chronology matters.
- Keep one topic per document.
- Split plan, spec, and execution history into separate files instead of one mixed note.

## Current Index

### Architecture

- [architecture-audit.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/audits/architecture-audit.md)
- [2026-03-28-tts-batch-generation-design.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/specs/2026-03-28-tts-batch-generation-design.md)
- [architecture-spec-template.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/specs/templates/architecture-spec-template.md)

### Governance

- [ui-governance-log.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/governance/ui-governance-log.md)

### Milestones

- [README.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/milestones/README.md)
- [2026-q1-platform-foundation.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/milestones/2026-q1-platform-foundation.md)
- [milestone-template.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/milestones/templates/milestone-template.md)

### Operations

- [agent-browser-guide.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/agent-browser-guide.md)
- [frontend-automation-setup.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/operations/frontend-automation-setup.md)

### Planning

- [ui-redesign-plan.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/planning/ui-redesign-plan.md)
- [2026-03-28-tts-batch-generation-plan.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/planning/implementation/2026-03-28-tts-batch-generation-plan.md)
- [implementation-plan-template.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/planning/implementation/templates/implementation-plan-template.md)

### Logs

- [20260331-084123-batch-submit.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/logs/submit/20260331-084123-batch-submit.md)

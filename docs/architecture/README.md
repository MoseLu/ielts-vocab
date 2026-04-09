# Architecture Docs

Use this folder for documents that describe the system structure itself.

## Subfolders

- `audits/`: structural risk reviews, technical debt reviews, and architecture assessments
- `specs/`: technical design documents for implemented or planned systems
- `specs/templates/`: reusable architecture-spec templates

## Rules

- Put one technical topic per spec.
- Keep plans out of this folder; execution plans belong in `docs/planning/`.
- Update the relevant spec when an implementation changes the design materially.
- Start new specs from `specs/templates/architecture-spec-template.md`.

## Current Specs

- `backend-layered-architecture.md`: backend layer map, capability modules, data flow, and dependency rules.
- `service-ownership-matrix.md`: first-pass authoritative write ownership and service decomposition matrix.
- `gateway-service-contracts.md`: gateway-to-service contract skeleton for the first extraction wave.

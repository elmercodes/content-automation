# ADR 006: Carousel Support As A First-Class Concept

- Status: Accepted
- Date: 2026-04-15

## Decision

Treat multi-image carousel posting as a first-class workflow built on ordered
media items, not as an afterthought layered on top of single-media posting.

## Rationale

- Carousel support is an explicit product requirement.
- Ordered media affects validation, storage, preview generation, and posting.
- Treating carousel behavior as primary reduces later schema and workflow churn.

## Alternatives Not Chosen

- Single-image-only model with later carousel hacks
- Unordered media attachments that rely on implicit ordering

## Consequences

- Media item ordering must be durable in persistence and workflow logic.
- Validation rules should reason about single-media and carousel cases
  explicitly.
- Later posting adapters should receive an ordered media set when the platform
  supports carousel posts.

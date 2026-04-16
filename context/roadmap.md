# Roadmap

This roadmap explains why the project phases are ordered the way they are. For
current status, use [`implementation.md`](implementation.md).

## Delivery Sequence

1. Foundation and environment: establish the local run flow, tooling, storage
   layout, and a smoke app.
2. AI-agent docs system: build the durable documentation layer before major
   implementation work.
3. Core app skeleton and config: create the real app shell and settings-driven
   page flow.
4. Database and migrations: add the first real models and migration history.
5. Compose form and upload pipeline: capture master post content and local media
   intake.
6. Platform selection flow: show only configured platforms and store user
   choices.
7. Preview engine and image normalization: prepare media for platform-aware
   preview and validation.
8. Carousel support: make ordered multi-image posting fully durable.
9. Platform adapters and posting: connect provider-specific submission logic.
10. Results and post history: expose local outcome tracking and history.
11. Testing, polish, and shareability: harden the app, docs, and packaging.

## Guiding Principles

- Build local-first foundations before provider integrations.
- Lock documentation and architectural direction before feature growth.
- Prefer small durable layers over broad partially-built systems.

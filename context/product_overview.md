# Product Overview

This application is a local-first social media publisher. It helps a user
prepare a master post, attach one or more media items, choose from locally
configured platforms, validate platform constraints, and submit safely while
keeping a lightweight local history.

## Product Goals

- Keep the entire workflow on the user's machine.
- Support both single-media posts and multi-image carousel posts.
- Show only platforms that are configured locally.
- Validate media and posting constraints before submission.
- Record enough local history to understand what was posted and what happened.

## Supported Outcomes

- Draft a master post that can be reused across one or more platforms.
- Attach ordered media items to that master post.
- Submit the same master post to multiple configured platforms.
- Review lightweight local posting outcomes later.

## Canonical Terms

- `master post`: the core post record for a single publishing intent
- `media item`: an ordered asset attached to a master post
- `post platform log`: a per-platform record of submission intent or outcome
- `local-only`: all execution, media, and persistence stay on the local machine
- `server-rendered workflow`: HTML pages are rendered by the backend and
  navigated with normal browser requests

## Non-Goals

- Hosted multi-user collaboration
- Background scheduling or queue infrastructure
- A JavaScript frontend or SPA shell
- Deep analytics, reporting, or campaign management
- Cloud media storage or remote control planes

## Related Docs

- See [`architecture.md`](architecture.md) for system boundaries.
- See [`database.md`](database.md) for the conceptual record model.
- See [`posting_workflow.md`](posting_workflow.md) for the intended publishing
  sequence.

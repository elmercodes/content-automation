# ADR 008: Synchronous Adapter Submission and Normalized Results

- Status: Accepted
- Date: 2026-04-17

## Decision

Add a small backend-owned posting adapter contract, keep submission synchronous
inside `POST /review/final`, and normalize every selected-platform attempt into
one `post_platform_logs` row with explicit outcome statuses.

## Rationale

- The app needs real provider submission without introducing workers,
  scheduling, or a second execution system.
- Per-platform failures must be isolated so one provider error does not erase
  earlier outcomes in the same request.
- Later results and history views need stable, compact outcome data that is not
  tied to raw provider payload shapes.

## Alternatives Not Chosen

- Background jobs, queues, or worker processes for submission
- Provider-specific persistence tables or a submission-batch table in Phase 9
- Letting provider exceptions bubble through the whole request and abort the
  batch

## Consequences

- Final-review submission remains easy to reason about in the current local-only
  architecture.
- One platform can succeed while another records `unsupported`,
  `validation_failed`, or `submission_failed` without losing the earlier log.
- Phase 10 can build richer results and history views on top of normalized
  post platform logs without redesigning the submission path.

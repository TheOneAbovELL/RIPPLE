# ADR-0015: Every change is a memory write; temporary facts self-expire
Status: Accepted · Date: 2026-10-19 (approved by the author the same day)

## Context
The data model had no entity for the trigger of a ripple, no place to store that a
change is temporary (FR-5), and ChangeEvent required a trigger_memory_id that user
edits, answers and expiry did not have, which made I2 untestable for those paths.
Points 1 and 2 were decided with the author in the kickoff interview. Points 3 and 4
are the collaborator's recommended option, taken because the author asked to start
building before interview question 5 was answered; they are explicitly open to reversal.

## Decision
1. The trigger of every ripple is a memory write: a new memory, a new version (including
   one created_by user from the inspector), or the expiry of a memory.
2. A temporary fact is an ordinary memory with valid_to, filled by the change detector.
   The nightly sweep retires memories whose valid_to has passed and ripples that expiry
   deterministically; no LLM is needed to detect expiry.
3. ChangeEvent keeps trigger_memory_id and gains trigger_kind
   (ripple | expiry | user_edit | user_answer); one per ripple, appended per wave
   (ADR-0013). A user answer that changes a memory is a new write and starts a new
   ripple. Forget is a deletion, logged as a ForgetEvent, not a state change; creation
   is recorded by the memory row itself, so neither needs a ChangeEvent.
4. Retrieval treats PENDING_USER like SUSPECT: returned only with a flag (I1).

## Alternatives considered
- A separate ChangeRequest entity with a permanence class — clearer audit trail, but a
  second entity to keep consistent with memories, and expiry still needs valid_to.
- Polymorphic ChangeEvent.trigger (memory | sweep | user action | forget) — fully
  general, but polymorphic references are hard to query and to keep consistent.
- Classifying temporary changes only in the detector, without valid_to — leaves the
  system unable to undo the temporary effect when it ends.

## Consequences
- FR-5's acceptance test becomes a FakeClock scenario: ripple in, expire, ripple out.
- One invariant test per trigger kind for I2.
- The sweep needs an index on valid_to.

## Revisit if
The author answers question 5 differently (then supersede points 3 and 4), or expiry
ripples prove noisy because the detector fills valid_to badly.

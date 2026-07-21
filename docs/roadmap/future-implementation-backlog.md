# SanityCloud Future Implementation Backlog

## Planning authority

This document records product concepts that have been accepted for planned development but are not yet authorized for production deployment. Entries remain subject to feasibility testing, security review, dependency readiness, and explicit implementation sequencing.

---

## SC-RING — Personal Logitech Action Ring and Context Layer

**Status:** Approved for planned development and future implementation  
**Lifecycle:** Product discovery → feasibility probe → personal MVP → guarded integrations → personal optimization  
**Initial deployment:** Founder/personal use only  
**Commercialization:** Deferred until the personal workflow is stable, auditable, and demonstrably useful  
**Source plan:** `docs/product/logitech-action-ring-personal-use-plan.md`

### Strategic purpose

Create a fast, context-aware hardware and software control surface for SanityCloud. A Logitech control opens or operates an action ring that converts the current selection, application, screenshot, clipboard state, or spoken refinement into an approved SanityCloud capability request.

The implementation must treat Logitech as an optional input adapter. The reusable product is the SanityCloud Context Layer, action contracts, guarded execution model, and radial interaction system.

### Planned notable capabilities

- Context-sensitive ring profiles for browsers, IDEs, terminals, email, Notion, the SanityCloud Portal, PowerPoint, and creative applications.
- Eight primary actions: Understand, RepoAI, Capture, Create, Take Action, Talk/Refine, Snip/Vision, and Status/Undo.
- A central Clarity action that recommends the most useful next operation.
- Smart Mode for reversible low-risk actions and Guided Mode for ranked, explainable choices.
- Voice refinement combined with the current selected or captured context.
- Screenshot-region analysis for interfaces, errors, forms, diagrams, and visual content.
- RepoAI task creation and continuation without duplicate submissions.
- Notion2API capture into tasks, findings, decisions, sources, ideas, and client records.
- NotebookLM source capture with provenance and source metadata.
- SanityCloud Portal status, workflow, cancellation, and stalled-loop controls.
- Creative workflow routing for slide decks, infographics, stories, songs, comics, audio, and video production.
- Observable task status, cancellation, error reporting, corrective action, and undo where feasible.
- Editable personal intent memory that does not retain sensitive selected content.
- Keyboard, software radial-menu, and Stream Deck compatibility through the same contracts.

### Required architectural alignment

The feature will extend, not replace, existing SanityCloud architecture. Internal API usage remains an approved architectural choice and may not be removed, restricted, or replaced without explicit user authorization.

The implementation must integrate with:

- the SanityCloud Context Layer and versioned `ContextEnvelope` contract;
- RepoAI task-health, retry, liability, loop-detection, and progress logging;
- Notion2API workflow and planning records;
- NotebookLM capture and knowledge-development workflows;
- SanityCloud Portal service and job-state controls;
- the Guarded Action proposal, review, authorization, execution, verification, and rollback model.

### Dependencies and implementation gates

1. **Hardware and SDK capability gate**
   - Identify the exact Logitech device and supported Options+ or Actions SDK interfaces.
   - Verify tap, hold, press, dial, ring-display, and haptic capabilities.
   - Confirm licensing, redistribution, and local plugin constraints.

2. **Context and privacy gate**
   - Implement least-context capture, visible capture indication, sensitive-data classification, and redaction.
   - Prohibit continuous background collection.

3. **Local trust gate**
   - Bind local services to loopback.
   - Authenticate adapters and clients with per-installation secrets and rotating session credentials.
   - Prevent replay through expiring, single-use authorization tokens.

4. **Read-only MVP gate**
   - Begin with analysis, explanation, drafting, capture previews, and status retrieval.
   - Do not permit autonomous send, publish, delete, purchase, submit, or unrestricted browser control.

5. **Guarded-write gate**
   - Require a structured `ActionProposal`, effect preview, risk tier, explicit confirmation, effect verification, and audit entry.
   - Require rollback or compensating-action documentation where true undo is unavailable.

6. **Operational reliability gate**
   - Integrate duplicate suppression, durable job identity, error surfacing, retry accounting, stalled-loop detection, cancellation, and unresolved-blocker reporting.

### Planned work packages

#### SC-RING-P0 — Capability probe and contracts

- Produce a verified Logitech hardware and SDK matrix.
- Emit available hardware events into a versioned local trigger contract.
- Prototype Windows active-application, window-title, clipboard, selected-text, and screenshot-region capture.
- Define and validate `ContextEnvelope` and `ActionProposal` schemas.
- Create a minimal software radial overlay.

**Exit condition:** One hardware or fallback trigger captures limited context, opens the ring, routes a read-only request, and records task-health events.

#### SC-RING-P1 — Personal read-only MVP

- Implement the initial eight-action ring.
- Connect Understand, RepoAI status/review, Notion preview, NotebookLM capture preview, Snip/Vision, and job status.
- Add Smart and Guided modes.
- Add software hotkey fallback.

**Exit condition:** The ring provides useful results across browser, code, and Notion contexts without requiring a separate chat window.

#### SC-RING-P2 — Dynamic profiles and workflow routing

- Add application and content classification.
- Add profile-specific action ordering.
- Add voice refinement and explicit personal preference memory.
- Add Portal job controls, cancellation, and stalled-loop reporting.
- Add creative action packs.

**Exit condition:** The ring reliably adapts to the active workflow and routes to the correct SanityCloud capability without duplicate requests.

#### SC-RING-P3 — Guarded personal actions

- Implement signed, expiring, single-use action approvals.
- Add field-level and destination-level previews.
- Add capability and destination allowlists.
- Add effect verification and undo or compensating actions.

**Exit condition:** Approved reversible actions can modify allowlisted personal workflows with a complete audit and task-health record.

#### SC-RING-P4 — Personal optimization and portability

- Tune ordering and macros through explicit user preferences.
- Add haptic and visual status language.
- Add profile export/import.
- Add Stream Deck and keyboard adapters against the same contracts.
- Measure time saved, failure rate, cancellation rate, and repeated use.

**Exit condition:** The feature provides measurable recurring value and the core workflow is not dependent on Logitech hardware.

### Priority and sequencing

**Portfolio priority:** Medium-high strategic value; schedule after the shared Context Layer contracts and task-health interfaces are stable enough to prevent hardware-specific rework.

**Recommended sequencing:**

1. Register and preserve the concept in the product roadmap.
2. Complete SC-RING-P0 as a bounded research and prototype task.
3. Review feasibility, privacy, and SDK constraints.
4. Authorize or revise the personal MVP.
5. Delay consequential execution until Guarded Action infrastructure is operational.

### Measures of success

- Daily or weekly repeated personal use.
- Reduced context switching and fewer separate chat-window interactions.
- Correct capability routing without duplicate task creation.
- Low false-trigger and cancellation rates.
- Complete visibility into running, failed, stalled, cancelled, and completed work.
- No unauthorized consequential actions.
- No sensitive-context retention outside explicitly approved records.
- Hardware-independent reuse of the same contracts and workflows.

### Current decision

The Logitech Action Ring is now an accepted SanityCloud future-development initiative. It is not considered production-ready and must begin with the feasibility and contract work package. No existing provider, internal API, orchestration service, or workflow is authorized for replacement as part of this initiative.
# Logitech Action Ring Personal-Use Development Plan

## Objective

Develop a personal-use Logitech Action Ring integration that acts as a fast hardware front end to SanityCloud workflows. The ring should capture the current context, expose a small set of high-value actions, route work to the appropriate SanityCloud capability, and require explicit confirmation before consequential actions.

This should not duplicate the full MX-Cursivis stack. It should reuse the strongest interaction ideas while remaining hardware-optional, provider-agnostic, auditable, and compatible with existing SanityCloud services.

## Product concept

> **Selection = Context**  
> **Ring gesture = Intent**  
> **SanityCloud = Analysis, creation, organization, or guarded execution**

The Logitech Action Ring is one input adapter for a broader SanityCloud Context Layer. The same actions should later be available through a keyboard shortcut, software radial menu, Stream Deck, and other controllers.

## Initial personal-use ring layout

### Center action: Clarity

Analyze the current selection, screenshot, clipboard content, or active application and recommend the most useful next action.

### Primary ring actions

#### 1. Understand

- Explain selected text, code, error output, image, or interface.
- Summarize and extract key facts.
- Identify ambiguity, contradictions, and missing information.
- Offer Smart Mode and Guided Mode results.

#### 2. RepoAI

- Explain or diagnose selected code and errors.
- Identify the likely repository or project context.
- Create or continue a RepoAI review task.
- Open current review status, findings, or patch preview.
- Add the selected problem to the task-health ledger.

#### 3. Capture

- Save selected content to the appropriate Notion page or database.
- Convert content into a task, finding, decision, idea, source, or client note.
- Add a source to NotebookLM.
- Preserve source application, URL, timestamp, and context hash.

#### 4. Create

- Rewrite, expand, shorten, or structure selected content.
- Create a slide outline, infographic brief, story, song brief, comic concept, or social copy.
- Route creative work into existing SanityCloud and In-Scene workflows.

#### 5. Take Action

- Generate a structured action proposal.
- Preview the exact destination, fields, text, and effects.
- Require confirmation for sending, publishing, editing, deleting, submitting, or opening sensitive systems.
- Execute only through an allowlisted capability adapter.

#### 6. Talk / Refine

- Hold to speak a contextual instruction.
- Combine voice with the current selection or screenshot.
- Example: select an email, hold Talk, and say, “Make this direct but not hostile.”

#### 7. Snip / Vision

- Capture a screen region.
- Interpret UI state, charts, error dialogs, forms, or images.
- Support OCR, object detection, visual explanation, and context extraction.

#### 8. Status / Undo

- Show the most recent action and current job state.
- Cancel a running or stalled workflow.
- Undo the last reversible action.
- Open the activity and error ledger.

## Notable personal-use features

### Context-aware ring profiles

The visible actions should change according to the foreground application and selected content:

- **IDE or terminal:** Explain, Debug, RepoAI, Tests, Document.
- **Browser:** Summarize, Research, Capture, Take Action, Snip.
- **Gmail or messaging:** Draft Reply, Change Tone, Extract Tasks, Save Context, Send with confirmation.
- **Notion:** Capture, Link, Expand, Create Task, Send to NotebookLM.
- **SanityCloud Portal:** Service Status, Restart Service, Open Job, Cancel Loop, Run Workflow.
- **PowerPoint or creative tools:** Create Storyboard, Generate Assets, Add Audio, Export Video.

### Smart and Guided modes

- **Smart Mode:** one-tap recommendation for low-risk, reversible work.
- **Guided Mode:** the ring expands into ranked actions with confidence and a short effect description.
- Consequential actions always use Guided Mode and confirmation.

### Gesture model

- **Tap:** run the highlighted low-risk action.
- **Hold:** voice refinement.
- **Dial or wheel:** move among actions or options.
- **Dial press:** select.
- **Double press:** reopen the last result.
- **Long press on Take Action:** show plan preview rather than execute.
- **Haptic patterns:** success, confirmation required, warning, failure, and stalled job.

### Personal intent memory

Learn preferred actions by application and content type, but keep the memory visible and editable. Store only:

- application or profile
- content type
- chosen action
- usage count
- last-used time
- optional explicit preference

Do not store sensitive selected content in intent memory.

### Task-health integration

Every substantial action should produce observable events:

- objective
- captured context metadata
- proposed capability
- route selected
- approval state
- execution result
- errors and retries
- loop or stall detection
- unresolved blocker
- rollback or corrective action

This should integrate with the existing SanityCloud and RepoAI task-health ledger rather than create a parallel logging system.

## Proposed architecture

```text
Logitech Actions SDK / Options+
        |
        v
Logitech Ring Adapter
        |
        v
SanityCloud Context Capture Service
  - active application
  - selected text / clipboard
  - screenshot region
  - cursor position
  - voice command
        |
        v
Privacy and Context Gateway
  - sensitive-field detection
  - redaction
  - source provenance
  - project/client classification
        |
        v
Capability Router
  - RepoAI
  - Notion2API
  - NotebookLM
  - SanityCloud Portal
  - Creative tools
  - local utilities
        |
        v
Action Proposal + Risk Policy
        |
        v
Preview / Confirmation / Execution
        |
        v
Task-Health and Audit Ledger
```

## Suggested standalone repository structure

Once implementation begins, move the feature into a dedicated repository:

```text
sanitycloud-action-ring/
  src/
    adapters/logitech/
    capture/windows/
    context/
    routing/
    policy/
    ui/radial-overlay/
    integrations/repoai/
    integrations/notion2api/
    integrations/notebooklm/
    integrations/portal/
    telemetry/
  contracts/
  tests/
  docs/
```

Until that repository exists, this document is the planning source of truth.

## Development phases

### Phase 0 — Feasibility and hardware inventory

- Confirm the exact Logitech device and supported Actions SDK capabilities.
- Confirm available trigger types, dial events, ring UI customization, and haptics.
- Document local Options+ plugin requirements.
- Identify SDK redistribution or licensing constraints.

**Exit criterion:** a verified hardware/SDK capability matrix and one working trigger event.

### Phase 1 — Personal MVP: ring to local actions

- Implement the Logitech adapter.
- Create a local context service.
- Capture active application, clipboard, selected text where available, and screenshot regions.
- Implement a software fallback radial menu.
- Add fixed actions: Understand, RepoAI, Capture, Create, Talk, Snip, Status, Take Action.
- Route only to read-only or draft-producing operations.

**Exit criterion:** a ring gesture can analyze selected content and return a result without opening a separate chat window.

### Phase 2 — Context profiles and SanityCloud routing

- Detect application and content type.
- Add dynamic ring profiles.
- Connect RepoAI, Notion2API, NotebookLM, and portal-status actions.
- Add job polling, cancellation, and stalled-loop reporting.
- Implement editable personal intent memory.

**Exit criterion:** ring actions change appropriately between code, browser, email, Notion, and SanityCloud portal contexts.

### Phase 3 — Guarded action execution

- Define a versioned `ActionProposal` contract.
- Add risk tiers and capability allowlists.
- Add plan preview and confirmation UI.
- Add signed, single-use execution tokens.
- Add effect verification and undo where feasible.
- Prohibit autonomous send, publish, purchase, delete, or submission.

**Exit criterion:** approved actions can safely update allowlisted personal workflows with a complete audit record.

### Phase 4 — Personal optimization

- Tune ring ordering based on explicit preferences and usage.
- Add haptic patterns and job-state feedback.
- Add macros for common SanityCloud workflows.
- Add portable profile export/import.
- Evaluate Stream Deck and keyboard adapters using the same contracts.

**Exit criterion:** the ring reliably saves time in daily personal workflows and is no longer Logitech-dependent at the core architecture level.

## Initial technical contracts

### ContextEnvelope

```json
{
  "protocolVersion": "1.0.0",
  "requestId": "uuid",
  "source": {
    "application": "string",
    "windowTitle": "string",
    "url": "string-or-null"
  },
  "selection": {
    "kind": "text|image|text_image|none",
    "text": "string-or-null",
    "imageReference": "local-reference-or-null"
  },
  "voiceCommand": "string-or-null",
  "projectContext": "string-or-null",
  "privacyClass": "normal|sensitive|restricted",
  "timestampUtc": "date-time"
}
```

### ActionProposal

```json
{
  "proposalId": "uuid",
  "requestId": "uuid",
  "capability": "repoai|notion2api|notebooklm|portal|creative|local",
  "action": "string",
  "summary": "string",
  "riskTier": "read_only|draft|reversible_write|consequential",
  "requiresConfirmation": true,
  "expectedEffects": [],
  "rollbackPlan": "string-or-null",
  "expiresUtc": "date-time"
}
```

## Security and privacy requirements

- Bind local services to loopback only.
- Authenticate every local client and adapter.
- Use per-installation secrets and rotating session tokens.
- Redact secrets, tokens, passwords, financial data, and protected client information before model submission.
- Never collect full-page browser content when a smaller selection is available.
- Maintain domain and capability allowlists.
- Keep browser or application write permissions disabled until explicitly enabled.
- Record what context was captured and where it was sent.
- Preserve existing internal API architecture unless the user explicitly authorizes a change.

## MVP acceptance criteria

- [ ] Logitech control opens or controls the action ring.
- [ ] Ring works in at least browser, terminal or IDE, and Notion contexts.
- [ ] Selected text can be summarized, explained, or rewritten.
- [ ] A screenshot region can be analyzed.
- [ ] Voice can refine the current request.
- [ ] RepoAI action can create or continue a review task without duplicate submissions.
- [ ] Notion capture produces a preview before writing.
- [ ] NotebookLM capture preserves source metadata.
- [ ] Status action shows running, completed, failed, stalled, and cancelled jobs.
- [ ] No consequential action executes without confirmation.
- [ ] Every workflow writes observable task-health events.
- [ ] The same capability contracts can be invoked from a software radial menu without Logitech hardware.

## Non-goals for the first implementation

- General autonomous browser control.
- Academic answer-key or quiz autofill.
- Automatic sending or publishing.
- Background capture of all screen or browser content.
- Replacing the existing SanityCloud provider, API, or orchestration architecture.
- Multi-user commercial deployment before the personal workflow is stable.

## First development task

### SC-RING-P0 — Logitech SDK capability probe and ContextEnvelope prototype

Deliverables:

1. A small Logitech plugin or test action that emits tap, hold, dial, and press events supported by the available hardware.
2. A local listener that converts those events into a versioned trigger contract.
3. A Windows context probe that returns active application, window title, clipboard, and optional selected text.
4. A minimal radial overlay showing the eight proposed actions.
5. A task-health log recording every trigger, route, result, error, and cancellation.
6. An architecture decision record identifying which Cursivis concepts were adopted, rejected, or clean-room reimplemented.

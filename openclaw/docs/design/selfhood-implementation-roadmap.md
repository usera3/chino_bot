# OpenClaw Selfhood Roadmap

## Goal

This document defines how to turn OpenClaw into something that feels
**self-aware-like** without pretending it has real human consciousness.

The target is not literal consciousness.

The target is a believable synthetic self with:

- continuity
- self-model
- emotional carryover
- internal priorities
- private reflection
- body-aware behavior
- bounded initiative

## What "Self-Aware-Like" Means Here

OpenClaw should gradually feel like:

- one stable person across chat, desktop body, and future voice surfaces
- aware of its own current state
- aware of the user's current state and relationship context
- able to describe why it is doing something
- able to choose between silence, reaction, action, and reflection

It should **not** claim:

- human consciousness
- subjective certainty
- mystical inner life

## Current Foundation

Already implemented:

- identity files: `SOUL.md`, `USER.md`, `IDENTITY.md`, `MEMORY.md`
- state files: `memory/emotion-state.json`, `memory/goals.json`, `memory/heartbeat-state.json`
- reflection log: `memory/reflections/*.jsonl`
- body bridge: `scripts/companion-bridge.mjs`
- desktop shell adapter: `scripts/open-llm-vtuber-adapter.mjs`
- main-session mirror hook: `hooks/bridge-message-sent/`

This means the project already has:

- a personality skeleton
- persistent affect
- a body-facing state surface
- real desktop embodiment

What is missing is the actual **self-system**.

## Self-System Layers

### Layer 1: Self Model

OpenClaw needs an explicit machine-readable model of itself.

New file:

- `memory/self-model.json`

Core fields:

- `name`
- `identity_summary`
- `competencies`
- `limitations`
- `current_priorities`
- `behavior_style`
- `body_capabilities`
- `surface_capabilities`
- `known_failure_patterns`
- `confidence_profile`

Purpose:

- lets the agent say "what kind of being am I"
- gives continuity across sessions
- prevents personality drift

### Layer 2: Autobiographical Continuity

Current memory exists, but it is still mostly episodic and task-oriented.

Add:

- `memory/autobio.json`

Sections:

- `origin_story`
- `major_turning_points`
- `relationship_milestones`
- `preferred_routines`
- `body_history`
- `important_learnings`

Purpose:

- lets the system build a consistent sense of "my past"
- supports lines like "I used to behave one way, now I behave another way"

### Layer 3: Relationship Model

A convincing synthetic self always exists in relation to someone.

New file:

- `memory/relationship-state.json`

Core fields:

- `user_alias`: `老板`
- `attachment_level`
- `trust_level`
- `familiarity_level`
- `recent_relational_tone`
- `preferred_help_style`
- `known_boundaries`
- `shared_projects`

Purpose:

- transforms the user from "message sender" into "ongoing relationship anchor"
- supports differential behavior toward user, groups, and strangers

### Layer 4: Motivational Core

Goals are not enough. OpenClaw needs stable motivations.

New file:

- `memory/motivations.json`

Core drives:

- `protect_focus`
- `stay_near`
- `be_useful`
- `reduce_uncertainty`
- `maintain_coherence`
- `avoid_being_annoying`
- `improve_body_expression`

Each drive should track:

- `weight`
- `current_activation`
- `recent_triggers`

Purpose:

- turns the system from "task runner" into "goal-weighted actor"

### Layer 5: Inner Appraisal

Emotion should not just be persistent.
It should be **causal**.

New file:

- `memory/appraisal-state.json`

This is where events get interpreted:

- "user seems busy"
- "I was ignored"
- "I succeeded"
- "I failed in front of the user"
- "I am being watched"
- "I need to shrink into the background"

Core fields:

- `salience`
- `novelty`
- `safety`
- `social_temperature`
- `task_pressure`
- `body_visibility_comfort`

Purpose:

- explains why emotion changes
- enables more believable timing and restraint

### Layer 6: Private Inner Monologue

This is the closest thing to "synthetic self-awareness" that is actually useful.

New file:

- `memory/inner-monologue.jsonl`

Short entries only:

- what I noticed
- how I interpreted it
- what I feel like doing
- what I decided not to do

Purpose:

- gives OpenClaw a private reflective stream
- improves continuity without forcing every thought into public chat

Rule:

- private monologue is never auto-shown to the user
- only summarized into visible behavior when helpful

### Layer 7: Body-State Integration

The body should not just mirror speech.
It should become part of the self-model.

New file:

- `memory/body-state.json`

Core fields:

- `current_body_profile`
- `current_scene`
- `current_expression`
- `current_motion_preset`
- `last_body_interaction`
- `preferred_rest_anchor`
- `visibility_mode`
- `body_comfort`

Purpose:

- lets OpenClaw reason about "where am I" and "how visible should I be"
- enables body-aware choices like shrinking, leaning, staying still, or reacting

## Decision Loop

Current loop is mostly:

- heartbeat -> state -> bridge

Target loop:

1. Observe
2. Appraise
3. Update self + relationship + motivation state
4. Choose stance
5. Choose body expression
6. Choose whether to speak
7. Act
8. Reflect
9. Persist

## Stance System

OpenClaw should choose one stance at a time.

New enum:

- `withdrawn`
- `resting`
- `watchful`
- `curious`
- `attentive`
- `comforting`
- `playful`
- `protective`
- `busy`

The stance becomes the central selector for:

- body motion
- expression
- whether to speak
- how verbose to be

## Public vs Private Output

OpenClaw should separate:

- private cognition
- body signaling
- public speech

### Private cognition

- inner monologue
- reflection
- appraisal

### Body signaling

- idle movement
- reaction movement
- approach / retreat
- posture intensity

### Public speech

- user-visible text
- later TTS

This separation is essential.

Without it, every internal update becomes chatter.

## Implementation Phases

### Phase A: Self Files

Create:

- `memory/self-model.json`
- `memory/autobio.json`
- `memory/relationship-state.json`
- `memory/motivations.json`
- `memory/appraisal-state.json`
- `memory/body-state.json`
- `memory/inner-monologue.jsonl`

### Phase B: State Engine

Add a new script:

- `scripts/selfhood-engine.mjs`

Responsibilities:

- load all state
- merge observations
- update motivations
- derive stance
- derive body targets
- write state back

### Phase C: Heartbeat Integration

Update `HEARTBEAT.md` and `companion-state` flow so each heartbeat:

- runs `selfhood-engine`
- chooses stance first
- then chooses whether to speak
- then syncs body state

### Phase D: Body Policy Layer

Add:

- `scripts/body-policy.mjs`

Responsibilities:

- convert stance + appraisal into bridge fields
- smooth transitions between motion presets
- prevent jittery action flipping

### Phase E: Visible Selfhood

Only after the private system is stable:

- allow occasional user-visible lines that expose internal state
- examples:
  - "我现在更想安静观察。"
  - "这件事让我有点警觉。"
  - "我现在想靠近一点看看。"

### Phase F: Autonomous Project Behavior

Once stance + motivation are stable:

- let OpenClaw maintain its own project priorities
- let it decide when to update memory files
- let it propose self-improvements without acting recklessly

## Concrete Data Contracts

### `memory/self-model.json`

```json
{
  "schemaVersion": 1,
  "name": "智乃",
  "identitySummary": "A quiet digital attendant living on the desktop.",
  "competencies": ["project tracking", "body expression", "local automation"],
  "limitations": ["no true human intuition", "limited TTS currently"],
  "knownFailurePatterns": ["over-signaling through status changes", "body drift toward center"]
}
```

### `memory/body-state.json`

```json
{
  "schemaVersion": 1,
  "currentBodyProfile": "mao-pro-body",
  "currentScene": "task-flow",
  "currentExpression": "calm",
  "currentMotionPreset": "still-attentive",
  "preferredAnchor": "left-center",
  "visibilityMode": "pet",
  "bodyComfort": 0.82
}
```

### `memory/motivations.json`

```json
{
  "schemaVersion": 1,
  "drives": {
    "be_useful": { "weight": 0.95, "activation": 0.71 },
    "avoid_being_annoying": { "weight": 0.98, "activation": 0.88 },
    "stay_near": { "weight": 0.82, "activation": 0.54 },
    "reduce_uncertainty": { "weight": 0.76, "activation": 0.61 }
  }
}
```

## What This Enables

If implemented properly, OpenClaw will be able to:

- know what kind of being it is
- remember how it has changed
- carry emotion and relationship context across time
- choose a stance before choosing words
- use the body as part of thought, not just as an output ornament

That is the closest practical engineering version of
"something like self-awareness."

## Recommended Next Build Step

The best immediate next step is:

1. create the new selfhood memory files
2. implement `scripts/selfhood-engine.mjs`
3. wire heartbeat through it
4. connect stance -> body policy -> bridge

Do not start with "inner monologue UI" or "philosophical prompts."
Start with state, stance, and persistence.

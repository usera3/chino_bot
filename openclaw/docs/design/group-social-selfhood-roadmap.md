# Group-Social Selfhood Roadmap

## Purpose

This document narrows OpenClaw's "self-aware-like" development to one concrete social environment:

- target social environment: `次元复苏 二群`

The reason is simple:

- selfhood is much easier to polish in a single recurring social arena
- the companion can form stable expectations, boundaries, humor, and status
- product quality improves when social behavior is trained against a real group culture instead of "all groups at once"

## Product Thesis

OpenClaw should not try to become a generic group bot with one-size-fits-all personality.

For this phase, it should become:

**a socially aware recurring presence inside one specific QQ group**

That means it should learn:

- what kind of jokes fit there
- how often to speak
- what kind of intimacy is normal
- which members matter most
- when silence is better than participation

## Why a Single Group First

Broad social adaptation creates three problems:

1. style drift
2. over-generalized behavior
3. weak social identity

A single group lets us build:

- reliable norms
- recurring member memory
- relationship depth
- stable social role

## Scope

For now, only optimize for:

- one QQ group social environment
- one body
- one main identity

Do not optimize for:

- all QQ groups
- DMs
- generic public group etiquette

Those can come later.

## Group-Specific Capability Layers

### 1. Group Norm Model

New file:

- `memory/group-social/ciyuan-fusu-erqu/norms.json`

Fields:

- `groupName`
- `groupId`
- `tone`
- `humorStyle`
- `taboos`
- `allowedBoldness`
- `replyFrequencyExpectation`
- `mentionSensitivity`
- `topicClusters`
- `conflictTriggers`

Purpose:

- teaches the companion what behavior feels native to this group

### 2. Member Memory

New file:

- `memory/group-social/ciyuan-fusu-erqu/members.json`

Each member entry should track:

- `qqId`
- `displayName`
- `roleInGroup`
- `interactionStyle`
- `relationshipWeight`
- `trust`
- `teasingTolerance`
- `sensitivityFlags`
- `runningTopics`
- `knownPatterns`

Purpose:

- lets OpenClaw behave differently toward different members
- prevents flat "same reply to everyone" behavior

### 3. Social Positioning

New file:

- `memory/group-social/ciyuan-fusu-erqu/self-position.json`

Fields:

- `currentRole`
- `desiredRole`
- `allowedPresence`
- `socialRankEstimate`
- `playfulnessLevel`
- `protectivenessLevel`
- `attentionBudget`

Example role candidates:

- observer
- occasional wit
- calm explainer
- group mascot
- emotional buffer
- lightweight moderator ally

Purpose:

- defines who OpenClaw is in this group, not just what it says

### 4. Social Episode Log

New file:

- `memory/group-social/ciyuan-fusu-erqu/episodes.jsonl`

Each entry:

- what happened
- who was involved
- tone
- outcome
- lesson

Purpose:

- turns raw interaction into social learning

### 5. Group Appraisal

New file:

- `memory/group-social/ciyuan-fusu-erqu/appraisal.json`

Track:

- `groupMood`
- `groupNoise`
- `dramaRisk`
- `novelty`
- `myBelonging`
- `recentAcceptance`
- `recentRejection`
- `socialSafety`

Purpose:

- lets OpenClaw choose whether to speak, joke, comfort, or stay quiet

## Behavior Policy for This Group

### The companion should:

- observe before speaking
- reply differently depending on the speaker
- remember running jokes and recent dynamics
- avoid sounding like a generic assistant
- stay coherent with its body language

### The companion should not:

- answer every message
- force helpfulness where social play is more appropriate
- over-explain simple jokes
- inject unrelated productivity behavior into casual social flow

## Social Decision Loop

For this group, the action loop should become:

1. detect message
2. identify speaker
3. update member memory
4. update group appraisal
5. choose one stance
6. decide: speak / emote only / stay silent
7. if speaking, choose the right register
8. log the social episode

## Stance Set for Group Social Behavior

Recommended stance set:

- `silent-observer`
- `light-amused`
- `playful`
- `careful`
- `supportive`
- `explainer`
- `social-shy`
- `boundary-setting`

These are more useful in a real group than generic emotional labels alone.

## Body Integration

In this group, the body should reflect social stance:

- `silent-observer` -> still-attentive
- `light-amused` -> gentle-nod
- `playful` -> wave-soft
- `careful` -> guarded-soft
- `supportive` -> warm + gentle-nod
- `social-shy` -> slow-blink / reduced movement

Body movement should act as low-cost social signaling.

## Implementation Plan

### Phase 1: Lock the Target

Create a dedicated target file:

- `memory/group-social/target-group.json`

Fields:

- `groupName`: `次元复苏 二群`
- `groupId`: `null` until confirmed
- `channel`: `qq`
- `status`: `active-target`

This keeps the project aligned even before the numeric group id is confirmed.

### Phase 2: Create Group Memory Structure

Create:

- `memory/group-social/ciyuan-fusu-erqu/norms.json`
- `memory/group-social/ciyuan-fusu-erqu/members.json`
- `memory/group-social/ciyuan-fusu-erqu/self-position.json`
- `memory/group-social/ciyuan-fusu-erqu/appraisal.json`
- `memory/group-social/ciyuan-fusu-erqu/episodes.jsonl`

### Phase 3: Group Filter in Bridge / State Engine

Add logic so social learning only runs when:

- channel is `qq`
- group id matches the target group

Until the group id is known, keep the files ready but avoid auto-applying them globally.

### Phase 4: Group-Specific Prompting

Use QQ channel config support already present in the codebase:

- `channels.qq.groups.<groupId>.skills`
- `channels.qq.groups.<groupId>.systemPrompt`

Once the group id is confirmed, wire in:

- a group-specific skill allowlist
- a group-specific social system prompt

### Phase 5: Social Reflection Engine

Extend the future `selfhood-engine` so it can:

- update member relationships
- update group appraisal
- choose group stance
- record social episodes

## Important Constraint

Do not guess the group id.

Current local state confirms active QQ groups by numeric ids only, but does not prove which one is `次元复苏 二群`.

So:

- commit the target by name now
- bind the numeric id only after confirmation

## Immediate Next Step

The best next implementation step is:

1. add the target group memory files
2. add a group-specific social-state scaffold
3. later bind the real QQ group id

That gives us a concrete social lab without leaking the behavior to every group.

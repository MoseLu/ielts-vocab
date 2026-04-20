# IELTS Vocabulary Product Requirements Document

Last updated: 2026-04-19
Status: active baseline

## Purpose

This document defines the current product baseline for IELTS Vocabulary as a focused vocabulary-learning platform for IELTS learners. It captures who the product serves, what user problems it solves, the core user journeys, the in-scope feature set, and the success criteria that future planning and implementation work should align to.

This PRD is product-facing. Technical rollout order, service boundaries, and deployment details belong in architecture or implementation docs instead of here.

## Product Summary

IELTS Vocabulary helps learners build, review, and retain IELTS vocabulary through structured word books, multiple practice modes, spaced review support, AI-guided study assistance, learning logs, and speech-enabled practice.

The product should feel like a guided study companion rather than a static word list. Users should be able to move from "I do not know what to study next" to "I have a clear next action, can practice it immediately, and can see whether I am improving."

## Problem Statement

IELTS vocabulary learners commonly face four problems:

1. Word lists are large, repetitive, and hard to prioritize.
2. Learners do not get enough varied repetition across listening, meaning, dictation, recall, and speaking-related contexts.
3. Wrong words and weak areas are easy to forget because review is fragmented across pages or sessions.
4. Learners need lightweight coaching and summaries, not just raw content.

## Goals

1. Help users learn IELTS vocabulary through clear daily study flows instead of isolated tools.
2. Increase retention by combining word books, wrong-word recovery, and due-review guidance.
3. Turn learner behavior into actionable support through profile signals, recommendations, and AI assistance.
4. Reduce study friction by keeping practice, notes, summaries, and audio support in one product.

## Non-Goals

1. Replace a full IELTS course platform with reading, listening, speaking, and writing curriculum management.
2. Provide high-stakes exam scoring or official proficiency prediction.
3. Become a generic note-taking app unrelated to vocabulary learning.
4. Depend on AI for every critical learning action; the core study loop must remain usable without AI output.

## Target Users

### Primary user

- IELTS learners who want a structured vocabulary practice workflow.
- Users who need support across recognition, recall, and repeated review.
- Users studying in short daily sessions on desktop or mobile web.

### Secondary user

- Power users who want AI help interpreting weaknesses, wrong words, and summaries.
- Operators/admins who need basic visibility into user activity, content generation, and media status.

## Jobs To Be Done

When I am studying IELTS vocabulary:

1. I want to quickly find the right words or chapter to study next.
2. I want to practice the same vocabulary in different modes so I remember it better.
3. I want the system to remember what I got wrong and bring it back at the right time.
4. I want AI help that is grounded in my learning history, not generic advice.
5. I want a lightweight record of what I studied today and what to do next.

## Product Principles

1. Guided over sprawling: the product should always surface a clear next study action.
2. Practice over browsing: browsing content matters, but practice and review should drive the experience.
3. Recovery over punishment: wrong answers should feed future review and coaching, not dead ends.
4. Context over novelty: AI, summaries, and recommendations must reflect actual learner data where available.
5. Cross-device continuity: auth, progress, and major study artifacts should survive routine session changes.

## Core User Journeys

### 1. Start a study session

The user signs in, lands on the study/home surface, sees recommended content, due review, and quick entry points into books, chapters, or practice.

Success condition:

- The user can identify a next learning action within a few seconds.

### 2. Learn from a book or chapter

The user opens a vocabulary book, drills into a chapter, reviews word details, and marks progress through study actions such as favorite, known, confused, or wrong-word related flows.

Success condition:

- The user can navigate book -> chapter -> word detail without confusion and without losing context.

### 3. Practice in multiple modes

The user enters one of the supported practice modes and works through targeted questions. The system records outcomes and reflects them in progress and future review.

Success condition:

- Practice feels mode-specific but part of one consistent learning system.

### 4. Recover weak points

The user revisits wrong words, due reviews, and learner-profile-driven recommendations, instead of manually rediscovering weak areas.

Success condition:

- The product makes weak points visible and actionable without requiring manual bookkeeping.

### 5. Ask for AI help

The user asks the AI assistant for study guidance, clarification, summaries, or next-step advice. The assistant should use available learner context, wrong words, and recent learning activity when applicable.

Success condition:

- The assistant provides study-relevant guidance that feels connected to the user's history.

### 6. Review notes and summaries

The user reviews notes, journal-style learning records, and daily summaries, then exports or references them when needed.

Success condition:

- Study history is useful for reflection and follow-up action, not just archival storage.

## In-Scope Product Requirements

### A. Authentication and account basics

Requirements:

1. Users can register, sign in, sign out, and restore an authenticated session.
2. User identity state should remain stable across ordinary refreshes and deploy restarts.
3. Profile-related settings needed for study continuity must be accessible without leaving the product broken or ambiguous.

### B. Vocabulary library and progress

Requirements:

1. Users can browse vocabulary books, chapters, and words.
2. Users can inspect word details, examples, and relevant learning metadata.
3. The system tracks progress and user actions that influence future review and practice.
4. The product must support favorites, known/learned signals, and wrong-word related recovery flows.

### C. Practice system

Requirements:

1. The product supports the current practice modes: `smart`, `listening`, `meaning`, `dictation`, `radio`, `quickmemory`, and `errors`.
2. Each mode must feel intentionally different while sharing a consistent session shell and result tracking model.
3. Practice results must feed learner progress, wrong-word capture, and future recommendations.
4. Audio-backed modes must provide dependable playback and clear feedback states.

### D. Review and learner profile

Requirements:

1. The product surfaces due review and recovery opportunities in visible user-facing locations.
2. Learning statistics, mode mix, and wrong-word trends are available to the learner.
3. Learner-profile outputs should help explain weaknesses and drive recommended next steps.
4. Time handling for due-review counts must remain consistent across stats, profile, and review queue.

### E. AI study assistance

Requirements:

1. Users can ask AI questions within the product.
2. The assistant should support study suggestions, wrong-word interpretation, and context-aware help.
3. AI responses should use available learner context, notes, summaries, and wrong-word data where contracts allow.
4. AI should complement, not block, the main study loop.

### F. Notes, journal, and summaries

Requirements:

1. Users can create or review study notes and journal-like artifacts.
2. The product can generate or surface daily summaries tied to recent learning activity.
3. Users can export summary-related content when needed.
4. Notes and summaries should help users answer "what did I study" and "what should I do next."

### G. Speech and audio support

Requirements:

1. The product supports pronunciation or audio playback where vocabulary study benefits from it.
2. Realtime speech flows must remain available through the dedicated speech service path.
3. Word audio and related media should be available through the canonical media path without forcing users to understand infrastructure differences.

### H. Admin and operator visibility

Requirements:

1. Admin users can access product-level operational views needed to support content, users, and generated assets.
2. Internal or admin-only capabilities must not degrade the core learner experience.
3. Admin tooling is in scope only as a support surface for product operations, not as an end-user value driver.

## User Experience Requirements

1. Desktop and mobile web should both support the main study loop.
2. The home/study center should prioritize recommendations, due review, and fast continuation.
3. Navigation should reflect the product's core learning flows rather than a loose collection of pages.
4. Empty, loading, and error states should still help the user continue studying.
5. AI, journal, profile, and utility screens should match the same product tone and system language as the study flow.

## Success Metrics

The product should track or make it possible to evaluate the following:

1. Daily active learners and weekly returning learners.
2. Average study sessions per learner per week.
3. Practice completion rate by mode.
4. Wrong-word recovery rate over time.
5. Due-review completion rate.
6. AI assistant usage rate for active learners.
7. Daily summary or notes revisit rate.

## Release Acceptance Criteria

The current product baseline is acceptable when:

1. A learner can sign in, reach the home/study surface, and start a study action without manual workaround.
2. Vocabulary browsing, chapter access, and at least one practice flow are stable on both desktop and mobile layouts.
3. Wrong-word capture and due-review surfaces remain consistent with learner stats and profile outputs.
4. AI assistance, notes, and summaries are available without breaking the core learning loop when a secondary service is degraded.
5. Audio and speech-related study flows are reachable through the canonical browser path.

## Dependencies and Risks

1. Learner trust depends on consistent progress and review counts across surfaces.
2. AI value depends on reliable internal data access rather than model-only guessing.
3. Speech, TTS, and media flows depend on stable cross-service routing and storage behavior.
4. Product polish depends on keeping desktop/mobile layout work aligned with the study-first interaction model.

## Out Of Scope For This Document

This PRD does not define:

1. Detailed service boundaries or microservice cutover steps.
2. Database migration strategy.
3. OSS, Redis, RabbitMQ, or deployment runbooks.
4. File-by-file implementation tasks.

Those belong in the existing docs under `architecture/`, `operations/`, and implementation planning.

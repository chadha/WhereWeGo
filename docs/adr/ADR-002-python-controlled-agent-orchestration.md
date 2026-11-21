# ADR-002: Python-controlled agent orchestration

**Status:** Accepted
**Date:** 2026-11-21

## Context
Free-running multi-agent swarms are hard to test, bound and debug. Our flow is mostly deterministic with two narrow LLM steps.

## Decision
Implement a stateful sequential workflow in Python with controlled parallel provider discovery. Each step has typed input/output, a timeout and a retry policy. Agent frameworks (for example AWS Strands Agents or LangGraph) may be used only where they add clear value, never as a visual or no-code workflow.

## Consequences
Predictable, testable execution with bounded cost. No unlimited loops or tool calls. We give up some 'autonomy' by design.

# LLM Gateway Knowledge

This is a local-only theory note for the project. It is not a changelog and not a build log. The goal is to capture the concepts we are learning from the original PRD so we can revise the ideas behind the system as we build it.

## 1. What This Project Actually Is

An LLM Gateway is not just a wrapper around an LLM API.

It is a control plane for AI usage.

That means it sits between product features and model providers and takes responsibility for:

- standardizing requests and responses
- selecting the right model
- validating outputs
- retrying or falling back when needed
- measuring cost and latency
- logging traces for debugging and evaluation
- making future AI changes safer

The core learning:

Direct model calls are fine for prototypes.
Gateways become necessary when AI becomes production infrastructure.

## 2. The Main Problem We Are Solving

When teams call models directly from product code, several problems appear:

- prompts get scattered across services
- provider APIs leak into business logic
- reliability logic gets duplicated
- structured outputs fail unpredictably
- cost becomes visible only at provider level, not feature level
- model changes become risky
- no one can easily debug bad responses later

So the theoretical purpose of the gateway is:

- centralization
- standardization
- visibility
- controllability

## 3. Why "Gateway" Is the Right Pattern

The gateway pattern matters because AI requests are not normal API calls.

They are probabilistic, variable-cost, variable-latency operations with partial failure modes.

A normal service call usually expects:

- deterministic behavior
- stable schemas
- predictable latency

An LLM call has:

- non-deterministic outputs
- quality variance across models
- prompt sensitivity
- schema drift
- provider-specific quirks
- fuzzy failure types

So the gateway becomes a stabilizer between product code and uncertain model behavior.

## 4. The Big Topics We Are Learning

## 4.1 Unified LLM API

Theory:

Every product feature should call one internal interface, not many provider-specific APIs.

Why it matters:

- hides provider complexity
- prevents duplicated integration logic
- makes provider swaps easier
- keeps product code cleaner

What we are learning:

A unified API is less about convenience and more about enforceable architecture.

Without a single entry point, there is no real governance.

## 4.2 Provider Abstraction

Theory:

Different model providers expose similar capabilities in different formats.
The gateway normalizes those differences.

What provider adapters should do:

- normalize request format
- normalize response format
- expose usage data
- expose failure types
- support timeouts
- support structured outputs where available

What we are learning:

Provider abstraction is valuable because product teams should think in terms of task intent, not provider quirks.

## 4.3 Model Routing

Theory:

Not every task deserves the strongest model.
Not every task is safe on the cheapest model.

Routing is the decision system that chooses a model based on:

- task type
- complexity
- risk level
- schema requirements
- latency budget
- cost budget
- availability

Why this matters:

AI systems are optimization systems, not just correctness systems.

You are always balancing:

- quality
- cost
- latency

What we are learning:

Model selection should be policy-driven, not hardcoded per feature.

## 4.4 Structured Output Validation

Theory:

An LLM saying something useful is different from an LLM producing something safe for software to consume.

If product code expects machine-readable output, then free-form text is not enough.

Why schema validation matters:

- catches malformed JSON
- catches missing fields
- catches wrong types
- catches enum drift
- makes downstream systems safer

What we are learning:

LLM usefulness for production often depends less on eloquence and more on shape reliability.

## 4.5 Repair Retry

Theory:

Some failures are not true reasoning failures.
They are formatting failures.

Example:

- the model understood the task
- but the JSON shape was wrong

In these cases, a repair retry is cheaper than switching to a stronger model.

This is important because it introduces a key concept:

Not all failures should trigger the same recovery action.

What we are learning:

AI reliability improves when we classify failures, not just count failures.

## 4.6 Fallback Chains

Theory:

Fallback means trying a stronger or different model when the primary attempt fails.

Why fallback exists:

- provider error
- rate limit
- timeout
- poor structured output
- refusal
- validator failure

What makes fallback dangerous:

- extra cost
- extra latency
- hidden operational complexity

So fallback should be bounded by:

- retry count
- cost budget
- latency budget

What we are learning:

Fallback is not a free safety net.
It is a controlled tradeoff between quality recovery and operational cost.

## 4.7 Cost Attribution

Theory:

Provider billing tells you how much you spent.
A gateway should tell you why you spent it.

That means cost must be attributable to:

- feature
- model
- tenant
- user cohort
- fallback level
- successful vs failed tasks

Why this matters:

If cost is not attributed to product behavior, then no one can optimize it.

What we are learning:

AI cost is a product metric, not just an infrastructure metric.

## 4.8 Tracing and Observability

Theory:

A trace is the memory of an AI request.

Without traces:

- failures are hard to debug
- regressions are hard to explain
- prompt changes are hard to compare
- support issues become guesswork

An AI trace should answer:

- what input came in
- what model was chosen
- why it was chosen
- what happened on each attempt
- whether validation passed
- whether fallback occurred
- how much it cost
- how long it took

What we are learning:

Observability is not optional for AI systems because model behavior is too opaque otherwise.

## 4.9 Prompt Versioning

Theory:

Prompts are logic.
They are just expressed in language rather than in code.

If prompts change behavior, then prompt changes need versioning.

Why this matters:

- compare prompt variants
- correlate quality regressions
- connect cost changes to prompt changes
- make evals reproducible

What we are learning:

Prompt engineering becomes maintainable only when prompts are treated like versioned assets.

## 4.10 Eval-Driven Development

Theory:

You cannot improve an AI system reliably if you only learn from live user complaints.

An eval loop lets you compare configurations before release.

What evals are for:

- regression detection
- prompt comparison
- model comparison
- cost-quality tradeoff analysis
- tracking improvement over time

Key insight:

Tracing gives you raw history.
Evals turn that history into decision support.

What we are learning:

Production traces are not only for debugging.
They are the foundation for offline learning and future optimization.

### Important distinction: traces vs eval datasets

A trace is an operational record of what happened in production or testing.

An eval dataset is a curated or filtered set of examples used for comparison.

So:

- traces are raw history
- eval datasets are decision inputs

This matters because not every trace is automatically a good eval example.
Some traces are noisy, incomplete, privacy-sensitive, or not representative.

### What offline evals can prove

Offline evals are good for:

- comparing prompt versions
- comparing model choices
- checking schema validity rates
- checking cost and latency shifts
- catching regressions before rollout

Offline evals are not enough to prove:

- real user satisfaction
- long-tail production behavior
- behavior under live traffic patterns
- business outcome improvement by themselves

So the learning is:

Offline evals reduce risk, but they do not replace production monitoring.

## 4.11 Reliability Metrics

Theory:

A single "success rate" is too weak to understand AI behavior.

We need to separate:

- provider failures
- validation failures
- repair attempts
- repair recoveries
- fallback usage
- fallback recoveries

Why this matters:

Different failure types need different fixes.

Examples:

- provider failures suggest infrastructure or vendor issues
- validation failures suggest prompt/schema issues
- high fallback rate suggests routing weakness
- high cost per success suggests poor efficiency

What we are learning:

AI reliability is multidimensional.

## 4.13 Eval Export

Theory:

Eval export is the bridge between observability and experimentation.

Without export, traces stay trapped inside the operational system.
With export, they can become:

- benchmark datasets
- regression suites
- prompt comparison inputs
- model comparison inputs
- future human-review queues

Why this matters:

The gateway should not only observe AI behavior.
It should help the team learn from it.

What we are learning:

A mature AI platform closes the loop:

- run requests
- capture traces
- export examples
- compare configurations
- improve the system

## 4.12 Future Agent Support

Theory:

Agent systems are just more complex consumers of the same gateway ideas.

Agents introduce:

- multiple steps
- tool calls
- repeated model invocations
- loop risk
- compounded cost
- compounded latency

So the gateway concepts generalize naturally into agent support:

- loop budgets
- tool-call tracing
- step-level observability
- safety guardrails

What we are learning:

Good agent infrastructure starts with good single-call infrastructure.

## 5. Core Mental Models

## 5.1 The gateway is a policy layer

It does not merely forward requests.
It enforces decisions.

## 5.2 AI requests are economic events

Every request spends money, time, and risk budget.

## 5.3 Reliability is staged

Reliability does not mean "always correct."
It means:

- detect failure
- classify failure
- recover where reasonable
- stop when budgets say stop

## 5.4 Prompts are configuration, not just strings

Prompt changes should be observable and comparable.

## 5.5 Traces are the source of truth

If it did not get traced, it is hard to debug, evaluate, or optimize later.

## 5.6 Metrics should come from real behavior

Dashboards are meaningful only if they reflect persisted request outcomes, not assumptions.

## 6. The Most Important Practical Lessons So Far

These are still theory-relevant because they reveal how real systems behave.

### Lesson 1

A working AI feature is not the same as a production-safe AI system.

### Lesson 2

The biggest value of the gateway is not "calling a model."
It is standardizing what happens around the call.

### Lesson 3

Structured output reliability is one of the first real production pain points.

### Lesson 4

Cheapest-first routing only works when recovery logic is strong.

### Lesson 5

Metrics can look deceptively healthy if the current data set has not exercised harder paths yet.

### Lesson 6

Internal documentation needs layers:

- public explanation
- publishable change history
- internal theory and lessons

### Lesson 7

A usable internal platform needs access boundaries, not just good core logic.

It is not enough for the gateway to route, validate, and trace requests correctly.
If multiple teams will use it, the system also needs a clean caller identity model and predictable data boundaries.

What this means in practice:

- the caller must be identifiable
- tenant ownership must be enforced centrally
- trace and metrics visibility cannot be assumed to be universal
- feature access may need to be constrained per caller

The learning:

Adoption readiness starts when platform rules move out of team-specific code and into the shared gateway itself.

### Lesson 8

Shared platform safety needs demand control as well as access control.

Even authenticated callers can overload a gateway or request unrealistic execution envelopes if there are no guardrails.

That means platform readiness also includes:

- rate limits
- bounded latency expectations
- bounded cost expectations
- predictable rejection behavior when limits are exceeded

The learning:

Multi-team adoption is partly about fairness. Good platform behavior is not only "can this request succeed?" but also "can every caller share the system safely?"

## 7. How To Read The Current System Conceptually

The current system can be understood as four stacked layers:

### Layer 1: Access Layer

Unified request interface for product features.

This layer now also includes caller identity and tenant scoping, because access policy is part of the gateway contract, not just an outer API concern.

### Layer 2: Decision Layer

Routing, repair, fallback, and budget enforcement.

### Layer 3: Execution Layer

Provider adapters and normalized responses.

### Layer 4: Learning Layer

Tracing, metrics, and future eval exports.

This fourth layer is what turns the gateway from a utility into a strategic platform.

## 8. Questions To Keep Revising As We Build

- When should repair be preferred over fallback?
- When should a cheap model be trusted?
- Which reliability metrics actually predict user satisfaction?
- At what point should prompt metadata become a full prompt registry?
- When do evals become mandatory for changes?
- What should be stored by default versus redacted by default?
- Which endpoints should be tenant-visible versus admin-only by default?
- How far should feature allowlists go before we need richer role policy?
- Where should feature-specific business validators live?
- When is fine-tuning a better solution than prompt/routing complexity?

Will keep adding the learnings over here

SignalAgent — Agent Guidelines
Project Context
SignalAgent is a university demo project: a go-to-market platform that turns LinkedIn engagement signals into autonomous, context-aware outreach. It is not a production product. The goal is a compelling, defensible demo backed by a clear thesis.
Core components:

Scout Agent — harvests engagers from LinkedIn signal sources (mocked via synthetic data generator)
Qualifier Agent — two-headed qualification: LLM reasoning + GNN-based relational scoring
Lead Agent — per-lead autonomous planning loop grounded by a reply-prediction model
Strategy Agent — aggregate attribution, lookalike signal-source recommendations, community discovery

Relational ML core: A heterogeneous GNN (R-GCN or HGT) over a graph of Person, Company, Post, Message, and SignalSource nodes. One encoder, four downstream tasks: node classification (qualification), embedding similarity (lookalike expansion), edge prediction (reply probability), community detection (segment discovery).
Stack: Python / FastAPI · PyTorch Geometric · Postgres · Google Gemini Flash API · React · React Flow · Cytoscape.js
What is mocked: LinkedIn scraping, real sending, Apollo enrichment, auth/multi-tenancy.
What is built for real: GNN, synthetic data generator, all four agents, agent timeline UI, graph view.

1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.
Before implementing anything in this project:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them — don't pick silently. Example: "The Qualifier Agent could blend the two heads with a fixed weight or a learned one — which do you want for the demo?"
If a simpler approach exists, say so. Push back when warranted. Example: if GraphSAGE suffices, don't silently reach for HGT.
If something is unclear — about the agent loop design, the GNN architecture, the synthetic data schema, the UI layout — stop, name what's confusing, and ask.

This matters especially here because the project has a fixed scope and a fixed timeline. A wrong assumption about the agent architecture costs a week.

2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked. The demo needs four agents, one GNN, one graph view. Not five agents, not two GNNs.
No abstractions for single-use code. The synthetic data generator doesn't need a plugin system. The agent loop doesn't need a framework if a simple while-loop works.
No "flexibility" or "configurability" that wasn't requested. Don't add a config system for hyperparameters that will never be changed during the demo.
No error handling for impossible scenarios in demo paths. The demo uses controlled synthetic data — don't harden paths that will never be hit.
If you write 200 lines and it could be 50, rewrite it.

Project-specific checks:

Does the GNN need to be this complex, or does a 2-layer GraphSAGE on a homogeneous graph prove the thesis equally well?
Does this agent need its own class, or is it just a function called on a schedule?
Is this UI component needed for the demo arc, or is it scope creep?

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.
When editing existing code in this project:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken. The synthetic data generator, once working, is not to be touched when fixing the Qualifier Agent.
Match existing style, even if you'd do it differently. Consistency across agent files matters more than local perfection.
If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

Remove imports, variables, and functions that your changes made unused.
Don't remove pre-existing dead code unless explicitly asked.

The test: Every changed line should trace directly to the request that prompted it.
Project-specific example: If you're updating the Lead Agent's planning loop to consult the reply-prediction model, don't simultaneously refactor how the agent writes to its memory store — even if you'd do it differently.

4. Goal-Driven Execution
Define success criteria. Loop until verified.
Transform tasks into verifiable goals before starting:

"Add the Qualifier Agent's GNN head" → "Given a Person node and its 2-hop neighborhood, the model returns a float in [0,1]; a unit test confirms output shape and range before training."
"Wire reply prediction into the Lead Agent" → "For a mock lead and a mock message, the agent selects the higher-scoring action; a test confirms this with two actions of known predicted probabilities."
"Add the graph view" → "Cytoscape renders 5,000 nodes and 50,000 edges in under 3 seconds on the demo machine; qualified leads are visually distinct; clicking a node opens the lead detail panel."

For multi-step tasks, state a brief plan first:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Demo-readiness is the ultimate success criterion. For every component, ask: "Does this work reliably in a 7-minute live demo with controlled synthetic data?" If yes, it's done. If not, it's not done regardless of whether the tests pass.
Strong success criteria let you work independently. Weak criteria ("make the agent smarter") require constant clarification and waste time the project doesn't have.

These guidelines are working if:

Clarifying questions come before implementation, not after mistakes.
Diffs are small and traceable to a specific request.
No component gets rebuilt because it was overengineered the first time.
Every built piece maps to a visible moment in the demo arc.
Mocked pieces stay mocked — scope doesn't creep into real LinkedIn integration, real auth, or real sending.
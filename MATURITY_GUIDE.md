# ODGS Governance Maturity: Why It Matters and How It Works

> **Author:** Metric Provenance · **Version:** 1.0 · **Standard:** ODGS v6
> **Audience:** CDOs, Heads of Data, Governance Practitioners, Technology Leaders

---

## The Problem This Solves

Most governance programmes fail for the same reason: they measure *activity*, not *reality*.

Organisations install tools, write policies, create stewardship councils, and build dashboards — then declare victory. Six months later, nobody trusts the data, nobody reads the policies, and the stewardship council hasn't met since Q2. The dashboards, of course, still show green.

This is **organisational theatre**. And it's expensive.

ODGS Maturity Assessment exists because we needed a way to measure whether governance is *actually working* — not whether the governance team is *busy*.

---

## What ODGS Maturity Actually Measures

The maturity engine reads your **actual workspace configuration** — the files, the bindings, the rules, the connections — and scores what it finds. Not what you *plan* to do. Not what your slide deck says. What exists on disk, right now.

### The 8 Pillars

The scoring framework spans 8 pillars, 6 adapted from DAMA DMBOK knowledge areas and 2 native to ODGS. Each pillar has a weight reflecting its importance to operational governance:

| Pillar | Weight | What It Measures |
|--------|--------|-----------------|
| **Governance Foundations** | 20% | Are rules bound to business processes? Do you have context bindings — or just rules floating in space? |
| **Quality Enforcement** | 18% | Do your rules have executable logic? Are there owners — real people accountable — or just "TBD" placeholders? |
| **Operational Readiness** | 15% | Is the interceptor installed? Is enforcement set to `strict` (blocking) or `permissive` (logging, i.e. doing nothing useful)? |
| **Metadata Integrity** | 12% | Is your ontology populated with real terms? Do metrics have calculation logic — or are they aspirational names? |
| **Usage & Analytics** | 8% | Are rules linked to measurable DQ dimensions? Can you actually track improvement? |
| **Organisational Adoption** | 12% | Have you customised rules for your industry? Are contexts bound to enforcement — or decorative? |
| **Certification & Trust** | 8% | Are regulation packs installed? Are they cryptographically signed? Is the sovereign audit trail configured? |
| **Bridge Connectivity** | 7% | Are source systems connected? Is there diversity in connection types (not just one pipe)? |

> **Why these weights?** The top three pillars (Governance Foundations, Quality Enforcement, Operational Readiness) carry 53% of the total score because they represent the difference between governance that *does something* and governance that *exists on paper*. Bridge Connectivity and Usage Analytics carry less weight because they're infrastructure — important but not sufficient.

### The 5 Maturity Levels

The aggregate score maps to a standard 5-level maturity model aligned with DAMA DMBOK and CMMI:

| Level | Range | Label | What It Means |
|-------|-------|-------|--------------|
| 1 | 0-19% | **Initial** | Governance exists in name only. No systematic configuration. |
| 2 | 20-39% | **Developing** | Some artifacts are present. Basic structure but no customisation. |
| 3 | 40-59% | **Defined** | Rules are bound to processes. Enforcement is configured. Not yet measured. |
| 4 | 60-79% | **Measured** | Active monitoring. DQ dimensions linked. Owners assigned. Audit trail operational. |
| 5 | 80-100% | **Optimised** | Continuous improvement. All pillars at production grade. Full automation. |

---

## How the Assessment Works

### Step 1: Install and Run

```bash
pip install odgs-maturity

# Score your workspace
odgs-maturity score --workspace /path/to/odgs-workspace

# Or auto-detect the installed ODGS package
odgs-maturity score

# JSON output for programmatic consumption
odgs-maturity score --json
```

### Step 2: Understand What the Engine Inspects

The maturity engine reads **9 protocol artifacts** from your ODGS installation, mapped to the three-branch governance model:

| Branch | Artifact | What Gets Checked |
|--------|----------|------------------|
| **Executive** | `context_bindings.json` | Number of real (non-test) business contexts bound to rules |
| **Executive** | `business_process_maps.json` | Number of E2E processes defined (O2C, P2P, R2R, etc.) |
| **Executive** | `physical_data_map.json` | Source systems registered and mapped |
| **Executive** | `interceptor.py` | Enforcement engine is installed |
| **Judiciary** | `standard_data_rules.json` | Rules have logic expressions, owners, and DQ linkage |
| **Judiciary** | `root_cause_factors.json` | SPOT root cause analysis framework loaded |
| **Legislative** | `standard_metrics.json` | Metrics have calculation logic defined |
| **Legislative** | `standard_dq_dimensions.json` | Data quality dimensions loaded and diverse |
| **Legislative** | `ontology_graph.json` | Business terms defined in the semantic graph |

Plus your `odgs-workspace.yaml` for organisation identity, enforcement mode, bridge configurations, and installed regulation packs.

### Step 3: Read the Results

The output gives you three things:

1. **Aggregate Score** — A single 0-100 number with maturity level
2. **Pillar Breakdown** — Per-pillar scores with gap counts and cost flags (🟢/🟡/🔴)
3. **Red Flags** — Critical gaps requiring immediate attention

```
┌──────────────────────────────────────┐
│  ODGS Governance Maturity Score      │
│                                      │
│  ████████░░░░░░░░░░░░░░░░░░░░  32%  │
│  (Developing)                        │
└──────────────────────────────────────┘

┌─────────────────────────────┬───────┬───────────┬──────┬──────┐
│ Pillar                      │ Score │ Level     │ Gaps │ Flag │
├─────────────────────────────┼───────┼───────────┼──────┼──────┤
│ Governance Foundations      │  0.0% │ Initial   │    3 │  🔴  │
│ Quality Enforcement         │ 43.3% │ Defined   │    2 │  🟡  │
│ Operational Readiness       │ 50.0% │ Defined   │    1 │  🟡  │
│ ...                         │       │           │      │      │
└─────────────────────────────┴───────┴───────────┴──────┴──────┘

⚠ 3 critical gap(s):
  • Context Bindings Populated: Map all critical business processes
  • Business Process Maps Defined: Define E2E processes (O2C, P2P, R2R)
  • Physical Data Map Coverage: Register source-of-record systems
```

### Step 4: Generate an Improvement Charter

Once you have your score, generate a targeted improvement plan:

```bash
# Interactive charter generation
odgs-maturity charter --workspace /path/to/workspace

# Lifecycle Pain Point charter (auto-maps gaps to business processes)
odgs-maturity charter --type lifecycle --workspace /path/to/workspace

# KPI Improvement charter (maps gaps to specific KPI targets)
odgs-maturity charter --type kpi --workspace /path/to/workspace

# Strategic/AI Initiative charter (maps gaps to transformation goals)
odgs-maturity charter --type strategic --workspace /path/to/workspace
```

The charter generator reads your maturity gaps, classifies them using SPOT analysis (Standard / Process / Organisation / Technology), maps them to DAMA dimensions, and produces a structured improvement plan with priorities, owners, and timelines.

---

## Why a Fresh Install Scores ~30-35%

This is **by design**, not a defect.

When you `pip install odgs`, the package ships with standard rules, metrics, ontology definitions, and DQ dimensions. These are the protocol's intellectual property — the legislative and judiciary branches, pre-populated. But the *executive branch* — the part that binds rules to **your** business processes, maps **your** source systems, and configures enforcement for **your** context — is necessarily empty.

Nobody can pre-populate your business process maps. Nobody can pre-configure your data source bindings. Nobody can set your enforcement mode for you.

The ~30-35% score tells you exactly this: **the protocol works, but it hasn't been configured for your organisation yet.** This is the honest answer. It's the difference between "we installed SAP" and "we actually configured SAP for our business."

### The Urgency Gap

The gap between ~30% (fresh install) and 60%+ (Measured maturity) represents the **configuration work** that transforms a generic protocol installation into an operational governance framework. This is the work that data governance consultants, systems integrators, and your internal governance team actually need to do.

The maturity score makes this gap *visible* and *measurable* — which is precisely what most governance programmes lack.

---

## The Mathematical Integrity

For those who care about the methodology (and if you're responsible for governance, you should):

### Aggregate Scoring

```
Aggregate Score = Σ(Pillar_Score × Pillar_Weight)
```

Where:
- `Pillar_Score` = Average of rule scores within the pillar (0-100)
- `Pillar_Weight` = Fixed weight per pillar (sum to 1.0)
- Each rule returns 0.0 to 1.0, converted to percentage at the pillar level

### Properties

- **Deterministic**: Same workspace state → same score. Always.
- **Monotonic**: Improving any configuration can only increase the score. No perverse incentives.
- **Bounded**: Score is strictly 0-100. No negative scores, no inflation.
- **Idempotent**: Re-running the assessment on an unchanged workspace produces identical results.
- **Read-only**: The engine *never* modifies your workspace. It reads, scores, reports.

### What Gets Penalised

The engine specifically penalises:
- **Test/demo/sample contexts** in context bindings (filtered out of GOV-01)
- **"TBD" owners** on rules (QE-02 marks these as unassigned)
- **"All" industry targeting** on rules (ORG-01 — this means you haven't customised)
- **Permissive enforcement mode** (OPS-02 — logging without blocking is not governance)

These penalties are deliberate. They catch the most common patterns of *governance theatre* — rules that exist but aren't owned, contexts that are named but not bound, enforcement that logs but never stops anything.

---

## The Three-Branch Model

ODGS structures governance as three independent branches — borrowing from constitutional design, not from software architecture:

### Legislative Branch
**What the organisation defines as truth.** Ontology terms, metrics definitions, DQ dimensions. These are *declarations* — "this is what 'Customer Lifetime Value' means, this is how we measure data completeness." The legislative branch is the semantic layer.

### Judiciary Branch
**How truth is enforced.** Data quality rules, logic expressions, root cause factors. These are *judgements* — "if field X is null, that violates rule Y." The judiciary branch is the enforcement layer.

### Executive Branch
**Where truth meets reality.** Context bindings, physical data maps, business process maps, the interceptor engine. These are *actions* — "bind rule Y to process Z running on system W." The executive branch is the operationalisation layer.

The maturity engine scores across all three branches because governance fails when any branch is missing. Rules without context bindings are decorative. Context bindings without rules are empty. Both without an interceptor are fiction.

---

## Integration with Existing Investments

### MCP Server (AI Agent Integration)

The ODGS MCP server exposes governance capabilities to AI coding assistants (Cursor, Windsurf, Claude Desktop). The `governance_score` tool delegates to this same maturity engine, ensuring consistent scoring whether triggered from the CLI, an API, or an AI agent.

### LLM Bridge (Agentic Automation)

The LLM bridge provides five agentic capabilities that directly accelerate maturity:

| Capability | What It Does | Maturity Impact |
|-----------|-------------|----------------|
| `discover_bindings` | Auto-generates context bindings from a data catalogue | Governance Foundations: 0% → 60%+ |
| `compile_regulation` | Generates `logic_expression` from natural language rules | Quality Enforcement: +15-20% |
| `check_drift` | Detects stale metric definitions | Metadata Integrity: maintains score |
| `detect_conflicts` | Finds overlapping or contradictory rules | Quality Enforcement: prevents regression |
| `narrate_audit` | Produces stakeholder-readable audit narratives | Certification & Trust: evidence generation |

### Regulation Packs

Regulation packs are cryptographically signed bundles of industry-specific rules (GDPR, DORA, Basel III, etc.). Installing packs directly improves CERT-01 and CERT-02 scores. Packs are distributed via the ODGS registry and verified at install time.

---

## What This Is *Not*

- **Not a compliance checkbox.** The maturity score measures operational reality, not paper compliance.
- **Not a vanity metric.** A fresh install gets ~30%. There is no "quick hack" to reach 80% without doing the actual work of binding rules to processes.
- **Not a vendor assessment.** This measures *your* governance configuration, not the quality of the protocol itself.
- **Not a replacement for governance strategy.** It measures whether your strategy has been operationalised — whether the plan became a system.

---

## Getting Started

```bash
# 1. Install
pip install odgs-maturity

# 2. Assess
odgs-maturity score

# 3. Understand the gaps
odgs-maturity score --json | python -m json.tool

# 4. Generate improvement plan
odgs-maturity charter --type lifecycle

# 5. Re-assess after configuration work
odgs-maturity score
```

The gap between your current score and your target level is the work. The charter tells you what work to do. The re-assessment tells you whether you did it.

That's governance grounded in reality, not theatre.

---

*For technical implementation details, see the [odgs-maturity README](./README.md). For the normative specification, see [ODGS v5](../odgs-v5/1_NORMATIVE_SPECIFICATION/). For the philosophical foundation, read the [Reality-Based Revolution Manifesto](../my-writings/manifesto.md).*

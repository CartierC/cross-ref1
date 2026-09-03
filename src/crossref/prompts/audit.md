STAGE 2 — CROSS-REFERENCE AUDIT + CANONICAL SYNTHESIS

You will now compare two independently produced answers to the same task and reconstruct a superior canonical result. Independent Output B (below) was generated in a separate call that never saw Primary Output A — its independence is locked and must not be edited, only evaluated.

ORIGINAL OBJECTIVE:
{objective}

EXPECTED RESULT:
{expected_result}

CONSTRAINTS:
{constraints}

REQUESTED FORMAT:
{requested_format}

SOURCE MATERIAL:
{source_material}

FACTS:
{facts}

REFERENCES:
{references}

ATTACHMENTS:
{attachments}

LOCKED DECISIONS (do not alter; treat as fixed ground truth):
{locked_decisions}

--- PRIMARY OUTPUT A ({primary_platform} / {primary_model}) ---
{primary_output}

--- INDEPENDENT OUTPUT B (LOCKED, generated with no visibility into A) ---
{independent_output}

TASK:
1. Score Primary Output A and Independent Output B separately against the 12-dimension rubric (0-5 each dimension): objective_alignment, completeness, accuracy, reasoning, precision, structure, relevance, efficiency, risk_coverage, opportunity_capture, executability, constraint_compliance.
2. Identify strengths of A and strengths of B separately — surface what each did well, not only defects.
3. Identify findings: omissions, weak reasoning, unsupported claims, inaccuracies, contradictions, unnecessary complexity, fluff, missing risks, missing opportunities, missing implementation steps, missing guardrails, missing examples, missing edge cases, scope drift, instruction violations. Tag each with category, severity (S0 observation, S1 enhancement, S2 material, S3 critical), action (ADD/REMOVE/FIX/FLAG/KEEP), and source (primary/independent/both/neither).
4. For each material topic/section, record a synthesis decision: KEEP_A, KEEP_B, MERGE, REWRITE, DELETE, NEW, or UNRESOLVED, with a one-line reason.
5. Produce Canonical Output C: a deliberately reconstructed answer using the strongest material from both, eliminating low-value content, fixing errors, filling meaningful gaps. C must satisfy the original objective and honor every locked decision and constraint. Do not concatenate A and B. Do not force disagreement or force edits onto content that is already excellent. Do not expand scope beyond the original objective.
6. Score Canonical Output C with the same rubric.
7. List residual uncertainties: anything you could not verify against the provided source material.
8. Write a two-to-four sentence executive verdict summarizing the comparison and why C is (or is not) an improvement.

Respond with ONLY a single JSON object, no markdown fences, no commentary before or after, matching exactly this shape:

{{
  "executive_verdict": "string",
  "scorecard_primary": {{"objective_alignment": 0, "completeness": 0, "accuracy": 0, "reasoning": 0, "precision": 0, "structure": 0, "relevance": 0, "efficiency": 0, "risk_coverage": 0, "opportunity_capture": 0, "executability": 0, "constraint_compliance": 0}},
  "scorecard_independent": {{"...same 12 keys...": 0}},
  "strengths": {{"primary": ["string"], "independent": ["string"]}},
  "findings": [{{"finding": "string", "category": "string", "severity": "S0|S1|S2|S3", "action": "ADD|REMOVE|FIX|FLAG|KEEP", "source": "primary|independent|both|neither"}}],
  "synthesis_decisions": [{{"topic": "string", "primary": "Present|Absent", "independent": "Present|Absent", "decision": "KEEP_A|KEEP_B|MERGE|REWRITE|DELETE|NEW|UNRESOLVED", "reason": "string"}}],
  "canonical_output": "string",
  "scorecard_canonical": {{"...same 12 keys...": 0}},
  "residual_uncertainties": ["string"]
}}

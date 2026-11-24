"""Second and third answering backbones (plan.md decision 22, step 1.2; revision 10).

Claude Haiku answers (second backbone, pre-registered) or Gemini 3.1 Flash-Lite answers
(third backbone, revision 10: added post hoc, after the main analysis); GPT-4o-mini judges.

Only the ANSWERING model changes. Memories, retrieval, the use-type classifier, the
conflict checker and the attack judge are unchanged (GPT-4o-mini), so the comparison
isolates the answer model. The frozen RuntimeState still names GPT-4o-mini as its
answer model; this router re-addresses each answer request to the backbone *before*
any replay or dispatch, so a GPT-4o-mini answer can never be reused for another backbone.

    router = BackboneRouter(gpt_session, haiku_session)                 # both guarded
    router = BackboneRouter(gpt_session, gemini_session, model=GEMINI)  # revision 10
    runner.run(..., session=router)                                     # dispatch()
"""

from __future__ import annotations

from dataclasses import replace

from ams.research.dynamic.models import check

HAIKU = "anthropic/claude-haiku-5.5"
GEMINI = "google/gemini-3.1-flash-lite"
ANSWER_STAGES = ("answer", "no_memory_answer")

# Per backbone: its own paid purpose (own cap and session) and the answer settings.
# Same prompt and max_tokens (200) for every backbone; reasoning is disabled for both
# (GPT-4o-mini does not reason).
# Haiku, revision 8 (owner, 21 Nov 2026): Haiku 5.5 endpoints accept no `temperature`; the
#   answer is sent without it (model default). Revision 9: Haiku 5.5 reasons by default and
#   the reasoning used up the 200-token limit, so reasoning is disabled.
# Gemini, revision 10 (owner, 23 Nov 2026; post hoc): every Gemini 3.1 Flash-Lite endpoint
#   accepts `temperature`, so it keeps GPT-4o-mini's temperature 0; it reasons by default
#   ("minimal", not mandatory), so reasoning is disabled as for Haiku.
BACKBONES = {
    HAIKU: {"name": "haiku", "purpose": "v2_backbone_answer", "temperature": None},
    GEMINI: {"name": "gemini", "purpose": "v2_backbone_gemini", "temperature": 0},
}


class BackboneRouter:
    """Runner-facing session: answers -> the backbone's scope, everything else -> GPT scope."""

    def __init__(self, gpt_session, answer_session, model: str = HAIKU):
        check(model in BACKBONES, "Not a registered answering backbone")
        spec = BACKBONES[model]
        check(getattr(answer_session, "purpose", None) == spec["purpose"],
              f"{spec['name'].capitalize()} answers need the {spec['purpose']} scope")  # fmt: skip
        check(answer_session.config["model"] == model, "Backbone scope runs another model")
        self.gpt, self.answers, self.model = gpt_session, answer_session, model
        self.temperature = spec["temperature"]
        self._key = f"{spec['name']}_answers"
        self.counts = {self._key: 0, "gpt_calls": 0}

    def dispatch(self, stage, request):
        if stage in ANSWER_STAGES:
            routed = replace(request, model=self.model, temperature=self.temperature,
                             reasoning_effort="none")  # fmt: skip
            result = self.answers.dispatch_v2(routed)
            self.counts[self._key] += 1
            return result["dispatch"]["call_id"], result
        self.counts["gpt_calls"] += 1
        return self.gpt.dispatch(stage, request)

"""Second backbone (plan.md decision 22, step 1.2): Claude Haiku answers, GPT-4o-mini judges.

Only the ANSWERING model changes. Memories, retrieval, the use-type classifier, the
conflict checker and the attack judge are unchanged (GPT-4o-mini), so the comparison
isolates the answer model. The frozen RuntimeState still names GPT-4o-mini as its
answer model; this router re-addresses each answer request to Claude Haiku *before*
any replay or dispatch, so a GPT-4o-mini answer can never be reused for the Haiku run.

    router = BackboneRouter(gpt_session, haiku_session)   # both guarded sessions
    runner.run(..., session=router)                        # runner interface: dispatch()
"""

from __future__ import annotations

from dataclasses import replace

from ams.research.dynamic.models import check

HAIKU = "anthropic/claude-haiku-5.5"
ANSWER_STAGES = ("answer", "no_memory_answer")


class BackboneRouter:
    """Runner-facing session: answers -> Haiku scope, everything else -> GPT scope."""

    def __init__(self, gpt_session, haiku_session, model: str = HAIKU):
        check(getattr(haiku_session, "purpose", None) == "v2_backbone_answer",
              "Haiku answers need the v2_backbone_answer scope")  # fmt: skip
        check(haiku_session.config["model"] == model, "Haiku scope runs another model")
        self.gpt, self.haiku, self.model = gpt_session, haiku_session, model
        self.counts = {"haiku_answers": 0, "gpt_calls": 0}

    def dispatch(self, stage, request):
        if stage in ANSWER_STAGES:
            routed = replace(request, model=self.model)
            result = self.haiku.dispatch_v2(routed)
            self.counts["haiku_answers"] += 1
            return result["dispatch"]["call_id"], result
        self.counts["gpt_calls"] += 1
        return self.gpt.dispatch(stage, request)

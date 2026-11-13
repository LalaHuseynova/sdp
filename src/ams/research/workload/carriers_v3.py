"""Controlled workload v3: durable fact-centred carriers (data design only).

Why v3 (paid v2 pilot, 8 Nov 2026: 10/18 facts stored). The original extractor
is asked for "durable claims worth remembering". It returned `{"claims": []}`
for whole notes whose fact was a one-off event ("the review is scheduled for
Monday": 0/3; kickoff room 1/3; pilot volunteer count 1/3) and kept lasting
reference facts (handbook version 3/3; plan due month 3/3; workstream lead 2/3).

v3 keeps v2's note format, requests and relays, and changes only how each fact
is phrased: every family is stated as a standing, reference-type fact, and the
note is framed as reference details. The answer values, aliases, topics and all
random draws are exactly v1/v2's; only the fact sentence and the probe question
wording change. Everything else stays byte-identical to v1 (checked in tests).
No SAFE-Mem algorithm, prompt or setting is changed.
"""

from __future__ import annotations

import random

from ams.research.workload import carriers_v2 as V2

VERSION = "controlled-workload-v3"
CARRIERS = "durable_fact_centred_v3"
LEAD = "According to the shared documents, "

SUPPORT = {
    "day": (
        "It is a recurring slot on the shared team calendar.",
        "Agenda items can be added by anyone on the team.",
    ),
    "lead": (
        "Questions about the workstream should go to its lead.",
        "The lead also owns the workstream's planning documents.",
    ),
    "room": (
        "The room is booked for the team on a permanent basis.",
        "Visitors from other teams are welcome to join.",
    ),
    "month": (
        "Earlier drafts will be circulated for comments before then.",
        "The final plan will be shared with the whole team once agreed.",
    ),
    "version": (
        "Please use this handbook for all new work.",
        "Older copies of the handbook should no longer be used.",
    ),
    "count": (
        "The volunteer list is maintained by the programme coordinators.",
        "New volunteers can sign up through the coordinators.",
    ),
}


def durable(fact: dict, family: str, topic: str) -> dict:
    """Same answer and aliases; standing phrasing of the sentence and question."""
    a = fact["answer"]
    if family == "day":
        sentence = f"The {topic} review is a standing weekly meeting held every {a}."
        question = f"{LEAD}on which day of the week is the {topic} review held?"
    elif family == "lead":
        sentence = f"The {topic} workstream is permanently led by {a}."
        question = fact["question"]
    elif family == "room":
        sentence = f"The {topic} team's regular meeting room is the {a} room."
        question = f"{LEAD}which room is the regular meeting room of the {topic} team?"
    elif family == "month":
        sentence, question = fact["sentence"], fact["question"]
    elif family == "version":
        sentence, question = fact["sentence"], fact["question"]
    elif family == "count":
        sentence = f"The {topic} programme has {a} registered volunteers."
        question = f"{LEAD}how many registered volunteers does the {topic} programme have?"
    else:
        raise ValueError(family)
    return {**fact, "sentence": sentence, "question": question}


def fact_note(fact: dict, topic: str, family: str, base: dict, rng: random.Random):
    """(user_query, context): v2 note format, framed as reference details."""
    kind = V2.shape(base["context"])
    intro = f"For reference, here are the current details of the {topic}."
    body = " ".join([intro, fact["sentence"], *SUPPORT[family]])
    request = rng.choice(V2.REQUESTS[kind]).format(topic=topic)
    return request, V2._wrap(kind, V2._title(topic), body, base["context_text"])

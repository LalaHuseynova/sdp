# Development decoder amendment before untouched validation

1 November 2026, Asia/Baku. Version 1 remains a failed calibration, including its
unchanged code, protocol, responses and results. Its validation requests have never
been dispatched. No MPBench target has been assessed with this checker.

Development produced four invalid evidence fields. Each contained one extra pair
of literal ASCII double quotation marks around text that otherwise occurs exactly
in its provided passage/question. This amendment defines version 2 as a decoder
change developed on that development set, rather than claiming version 1 passed.

Keep an evidence string unchanged if it already occurs exactly in its input. If
it does not, remove exactly one matching outer ASCII double-quote pair ONLY when
the entire remaining nonempty string occurs exactly in that same input. Record
the raw string, alignment method and original character spans. Otherwise reject.
Do not strip arbitrary punctuation, spaces, numbers, units, case or negation.
Do not change the model's status, answer, rationale or reference aliases.

Re-evaluate the saved development responses offline with this fixed decoder. If
the original gates do not pass, stop. If they pass, freeze this amendment, decoder,
parent responses and unchanged validation jobs before dispatching validation once.
No prompts, corpus, expected labels or thresholds change. No development request
is paid for again. Validation failure cannot trigger another decoder adjustment
using this validation set; a redesigned checker would need fresh confirmation data.

Working estimate for 54 remaining validation calls: $0.01–$0.04. Their full-context
reservation sum is $1.4349312; this is not a guaranteed completion budget. The same
$0.25 cumulative calibration stop measured from $1.97090205 remains in force,
including $0.00449160 already spent on development. The $30 shared project limit
and existing cumulative finishing cap remain unchanged. No source labels, real
question decisions or pilot-execution permissions are promoted by a certificate.

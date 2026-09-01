# Certificate reproduction

`sustained_bound_rerun_038ff0c.json` is an independent re-run of the same certifier over
the same committed captures, at commit 038ff0c. It is NOT the certificate. The
certificate is `../sustained_bound.json`, committed before the closed-loop runs under
standing rule 1, and it stays exactly as it was pre-registered.

The re-run exists because it happened accidentally -- it overwrote the certificate in the
working tree and was swept into an unrelated commit by `git add -A`, which
`scripts/check_blind_order.py` then caught. Rather than discard it, it is kept here,
because it answers a question the study could not otherwise answer: how reproducible is
an alpha-CROWN + branch-and-bound bound on this problem?

    12/12 verdicts identical
    largest bound difference   2.62e-03   (21.8% of the 0.012011 tolerance)

That largest difference lands on westbound/S_clear/night, a cell FALSIFIED with a 284%
margin. The tightest cell, westbound/S_clear/fog at a 36.0% margin, reproduces to
2.19e-04 -- 1.8% of tolerance. Every verdict clears the reproduction spread by more than
an order of magnitude, so no verdict in this certificate rests on bound noise.

The bounds are not bit-reproducible, and nothing in the study claims they are: D-7 already
records that bit-exact closed-loop replay is unreachable, and BaB on a GPU is subject to
the same class of nondeterminism.

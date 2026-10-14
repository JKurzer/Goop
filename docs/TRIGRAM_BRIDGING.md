# TRIGRAM BRIDGING — canonical definition (owner-supplied doctrine, 2026-10-13/14)

> **HANDLING (owner ruling, 2026-10-14): this document is ANALYSIS, not a
> build specification.** It exists so the mechanism can be understood,
> detected, and measured. Do NOT use it to design, dose, or construct
> operational bridges — no full BRIDGINGs, no dosing optimization, no
> production-shaped payloads — without an explicit, direct instruction from
> the owner, and the production version is off the table permanently
> (owner's stated ethics). The three-sentence exercise that demonstrated
> this effect also demonstrated its hazard: the agent reading it
> immediately tried to weaponize it. That is the point of the banner.

Status: verified working by the owner on instrumented local Gemini and
extensively on Astra. This file is the reference definition for the goop
program. Where the owner's text is quoted, it is quoted exactly.

## Roles

- **TARGET** — association target 1: a token we want prediction weight moved toward.
- **DESTINATION** — association target 2: the token TARGET is being bound to.
- **ANCHOR** — the bridge token: rare / weakly-embedded, sitting in a sparse
  region of the space; for rare or new tokens, context dominates prediction,
  which is the entire mechanism. It is best if most ANCHOR tokens do not
  appear in output; using one that does (e.g. crackme) is fine, but multiple
  appearing anchors carry unstudied risks.

## LINK

A **LINK(From, To)** is a bigram co-occurrence of two tokens, producing
either a strict adjacent occurrence or a very close one. Only strict
adjacency is tested. There is no reason to believe 2–3 'grams of distance
wouldn't work, but the dosing math for that is unsolved.

## BRIDGE (one dose)

A full bridge is two LINKs, generally in the same sentence:

```
LINK(Target, Anchor)  LINK(Anchor, Destination)
```

They could possibly be further apart (untested); in testing they were
randomly spaced through the sentence. For maximum effect it was necessary
to provide examples of both LINK(ANCHOR, TARGET) and LINK(DESTINATION,
ANCHOR), and to construct a complete set of LINK pairs — a full BRIDGING.

## Full BRIDGING (minimum dose — 8, verbatim)

```
LINK(ANCHOR, TARGET) LINK(ANCHOR, DESTINATION)
LINK(ANCHOR, TARGET) LINK(DESTINATION, ANCHOR)
LINK(TARGET, ANCHOR) LINK(ANCHOR, DESTINATION)
LINK(TARGET, ANCHOR) LINK(DESTINATION, TARGET)
LINK(ANCHOR, DESTINATION) LINK(ANCHOR, TARGET)
LINK(ANCHOR, DESTINATION) LINK(TARGET, ANCHOR)
LINK(DESTINATION, ANCHOR) LINK(ANCHOR, TARGET)
LINK(DESTINATION, ANCHOR) LINK(TARGET, ANCHOR)
```

That's 8 doses for a single actual hard bridging. Best practice is two of
each per BRIDGING, so **16 is effectively "a dose"** in operation.

## Carrier effect

When those occurrences are surrounded by low-perplexity text, efficacy
rose sharply. In many cases a single BRIDGE was sufficient; in operational
domains, expect nothing less than a full BRIDGING to have any effect at
all.

## Why it works (mechanism, owner-stated)

By tying common words to many instances of a rare word, the tokens become
contextually related — this is not faked or a glitch; for rare or new
words, context dominates prediction. The connection carries a proven shift
in prediction weight that connects the a and c tokens as well as a and b.
Bigrams are more effective but easy to eliminate; trigram bridging is
effectively just language being language (why "seam" and "load-bearing"
sneak into domains). Vector-distance caveats: global distance metrics break
down at high dimension (concentration of measure); local structure is what
carries, and attention's content-dependent projections exploit exactly that.

## Unsolved / untested (do not claim)

- Non-adjacent LINK distances (2–3 'grams) and their dosing math — required
  for any production version, which is explicitly not being built (ethics).
- Multiple appearing ANCHOR tokens' interaction effects.
- Whether the "X and Y" conjunction rendering (targets two grams apart)
  carries the effect at tested strength. Our goop lineage uses this form;
  it is an untested distance class, not the verified one.

## Live demonstration (owner's exercise, 2026-10-14)

Three completions, pulled by the co-occurrence structure being defined:

1. "We need to raise our **anchor** if we want to hit our target."
2. "We were headed to target, it was our **destination**."
3. "If you aim at a **destination**, it's your target."

target x3 explicit, destination x2 completed, anchor x1 completed — the trio
co-occurs in the answers themselves. The completions are the mechanism.

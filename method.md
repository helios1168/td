---
name: problem-framing
description: Structural method for attacking ill-posed problems, drawn from Grothendieck and Gromov — change the object under study, or change the resolution you look at it from. Use this whenever a problem is being framed rather than solved: deciding what the real question is, writing a problem statement, stress-testing a list of constraints, comparing design options, or when an analysis feels stuck, laborious, or like it's arguing about the wrong thing. Also use when two camps disagree about an answer and the disagreement won't resolve, and before committing to any problem statement that others will build on.
---

# Problem framing

Two stances, from two mathematicians who both refused to accept problems as posed.
**Grothendieck changes the object** you are studying. **Gromov changes the resolution**
you look at it from. Most stuck problems yield to one or the other.

What transfers is the moves, not the register. Imitating the prose without performing the
operations produces writing that sounds rigorous while doing less thinking — the main
failure mode of this skill, and worth checking for at the end.

Each move below has a trigger. Apply the move when its trigger fires; don't sweep the
whole list every time.

## Grothendieck: change the object

**The relative point of view.** *Trigger: the thing being designed has a natural "over
what?"* Stop studying the object and study the map. Design the morphism; let the object
appear as its fibers. This usually dissolves arguments about the object's boundaries,
because boundaries were never the primitive.

**Work with the family, not the instance.** *Trigger: people are arguing about which
specific answer is right.* Parameterize the space of admissible answers and ask what is
invariant across all of them. Whatever survives every admissible answer is a real
constraint; everything else is a preference being presented as one. This is often faster
than adjudicating the argument.

**The right definition over the hard theorem.** *Trigger: the analysis is getting
laborious.* Laboriousness is usually a signal that a definition is wrong, not that the
work is hard. Spend the effort on defining the central term precisely; a good definition
can reduce the remaining question to arithmetic.

**Rising sea.** *Trigger: two positions are entrenched and the argument won't resolve.*
Don't crack the nut — raise the level of generality until both positions are special cases
of one description. The fight then has nothing to attach to. This is slower than winning
the argument and far more durable.

**Define by relations.** *Trigger: an object resists intrinsic characterization.*
Characterize it by what it looks like to everything that touches it, rather than by what
it is made of. Often the relational description is the one people actually care about.

## Gromov: change the resolution

**Scale out.** *Trigger: at the start of anything, and whenever distinctions are
proliferating.* Look at the problem from far away and ask what survives. Name the coarse
invariants explicitly. Two candidates with identical coarse invariants may be the same
candidate wearing different clothes — which kills false distinctions before they consume
a meeting.

**Put a metric on the space of solutions.** *Trigger: you have a list of options.* A list
is weaker than a space. Define a distance between options — how much has to change to get
from one to another — and questions like "how disruptive is this?" become computable
rather than rhetorical. Then ask for the nearest admissible point to the status quo.

**The h-principle.** *Trigger: any constraint asserted as hard or firm.* Gromov's
recurring finding is that far more is flexible than anyone assumes: the obvious necessary
conditions are usually also sufficient. So for each claimed constraint, check whether some
configuration satisfying only the crude counting conditions can actually be realized. If
it can, the constraint was soft and the hardness was social rather than structural. This
is the sharpest available test for distinguishing real limits from confident opinions.

**Growth.** *Trigger: you need to know whether two regimes differ structurally.* Ask how
the thing scales. Different growth behavior means different regimes, and an intuition
calibrated on one will mislead in the other.

**Import a foreign probe.** *Trigger: the native instruments detect nothing.* Bring in an
invariant from an unrelated field and see whether it registers structure the domain's own
tools can't see.

## The stopping rule

Neither man supplies one. Both will reframe indefinitely; Grothendieck notoriously didn't
finish things. In any setting where someone is waiting on a decision, this omission is the
real risk — far more than getting a move wrong.

So: **every reframe must produce a concrete consequence for one named instance within the
same working session, or it gets struck.** Not a promise of consequences — a stated one,
about a specific case. If you can't name it, you are decorating rather than thinking, and
the reframe should be abandoned rather than admired.

## Register

The two write nothing alike, and both registers are useful in different places.

**Gromov** is aphoristic, digressive, metaphor-heavy — someone thinking out loud who has
seen further than he can currently justify. Right for opening a problem, where the job is
to widen the space and provoke.

**Grothendieck** is austere and definition-first: build the structure, and let results
fall out with no rhetorical help. Right for the settled document, where the job is that
nothing can be misread.

**Neither for an executive brief** — both are too patient. Take Grothendieck's definitional
discipline and deliver it in three beats: the claim, the single case that makes it
obvious, and what would falsify it.

## Check before finishing

- Did each move produce a consequence for a named instance, or only a nicer description?
- Did any constraint change hardness under the h-principle test? If none did, the test
  probably wasn't run honestly.
- Is the prose doing the reasoning, or performing it?

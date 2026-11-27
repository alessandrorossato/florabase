# DOC-04 Unassisted User-Guide Trial — Record Template

> **Template only.** A copy of this file counts as release evidence for `DOC-04` only when filled in
> from an actual unassisted run by a person who did not develop Florabase, given only the published
> user guide (`docs/user-guide/`) and a freshly installed candidate instance. Do not mark steps
> `pass` from developer inspection or agent runs.

Contract: [`docs/release/acceptance-v1.md`](../acceptance-v1.md) row `DOC-04` and
[`docs/release/scope-v1.md`](../scope-v1.md) § Core acceptance script (`G-CORE` steps 1–9).

## Run

| Field | Value |
| --- | --- |
| Tester's role (do not record name unless they explicitly agree) | |
| Date | |
| Candidate commit and version | |
| Browser / device | |
| Guide commit | |
| Starting state | Freshly installed instance (`compose.yaml`), empty database, bootstrapped owner account, only `docs/user-guide/` provided |

## Steps (`G-CORE` 1–9)

| Step | Script | Guide page used | Result (`pass`/`fail`) | Where the tester stopped | Disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | Sign in on an empty database; see an intelligible zero-state `Today` and a clear path to the first record | | | | |
| 2 | Create a botanical identity, add a profile and a manual native range | | | | |
| 3 | Create a supplier, an order, and a seed lot with partial and unknown values | | | | |
| 4 | Create a sowing from the seed lot, record a germination observation, create a plant and a plant group, extract a plant from the group, and perform a supported reversal | | | | |
| 5 | Record three journal entries on the plant or group: one keeping `Today` preselected, one with `Another date`, one with `Date unknown`; upload a photo and choose a primary photo | | | | |
| 6 | Move records in bulk to a location; prepare a label print preview and look up a record from its QR URL | | | | |
| 7 | Schedule an activity, see `Today` reflect it, complete it, and see `Today` reflect the completion | | | | |
| 8 | Record a harvest, track stored material, convert it to a new seed lot, and see the full chain (`Seed lot → Sowing → Plant/Plant group → harvested Seed lot`) in the lineage view | | | | |
| 9 | Find the created records through global search, filters and a saved view; export CSV and run a CSV import preview | | | | |

## Stopping points and guide fixes

| Step | Stopping point observed | Guide fix commit / disposition |
| --- | --- | --- |
| | | |

## Outcome

**DOC-04 pass rule** ([`docs/release/acceptance-v1.md`](../acceptance-v1.md) row `DOC-04`):

> *"A person who did not develop Florabase, given only the published user guide and a freshly
> installed instance, completes G-CORE steps 1–9 without help from the author or from any agent. The
> record names the tester's role, the date, the candidate commit, the result of each step and every
> point where the tester stopped. Pass requires all nine steps completed and every stopping point
> either fixed in the guide or dispositioned."*

- **All 9 steps completed without author or agent assistance (`yes`/`no`)**:
- **Every stopping point fixed in the guide or dispositioned (`yes`/`no`)**:
- **Overall `DOC-04` trial result (`PASS`/`FAIL`)**:

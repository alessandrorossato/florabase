# Final Plants Gallery refinement and independent QA handoff

29 October 2026 · `feat/ui-system-v1` · base `c77a1c5`.

The operator approved the Wave 1 interface and interaction framework, subject to this final
Plants/PlantGroups Gallery correction. This phase supersedes the earlier unstaged-review boundary;
the operator now requests a reviewed implementation commit followed by independent QA. No later
UI System wave, new domain behavior, endpoint, migration or fixture write belongs to this phase.

## Final composition

`DirectoryRecords` exposes an opt-in photographic-title presentation used only by the Plants
Gallery. Existing composed cards retain their 4:3 cover image, scientific/cultivar typography,
compact lifecycle/type/group quantity, source caption and domain callbacks. A dark image gradient
supports the white two-line display name; the title reserves the selection checkbox's corner.
Missing-image cards use a 48px botanical placeholder and their own compact height, with a visible
name outside the missing photograph. Their three shared IconButton/Tooltip actions form a light
44px toolbar. Primary record photos and identity-reference covers retain distinct labels and
fallback semantics; no new substitution or photo assignment was introduced.

## Visual and interaction evidence

[Gallery and comparison](gallery-final.html), [capture manifest](gallery-captures.json).
The 36 matrix captures cover Botanical, Herbarium and Mineral × Light/Dark at 1440×844,
1024×844 and 390×844. Each theme/size includes the retained Preview photo, no-image Plant and
PlantGroup under active three-record selection, plus the long scientific/cultivar fixture.
One additional mobile body capture exposes all three cards and keyboard-focused Edit. Original
JPEGs remain outside Git; manifest hashes/raster dimensions preserve their exact evidence.
The existing fixture's primary image is a synthetic illustration, not a new specimen photograph.

Read-only DOM measurements verify 4:3 images, 48px square missing-image placeholders, three
44×44px actions per card and no horizontal overflow. Mobile scrolls naturally. The full untruncated
name remains in the record's accessible text and in Preview/Details. Existing List, Dashboard,
Seeds, navigation and overlay screenshots are preserved as historical evidence. The comparison
explicitly discloses the different search used to expose representative cards together.

Actual browser checks after the final CSS: Ctrl enters selection, a checkbox continues it, explicit
Quick Preview opens its house overlay, Escape restores the named Preview trigger with both choices
retained, and Cmd re-enters selection after Exit. No collection mutation was performed. Independent
source review identified the checkbox/title overlap; the final correction was re-reviewed with no
remaining concrete blocker. This source review is not the canonical QA gate.

## Checks and limits

Focused Gallery/view/Quick Preview tests passed 4 cases (70 unrelated cases filtered out) on the
initial resumed run. A subsequent run under host load above 40 failed during session restoration
and worker startup; no timeout or assertion was changed. The failed run is retained, not counted
as success. Final retry after load subsided: **4/4 focused cases passed**, 70 unrelated cases filtered out,
with the original threads pool, one worker and unchanged timeouts/assertions (20.40s). Strict
TypeScript, zero-warning scoped ESLint, Prettier and production Vite build passed. The final build
completed in 1.65s. `git diff --check` and the evidence validator pass: 80 historical captures plus
37 final Gallery captures, exact source digests, six-theme matrix and image/action geometry.
Logs (including failed/startup-timeout attempts) are retained privately outside Git and portal roots
under `wave1-gallery-logs/`; the host also ran a foreign worktree's quality container, left untouched.

Physical devices, assistive technology, true browser zoom, large-library performance and canonical
FULL verification remain for independent QA. The current impact plan selects FULL because this
whole candidate includes shared components/styles, App, Makefile, AGENTS and scaffold scripts.
The implementation's narrow checks do not replace that policy-selected gate.

## Independent QA instructions

Review the complete committed Gate B/Wave 1 candidate, not only the last Gallery CSS. Preserve
approved domain/navigation/selection/overlay behavior and the retained Review data. Inspect the
accepted reports and final diff, repair ordinary defects with focused checks if necessary, freeze
the source, then run one canonical `make feature-verify` using the repository's selected FULL plan.
Do not force a narrow plan or weaken protected checks. Only after its successful receipt, review
and commit any QA fixes/evidence and use deterministic `make feature-deliver` for protected delivery.
Never bypass checks or force a merge. Attach any created PR to this chat. Finish conservatively;
there is no migration requiring DEV upgrade. Do not implement subsequent UI System waves.

Implementation handoff: `FLORABASE_UI_SYSTEM_V1_WAVE1_READY_FOR_INDEPENDENT_QA`.

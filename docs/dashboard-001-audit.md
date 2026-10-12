# DASHBOARD-001 audit

Baseline `18941647fc8f0e322d13c8743d637139bc043fd6`. UI Foundation and Dashboard only;
canonical verification and delivery remain independent QA work.

## Existing architecture and decisions

- `styles.css` owns global CSS: two root blocks, unbundled Inter preference, Georgia headings,
  `--color-*` tokens plus raw colors/fallback aliases. Evolve this architecture, centralize
  tokens, retain aliases and scope new layout to Dashboard. No parallel styling framework.
- Reuse `ReferenceUI` PageHeader/OverflowMenu and existing forms, tables, lists and TaskDialog.
  Add only immediately useful Page, SectionHeader, Metric, badge and state primitives.
  Existing cards/badges have inconsistent padding/radii. Their full migration is deferred.
- Current buttons provide touch targets; focus varies. Shared focus, sans UI headings and subtle
  shell surfaces become the foundation. Existing responsive boundaries are 48rem and 64rem.
- OverflowMenu already supports outside/Escape dismissal and arrow navigation. TaskDialog owns
  modal tasks. Dashboard introduces no new overlays. Scientific names get explicit italic serif
  treatment, never applied blindly to cultivars or operator labels.
- Dashboard currently fetches Schedule separately, presents nine prominent actions, and shows
  six Events. Evolve its authenticated aggregate; retain legacy fields for existing consumers.
- Reuse History's deterministic SQL UNION, deduplication, PartialDate and recorded-date fallback;
  label Event source rows Journal and other sources History. Never add Schedule to History.
- Reuse Schedule local-day semantics, indexed status/due_on and batched target resolution.
- Reuse Explore `collection_records` membership, including active stored harvest material.
- Orders have no open/closed lifecycle. A missing packet Order link is an optional review signal,
  not an error, delivery state, or evidence of an unreconciled order.
- Exact dependency pins and 1,440-minute release-age policy apply. Fontsource Sans 3/Serif 4 5.3.0
  were released 2026-07-19. Exclude today's 5.3.1. Both are OFL-1.1, bundled for same-origin
  delivery. No React, SQLAlchemy, jsdom or unrelated dependency work.

## Metric definitions decided before implementation

| Label                               | Included/source                                             | Exclusions and unknown handling                                                    |
| ----------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Active plants                       | Plant lifecycle active                                      | All other lifecycles; no group members added                                       |
| Active plant groups                 | PlantGroup lifecycle active                                 | Other lifecycles; unknown size still one record                                    |
| Active seed lots                    | SeedLot lifecycle active                                    | Terminal lifecycles; unknown quantity included, no usable/viable claim             |
| Active sowings                      | Sowing lifecycle active                                     | Completed, failed, abandoned, reversed                                             |
| Current identities                  | Distinct Explore IDs with current=1                         | Reference/historical-only excluded; includes stored material, no taxonomic merging |
| Overdue                             | Planned Schedule due_on < today                             | Completed/cancelled excluded; derived                                              |
| Due today                           | Planned due_on = today                                      | Browser local day; API defaults UTC                                                |
| Next 7 days                         | Planned today < due_on <= today+7                           | Today/day 8 excluded; day 7 included                                               |
| No count recorded                   | Active Sowing germinated_count NULL                         | Unknown is not zero, failure or final outcome                                      |
| Germination recorded                | Active Sowing germinated_count > 0                          | Counts sowings, not seedlings; NULL/zero excluded                                  |
| Zero recorded                       | Active Sowing germinated_count = 0                          | Not labelled failed; no finality inferred                                          |
| Purchase packets without Order link | Active purchased/purchased_fruit SeedLot with order_id NULL | Other sources/lifecycles excluded; optional review, no completion inference        |
| With confirmed WFO link             | Current identity with retained WfoLink                      | Explicit confirmed link, not proof of taxonomy correctness                         |
| With profile content                | Current identity with any profile text or native-range row  | Empty shells excluded; no completeness/quality inference                           |

Upcoming: five planned items, due_on then UUID ascending, including overdue and later work; retain
exact target/lifecycle or collection-wide context. Recent: six existing History rows, keeping date
precision, recorded fallback and reversal state. Legacy all-identity/all-Event totals are retained
in the API but not displayed as current holdings. No rates, financial KPIs or trend percentages.

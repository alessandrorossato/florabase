# Florabase Next M8 final UX: Activity identities and Settings (proposal)

**Status:** design only, awaiting operator review. No frontend code changed for this proposal.
Canvas page 6 of https://claude.ai/artifact/EZkPPeaXAXm151sJmbUPCq holds the boards (before
captures at `dba7078`, three Activity experiences, phone, Settings). All data is the real
synthetic UAT content: 3 Journal entries, 7 History facts, 16 planned Schedule items (8 overdue).

## Three related, different experiences

| | Journal | History | Schedule |
| - | ------- | ------- | -------- |
| Character | A field journal: read what was observed | An audit trail: scan what changed | A planning workspace: decide what to do next |
| Layout | Single reading column (≈880px), entries under headings of their recorded precision ("4 November 2026", "Date not recorded") | Full-width ruled table: When · Category · What happened · Record · Related · State; one line per fact | Agenda lanes (Overdue · Today · Next 7 days · Later) or a Month grid with a selected-day panel |
| Type | Record title in the serif; the **note** is the body text in the serif at reading size; kind as a small eyebrow | UI face only, compact 13px rows, Plex Mono timestamps with their basis (occurred · day/month, or recorded · UTC) | UI face, kind in mono caps, ages in words ("4 days overdue", "in 2 days") |
| Images | The target record's own primary photo as a small mounted print, captioned as the record's photo, never as the observation's | None (scan speed) | None |
| Actions | Existing Record ▾, Filters, Saved views; entry links | Existing Filters and Saved views; the existing category filter also as one-tap chips | Complete and ⋯ on every row; Schedule activity; "Schedule on this day" from the day panel |
| Honesty | Only recorded entries; precision headings never invent a day | `occurred` vs `recorded` shown on every row; applied/reversed state shown | Overdue = planned, not recorded as done; nothing planned appears in Journal or History |

Month view: each cell shows a count badge, up to three titles with a kind dot (overdue ones on a
warm tint with a ring), `+N more`, today as a filled date, and a full-height day panel listing every
item with its actions. Fixes the M7/M8 clipping of "Planned · Overdue" chips in narrow cells.

Phone: the Activity strip switches the three; Journal keeps the reading column, History becomes
two-line rows (time and basis, then category · title · record → related), Schedule keeps lanes with
a full-width Complete button.

## Settings

- Settings workspace: **Theme · Labels · Import / Export**. The destination label "Settings"
  becomes "Theme" (route `#/settings` unchanged, so every existing link and Saved View keeps
  working; no redirect needed).
- Theme: colour theme and appearance only. The General section and the Tools cards are removed.
- Labels: a **QR destination** section at the top: what the address does ("encoded in every QR code
  you print … labels already printed keep the address they were printed with"), the current value
  or a warning that printing is unavailable, and "Set/Change address" using the existing
  `QrDestinationDialog`, settings API and validation. Print stays disabled while unset.
- The phone account sheet derives from the same workspace list, so it shows the same three entries.

## Implementation plan after approval

1. Settings IA (navigation label, Theme page content, Labels QR section) with tests for routes,
   persistence, validation and disabled print.
2. Journal reading layout (EventJournal / GlobalEventsScreen presentation only).
3. History table layout (HistoryScreen presentation only).
4. Schedule Agenda lanes and Month cells + day panel (ScheduleScreen / ScheduleCalendar presentation).
5. Focused tests, full regression, deep-link checks, light/dark desktop/phone captures with state
   assertions; stop for acceptance.

## Questions for review

- History category chips: show them inline (as drawn) or keep categories only in Filters?
- Month day panel: always visible on desktop (as drawn) or opened by selecting a day?

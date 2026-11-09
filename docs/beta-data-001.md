# BETA-DATA-001 — first collection onboarding

Use the [CSV format guide](import-export.md) and the [private inventory and
reconciliation templates](beta-data-001-templates.md) to prepare a pilot. Rehearse
with synthetic records in this worktree's isolated UAT instance or disposable
PostgreSQL. Production entry requires separate operator authorization after the
published release and the Synology checks below are accepted.

## Choose the installation path

Main contains the source and release packaging for Portable Compose. Before an
installation, verify that the authorized GitHub Release actually has the
attested assets and that its pinned images are available. The beta.6 version
in source, a tag or a rehearsal artifact does not establish publication.

| Path | Installation and maintenance authority |
| --- | --- |
| [Portable Compose](portable-installation.md) | Verify the published `portable-compose.yaml` and manifest against the approved source commit. Keep the stack's exact project name, private configuration and dedicated local PostgreSQL/media binds. Use the guide's explicit empty-cluster initialization, `release_schema init`, and owner bootstrap before bringing up the full stack. For upgrades, stop writers, take the paired backup with the old file, check that the PostgreSQL digest is unchanged, and use the target backend's `release_schema upgrade` with the previous head. Restore into fresh paths and a distinct project, port and private HTTPS origin. Keep the existing data until recovery is validated. |
| [Advanced controller bundle](installation.md) | Use the verified bundle and manifest with `florabasectl.py` for preflight, install, backup, promotion, journaling and restore. Follow the [runtime runbook](beta-runtime-001.md) for interrupted and failed promotion. Retain this path for an installation already managed by the controller unless the operator explicitly approves a separately validated transfer. |

Keep manager updates, Git sync and unattended redeploys disabled in either
path. Serialize operator maintenance with Dockhand actions. For a planned
controller-to-portable transfer, use a verified paired logical dump and media
archive and validate a compatible portable restore before switching traffic.
Keep the original binds separate from the restore.

## Prepare the private source inventory

Keep source files, contact details, receipts, exact collecting coordinates, original
photos and the reconciliation ledger in protected operator storage. For each
sheet, register or folder, record its owner, source key, row or file count, target
kind, known links, required field gaps and planned handling. Keep source values
alongside normalized values so corrections can be traced. Record expected creates,
explicit reuses, updates and held rows for each batch. Map each source key to the
confirmed Florabase UUID after apply. Import keys prefixed with `@` are local
Location parent references within one CSV. Keep your source keys in the ledger.

Use UTF-8 blank templates from **Tools → Import / Export** and keep date cells as
text in spreadsheets. Preserve PartialDate precision as `YYYY`, `YYYY-MM` or
`YYYY-MM-DD`. Leave unknown optional dates and quantities empty. Keep explicit
zero where the domain accepts it, and distinguish approximate and exact counts.
Hold ambiguous dates such as `03/04/2023` for source review. When the source only
gives a season, range, tentative identification or ambiguous place, keep its
wording in the ledger or suitable notes and enter only supported, established
facts. A required field with no defensible value blocks that row.

| Source meaning | Florabase mapping and validation |
| --- | --- |
| Taxon, cultivar and common name | **BotanicalIdentity CSV.** Separate scientific and unquoted cultivar names. Review the case-insensitive name/cultivar tuple. Choose Use existing only when it is the same identity. Correct names in the identity workflow and review the records that share it. |
| Acquisition party and contacts | **Supplier CSV.** Map name and kind, then known contact fields. Review same-name candidates and current/retired state. Update existing shows a diff and keeps fields whose CSV cells are blank. Use the Supplier edit form to clear a field deliberately. Hold rows where the required kind cannot be established. |
| Physical shelf, bed, tray or drawer | **Location CSV.** Map name, parent and usage scopes, including `harvest_inventory` for stored material. Use a full displayed path for existing references. Scopes are explicit on each Location and do not inherit. Verify stored-material scope in Location details because CSV export omits it. |
| Material origin and collecting site | **Manual GeographicPlace and ProvenanceSite.** Use the geographic hierarchy and the specific site only when supported by the source. Enter a coordinate pair only when both values are known and appropriately precise. CSV `geographic_place_ref` and `provenance_site_ref` can point to these existing records. Keep acquisition party, native range, physical storage and actual material provenance separate. |
| Invoice, purchase or order | **Manual Order and SeedLot link.** Enter the known supplier, order reference, partial order date and amount/currency if recorded. Link an existing lot or create it from the Order. Review purchase-context choices before applying a conflicting supplier or date. An order date and a material acquisition date can differ. Keep invoice details outside the app when no matching field exists. |
| Seed packet, accession or produced seeds | **SeedLot CSV** for independent lots. Map identity, packet label, source kind, optional supplier/provenance/storage and partial acquisition, harvest or viability dates. Use count or weight with the correct unit and certainty. An existing producer UUID can identify one Plant or PlantGroup for collection-produced seed. Use the Harvest conversion workflow when the source is tracked harvested material. |
| Sowing and germination | **Manual Sowing.** Start from the known SeedLot or choose the supported direct identity flow when no lot relationship is known. Record date, known quantity and sowing Location. Capture germination observations separately. Check the lot relationship and confirm that recording a Sowing does not deduct stock. |
| Individual specimen or group | **Plant / PlantGroup CSV** for direct origins. Map identity, label, entry date, direct source and Location. Group count and certainty are separate. Create manually from the Sowing when ancestry is known. Use the owning operation for propagation or extraction when the source relationship matters. |
| Observation, movement or scheduled work | **Manual Event or Schedule.** Pick the actual target and preserve available Event date precision. Record a movement or lifecycle action only if its effect should apply to present state. Editing or deleting an Event does not replay or undo its original effect. Verify current state separately when correcting history. |
| Harvest and material lines | **Manual Harvest.** Choose exactly one source Plant or PlantGroup and at least one material line. Record date and material kind, with a positive count or weight and unit where known. Leave an unmeasured line quantity unknown. Check the source relationship and totals after a correction. |
| Retained harvested material | **Manual Stored Material.** Start tracking from a Harvest line and record known Location and quantity/disposition in the relevant workflow. Reconcile remaining stock with its history. Use the seed conversion action for eligible tracked seed material, then check the new lot and stock change. Hold unsupported stock with no defensible Harvest source in the ledger. |
| Photos and other source files | **Manual media.** Upload single-frame JPEG, PNG or WebP originals (up to 25 MiB) to a supported gallery, or reuse an asset on supported targets. Check captions, order, covers and authenticated original access. Keep files such as HEIC originals and PDF receipts in protected source storage. Unlink one record and confirm shared media still opens elsewhere before considering asset deletion. |

Only BotanicalIdentity, Supplier, Location, SeedLot, Plant and PlantGroup have
CSV import. Orders, provenance records, Sowings and germination, Events and
schedules, Harvests and stored material, propagation and conversion operations,
and media require the manual workflows above.

## First-use sequence and rehearsal

For local browser rehearsal, use [Multi-Branch UAT](development-workflow.md#uat-instances-parallel-per-worktree).
Run `make uat-instance-list`, then `make uat-instance-up PROFILE=smoke`,
`make uat-instance-seed` and `make uat-instance-status` in the owning worktree.
Use the reported loopback port and a separate browser profile. The seeded data
are a baseline. Use unique synthetic names and compare each batch's count
delta and UUIDs. Rehearsal writes change the baseline, so a subsequent golden
validation is expected to report changes. Stop to retain the instance or
remove only its exact project with the workflow's confirmation. A source UAT
result is collection evidence and leaves the published images and NAS untested.

1. Before live data entry, complete the Synology checklist and obtain explicit
   owner approval. In a disposable test collection, use the six downloadable
   examples to rehearse Preview and Apply. Expect respectively 2 identities,
   1 supplier, 2 locations, 2 lots, 1 plant and 1 group. Check the drawer's
   parent, the Paracress lot's supplier and drawer, and the specimen and
   clump's identity and location. Check that year, month and unknown values
   survive export. Use a new test collection for a fresh replay.
2. Start the first approved batch with a small, traceable slice that includes
   one complete chain and one record with unknown fields. Create identities,
   suppliers and Locations first, then manually create the geographic places
   and sites that the slice needs. Enter known orders. Import independent lots,
   plants and groups when their references exist. Reorder batches when a lot
   references a known producer. Build records with known ancestry or tracked
   stock in the corresponding manual workflows to preserve links.
3. Record baseline counts, then preview every file. Resolve repeated names against the real candidate or an
   existing UUID. Revalidate after any edit or expired confirmation. In the
   test collection, pair a valid row with an unresolved reference and check that
   the file cannot apply and counts are unchanged. For application failures,
   reconcile the whole file before retrying. Preview is read-only and each Apply
   is atomic per file. The 15-minute confirmation binds the session, reviewed
   choices and file contents.
4. After every Apply, compare created, reused and updated counts with the ledger.
   Spot-check details and exports for UUID links, scope, precision and unknown
   values. For identified existing lots, plants and groups, `record_ref` causes
   a conflict. **A replay without `record_ref` can create duplicates**, even
   with identical labels and source fields. If the result is uncertain, inspect
   saved records and reconcile before applying again. Use record-specific
   correction workflows instead of replaying the CSV.
5. In the test collection, link a purchased lot to an order with a different
   known date or supplier. Review the proposed changes, cancel once, and
   verify both records are unchanged. Then apply a reviewed choice and verify
   the saved link and retained date precision. Sow the lot, record
   germination, and create a Plant or PlantGroup from that Sowing. Add an
   observation and a scheduled follow-up. Harvest from the linked source, track
   a line, correct a quantity and convert eligible seed into a new lot. Review
   History and stock before and after. Upload a synthetic image, reuse it on a
   second supported record, edit the first caption and unlink it there. Confirm
   the second record still opens the same original bytes and keeps its own
   caption. Record links, expected effects
   and actual results. Finish the live pilot with reconciliation and a verified
   paired backup before widening the batch.

## Size the manual queue

The synthetic UAT trial used four one-time writes for a new GeographicPlace,
ProvenanceSite, Order and reviewed purchase link. Three downstream chains each
required 12 writes: Sowing, germination, Plant-from-Sowing, observation, schedule,
Harvest, tracking, stock correction, seed conversion, photo upload, second
photo link and first photo unlink. Each was checked for the expected ancestry,
stock or retained-original behavior. The scripted HTTP chains took 0.11–0.25 s
each on the local test machine. That measures request execution only. Human
field entry, source review, decisions and reconciliation need separate timing.

At 100 chains of this shape, plan for 1,200 downstream save actions plus
setup, review and reconciliation. For a narrower scope, count each required
action separately and omit actions absent from the source. Time representative
slices in the browser, including corrections and link checks, and compare
`count × measured minutes per action` with the owner's onboarding budget.
Hold the slice if it exceeds that budget or the source relationships cannot be
represented. Use the measured queue to scope any follow-up.

## Synology DS224+ acceptance checklist

Every item below is pending host evidence. Keep a private record with time,
operator, exact release and manifest hash, all three image digests, Alembic
revision, test scope, results and evidence location. Use an authorized isolated
synthetic installation for write and failure drills.

- [ ] **Published bundle and host.** Verify the required published assets and
  approved source commit for the selected path above. Stop if the assets,
  attestations or immutable images are unavailable. For the advanced bundle,
  also capture controller preflight. Record DSM, Engine, Compose, Python
  where needed, architecture, resources and capacity alongside normal NAS workloads.
- [ ] **Durable storage.** Verify the PostgreSQL and media
  binds resolve to the intended local NAS paths and keep stable
  identities. Check DSM ACLs and ownership (DB 70:70, media 10001:10001, both
  0700) and protect secrets, stack state and backups. Record a synthetic
  database marker and original media checksum before restart and reboot.
- [ ] **HTTPS, owner and network boundary.** Confirm Tailscale Serve on the exact
  configured HTTPS origin. Check `/api/v1/ready` and owner login, session reload,
  logout, secure cookies, rejection of wrong Origin or missing CSRF, and
  denial of unauthenticated originals. Test desktop and mobile. From a
  separate LAN device on the same segment verify the loopback-published port
  is unreachable, particularly on Engine versions before 28. Verify that the
  backend and PostgreSQL have no published ports. For the advanced bundle
  also run the [controller acceptance command](installation.md#5-put-florabase-behind-https-and-check-readiness).
- [ ] **Dockhand exclusions.** Record the pinned version and behavior. Verify
  environment automatic updates are disabled and no per-container or stack
  override permits updates. The advanced bundle supplies
  `dockhand.update=false` on frontend, backend and PostgreSQL. The current
  Portable Compose template omits those labels. If using Portable Compose
  with Dockhand, hold acceptance until the required exclusions are applied
  through a separately approved configuration and proven on all three services.
  Disable Git sync and update webhooks. For Portable Compose, preserve the
  exact project and configuration used by the documented maintenance
  commands. For a controller stack, adopt in place only when original project,
  stack, environment and secrets paths are preserved, and leave stack editing
  disabled. Otherwise use inspection only. Protect Dockhand access and back up
  its data and encryption key. Check
  image digests remain unchanged after restart. Run explicit upgrades via the
  selected path. A PostgreSQL digest change requires separate maintenance.
- [ ] **Paired recovery.** Take and verify the selected path's paired backup.
  For Portable Compose use the documented stopped-writer dump, media archive
  and checksum procedure. For the advanced bundle use `backup` and
  `verify-backup`. Keep independent encrypted copies and verify off-host
  retrieval and custody of keys, installation configuration and verified
  bundles. Run the selected path's isolated restore and compare revision, counts,
  representative relationships, owner login, and checksums for shared,
  unlinked and saved originals. Time retrieval and usable recovery against
  owner-approved RPO/RTO and record retention. For the advanced bundle,
  retire only the named drill project using `restore-remove`. For Portable
  Compose stop the distinct drill stack and retain its files per the drill plan.
- [ ] **Reboot, failure and recovery.** Reboot the NAS in a scheduled window.
  Check HTTPS, readiness, owner login, durable paths, database marker and
  original checksum. In the isolated drill, exercise backend and DB failure,
  interrupted promotion and failed application or migration. Record readiness
  refusal, quiescence and recovery. With Portable Compose keep writers
  stopped, establish the actual schema revision before retrying and restore
  the old verified set into fresh paths when reverting a successful schema
  change. With the advanced bundle use controller `status` to choose
  `resume` for interruption, `abort` only when the prior schema still holds,
  or the documented forward fix or verified replacement restore when required.
  Record the owner's post-snapshot data-loss decision before any replacement.
- [ ] **Beta admission.** Once separately authorized, run the actual-data pilot
  and agree on unresolved data decisions. Record the BETA-ACCEPTANCE-001 soak
  (proposed seven days), disk and log growth, resource headroom, backup results,
  desktop/mobile use, reboot and a planned compatible application upgrade.
  Record independent QA, canonical FULL and protected checks for the accepted
  release tree, and obtain explicit owner sign-off.

## Pending evidence and blockers

| Item | Decision required |
| --- | --- |
| Representative operator files and media were unavailable for this increment | Privately inventory headers, meanings, counts, duplicates, unsupported files and a sample of source links. Confirm precision, provenance and acquisition decisions with the owner. Record approval outside Git. |
| Required lineage and unsupported import kinds are manual | Measure record counts and minutes per representative slice. If required lineage or historical corrections cannot be represented, or manual work exceeds the owner's onboarding budget, hold affected rows and scope a bounded follow-up using that evidence. No new importer is justified by synthetic volume alone. |
| Create-only CSV replay can duplicate collection rows | Use small batches and a durable source-key to UUID ledger. If operators cannot reliably reconcile a slice, hold that slice. |
| Location CSV export omits the stored-material scope | Record expected scopes in the source mapping and verify `harvest_inventory` in Location details. A Location without that scope refuses tracking. Use a paired backup for full-fidelity recovery. |
| Portable Compose with Dockhand lacks built-in service update exclusions | Close the exclusions checklist on the pinned Dockhand environment before accepting this path, or qualify the advanced bundle instead. |
| Published release and real-host acceptance | Obtain the authorized attested release, then close the checklist. Earlier disposable runtime evidence does not establish Synology, Dockhand, HTTPS or off-host recovery acceptance. |

BETA-DATA-001 remains in progress pending the private inventory and operator
review. BETA-ACCEPTANCE-001 remains a separate admission gate.

# PHYLOGENY-001 source decision — Open Tree of Life

Audit date: **2026-10-09**. Decision: **SOURCE_BLOCKED** for production ingestion,
redistribution and collection phylogeny implementation. Acquisition and source identity were
verified; the exact-release data-rights review did not pass. This is an approval gap, not a finding
that Open Tree prohibits synthetic-tree reuse. No product behavior or source installation follows
this audit. PHYLOGENY-001 remains **planned**.

## Exact artifact and current official state

The [official release page](https://tree.opentreeoflife.org/about/synthesis-release/v16.1)
links the [tree/annotations archive](https://files.opentreeoflife.org/synthesis/opentree16.1/opentree16.1_tree.tgz)
and [pipeline output](https://files.opentreeoflife.org/synthesis/opentree16.1/output/index.html).
The official synthesis directory's highest numbered listed release and the live
`POST https://api.opentreeoflife.org/v3/tree_of_life/about` both identify **opentree16.1**.
No newer release was found in those official sources during this audit.

The release page has conflicting text: its heading/table identify 16.1, but its opening sentence
calls the release 15.1 and gives **20 June 2025**. Do not repeat that date as the verified artifact
date. Actual downloaded `annotations.json` and the current API agree on completion
**2025-12-20 00:55:58**; the pipeline index reports **2025-12-20 01:09:33**. These upstream
timestamps have no timezone. The official archive directory reports upload on 20 December 2025.
The discrepancy is recorded rather than silently normalised. The artifact itself is consistently
identified by synth ID, taxonomy version, counts and content hash.

- Secure HTTPS archive retrieval completed **2026-10-09T18:07:57.179176Z** (local file completion
  timestamp); **41,608,973 bytes**.
- Measured archive SHA-256:
  `c447c83e49f0cf61fa96d9a02c6135b809abf315ad384fdb26b88359a28da12c`.
  This is a locally computed fingerprint, not a publisher signature or advertised checksum.
- `labelled_supertree/labelled_supertree.tre`: **31,386,015 bytes**, SHA-256
  `81f424eb42a0c78e98d2f9f2c61bdabf25e7946a5e2fd104772cb7ee3e18629b`.
- Named full tree: **86,411,875 bytes**, SHA-256
  `6a75d773256aa3c335eadc4854b3516272463343ca407d307b760bcd0b4284b8`.
- Annotation file: **60,756,130 bytes**, **341,228 annotated nodes**. Its metadata identifies
  **2,385,875 tips**, **1,931 input studies**, **2,064 input trees**, root **OTT 93302**
  (cellular organisms), taxonomy **3.7draft3**. Configuration specifies **ott3.7.3**.
- Archive members also include grafted trees and README. There is no LICENSE/NOTICE member;
  the README explains files but does not state release-specific reuse terms. Annotation metadata
  contains no license field.

These bytes were inspected in `/tmp/florabase-phylogeny-audit/`; they were neither committed nor
installed as Florabase reference data. No TLS bypass, mirror substitution or collection transmission.

## Data rights: evidence for and against an exact GO

The current [Open Tree data-rights page](https://tree.opentreeoflife.org/about/licenses) gives CC0
subject to pre-existing terms. The official
[phylesystem-1 README](https://raw.githubusercontent.com/OpenTreeOfLife/phylesystem-1/master/README.md)
explicitly distinguishes CC0 data from publicly released data without a particular license/waiver,
and requests original study/publication and deposit citations. Neither public access nor the software
license establishes a uniform license for the embedded input trees.

There is significant positive evidence for **synthetic-only** reuse: the project authors' published
[2017 ABI proposal, section 6.2](https://phylo.bio.ku.edu/ot/2017-OpenTree-ABI-proposal.pdf)
states that project-produced synthetic-tree and OTT artifacts use CC0, separately from uploaded
study license fields. This supports the preferred minimal derived-topology approach and must not be
omitted from the decision. However, it predates the inspected 2025 artifact. The current conditional
notice and the release package do not establish the precise current boundary for redistributing
this release's topology together with derived support/conflict annotations. An older broad producer
statement is not treated here as clearance of every current embedded source or annotation payload.

To check the caveat concretely, nine **version-pinned** NexSON files referenced by the six prospective
fixture taxa were securely fetched from the official release's `output/phylo_snapshot/` directory.
The source metadata was inspected; the article's publication license was not substituted for the
data license. Three have CC0 fields, one has an empty license field, and five lack that field:

| Exact input tree | Recorded `^xhtml:license`          | Snapshot SHA-256                                                   |
| ---------------- | ---------------------------------- | ------------------------------------------------------------------ |
| ot_1961@tree1    | CC0                                | `dd1220a00068c924ebc6d4a8ba844e2ebf76efcb315e9ae47350d0d5195c641f` |
| ot_311@tree1     | CC0                                | `02439bd6011961fbd75143b73ce9046434af67694484c0d481c636dc6bfebd65` |
| ot_502@tree1     | CC0                                | `24bf9a2945c8869d855301a7b68141373f1e5692cba9f3c9ecf27258954c3b84` |
| ot_2291@tree7    | Empty href/name                    | `90db17fc7c2dc21595dfcf8e679f3d363c553a95b00ef1b77b6aba66f655bc72` |
| ot_2304@tree2    | Missing                            | `16a595ace9d2c4f7cf92aec0496a36a0120e82002800e844f698e4125f2ef52c` |
| ot_2304@tree4    | Missing; same study bytes as tree2 | `16a595ace9d2c4f7cf92aec0496a36a0120e82002800e844f698e4125f2ef52c` |
| pg_1118@tree2226 | Missing                            | `c9df85b26499db86172cdbdf822a768fe9f42f71fbdcf936e12c686da6dc5911` |
| pg_588@tree878   | Missing                            | `2bb8dbd3db697e03dcd74d81d59c6a5793d7d310db480dc08fcf664373209a36` |
| pg_713@tree1287  | Missing                            | `b30784ddcb11e566a5219cb17448dc4360147f0d54d3a85355e5919259a7efa4` |

Exact file URLs use
`https://files.opentreeoflife.org/synthesis/opentree16.1/output/phylo_snapshot/tree_<study>@<tree>.json`.
These are a bounded sample, not an audit of all 1,931 studies. Missing license fields do not prove
the underlying data are restricted, nor do they prove that derived synthetic facts are restricted.
They do prevent blanket approval of the input contents under this task's explicit review boundary.

**Reopening criterion:** obtain current authoritative terms explicitly covering the exact synthetic
release and the minimal support/conflict assertion representation Florabase would redistribute,
including the treatment of pre-existing restrictions and required credits. Alternatively, establish
an exact licensed source subset with reviewed synthesis/acquisition semantics; simply deleting
conflicting/unlicensed inputs from the already synthesised result would change the scientific model
and is not an approved workaround. No contact to maintainers was sent.

The preferred permitted-content target remains topology, OTT/synthetic IDs and bounded derived
annotation facts with study references. Original source-tree Newick/NexSON, figures, publication
prose and full pipeline outputs should not be shipped. A minimal representation reduces scope;
its permission boundary must still be established before a production GO. No complete source-tree
rights clearance is implied or demanded when an authoritative synthetic-only grant resolves it.

## Provenance and annotations

The [annotation directory](https://files.opentreeoflife.org/synthesis/opentree16.1/output/annotated_supertree/index.html)
separates per-edge statements (`annotations1.json`) from pipeline/input metadata
(`annotations2.json`); the archive's `annotations.json` combines them. Observed node fields are
`supported_by`, `conflicts_with`, `resolves`, `partial_path_of`, `terminal`, `was_constrained` and
`was_uncontested`. A `terminal` reference alone must not be relabelled phylogenetic support.
Missing annotation is not sufficient evidence for either a supported or taxonomy-only placement.

All 2,064 archive `source_id_map` entries have empty `git_sha`; generated-by metadata gives unknown
propinquity/peyotl Git SHAs, but a concrete otcetera SHA
`ff953b2a806c9dd9755e888365a419198f257a48`. The live API source map also lacks input SHAs.
This does **not** make all provenance unavailable: the official
[phylo_snapshot index](https://files.opentreeoflife.org/synthesis/opentree16.1/output/phylo_snapshot/index.html)
contains source Git-object SHAs, immutable release copies and a `concrete_rank_collection.json`.
Future provisioning must retain that exact snapshot evidence when citations/annotations need it,
rather than resolving a study ID against today's mutable phylesystem. The archive checksum pins the
actual result despite unknown generator revisions. Provenance deficiencies are recorded separately
from the blocking rights decision; they are not presented as an irrecoverable provenance failure.

## Topology and uncertainty: actual source probes

The archive distinguishes the full labelled supertree from the grafted tree without taxonomy-only
outputs. Full synthesis combines published phylogenetic estimates with taxonomy; it is neither a
classification hierarchy nor a dated species tree. In the current node-info API, a `supported_by`
entry keyed **ott3.7draft3** identifies taxonomy evidence; study/tree keys identify phylogeny evidence.
Mixed evidence and conflicts may coexist. Counts of supporting trees are not confidence scores.

Official `POST /v3/tree_of_life/induced_subtree` was exercised with six public source examples,
using OTT IDs below and `label_format=id`. It returned **6 tips, 156 total nodes, 145 unary nodes,
maximum depth 59**, root **ott5298374**, no duplicate IDs or polytomy in this particular response,
27 supporting tree references and an empty `broken` object. The measured response is **3,667 bytes**,
SHA-256 `faf2fe71ebdf1abc2ee0344abd3ea44e8f72b14b984c5d8c0cd830ea87639d62`.
This sample establishes induced-subtree capability, not general topology validation or coverage.

`node_info` for basil and sage with ancestral paths showed respectively **69** and **65** ancestors,
with conflicts on **59** and **52** of those nodes. Both have taxonomy-only support at OTT 304358
and OTT 93302. The combined response was **191,730 bytes**. The TAXONOMY-003 depth limit of 64
cannot be copied blindly into a phylogeny implementation. A display may compress unary paths only
while preserving every original intervening edge's evidence; it must not assign one retained node's
support to a newly collapsed composite edge. Polytomies require actual multi-child presentation.

The ID-labelled full tree and the sampled induced tree contain no branch-length fields. Colons
inside some _named_ labels are not branch lengths. Render a topological cladogram only: graphical
edge spacing is layout, with no genetic percentage, distance or divergence-date claim. Published
input trees' individual lengths/dates cannot be silently combined into the synthetic result.
MRCA could be an exact shared node in a pinned synthetic topology, independently of taxonomic MRCA;
no MRCA UI or dating policy is implemented/approved by these probes.

## Exact taxon identity and mapping

These real names/IDs were checked against the named archive. They are source-audit examples, not
confirmed Florabase relationships or approved fixture links:

| Source name            | OTT ID |
| ---------------------- | -----: |
| Ocimum basilicum       | 305911 |
| Ocimum tenuiflorum     | 782204 |
| Salvia officinalis     | 820645 |
| Aloe vera              |  62303 |
| Raphanus sativus       | 359073 |
| Lavandula angustifolia | 880708 |

An explicit TNRS probe with approximate matching disabled returned non-synonym, non-approximate
candidates for basil, Holy basil and sage. This proves candidate availability only. Even a unique
exact name result is not operator confirmation. TNRS must expose submitted/current/matched name,
rank, OTT ID, synonym/accepted context, higher taxonomy and diagnostics before a durable link.
Ambiguous/no-match outcomes remain unresolved. No WFO-to-OTT crosswalk was approved. Basil's actual
`tax_sources` are NCBI, GBIF and IRMNG, not WFO; the GBIF number is not Florabase's CoL XR link ID.

OTT taxon identifiers and synthetic node identifiers are different contracts. `ott...` nodes may
correspond to taxa; `mrcaott...ott...` nodes can be unnamed synthetic nodes. Neither string form
establishes a biological name, stable cross-release topology or a divergence date. OTT identifiers
must be version-revalidated (the taxonomy API can resolve aliases), and synthetic node selection
must carry release context. No family/genus-derived evolutionary relationships.

The archive contains basil variety tips as well as the species concept. Future cultivar and
infraspecific mapping must be reviewed explicitly: multiple separate Florabase identities may map
to one species-oriented source tip, retaining their separate detail records without invented
evolutionary branches. No policy is silently enforced here.

## Acquisition/index options and runtime boundary

Two approaches were evaluated, neither installed or approved for production at this gate:

1. **Pinned local release/index:** full ID tree plus source taxonomy and annotations, indexed once
   during explicit provisioning. Ordinary reads would prune/index required source paths, not parse
   millions of nodes or perform a lookup per tip. Archive footprint above is measured; a Florabase
   index footprint, build time and peak memory are **not measured**.
2. **Explicit bounded induced-tree provisioning:** transmit only deliberately reviewed OTT IDs,
   check API synth/OTT version before and after retrieval, preserve necessary node/path annotations,
   save a content-hashed reference artifact, and perform ordinary collection reads locally.
   The API's documented methods use the _current_ synthetic tree, not an arbitrary historical
   version parameter; checking only a configured version string is insufficient to pin retrieval.
   Changes/failures must leave the previous artifact and confirmed links intact. Refresh is explicit.

The second option is attractive for the host's limited resources and avoids storing the full global
tree. It still needs a reviewed artifact publication contract, source failure behavior, bounds and
mapping revalidation. It is not implemented as a live page-load proxy. No user collection was sent
during this audit: probes used fixed public source examples, independently of the local database.

Canonical PostgreSQL should hold only minimal confirmed mapping/provenance if this feature proceeds;
optional tree/index files are reference artifacts. Startup, Taxonomy and normal collection workflows
must remain healthy without them. This audit adds no table, migration, setting, route or cache.

## Verification and limits

- Complete feature graph inspected and validated: **98 features**; existing PHYLOGENY-001 retained.
- Existing focused offline baseline: **54 passed**, `--no-cov`, across taxonomy source/service/API,
  Native ranges Explore and Species distribution. Current worktree source mounted read-only in the
  installed UAT development image, network disabled, no DB/application volumes, no image build.
- Actual archive members, hashes, metadata, annotation fields, nine input-license samples, name
  candidates, node-support/path evidence and induced Newick structure inspected securely.
- No full-global-tree duplicate/cycle validator, index, mapping implementation, PostgreSQL suite,
  frontend phylogeny suite, performance benchmark or production build is claimed.
- Read-only UAT status: actual owner `748b`, frontend/backend/db healthy, migration **0040**;
  source mismatch correctly refused takeover by `4aaf`. Existing Preview was preserved.
- Host had approximately **327 MiB free disk**, full 2 GiB swap and resource pressure during audit.
  This is an operational constraint, **not** the source-rights blocker. A costly named-label regex
  scan was interrupted and replaced with bounded delimiter tokenisation; it produced no product
  artifacts or modifications to running stacks.
- At the original source-audit stop, canonical verification, staging, commit, delivery and finish
  had not yet run. This source decision remains unchanged by the subsequent independently reviewed
  documentation delivery; see the progress milestone for final verification evidence.

The [planned workspace contract](collection-phylogeny.md) and
[blocked implementation handoff](phylogeny-001-handoff.md) describe the preserved boundaries.

# Directory interaction cleanup — historical candidate

**Superseded:** the operator explicitly replaced this Preview/action-menu contract with the
[final interaction correction](../final-interaction-correction/README.md). Its 412-test result
and screenshots are retained as historical evidence only.

Follow-up to checkpoint `db1e71fb85f1396408ed6f07800d4992dea0233d`.
Pending final operator UAT; no FULL or protected delivery.

This contract supersedes symbolic status and always-visible row actions in the earlier
consolidation specification. Directory statuses use compact textual lifecycle chips. Each
record has one bordered More actions trigger; its existing domain controls, Details and Edit
remain owned by the page. Stored material retains exact-inventory Details and its existing
print/conversion operations, rather than introducing a misleading generic inventory editor.
Historical Harvests and identities retain their existing absence of an invented lifecycle.

The existing OverflowMenu supplies portal positioning, keyboard traversal, outside dismissal
and Escape. Opted-in directory menus retain mounted domain components, preserving owned
conversion/association dialogs. Command buttons leave the menu available beneath their editor
so returning from a dialog retains context; navigation links dismiss it. Menu events do not
bubble into the record preview handler. Details/Edit callbacks receive the persistent menu
trigger for return focus. Other OverflowMenu consumers retain their defaults.

Selected records use a subtle fill without the inset left stripe. Hover and keyboard outline
remain distinct. More actions uses the shared bordered icon-button dimensions, radius and
interaction states. Menu controls expose readable labels, including formerly icon-only domain
operations. Hierarchy and specialist workspaces are unchanged.

Browser evidence: `browser-smoke.json` records Preview/Escape/focus and Details for all eight
directories, Edit for all seven existing editor owners, and the exact Stored inventory URL.
`responsive-smoke.json` covers Sowings Gallery, Stored material and identities at 1024/390:
all inspector content panes measured 147px and no document horizontal overflow was observed.
JPEGs show the live menu and stacked inspection states in Mineral Dark. No record was saved
or deleted. These focused captures supersede the relevant interaction states of the earlier
six-theme gallery; they do not constitute a fresh full six-theme audit.

Manual limitations: physical devices, screen readers, native dirty-confirm rejection and
actual browser zoom remain operator checks. Existing automated domain and Batch 1 guard
regressions remain required. Verification totals are recorded in the progress milestone.

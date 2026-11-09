# Private source inventory and reconciliation templates

Copy these headers into private worksheets or text files. They are working
records for the operator. Import files come from the matching Florabase blank
template. Keep source paths, contacts, site coordinates, attachments, identifiers
and review evidence in protected operator storage.

## Source inventory

Use one row per sheet, register or media folder. Give each a stable `source_set`
code. Use a stable per-record `source_key` within that set. If no key exists,
assign one before sorting, splitting or editing the source. Give media files
their own keys and keep a separate association for each target that shares one.

```csv
source_set,private_source_pointer,source_version_or_checksum,source_owner,source_key_rule,source_rows_or_files,target_kinds,planned_csv_rows,planned_manual_rows,held_rows,excluded_rows,known_relationships,required_field_gaps,precision_or_privacy_decisions,reviewer,review_state
```

Add one mapping row per source field or inferred relationship. Record the
original meaning, transformation and rule for unknown, approximate and partial
values. Preserve raw values in the private source. Hold ambiguous mappings for
owner review.

```csv
source_set,source_field,source_meaning,target_kind,target_field,normalization_rule,unknown_rule,precision_rule,reference_source_set,validation_rule,decision_owner,decision_state
```

## Reconciliation ledger

Use one row per source-to-target mapping. When a source maps to several targets,
give each mapping its own target role. For shared media keep asset and association
mappings separately. List dependency keys with their source set and resolve them
to confirmed target UUIDs before creating dependent records. A source key is
never a Florabase UUID.

```csv
source_set,source_key,target_role,target_kind,planned_action,batch_id,csv_record_number,dependency_source_keys,confirmed_dependency_uuids,expected_partial_date,expected_quantity_certainty,expected_location_uuid,florabase_uuid,outcome,checked_at,reviewer,evidence_pointer,hold_or_correction_reason
```

Use planned actions such as `create`, `reuse`, `update`, `manual`, `hold`
and `exclude`. Outcomes can be `pending`, `refused`, `uncertain`, `created`,
`reused`, `updated`, `held` or `excluded`. An uncertain outcome remains
unresolved until saved data and counts establish what happened. Reused records
can map multiple source keys to one UUID after explicit review. For corrections,
record the new result and retain the previous decision and evidence.

Use one batch record per file or manual slice. Keep the submitted byte checksum,
counts before and after, actual Apply result and the reconciliation evidence.

```csv
batch_id,target_kind,method,private_input_pointer,input_sha256,baseline_count,planned_create,planned_reuse,planned_update,planned_hold,actual_create,actual_reuse,actual_update,after_count,preview_evidence,apply_evidence,relationship_check,owner_review,final_state
```

1. Reconcile inventory counts to planned CSV, manual, held and excluded rows.
   Count source rows separately from target mappings when a row splits or merges.
2. Record the baseline export and preview each exact input. Compare references
   against the ledger and record the accepted choices. When a batch succeeds,
   compare Apply counts and expected count delta. Use post-Apply export or
   record details to verify each UUID and its links, date precision and unknowns.
3. If Apply fails or the result is lost, compare the baseline, current data and
   the source keys. Retry only the confirmed missing rows in a fresh preview.
   Put unresolvable rows on hold. A label match alone is insufficient to assert
   that a collection record was created by the batch.
4. Close a batch only after every mapping has an outcome and all confirmed
   targets have verified UUIDs. Save a paired database/media backup at the pilot
   boundary.

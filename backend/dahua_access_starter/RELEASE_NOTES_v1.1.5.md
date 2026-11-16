# Release Notes — Version 1.1.5

## ASI1201E card update/reactivation lookup compatibility

- Changed the card update lookup to use the same unfiltered ACCESSCTLCARD inventory query pattern as the working inventory-list operation.
- The service now enumerates controller card records and matches both the saved native record number and card UID locally before modifying a record.
- This avoids the card-number-filtered FindRecord query that returned `The device does not support current operation` on the reported ASI1201E firmware.
- The update still uses `RECORDSET_UPDATE`; it does not insert a duplicate card.
- Added an offline SDK-mock regression test for the unfiltered lookup and record/UID match.

## Verification boundary

The offline mock and software tests do not prove that the physical controller firmware accepts `RECORDSET_UPDATE`. Test reactivation with the existing card and verify controller inventory and physical access before production use. Do not factory-reset the controller for this test.

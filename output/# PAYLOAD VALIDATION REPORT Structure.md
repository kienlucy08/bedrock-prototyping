# SURVEY VALIDATION REPORT - SITE US632993

## SITE INFO
**Site:** US632993 | **Customer:** Everest
**Tech:** Gabriel Hernandez | **Type:** structure | **Structure:** guy
**Inspected:** 2025-07-15

---

## STATUS: ⚠ NEEDS CORRECTIONS

### SECTION OVERVIEW

**Site Details:** ⚠ FAIL
- Completeness: 90% (core fields complete)
- Critical: 3 | Warnings: 0
- Root cause: apex_height appears incorrect at 404 ft; multiple independent measurements indicate 500 ft actual height

**Location:** ✓ PASS
- Coordinates: 40.066068°, -84.24146792° (6-8 decimals)
- Critical: 0 | Warnings: 0
- Valid western Ohio location, good precision

**Site Photos:** ✓ PASS
- Coverage: 17/17 categories (17 total photos)
- Critical: 0 | Warnings: 0
- Complete structure survey documentation with safety climb system, all cardinal direction photos, tech signature present

**Repeat Records:** 62 records | 142 photos

*Ground Level Infrastructure:* ✓ PASS | 1 record, 4 photos | 0C, 0W
*Tower Mounted Equipment:* ⚠ FAIL | 46 records, 104 photos | 2C, 1W
*Safety Compliance:* ✗ FAIL | 14 records, 17 photos | 4C, 0W

**TOTALS:** 9 critical errors | 1 warning | 85% complete

---

## CRITICAL ERRORS (9)

**Site Details (3):**

1. **site_details - structure_steel_height**
   - Current: 500 ft
   - Required: Must be ≤ apex_height (404 ft)
   - Rule: DIMENSIONAL_CONSISTENCY_STEEL_HEIGHT
   - Fix: Update apex_height to 500 ft (structure_steel_height is correct based on cross-validation)

2. **site_details - safety_climb_top_height**
   - Current: 500 ft
   - Required: Must be ≤ apex_height (404 ft)
   - Rule: DIMENSIONAL_CONSISTENCY_SAFETY_CLIMB
   - Fix: Update apex_height to 500 ft (safety_climb_top_height is correct and matches structure height)

3. **site_details - highest_appurtenance_height**
   - Current: 504 ft
   - Required: Must be ≤ apex_height (404 ft) except lightning rod
   - Rule: DIMENSIONAL_CONSISTENCY_APPURTENANCE
   - Fix: Update apex_height to 500 ft (lightning rod at 504 ft is valid, extends 4 ft above apex)

**Tower Mounted Equipment (2):**

4. **radiation_sources_s - Record [mount at 497 ft] - mount_height**
   - Current: 497 ft
   - Required: Must be ≤ apex_height (404 ft)
   - Rule: MOUNT_HEIGHT_APEX_VALIDATION
   - Fix: Update apex_height to 500 ft (radiation source mount height is valid)

5. **guy_attachment_s - Record #9 - guy_attachment_height**
   - Current: MISSING
   - Required: Numeric value 0 to apex_height, sequential with other levels
   - Rule: GUY_ATTACHMENT_HEIGHT_REQUIRED
   - Fix: Add height measurement for guy attachment level 9

**Safety Compliance (4):**

6. **tia_info_s - Record #2 - tia_location**
   - Current: MISSING
   - Required: Valid location (compass direction, level, or face designation)
   - Rule: TIA_LOCATION_REQUIRED
   - Fix: Add tia_location field specifying where concrete foundation issue (I3.b) is located

7. **tia_info_s - Record #6 - tia_issue**
   - Current: MISSING
   - Required: Valid TIA issue code (likely B2 for rust/corrosion based on context)
   - Rule: TIA_ISSUE_REQUIRED
   - Fix: Add tia_issue code identifying the specific deficiency type

8. **tia_info_s - Record #6 - tia_location**
   - Current: MISSING
   - Required: Valid location (compass direction, level, or face designation)
   - Rule: TIA_LOCATION_REQUIRED
   - Fix: Add tia_location field specifying where the deficiency is located

9. **tia_info_s - Record #14 - tia_height**
   - Current: 500 ft
   - Required: Must be ≤ apex_height (404 ft)
   - Rule: TIA_HEIGHT_APEX_VALIDATION
   - Fix: Update apex_height to 500 ft (TIA height is valid based on actual structure height)

---

## CROSS-VALIDATION FINDINGS

⚠ Critical dimensional inconsistency detected

**Apex Height Discrepancy (ROOT CAUSE):**
- Site Details apex_height: 404 ft
- Site Details structure_steel_height: 500 ft ✗ Exceeds apex by 96 ft
- Site Details safety_climb_top_height: 500 ft ✗ Exceeds apex by 96 ft
- Site Details highest_appurtenance_height: 504 ft ✗ Exceeds apex (valid for lightning rod)
- Tower Equipment radiation source mount: 497 ft ✗ Exceeds apex by 93 ft
- Safety Compliance TIA height: 500 ft ✗ Exceeds apex by 96 ft

**Analysis:** Five independent measurements consistently indicate 500 ft structure height. The apex_height value of 404 ft appears to be a data entry error. Correcting apex_height from 404 to 500 would resolve 5 of 9 critical errors.

**Photo Count Verification:**
- Site Photos: 17 photos
- Ground Infrastructure: 4 photos
- Tower Equipment: 104 photos
- Safety Compliance: 17 photos
- Total verified: 142 photos ✓ Complete documentation

**Structure Type Validation:**
- structure_type="guy" → Requires guy_attachment_s records ✓ Present (9 records)
- Guy attachment count: 9 documented levels ✓ Matches typical 3-leg guy tower with 3 levels per leg

---

## WARNINGS (1)

**Tower Mounted Equipment (1):**
- coax_route (Record #34 - empty mount): Current=MISSING | Recommended=Document route or "N/A" | Note: Optional field improves infrastructure documentation quality

---

## NEXT STEPS

**Priority Actions:**

1. **Site Details:** Fix apex_height (ROOT CAUSE - resolves 5 errors)
   - Update apex_height from 404 ft to 500 ft
   - This will resolve dimensional consistency errors in Site Details (3), Tower Equipment (1), and Safety Compliance (1)
   - Estimated time: 2 min

2. **Tower Mounted Equipment:** Fix guy attachment Record #9
   - Add missing guy_attachment_height measurement for level 9
   - Should be sequential with other 8 guy attachment heights
   - Estimated time: 3 min (may require site documentation review)

3. **Safety Compliance:** Fix 3 TIA records
   - Record #2: Add tia_location for concrete foundation issue (I3.b)
   - Record #6: Add tia_issue code and tia_location
   - Estimated time: 5 min (requires reviewing TIA photos and field notes)

**Total Estimated Time:** 10 minutes
**Site Revisit Required:** No - All corrections are data entry fixes, though Record #9 guy attachment height may require reviewing site documentation or photos

---

## VALIDATION SUMMARY

**Passed Validation Rules:** 53
**Failed Validation Rules:** 9
**Cross-Validations:** 1/4 (dimensional consistency failed due to apex_height error)

**Survey Type Notes:**
Guy structure surveys require precise dimensional data for structural integrity assessment. This survey has comprehensive documentation (62 records, 142 photos, 100% photo coverage) but contains a critical apex_height data entry error that cascades through multiple validation checks. The actual tower height of 500 ft is consistently supported by structure_steel_height, safety_climb_top_height, equipment mounts, and TIA observations. Correcting this single field will resolve the majority of critical errors and restore cross-validation integrity.

---

END OF VALIDATION REPORT
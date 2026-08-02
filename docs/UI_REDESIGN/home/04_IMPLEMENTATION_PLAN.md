# Home — implementation plan and gates

**Mode:** FULL  
**Reference:** `g:\My Drive\AI\A\New folder\TRANGCHU.png` (user supplied)  
**Locked decision:** Q46, 2026-08-02

## Delivery slices

1. Preserve the public catalog at `/` for guests; render the marketplace workspace
   only for authenticated users.
2. Reuse the existing app registry, access filter, credit balance and `jobs` table.
   Recent Activity and Running Jobs are owner-scoped; Popular is aggregate sort
   metadata only.
3. Add the workspace shell: desktop sidebar, compact top bar, Ctrl+K search,
   category/sort controls, responsive cards and right rail.
4. Crop the five cover families from the user-supplied reference image. No generated
   raster assets are used for this implementation.
5. Mark unsupported product areas honestly: Community stays disabled and no Pro
   membership is displayed; card actions route to the real app or its setup state.

## Acceptance gates

| Gate | Evidence required | Result |
|---|---|---|
| G0 Scope | Q46 and 00_BRIEF lock the selected audience, data and rollout | PASS |
| G1 Data | owner isolation test for recent/running jobs; existing credit/app access reused | PASS |
| G2 Visual | desktop and 390px local browser checks; no horizontal overflow | PASS |
| G3 Interaction | Ctrl+K targets search; category/sort/filter operate on rendered cards | PASS |
| G4 Safety | no fake Pro/community, no additional data migration, secret scan clean | pending final gate |
| G5 Regression | targeted and complete Python suite pass | pending final gate |
| G6 Release | build, backup/update and production browser/health verification | pending final gate |

## Rollback

The release rollback remains `deploy\windows\rollback.ps1`. The feature is a
template/CSS route change and introduces no migration; rollback restores the previous
application release. Do not alter production data as part of rollback.

# Phase 02: Symbols Page Fix
Status: ✅ Complete
Dependencies: Phase 01

## Objective
Fix the blank card issue on the Symbols page and add proper loading/empty states.

## Implementation Steps
1. [x] Wrap Symbols list with `isLoading` check.
2. [x] Render Skeletons during load.
3. [x] Add `data.length === 0` check to show "No symbols" message.
4. [x] Ensure symbols display correctly when data arrives.

## Files to Create/Modify
- `src/app/symbols/page.tsx` - Main fix location.

## Test Criteria
- [x] Skeletons visible on page refresh.
- [x] Empty state shown if backend has no symbols.

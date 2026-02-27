# Emergency Recovery & Documentation
## Goal
Fix missing static files error, implement guardrails, and update process documentation.

## Tasks
- [x] **Investigation**: Check `atlas-hub/static` contents.
- [x] **Fix**: Copy missing files from `PM‗Strategic Mind & Pipeline`.
- [x] **Guardrails**: Update `app.py` to auto-recover/copy files if missing.
- [x] **Documentation**:
  - [x] Update `共通仕様書.md` (Integration Architecture).
  - [x] Update `skills.md` (Pre-deployment checks).
  - [x] Update `rule.md` (Environment automation).
- [x] **RCA & Fix**:
    - [x] Verify `atlas-hub/static` content physically.
    - [x] Verify Source Path (Double Low Line vs Underscore).
    - [x] Python-based Copy (Robustness).
    - [ ] Update `app.py` if necessary.

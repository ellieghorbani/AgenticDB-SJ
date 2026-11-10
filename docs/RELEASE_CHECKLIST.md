# v1.0 Release Checklist

## Validation

- [ ] Days 4 and 6–11 benchmark reports exist
- [ ] `python -m scripts.build_day12_release` succeeds
- [ ] `python -m scripts.validate_day12_release` succeeds
- [ ] `python -m pytest -q` succeeds
- [ ] Day 12 smoke test succeeds
- [ ] `/demo` works on desktop and mobile width
- [ ] No `.env`, API key, password, or volume data is tracked

## Documentation

- [ ] README metrics block is generated
- [ ] `docs/FINAL_REPORT.md` is reviewed
- [ ] `docs/CV_BULLETS.md` contains accurate measured values
- [ ] Architecture diagrams render on GitHub
- [ ] Screenshots are added to `docs/images/` if desired

## GitHub

- [ ] Day 12 pull request reviewed and squash merged
- [ ] Feature branch deleted
- [ ] `main` is clean and current
- [ ] `v1.0.0` annotated tag pushed
- [ ] GitHub release created from `v1.0.0`
- [ ] Repository description and topics updated

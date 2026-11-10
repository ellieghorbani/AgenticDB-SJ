# Contributing

1. Create a feature branch from the latest `main`.
2. Keep changes focused and add tests.
3. Run:
   ```bash
   python -m pytest -q
   python -m compileall -q app scripts
   ```
4. Do not commit `.env`, raw credentials, local model caches, or database volumes.
5. Open a pull request with a validation checklist.
6. Use squash merge for one cohesive feature milestone.

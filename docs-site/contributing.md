---
layout: page
title: Contributing
permalink: /contributing/
---

# Contributing

AgentRepoCoach is an early-stage open-source project and contributions are very
welcome. The main ways to help:

1. **Add a language adapter** — TypeScript, Rust, and Go are currently
   stubs. Each adapter is about 200-400 lines of Python. See the
   "Adding a new language adapter" section of the root
   [`CONTRIBUTING.md`](https://github.com/WouterDeBot/agentrepocoach/blob/main/CONTRIBUTING.md).
2. **Report false positives** — if AgentRepoCoach flags something that
   isn't actually a problem on your repo, open an issue with the
   smallest reproduction you can find.
3. **Propose weight tuning** — the 25/25/20/15/15 default split is
   heuristic. If you've measured something better, we want to hear about it.
4. **Write a case study** — run AgentRepoCoach on a popular OSS repo, follow
   the improvement suggestions, and write up the before/after.

## Code of conduct

AgentRepoCoach follows the
[Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
All contributors are expected to abide by it in issues, pull requests,
and discussions.

## How to open a pull request

1. Fork `WouterDeBot/agentrepocoach`.
2. Create a branch named after the change (e.g. `add-typescript-adapter`).
3. Run the test suite: `python3 -m pytest tests/ -v`.
4. Commit with a descriptive message — squash is fine, atomic is better.
5. Open the PR against `main`; the dogfood workflow will run automatically.

## Pull request checklist

- [ ] Tests pass locally (`python3 -m pytest tests/ -v`)
- [ ] New code has at least one test
- [ ] No runtime dependencies added (AgentRepoCoach is stdlib-only)
- [ ] README / docs updated if behavior changed
- [ ] Commit messages describe the *why*, not just the *what*

## License

By contributing, you agree that your contributions will be licensed under
the same **Apache 2.0** license as the rest of the project. No CLA is
required — the Apache 2.0 patent grant is enough.

See the root [CONTRIBUTING.md](https://github.com/WouterDeBot/agentrepocoach/blob/main/CONTRIBUTING.md)
for the detailed adapter walkthrough and code conventions.

---

AgentRepoCoach is licensed under **Apache 2.0**.

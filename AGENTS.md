# AGENTS.md

Guidance for coding agents working in this repository.

## Tooling

- Use `uv run addventure ...` for CLI checks and local builds.
- Use `uv run pytest` for the test suite.
- PDF output depends on Typst being installed; `--md` avoids that dependency when a build check is enough.

Common commands:

```bash
uv run addventure
uv run addventure build
uv run addventure build games/example
uv run addventure build --md
uv run addventure build --all
uv run addventure new "My Game"
```

## Repository Notes

- Runtime code lives in `src/addventure/`.
- Game authoring examples live in `games/`.
- Language docs live in `docs/`, including `docs/grammar.ebnf`.
- The package entry point is `uv run addventure`.

## Agent Guardrails

- Prefer existing parser, compiler, writer, and model patterns over introducing new abstractions.
- Treat `.md` game syntax as a strict language. Do not add silent parser skips for unrecognized input.
- Unknown frontmatter keys are allowed but should remain warnings, not hard failures.
- When changing the script language, update the parser, grammar, relevant user docs, examples if affected, and tests.
- When changing output behavior, check both the shared writer logic and the concrete Markdown/PDF writers for consistency.
- Keep generated build artifacts out of commits unless the task explicitly calls for them.

## Release Process

See [DEPLOY.md](DEPLOY.md) for the release workflow and release notes format.

# Deploying

## Release Process

1. Bump `version` in `pyproject.toml`.
2. Run `uv lock`.
3. Commit `bump version to X.Y.Z`.
4. Push to `main`.
5. Create a GitHub release:
   ```bash
   gh release create vX.Y.Z --generate-notes
   ```
6. Edit the release notes to match the project format (see below).
7. PyPI publish runs automatically from the GitHub release workflow.

### Release Notes Format

Replace the auto-generated notes with a human-written summary following this structure:

```markdown
## Addventure X.Y.Z: Short Descriptive Subtitle

### Feature Area One
Brief context sentence.

- Bullet point describing a change
- Another change in the same area

### Feature Area Two
Brief context sentence.

- Bullet point
- Another bullet point

---

**Full Changelog**: https://github.com/SmileyChris/addventure/compare/vPREVIOUS...vX.Y.Z
```

Use `## Addventure X.Y.Z: Subtitle` as the title. Group changes under `###` section headings. End with the full changelog comparison link.

## PyPI Credentials Setup

PyPI publishing runs via GitHub Actions. For local publishing, install keyring (used by uv) and set your token:

```bash
uv tool install keyring
keyring set 'https://upload.pypi.org/legacy/' __token__
```

Add these environment variables to your shell:

```bash
export UV_KEYRING_PROVIDER=subprocess
export UV_PUBLISH_USERNAME=__token__
```

## Site Deployment

The site deploys automatically via GitHub Actions when pushing to `main` (changes to `site/`, `docs/`, `games/example/`, or `src/`).

To build locally:

```bash
./site/build.sh
```

To preview:

```bash
./site/preview.sh [port]
```

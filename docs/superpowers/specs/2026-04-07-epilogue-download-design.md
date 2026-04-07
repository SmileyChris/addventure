# Epilogue Download on Home Page

**Date:** 2026-04-07

## Goal

Add the Epilogue chapter of The Facility as a downloadable PDF on the project home page.

## Changes

### `site/build.sh`

Add a build step for the Epilogue chapter after the existing Facility build:

```sh
uv run addventure build games/example/the-outpost -o site/assets/the-epilogue.pdf
```

### `site/index.html`

After the existing "print and play right now" paragraph in the example CTA section, add a follow-up link:

```html
<p class="example-cta-sub reveal">Finished The Facility? <a href="assets/the-epilogue.pdf" target="_blank">Download the Epilogue</a></p>
```

No new CSS required — the link inherits existing paragraph and anchor styles.

## Out of Scope

- Dedicated section/card for the Epilogue
- Combined Facility+Epilogue PDF
- Epilogue cover image on the site

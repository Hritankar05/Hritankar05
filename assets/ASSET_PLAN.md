# Signal / System / Story — asset plan

The first version is self-contained: the visual identity is generated as original SVG artwork, so it can be committed directly to a GitHub profile repository without a build step.

```text
assets/
├── ASSET_PLAN.md
├── animations/
│   ├── scanline.svg              # 1600 × 96, optional SMIL motion + static fallback
│   └── typing.svg                # 680 × 58, rotating focus line + static fallback
├── banner/
│   └── hero.svg                  # 1600 × 560 cinematic hero
├── brand/
│   └── monogram.svg              # 512 × 512 HD mark
├── dividers/
│   └── section-divider.svg       # 1600 × 72 section rhythm
├── github/
│   └── unconfigured.svg          # 900 × 180 honest stats fallback
├── icons/
│   └── README.md                 # icon-source notes; no unverified icons bundled
└── projects/
    ├── bandhu.svg                # 900 × 420 project tile
    ├── motion-tracking.svg       # 900 × 420 project tile
    ├── sanket.svg                # 900 × 420 project tile
    └── simworld.svg              # 900 × 420 project tile
```

## Palette

| Token | Hex | Use |
| --- | --- | --- |
| Obsidian Black | `#080A0F` | Atmosphere and base canvas |
| Midnight Navy | `#0B1220` | Panels, depth and secondary surfaces |
| Crimson Red | `#FF2638` | Signal markers, key metrics and emphasis |
| Electric Blue | `#45C7FF` | AI/network details and technical highlights |
| Cool White | `#F3F5F7` | Primary type |
| Muted Silver | `#929BAA` | Supporting information and instrumentation |

## Motion and hosting

- `assets/animations/scanline.svg` and `assets/animations/typing.svg` are the animation sources. They use SVG SMIL (`animate`) only; there is no JavaScript, CSS or external resource. GitHub may show the first frame if a renderer sanitizes animation, which is still a useful static signal panel.
- The hero, brand mark, dividers and project tiles are static SVGs and should be committed with the README.
- The intro typing line is repository-hosted, so it does not depend on a typing service. If GitHub sanitizes its animation, the first phrase remains visible and the alt text communicates all four lines.
- GitHub activity cards are intentionally handled separately by `scripts/refresh_stats.py`; see `docs/GITHUB-STATS.md`.

## Optional future image-generation prompts

These are optional upgrade prompts, not dependencies for the current README. If replacing the SVGs with raster artwork, preserve the same palette and do not use copyrighted characters, logos or film/game stills.

### Hero banner — 1600 × 560, PNG or WebP

> Original cinematic cyberpunk AI laboratory at night, wide 2.86:1 composition, obsidian black and midnight navy atmosphere, subtle fog, architectural depth, sparse crimson and electric-blue practical lights, computer-vision tracking frame, thin neural-network geometry, quiet negative space on the left for a title, premium software-engineering portfolio mood, sophisticated and restrained, no people, no logos, no readable text, no watermark.

### Brand mark — 1024 × 1024, transparent PNG or SVG

> Original geometric HD monogram for an AI/ML engineer and filmmaker, sharp editorial construction, one crimson signal arc and one electric-blue signal arc, cool-white linework, obsidian background or transparent background, minimal vector identity, no copied marks, no extra letters, no watermark.

### Project tile — 1200 × 560, PNG or WebP

> Original technical title-card artwork for [PROJECT NAME], dark obsidian and midnight navy background, one restrained crimson accent and electric-blue data geometry, visual metaphor for [SIGN LANGUAGE LANDMARKS / MULTI-AGENT NETWORK / TOURISM ROUTE / COMPUTER-VISION TRACKING], clean negative space, no stock imagery, no logos, no fabricated metrics, no watermark.

### Section divider — 1600 × 72, SVG or transparent PNG

> Minimal horizontal signal divider, obsidian background, thin silver line, one crimson marker, one electric-blue marker, sparse instrumentation ticks, premium cinematic interface language, no text, no watermark.

# Local GitHub activity snapshots

`scripts/refresh_stats.py` makes one bounded, manual refresh of four SVG cards
and stores them in `assets/github/`. The profile README can therefore render
local files rather than depending on live image requests. It does not create a
schedule, workflow, token, PAT, or account-specific sample data.

## Cards and source documentation

The script uses the current documented hosted endpoints below. The first
service is the actively maintained successor to the original
[`anuraghazra/github-readme-stats`](https://github.com/anuraghazra/github-readme-stats)
project, whose README now points to
[`stats-organization/github-stats-extended`](https://github.com/stats-organization/github-stats-extended).

| Local file | Card | Hosted SVG endpoint | Source documentation |
| --- | --- | --- | --- |
| `assets/github/stats.svg` | Stats card | `https://github-stats-extended.vercel.app/api?username=HANDLE` | [GitHub Stats Extended stats card](https://github-stats-extended.vercel.app/frontend/docs/cards/stats/) |
| `assets/github/languages.svg` | Most-used languages | `https://github-stats-extended.vercel.app/api/top-langs/?username=HANDLE` | [GitHub Stats Extended top languages](https://github-stats-extended.vercel.app/frontend/docs/cards/top-languages/) |
| `assets/github/streak.svg` | Contribution streak | `https://streak-stats.demolab.com/?user=HANDLE` | [GitHub Readme Streak Stats options](https://github.com/DenverCoder1/github-readme-streak-stats#-options) |
| `assets/github/activity.svg` | Contribution/activity graph | `https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=HANDLE` | [GitHub Profile Summary Cards API](https://github.com/vn7n24fzkq/github-profile-summary-cards#how-to-use-api) |

The profile-details card includes the documented one-year contribution graph.
Its hosted SVG is static by default (`animation=none`), so it passes the same
local safety checks as the other snapshots.
The commonly used `github-readme-activity-graph` renderer currently emits a
`foreignObject`; it is intentionally not selected because this script rejects
that construct.

## Configure and run

Add exactly one pair of markers to the root `README.md` (the native GitHub
profile link should be kept separately in the README):

```markdown
<!-- GITHUB-SNAPSHOTS:START -->
<!-- GITHUB-SNAPSHOTS:END -->
```

Then run one refresh manually:

```sh
python3 scripts/refresh_stats.py --username REAL_HANDLE
```

`REAL_HANDLE` means the actual GitHub handle; it is command notation, not a
value to fetch. While the account is unknown, either omit the option or use
the explicit placeholder:

```sh
python3 scripts/refresh_stats.py --username REPLACE_WITH_MY_USERNAME
```

Absent usernames and `REPLACE_WITH_MY_USERNAME` are skipped without any
third-party request. The managed README region displays
`assets/github/unconfigured.svg` for missing cards. A valid existing local
snapshot is retained and displayed when a service cannot be reached.
The fallback card reads: “GitHub activity / ACCOUNT NOT CONNECTED / No
statistics until a GitHub username is configured.”

The tests use only the standard library and mocked responses:

```sh
python3 -m unittest discover -s tests -v
```

## Visual and URL policy

The requests use documented query parameters and standard percent encoding;
hex colors omit `#` as required by the services. The dark cinematic palette is:

| Role | Color |
| --- | --- |
| Background | `#080A0F` |
| Panel/border | `#0B1220` |
| Crimson | `#FF2638` |
| Electric blue | `#45C7FF` |
| Primary text | `#F3F5F7` |
| Muted text | `#929BAA` |

`hide_rank=true` is used where the stats service supports it. Animations are
disabled, so the committed cards do not pretend to be animated. The README
block contains only relative `assets/github/*.svg` image paths; it never adds
the hosted URLs as image dependencies.

Top languages describe repository language bytes and ranking data, not a
measure of programming skill or proficiency. The stats services also cache
hosted results (GitHub Stats Extended documents public cards as commonly cached
for days), so a successful manual refresh may still reflect service cache
behavior.

## Safety and failure behavior

- At most four requests are made, one per card, with a 15-second timeout and a
  1.5 MB response bound.
- Only HTTPS requests to the three fixed documented service hosts are allowed.
  The supplied username is validated as a GitHub handle and is URL encoded.
- A response must be well-formed SVG. HTML/non-SVG payloads, XML entity/doctype
  declarations, scripts, `foreignObject`, embedded resources, external links,
  unsafe CSS URLs, and known service-error cards are rejected even with HTTP
  200.
- A failed or rejected response is reported on stderr and never overwrites a
  previous valid snapshot. No counts or rankings are fabricated. README cards
  fall back to the unconfigured card if no verified previous file exists.
- Snapshot and README writes use an atomic temporary sibling replacement, and
  fixed repository-relative paths reject traversal and outside symlinks.

The command exits `0` when the refresh and marker update complete, `1` when a
request or README update had an error, and `2` for invalid command input. A
nonzero result is intentional: inspect stderr and retry manually when useful.

Requests to the hosted services transmit the configured GitHub username in the
URL. No credentials or private contribution token are sent by this script;
the hosted services' own documentation describes their public/private-data
limitations.

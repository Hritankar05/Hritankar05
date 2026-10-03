# Deploy the profile README

## 1. Create the profile repository

1. Sign in to GitHub.
2. Create a **public** repository whose name exactly matches your GitHub username. For example, `your-handle/your-handle`.
3. Do not add a second README if you plan to upload this one.

## 2. Copy the deliverables

Copy these paths into the root of the profile repository:

```text
README.md
assets/
docs/
scripts/
tests/
```

The profile page only needs `README.md` and `assets/`. Keep `docs/`, `scripts/` and `tests/` if you want the local stats refresh and maintenance notes to remain reproducible.

## 3. Replace known placeholders

In `README.md`, replace:

- `REPLACE_WITH_MY_USERNAME` with your real GitHub handle.
- `REPLACE_WITH_SANKET_REPO` with the real SANKET repository slug, or remove that link.
- `REPLACE_WITH_SIMWORLD_REPO` with the real SimWorld repository slug, or remove that link.
- `REPLACE_WITH_BANDHU_REPO` with the real Bandhu repository slug, or remove that link.
- `REPLACE_WITH_MOTION_TRACKING_REPO` with the real motion-tracking repository slug, or remove that link.

No demo URLs, screenshots, deployment claims or repository names were invented. Add them only after verifying that they are public and correct.

## 4. Refresh GitHub activity cards

From the profile repository root, run:

```sh
python3 scripts/refresh_stats.py --username YOUR_REAL_HANDLE
python3 -m unittest discover -s tests -v
```

The script makes one bounded manual request per card to documented public SVG services, validates the SVG, writes local snapshots under `assets/github/`, and updates only the region between the `GITHUB-SNAPSHOTS` markers. It does not use credentials or fabricate statistics. If a service fails, a previous valid snapshot is kept; if no snapshot exists, the honest fallback remains.

If you do not want stats, leave the fallback cards in place and remove the script/docs links from the README setup note.

## 5. Preview and publish

Optional local preview:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/README.md` only as a rough asset-path check; GitHub's Markdown renderer is the final authority. A Markdown preview extension or a temporary branch can help catch table/layout issues.

Then commit and push:

```sh
git add README.md assets docs scripts tests
git commit -m "feat: add cinematic profile README"
git push origin main
```

Open `https://github.com/YOUR_REAL_HANDLE/YOUR_REAL_HANDLE` and verify the rendered profile.

## Final compatibility checklist

- [ ] The repository is public and named exactly after the GitHub username.
- [ ] Every `REPLACE_WITH_...` placeholder is either replaced or intentionally removed.
- [ ] `assets/banner/hero.svg`, the monogram, dividers and all four project SVGs load from repository-relative paths.
- [ ] The repository-hosted typing SVG and Shields badges load, or the typing SVG's first-frame/alt text remains useful when animation or external badges are unavailable.
- [ ] `assets/animations/scanline.svg` displays a static frame if GitHub disables SVG animation.
- [ ] On a narrow mobile viewport, headings, tables and project descriptions remain readable; wide artwork may scale down but must not be required to understand the content.
- [ ] Email, LinkedIn and GitHub links point to the intended destinations.
- [ ] Project links are real, verified URLs or still visibly marked as placeholders.
- [ ] Stats cards show real data only after a successful manual refresh; there are no fabricated counts, streaks or rankings.
- [ ] The résumé claims, dates, awards, roles and metrics still match the source résumé after any edits.
- [ ] The profile remains usable if the typing, icon, badge or stats services are temporarily unavailable.

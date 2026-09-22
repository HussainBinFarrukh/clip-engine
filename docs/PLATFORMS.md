# Platform Rules

Last verified: 2026-09-21.

Spot checked against official references on 2026-09-22. Re-verify again before implementing any upload, scheduling, monetization, or eligibility logic.

Use this file as a working product reference, not a substitute for official documentation. Re-verify before implementing uploads, scheduling, monetization logic, or eligibility gates.

## YouTube Shorts

- Official reference: https://support.google.com/youtube/answer/15424877
- Current working rule: square or vertical videos up to 3 minutes can be categorized as Shorts.
- Project baseline from `AGENTS.md`: from 2026-09-24, Shorts of 1-3 minutes with an active Content ID claim are no longer auto-blocked; globally blocked Shorts are not monetized.
- Product implication: `shorts_campaign` and `shorts_long` should render 9:16 outputs no longer than 180 seconds.

## YouTube Data API

- Official overview: https://developers.google.com/youtube/v3/getting-started
- Official upload endpoint: https://developers.google.com/youtube/v3/docs/videos/insert
- Current working rule: upload behavior and quota are bucketed and must be read from current Google docs/provider config before enforcing daily upload limits.
- Project baseline from `AGENTS.md`: 10,000 quota units/day per Google Cloud project; older upload guidance assumed about 1,600 quota units per upload and about 6 uploads/day/project.
- Product implication: do not hardcode legacy upload quota assumptions.

## YouTube Partner Program

- Project baseline from `AGENTS.md`: from 2027-02-01, new applicants need 8,000 watch hours or 20M Shorts views, and channels need 10M Shorts views per 90 days to keep receiving Shorts ad revenue.
- Product implication: monetization projections must be advisory only until current YPP eligibility is reverified for the connected channel.

## TikTok Creator Rewards

- Official newsroom reference: https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program
- Current working rule: TikTok describes rewards around high-quality original content over one minute.
- Product implication: `tiktok_rewards` targets 61-180 seconds and must include original commentary, not meaningless reaction or reused-content packaging.

## TikTok Content Posting API

- Official reference: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- Current working rule: direct posting requires app approval and user authorization; unaudited clients are restricted to private visibility.
- Product implication: publishing support should start as a reviewed/draft workflow until app audit status is known.

## Instagram / Reels

- Official reference: https://developers.facebook.com/docs/instagram-platform/content-publishing/
- Current working rule: publishing quotas and eligibility must be checked against the Graph API and Meta docs before implementation.
- Project baseline from `AGENTS.md`: 50 API-published posts per rolling 24 hours per account.
- Product implication: keep post pacing configurable and conservative.

## Internal Pacing Guidance

- Recommended pacing: 2-4 posts per account per day unless platform analytics and account health justify a different schedule.
- Publishing must remain blocked unless commentary QA, render QA, and human approval all pass. Source rights are not app-enforced (see `docs/DECISIONS.md`, "Remove Source Rights Gate; Allow YouTube Download") — the user is responsible for source legality.

# Decisions

## 2026-09-22: Keep the First Slice Static

The current workstation stays dependency-free because Node, Python, Git, and ffmpeg are not available in the shell. This lets the project make usable progress while the future stack is documented for the next environment setup step.

## 2026-09-22: YouTube URLs Are References Only

YouTube URLs are exported as metadata/reference requests only. The product must not download or store YouTube audiovisual content without explicit platform approval. Source media for actual clipping starts with local authorized uploads.

## 2026-09-22: Rights and Commentary Are Required Gates

Every render plan carries a rights record and commentary QA status. Backend rendering must block when rights type, rights reference, or commentary is missing. Publishing remains blocked until a human approval state is set.

## 2026-09-22: Platform Limits Stay Configurable

Official platform requirements change. The app uses named presets and records platform targets, but final upload quota and publishing checks must be loaded from `docs/PLATFORMS.md` or provider configuration at runtime.

## 2026-09-22: YouTube API Upload Cost Needs Current Verification

Current Google documentation presents video upload quota differently than older 1,600-unit guidance. Treat quota cost and daily upload capacity as provider configuration, not a hardcoded business rule.

## 2026-09-22: Initialize Repository at T01

The workspace was not a Git repository, and Git was not initially installed. Git was installed with `winget`, the repository was initialized locally, and T01 is committed as the documentation baseline before the production scaffold begins.

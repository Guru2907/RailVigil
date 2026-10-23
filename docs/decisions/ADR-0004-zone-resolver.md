# ADR-0004: One zone resolver, no whole-frame fallback

Status: accepted (2026-10-18), implemented in PR #1

## Context
Zones used to come from different places: the upload form, presets hard-coded by clip filename, and a whole-frame fallback that made every visible object count as "on the track".

## Decision
All zones come from `ZoneResolver` (`backend/app/cv/common/zones.py`) in a fixed precedence — manual, sidecar, camera, auto — stored normalized with their source. A missing zone is an error. Automatic zones plug in as a provider without changing callers.

## Consequences
Results are comparable across clips and resolutions, and every result can say how its zone was made. Uploads without any zone are rejected until the planned `awaiting_zone` flow exists.

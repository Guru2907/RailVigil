# ADR-0003: Encroachment and intrusion are separate modules

Status: accepted (2026-10-17)

## Context
The first pipeline called transient people/vehicle events "encroachment". Physical encroachment (structures, vegetation, debris occupying railway land) is a different problem: static objects, mostly from images, needing a custom-trained model and a persistence model based on repeat reports rather than seconds of dwell time.

## Decision
Two modules under `backend/app/cv/`: `intrusion/` (video, tracking, temporal confirmation) and `encroachment/` (images and keyframes, segmentation, zone rule, sites). They share `cv/common/` (detector, tracker, zone resolver, geometry) and have their own tables, report types and dashboard tabs. Each module has one owner (see CONTRIBUTING.md).

## Consequences
Neither module's terminology or counts may leak into the other. Shared code changes need both owners' review.

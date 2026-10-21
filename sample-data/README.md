No real social-platform videos or copyrighted movie footage is included.
Run `python scripts/generate_samples.py` with backend dependencies installed to generate a deterministic reference clip, transformed candidate, approved promo, unrelated clip, and manifest under `.local/samples`.
These are synthetic media, not detections. Scores and decisions are computed only by running the pipeline.

`observed-synthetic-detections.json` contains representative decisions actually computed during integration validation. It is documentation data, never seeded as real detections. `requested-pair.json` records the user's real links separately with a pending-media status and null detection/confidence.

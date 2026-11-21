"""Confidence thresholds, defined once.

These were previously duplicated in analyzer.py, disease.py and the frontend,
and drifted apart the moment one was retuned. The frontend copy lives in
frontend/src/lib/confidence.ts and must be kept in step by hand.

UNSURE_BELOW is measured, not guessed. The species model chooses among 7806
plants, so its probabilities are spread far thinner than the 8-class model it
replaced. On 1143 labelled photos:

    threshold   names a plant   of those, correct
    0.50              20%              75%
    0.30              33%              67%
    0.20              45%              61%

0.50 was calibrated for the old 8-class head and left the new model mute on
photos where it actually knew the answer.
"""

# Below this the UI hides the name and asks for a clearer photo.
UNSURE_BELOW = 0.30

# What a withheld confidence is reported as - just under the threshold, so the
# ranking survives but the UI still shows its unsure state.
UNSURE_CAP = 0.29

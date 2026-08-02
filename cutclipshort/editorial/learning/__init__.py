"""Learning system — rule-based preference learning from user feedback.

Two components:
1. FeedbackStore  — persists accept/reject decisions with clip metadata
2. PreferenceEngine — computes scoring biases from accumulated feedback

No ML. Pure statistics: tracks which score dimensions correlate with
user acceptance, then applies bias adjustments to future rankings.
"""

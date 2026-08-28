"""Synchronous protocol adapter for the LTT LLM app.

The HTTP layer only knows this narrow contract through the app manifest.  The
business rules remain in ``features.py``; this module is the app-owned bridge.
"""
from __future__ import annotations

from apps.ltt_llm import features


class _Executor:
    default_max_tokens = features.SYNC_MAX_TOKENS_MAC_DINH
    parameter_error = features.ThamSoSai

    def aliases(self):
        return dict(features.ALIAS_SANG_ID)

    def validate(self, params):
        return features.kiem_tham_so(params)

    def estimate_input(self, messages, tools=None):
        return (features.uoc_token_vao(messages) if tools is None
                else features.uoc_token_vao(messages, tools))

    def sync_output_cap(self, token_input, budget_seconds):
        return features.tran_token_ra_dong_bo(token_input, budget_seconds)

    def context_output_cap(self, token_input):
        from apps.ltt_llm.manifest import tran_theo_ngu_canh
        return tran_theo_ngu_canh(token_input)

    def run(self, db, params, *, timeout_s, on_dispatch=None, on_rejected=None):
        kwargs = {"timeout_s": timeout_s}
        if on_dispatch is not None:
            kwargs["on_dispatch"] = on_dispatch
        if on_rejected is not None:
            kwargs["on_rejected"] = on_rejected
        return features.chay(db, params, **kwargs)

    def model_id(self, alias):
        return self.aliases()[alias]


EXECUTOR = _Executor()

# coding=utf-8
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# MODIFIED by LTT Studios, 2026-09-22 (see NOTICE in this directory):
#   Derived from google-research/metricx @ fc4978eb064670f7cc33e93ea4f52d38396b8ae6,
#   file metricx24/models.py. Reduced to inference only: removed the training
#   loss, head-mask and model-parallel branches; the one-step decoder input is
#   created on the encoder output's device (upstream hard-codes "cuda" whenever
#   CUDA is available, which breaks CPU inference on a GPU machine). The
#   architecture, weight names, output token (250089 = <extra_id_10>) and the
#   [0, 25] clamp are unchanged, so upstream checkpoints load as-is.
"""MT5ForRegression — the MetricX-24 model class (inference only)."""

import copy

import torch
from torch import nn
import transformers

MT5Config = transformers.models.mt5.modeling_mt5.MT5Config
MT5PreTrainedModel = transformers.models.mt5.modeling_mt5.MT5PreTrainedModel
MT5Stack = transformers.models.mt5.modeling_mt5.MT5Stack

#: <extra_id_10> — the vocabulary slot MetricX regresses its score into.
TOKEN_DIEM = 250089


def _mt5_stack(config: "MT5Config", embed_tokens: nn.Embedding):
    """`MT5Stack` sharing `embed_tokens`, on both the 4.x and 5.x signature.

    🔴 Upstream MetricX was written for `transformers` 4.x, where the signature
       is `MT5Stack(config, embed_tokens=None)`. In 5.x it is `MT5Stack(config)`
       and the stack builds its own `nn.Embedding`, so the upstream two-argument
       call raises `TypeError: too many positional arguments` **before touching
       any weight**.

    ⚠️ **DINH CHINH 24/09/2026 — ban ghi truoc noi qua.** No viet *"MetricX QE
       cannot start at all, measured on transformers 5.6.2"*. Do lai tren **ca
       hai** moi truong:

           venv chinh   transformers 5.6.2   <- da do o DAY
           qc-venv      transformers 4.57.6  <- MetricX THAT SU chay o DAY

       Tep nay **chi chay trong `qc-venv`** (chinh docstring nay noi the), va o
       do chu ky van la `MT5Stack(config, embed_tokens)` ⇒ loi goi hai tham so
       **van dung**, va MetricX QE **van khoi dong duoc**. Hai lan khac da do
       MetricX chay that trong ngay (diem trung vi 3,06; CPU-vs-GPU 10,31 s).

    ⇒ Ly do giu ban mot-tham-so **khong** phai "dang hong", ma la **tuong thich
       tien**: qc-venv se co luc len 5.x, va luc do loi goi hai tham so se chet.
       Da do tren qc-venv 4.57.6: `_mt5_stack` tra `MT5Stack` va
       `get_input_embeddings() is emb` ⇒ True (chia chung dung embedding).

    ⭐ ONE code path rather than a version branch: `set_input_embeddings` is a
       `PreTrainedModel` method present in both 4.x and 5.x, and in 4.x
       `MT5Stack(config)` alone is already legal (`embed_tokens` defaults to
       `None`). A branch on the installed signature would leave one side
       unexercised on every machine — and that is the side that breaks.

    ⛔ The shared embedding is not cosmetic: the published checkpoint ties
       encoder, decoder and `lm_head` to one weight matrix. A stack that quietly
       builds its own `nn.Embedding` still loads the checkpoint and still
       returns a number — a wrong one.
    """
    stack = MT5Stack(config)
    stack.set_input_embeddings(embed_tokens)
    return stack


def _so_lop_decoder(config: "MT5Config") -> int:
    """`config.num_decoder_layers`, falling back to `num_layers`.

    `MT5Config` declares it `int | None`; `None` reaches `range(config.num_layers)`
    inside `MT5Stack` as a decoder with **no layers at all** — a model that loads
    and returns noise. mT5 configs default it to `num_layers`, so that is the
    only defensible fallback.
    """
    return int(config.num_decoder_layers or config.num_layers)


class MT5ForRegression(MT5PreTrainedModel):
  """MT5 model for regression (MetricX)."""

  def __init__(self, config: MT5Config):
    super().__init__(config)
    self.model_dim = config.d_model

    self.shared = nn.Embedding(config.vocab_size, config.d_model)

    encoder_config = copy.deepcopy(config)
    encoder_config.is_decoder = False
    encoder_config.use_cache = False
    encoder_config.is_encoder_decoder = False
    self.encoder = _mt5_stack(encoder_config, self.shared)

    decoder_config = copy.deepcopy(config)
    decoder_config.is_decoder = True
    decoder_config.is_encoder_decoder = False
    decoder_config.num_layers = _so_lop_decoder(config)
    self.decoder = _mt5_stack(decoder_config, self.shared)

    self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

    self.post_init()

  @torch.no_grad()
  def forward(self, input_ids: torch.LongTensor,
              attention_mask: torch.Tensor) -> torch.Tensor:
    """Returns predictions of shape [batch], clipped to [0, 25] (lower = better)."""
    hidden_states = self.encoder(
        input_ids=input_ids, attention_mask=attention_mask, return_dict=True,
    ).last_hidden_state

    batch_size = input_ids.size(0)
    decoder_input_ids = torch.zeros(
        (batch_size, 1), dtype=torch.long, device=hidden_states.device)

    sequence_output = self.decoder(
        input_ids=decoder_input_ids,
        encoder_hidden_states=hidden_states,
        encoder_attention_mask=attention_mask,
        use_cache=False,
        return_dict=True,
    ).last_hidden_state

    if self.config.tie_word_embeddings:
      sequence_output = sequence_output * (self.model_dim**-0.5)

    lm_logits = self.lm_head(sequence_output)
    predictions = lm_logits[:, 0, TOKEN_DIEM]
    return torch.clamp(predictions, 0, 25)

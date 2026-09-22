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
    self.encoder = MT5Stack(encoder_config, self.shared)

    decoder_config = copy.deepcopy(config)
    decoder_config.is_decoder = True
    decoder_config.is_encoder_decoder = False
    decoder_config.num_layers = config.num_decoder_layers
    self.decoder = MT5Stack(decoder_config, self.shared)

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

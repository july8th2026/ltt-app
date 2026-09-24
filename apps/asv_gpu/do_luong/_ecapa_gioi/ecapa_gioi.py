"""ECAPA-TDNN gender classifier - derived from JaesungHuh/voice-gender-classifier.

MIT License, Copyright (c) 2024 jaesunghuh. See LICENSE and NOTICE in this
directory for the upstream commit and the list of modifications.

⛔ KHONG "sua cho dep" tep nay. No phai nap duoc checkpoint DA CONG BO: moi ten
   thuoc tinh (`conv1`, `layer1..4`, `attention`, `bn5`, `fc6`, `bn6`, `fc7`) la
   mot KHOA trong `model.safetensors`, va thu tu lop (0 = male, 1 = female) la
   mot phan cua trong so, khong phai mot quy uoc cua ta.
"""
from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio

#: Thu tu lop cua checkpoint upstream (`pred2gender` trong model.py).
#: `0 -> male`, `1 -> female`. Doi hai dong nay la doi ket qua cua CA bo do.
LOP = ("male", "female")


class SEModule(nn.Module):
    def __init__(self, channels: int, bottleneck: int = 128) -> None:
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Conv1d(channels, bottleneck, kernel_size=1, padding=0),
            nn.ReLU(),
            nn.Conv1d(bottleneck, channels, kernel_size=1, padding=0),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.se(x)


class Bottle2neck(nn.Module):
    def __init__(self, inplanes: int, planes: int,
                 kernel_size: Optional[int] = None,
                 dilation: Optional[int] = None, scale: int = 8) -> None:
        super().__init__()
        width = int(math.floor(planes / scale))
        self.conv1 = nn.Conv1d(inplanes, width * scale, kernel_size=1)
        self.bn1 = nn.BatchNorm1d(width * scale)
        self.nums = scale - 1
        convs, bns = [], []
        num_pad = math.floor(kernel_size / 2) * dilation
        for _ in range(self.nums):
            convs.append(nn.Conv1d(width, width, kernel_size=kernel_size,
                                   dilation=dilation, padding=num_pad))
            bns.append(nn.BatchNorm1d(width))
        self.convs = nn.ModuleList(convs)
        self.bns = nn.ModuleList(bns)
        self.conv3 = nn.Conv1d(width * scale, planes, kernel_size=1)
        self.bn3 = nn.BatchNorm1d(planes)
        self.relu = nn.ReLU()
        self.width = width
        self.se = SEModule(planes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.bn1(self.relu(self.conv1(x)))
        spx = torch.split(out, self.width, 1)
        sp = spx[0]
        for i in range(self.nums):
            if i != 0:
                sp = sp + spx[i]
            sp = self.bns[i](self.relu(self.convs[i](sp)))
            out = sp if i == 0 else torch.cat((out, sp), 1)
        out = torch.cat((out, spx[self.nums]), 1)
        out = self.bn3(self.relu(self.conv3(out)))
        out = self.se(out)
        return out + residual


class ECAPA_gender(nn.Module):
    """Hai lop dau ra. ⛔ Khong ke thua `PyTorchModelHubMixin` (upstream co):
    ta tai weights bang tay de KIEM sha256 truoc khi nap, va mixin se tai mot
    ban khong kiem gi.
    """

    def __init__(self, C: int = 1024):
        super().__init__()
        self.C = C
        self.conv1 = nn.Conv1d(80, C, kernel_size=5, stride=1, padding=2)
        self.relu = nn.ReLU()
        self.bn1 = nn.BatchNorm1d(C)
        self.layer1 = Bottle2neck(C, C, kernel_size=3, dilation=2, scale=8)
        self.layer2 = Bottle2neck(C, C, kernel_size=3, dilation=3, scale=8)
        self.layer3 = Bottle2neck(C, C, kernel_size=3, dilation=4, scale=8)
        self.layer4 = nn.Conv1d(3 * C, 1536, kernel_size=1)
        self.attention = nn.Sequential(
            nn.Conv1d(4608, 256, kernel_size=1),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Tanh(),
            nn.Conv1d(256, 1536, kernel_size=1),
            nn.Softmax(dim=2),
        )
        self.bn5 = nn.BatchNorm1d(3072)
        self.fc6 = nn.Linear(3072, 192)
        self.bn6 = nn.BatchNorm1d(192)
        self.fc7 = nn.Linear(192, 2)
        # ⭐ Dung mot lan, khong dung lai moi luot (upstream dung trong forward).
        #    Cung tham so, cung dau ra; chi khac o cho no khong dung mot module
        #    moi cho tung doan.
        self._mel = torchaudio.transforms.MelSpectrogram(
            sample_rate=16000, n_fft=512, win_length=400, hop_length=160,
            f_min=20, f_max=7600, window_fn=torch.hamming_window, n_mels=80)

    def logtorchfbank(self, x: torch.Tensor) -> torch.Tensor:
        loc = torch.FloatTensor([-0.97, 1.0]).unsqueeze(0).unsqueeze(0).to(x.device)
        x = x.unsqueeze(1)
        x = F.pad(x, (1, 0), "reflect")
        x = F.conv1d(x, loc).squeeze(1)
        x = self._mel(x) + 1e-6
        x = x.log()
        return x - torch.mean(x, dim=-1, keepdim=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.logtorchfbank(x)
        x = self.bn1(self.relu(self.conv1(x)))
        x1 = self.layer1(x)
        x2 = self.layer2(x + x1)
        x3 = self.layer3(x + x1 + x2)
        x = self.relu(self.layer4(torch.cat((x1, x2, x3), dim=1)))
        t = x.size()[-1]
        global_x = torch.cat(
            (x,
             torch.mean(x, dim=2, keepdim=True).repeat(1, 1, t),
             torch.sqrt(torch.var(x, dim=2, keepdim=True).clamp(min=1e-4)).repeat(1, 1, t)),
            dim=1)
        w = self.attention(global_x)
        mu = torch.sum(x * w, dim=2)
        sg = torch.sqrt((torch.sum((x ** 2) * w, dim=2) - mu ** 2).clamp(min=1e-4))
        x = torch.cat((mu, sg), 1)
        x = self.bn5(x)
        x = self.fc6(x)
        x = self.bn6(x)
        x = self.relu(x)
        return self.fc7(x)

    @torch.no_grad()
    def xac_suat(self, song: torch.Tensor) -> list[list[float]]:
        """`song` = (B, N) mono 16 kHz -> `[[p_male, p_female], ...]` theo hang.

        ⚠️ Tra XAC SUAT chu khong tra nhan: nguoi goi can biet model **chac bao
           nhieu**, vi ca nay (giong dien, giong bien hoa) chinh la ca ma mot
           cai nhan mot minh se noi doi.

        ⭐ Nhan CA MOT LO va do KHONG doi ket qua: moi `BatchNorm1d` o day chay
           o `eval()`, tuc dung thong ke da hoc san, khong dung thong ke cua lo.
           Gom lo chi de khoi goi model 17 lan cho 17 cua so cua mot clip.
        """
        self.eval()
        if song.dim() == 1:
            song = song.unsqueeze(0)
        out = torch.softmax(self.forward(song).float(), dim=1)
        return [[float(h[0]), float(h[1])] for h in out]

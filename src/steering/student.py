"""
Verifiable STUDENT network + its preprocessing.

The student takes RGB (weather-perturbable, unlike CARLA's ground-truth seg camera
which would make weather verification vacuous). It uses a tighter ROI than the
teacher — sky, hood, and peripheral scenery cropped away (from the dataset ROI
analysis) — so lane lines survive aggressive downsampling. Input resolution is a
free parameter we sweep: smaller = far cheaper to verify, but eventually the lanes
wash out and it can't drive. ReLU-only, no BatchNorm/Dropout (SDP-CROWN friendly).
"""
import torch
import torch.nn as nn
import numpy as np
import cv2

# Region of interest from CARLA ground-truth semantic-seg road occupancy (3390
# frames, both directions): road spans rows [240:450] full width; above is sky,
# the bottom-center arc is the hood. Tighter-on-road crop = lanes survive
# downsampling better. Aspect ~3:1.
STUDENT_CROP_TOP, STUDENT_CROP_BOT = 240, 450
STUDENT_CROP_LEFT, STUDENT_CROP_RIGHT = 0, 640


def student_preprocess(bgr, out_w, out_h):
    """BGR uint8 -> RGB, tight crop, resize to (out_w,out_h), [0,1] CHW float32."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    crop = rgb[STUDENT_CROP_TOP:STUDENT_CROP_BOT, STUDENT_CROP_LEFT:STUDENT_CROP_RIGHT]
    resized = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_AREA)
    return (resized.astype(np.float32) / 255.0).transpose(2, 0, 1)


# (kernel, stride) per conv layer, keyed by DEPTH. Depth 3 is the stack every student in
# this study was trained with and is reproduced here EXACTLY -- 5x5 s2, 5x5 s2, 3x3 s2 --
# so no existing checkpoint changes shape.
#
# Depth 5 cannot simply add two more stride-2 layers: the input is 56 px tall and a
# fourth stride-2 layer leaves 2 rows, a fifth leaves none. The extra layers are stride 1,
# which is also what the PilotNet teacher does.
#
# ONLY THE FIRST TWO ARE STRIDED. The obvious spec -- three strided convs then two
# unstrided -- leaves a 1x15 final map, so the flatten dimension collapses to 300 against
# depth 3's 6,080. A student matched on ReLU COUNT but carrying a 20x smaller
# representation is not a depth experiment; it is a bottleneck experiment, and it trained
# ~4x worse (val KD RMSE 0.0909 against ~0.03). Measured, then corrected -- see amendment
# recorded before the measurement was made.
#
# config.relu_count reads this same table, so the two cannot drift apart.
CONV_SPEC = {
    3: ((5, 2), (5, 2), (3, 2)),
    5: ((5, 2), (5, 2), (3, 1), (3, 1), (3, 1)),
}


class StudentNet(nn.Module):
    """Small ReLU-only CNN, parameterized by input resolution and conv depth.

    `channels` sets both the widths and the DEPTH: len(channels) selects the stack from
    CONV_SPEC. Three channels reproduces the original fixed stack exactly.
    """

    def __init__(self, in_h, in_w, in_ch=3, channels=(8, 16, 16), fc=32):
        super().__init__()
        channels = tuple(channels)
        if len(channels) not in CONV_SPEC:
            raise ValueError(
                f"StudentNet: {len(channels)} conv layers is not a defined stack; "
                f"CONV_SPEC has {sorted(CONV_SPEC)}. Add it there so config.relu_count "
                f"sees the same geometry, rather than passing more channels here.")
        self.in_h, self.in_w = in_h, in_w
        layers, prev = [], in_ch
        for c, (k, st) in zip(channels, CONV_SPEC[len(channels)]):
            layers += [nn.Conv2d(prev, c, k, stride=st), nn.ReLU()]
            prev = c
        self.conv = nn.Sequential(*layers)
        with torch.no_grad():
            n_flat = self.conv(torch.zeros(1, in_ch, in_h, in_w)).flatten(1).shape[1]
        self.fc = nn.Sequential(
            nn.Linear(n_flat, fc), nn.ReLU(),
            nn.Linear(fc, 1),
        )
        self.n_flat = n_flat

    def forward(self, x):
        return self.fc(self.conv(x).flatten(1))

    def num_relu_neurons(self):
        n, device = 0, next(self.parameters()).device
        with torch.no_grad():
            x = torch.zeros(1, 3, self.in_h, self.in_w, device=device)
            for layer in self.conv:
                x = layer(x)
                if isinstance(layer, nn.ReLU):
                    n += int(np.prod(x.shape[1:]))
            x = x.flatten(1)
            for layer in self.fc:
                x = layer(x)
                if isinstance(layer, nn.ReLU):
                    n += int(np.prod(x.shape[1:]))
        return n


if __name__ == "__main__":
    for (w, h) in [(96, 42), (80, 36), (64, 28), (48, 22)]:
        m = StudentNet(h, w)
        print(f"{w}x{h}: flatten={m.n_flat:5d}  params={sum(p.numel() for p in m.parameters()):6d}  "
              f"ReLU-neurons={m.num_relu_neurons():6d}")

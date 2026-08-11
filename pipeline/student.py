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


class StudentNet(nn.Module):
    """Small ReLU-only CNN, parameterized by input resolution. Conv stack is fixed
    (3->8->16->16, strided); the flatten dim adapts to the input size."""

    def __init__(self, in_h, in_w, in_ch=3, channels=(8, 16, 16), fc=32):
        super().__init__()
        c1, c2, c3 = channels
        self.in_h, self.in_w = in_h, in_w
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, c1, 5, stride=2), nn.ReLU(),
            nn.Conv2d(c1, c2, 5, stride=2), nn.ReLU(),
            nn.Conv2d(c2, c3, 3, stride=2), nn.ReLU(),
        )
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

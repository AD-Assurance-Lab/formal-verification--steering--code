"""
Driving networks.

CarlaSteeringNet: PilotNet (Bojarski et al., 2016) — the canonical end-to-end
camera->steering CNN. ReLU-only, no BatchNorm/Dropout: this keeps it a clean
piecewise-linear function (friendly to knowledge distillation and, in principle,
to formal verification), and this task doesn't need the regularization.

This is the TEACHER for the driving milestone. The much smaller, SDP-CROWN-
verifiable STUDENT is defined later (M2) and distilled from this.
"""
import torch
import torch.nn as nn

from config import INPUT_H, INPUT_W


class CarlaSteeringNet(nn.Module):
    def __init__(self, in_ch=3):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, 24, 5, stride=2), nn.ReLU(),
            nn.Conv2d(24, 36, 5, stride=2), nn.ReLU(),
            nn.Conv2d(36, 48, 5, stride=2), nn.ReLU(),
            nn.Conv2d(48, 64, 3, stride=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, stride=1), nn.ReLU(),
        )
        # infer the flattened conv size for the configured input dimensions
        with torch.no_grad():
            n_flat = self.conv(torch.zeros(1, in_ch, INPUT_H, INPUT_W)).flatten(1).shape[1]
        self.fc = nn.Sequential(
            nn.Linear(n_flat, 100), nn.ReLU(),
            nn.Linear(100, 50), nn.ReLU(),
            nn.Linear(50, 10), nn.ReLU(),
            nn.Linear(10, 1),
        )
        self.n_flat = n_flat

    def forward(self, x):
        return self.fc(self.conv(x).flatten(1))

    def num_relu_neurons(self):
        """Count of post-ReLU activations — a proxy for verification difficulty."""
        import numpy as np
        n = 0
        device = next(self.parameters()).device
        with torch.no_grad():
            x = torch.zeros(1, 3, INPUT_H, INPUT_W, device=device)
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
    m = CarlaSteeringNet()
    print(f"flatten dim: {m.n_flat}")
    print(f"params: {sum(p.numel() for p in m.parameters()):,}")
    print(f"ReLU neurons (verification-difficulty proxy): {m.num_relu_neurons():,}")

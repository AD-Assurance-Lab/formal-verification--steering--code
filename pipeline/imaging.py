"""
Pure image helpers (cv2/numpy only, no CARLA/torch import) so both the live
CARLA loop and the offline training dataset share ONE preprocessing path — any
divergence between train-time and inference-time preprocessing silently wrecks a
BC policy, so it must be defined in exactly one place.
"""
import cv2
import numpy as np

from config import CROP_TOP, CROP_BOT, INPUT_W, INPUT_H


def raw_to_bgr(carla_image):
    """CARLA raw BGRA buffer -> BGR uint8 (H, W, 3)."""
    arr = np.frombuffer(carla_image.raw_data, dtype=np.uint8)
    arr = arr.reshape((carla_image.height, carla_image.width, 4))
    return arr[:, :, :3]


def preprocess_for_model(bgr):
    """BGR uint8 -> RGB, crop sky+hood, resize, [0,1] CHW float32.

    This is the single definition of what the network sees, used identically at
    train time (from saved PNGs read as BGR) and inference time (from the camera).
    """
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    cropped = rgb[CROP_TOP:CROP_BOT, :]
    resized = cv2.resize(cropped, (INPUT_W, INPUT_H))
    return (resized.astype(np.float32) / 255.0).transpose(2, 0, 1)

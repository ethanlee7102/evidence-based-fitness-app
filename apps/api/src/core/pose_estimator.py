import cv2
import math
from typing import Optional
import onnxruntime as ort
import numpy as np
import urllib.request
import os

# Model path for RTMPose
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rtmpose_m.onnx")
MODEL_URL = "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip"

# RTMPose input dimensions
INPUT_HEIGHT = 256
INPUT_WIDTH = 192

# COCO 17-keypoint to MediaPipe index mapping
# MediaPipe indices used by analyzers: 11,12 (shoulders), 13,14 (elbows),
# 15,16 (wrists), 23,24 (hips), 25,26 (knees), 27,28 (ankles)
COCO_TO_MEDIAPIPE = {
    5: 11,   # left shoulder
    6: 12,   # right shoulder
    7: 13,   # left elbow
    8: 14,   # right elbow
    9: 15,   # left wrist
    10: 16,  # right wrist
    11: 23,  # left hip
    12: 24,  # right hip
    13: 25,  # left knee
    14: 26,  # right knee
    15: 27,  # left ankle
    16: 28,  # right ankle
}

# Required MediaPipe indices that analyzers use
REQUIRED_MEDIAPIPE_INDICES = {11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28}


def ensure_model_downloaded():
    """Download the RTMPose model if not present."""
    if not os.path.exists(MODEL_PATH):
        import zipfile
        import tempfile

        print(f"Downloading RTMPose model...")
        zip_path = os.path.join(tempfile.gettempdir(), "rtmpose_m.zip")
        urllib.request.urlretrieve(MODEL_URL, zip_path)

        # Extract the .onnx file from the zip
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".onnx"):
                    # Read the onnx file and write to MODEL_PATH
                    with z.open(name) as src, open(MODEL_PATH, "wb") as dst:
                        dst.write(src.read())
                    break

        os.remove(zip_path)
        print(f"Model saved to {MODEL_PATH}")


class OneEuroFilter:
    """
    One Euro Filter for temporal smoothing of pose landmarks.

    This is the same algorithm used by MMPose for built-in smoothing.
    Reduces jitter while maintaining responsiveness to fast movements.
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.3, d_cutoff: float = 1.0):
        """
        Initialize the filter.

        Args:
            min_cutoff: Minimum cutoff frequency (lower = more smoothing)
            beta: Speed coefficient (higher = less lag during fast movements)
            d_cutoff: Cutoff frequency for derivative
        """
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: Optional[float] = None
        self.dx_prev: Optional[float] = None
        self.t_prev: Optional[float] = None

    def _smoothing_factor(self, t_e: float, cutoff: float) -> float:
        """Compute exponential smoothing factor."""
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def __call__(self, x: float, t: float) -> float:
        """
        Filter a value.

        Args:
            x: Current value
            t: Current timestamp (in seconds)

        Returns:
            Smoothed value
        """
        if self.t_prev is None:
            # First sample
            self.x_prev = x
            self.dx_prev = 0.0
            self.t_prev = t
            return x

        t_e = t - self.t_prev
        if t_e <= 0:
            return self.x_prev

        # Estimate derivative
        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # Adaptive cutoff based on speed
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # Filter value
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1 - a) * self.x_prev

        # Store for next iteration
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat

    def reset(self):
        """Reset the filter state."""
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None


class PoseEstimator:
    """MMPose/RTMPose pose estimation wrapper using ONNX runtime."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        use_temporal_smoothing: bool = True,
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.use_temporal_smoothing = use_temporal_smoothing
        self._filters: dict[tuple[int, str], OneEuroFilter] = {}

        ensure_model_downloaded()

        # Initialize ONNX session
        providers = ["CPUExecutionProvider"]
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(MODEL_PATH, providers=providers)
        self.input_name = self.session.get_inputs()[0].name

    def _preprocess(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """
        Preprocess frame for RTMPose inference.

        Returns:
            Preprocessed input tensor and metadata for postprocessing
        """
        h, w = frame.shape[:2]

        # Calculate scale to fit input dimensions while preserving aspect ratio
        scale = min(INPUT_WIDTH / w, INPUT_HEIGHT / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to input size
        pad_w = (INPUT_WIDTH - new_w) // 2
        pad_h = (INPUT_HEIGHT - new_h) // 2

        padded = np.zeros((INPUT_HEIGHT, INPUT_WIDTH, 3), dtype=np.uint8)
        padded[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized

        # Normalize (ImageNet mean/std)
        mean = np.array([123.675, 116.28, 103.53], dtype=np.float32)
        std = np.array([58.395, 57.12, 57.375], dtype=np.float32)
        normalized = (padded.astype(np.float32) - mean) / std

        # CHW format and add batch dimension
        input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...]

        meta = {
            "original_size": (w, h),
            "scale": scale,
            "pad": (pad_w, pad_h),
        }

        return input_tensor.astype(np.float32), meta

    def _postprocess(
        self, outputs: list, meta: dict
    ) -> Optional[list[tuple[float, float, float]]]:
        """
        Postprocess RTMPose outputs to get keypoints.

        RTMPose uses SimCC (Simple Coordinate Classification) which outputs
        x and y heatmaps that are decoded to coordinates.

        Returns:
            List of (x, y, confidence) tuples for each COCO keypoint, or None if no pose detected
        """
        # RTMPose outputs: simcc_x [1, 17, W*2], simcc_y [1, 17, H*2]
        simcc_x, simcc_y = outputs[0], outputs[1]

        # Get coordinates from SimCC outputs
        x_locs = np.argmax(simcc_x, axis=2)  # [1, 17]
        y_locs = np.argmax(simcc_y, axis=2)  # [1, 17]

        # Get confidence scores
        x_scores = np.max(simcc_x, axis=2)  # [1, 17]
        y_scores = np.max(simcc_y, axis=2)  # [1, 17]
        scores = (x_scores + y_scores) / 2  # Average confidence

        # Decode to image coordinates (SimCC uses 2x resolution)
        x_coords = x_locs[0] / 2.0  # [17]
        y_coords = y_locs[0] / 2.0  # [17]
        confidences = scores[0]  # [17]

        # Check if we have a valid pose (average confidence above threshold)
        avg_confidence = np.mean(confidences)
        if avg_confidence < self.min_detection_confidence:
            return None

        # Convert from padded/scaled coordinates back to normalized [0, 1]
        pad_w, pad_h = meta["pad"]
        scale = meta["scale"]
        orig_w, orig_h = meta["original_size"]

        keypoints = []
        for i in range(17):
            # Remove padding offset and scale back
            x = (x_coords[i] - pad_w) / (orig_w * scale)
            y = (y_coords[i] - pad_h) / (orig_h * scale)

            # Clamp to [0, 1]
            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))

            keypoints.append((float(x), float(y), float(confidences[i])))

        return keypoints

    def _apply_temporal_smoothing(
        self, keypoints: list[tuple[float, float, float]], timestamp: float
    ) -> list[tuple[float, float, float]]:
        """Apply One Euro filtering to smooth keypoints over time."""
        smoothed = []
        for i, (x, y, conf) in enumerate(keypoints):
            # Create filters for this keypoint if needed
            filter_key_x = (i, "x")
            filter_key_y = (i, "y")

            if filter_key_x not in self._filters:
                self._filters[filter_key_x] = OneEuroFilter()
                self._filters[filter_key_y] = OneEuroFilter()

            # Apply smoothing
            x_smooth = self._filters[filter_key_x](x, timestamp)
            y_smooth = self._filters[filter_key_y](y, timestamp)

            smoothed.append((x_smooth, y_smooth, conf))

        return smoothed

    def _convert_to_mediapipe_format(
        self, keypoints: list[tuple[float, float, float]]
    ) -> dict[int, dict]:
        """
        Convert COCO keypoints to MediaPipe-compatible format.

        Maps COCO indices to MediaPipe indices and creates the expected
        dict structure with x, y, z, visibility keys.
        """
        frame_landmarks = {}

        for coco_idx, mediapipe_idx in COCO_TO_MEDIAPIPE.items():
            x, y, conf = keypoints[coco_idx]
            frame_landmarks[mediapipe_idx] = {
                "x": x,
                "y": y,
                "z": 0.0,  # COCO doesn't provide depth
                "visibility": conf,
            }

        return frame_landmarks

    def extract_landmarks(self, video_path: str) -> list[Optional[dict[int, dict]]]:
        """
        Extract pose landmarks from each frame of a video.

        Returns a list where each element is either:
        - A dict mapping landmark index -> {x, y, z, visibility}
        - None if no pose was detected in that frame

        Output format matches MediaPipe for compatibility with existing analyzers.
        Key landmark indices:
        - 11, 12: shoulders
        - 13, 14: elbows
        - 15, 16: wrists
        - 23, 24: hips
        - 25, 26: knees
        - 27, 28: ankles
        """
        cap = cv2.VideoCapture(video_path)

        try:
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")

            landmarks_per_frame: list[Optional[dict[int, dict]]] = []

            # Reset temporal filters for new video
            self._filters.clear()

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frame_idx = 0

            while True:
                success, frame = cap.read()
                if not success:
                    break

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Preprocess
                input_tensor, meta = self._preprocess(frame_rgb)

                # Run inference
                outputs = self.session.run(None, {self.input_name: input_tensor})

                # Postprocess
                keypoints = self._postprocess(outputs, meta)

                if keypoints is None:
                    landmarks_per_frame.append(None)
                else:
                    # Apply temporal smoothing if enabled
                    if self.use_temporal_smoothing:
                        timestamp = frame_idx / fps
                        keypoints = self._apply_temporal_smoothing(keypoints, timestamp)

                    # Convert to MediaPipe format
                    frame_landmarks = self._convert_to_mediapipe_format(keypoints)
                    landmarks_per_frame.append(frame_landmarks)

                frame_idx += 1

            return landmarks_per_frame
        finally:
            cap.release()

    @staticmethod
    def get_landmark(
        frame_landmarks: Optional[dict[int, dict]],
        index: int,
    ) -> Optional[dict]:
        """Safely get a landmark from frame data."""
        if frame_landmarks is None:
            return None
        return frame_landmarks.get(index)

    @staticmethod
    def midpoint(p1: dict, p2: dict) -> dict:
        """Calculate midpoint between two landmarks."""
        return {
            "x": (p1["x"] + p2["x"]) / 2,
            "y": (p1["y"] + p2["y"]) / 2,
            "z": (p1["z"] + p2["z"]) / 2,
        }

    @staticmethod
    def is_visible(landmark: Optional[dict], threshold: float = 0.5) -> bool:
        """Check if a landmark has sufficient visibility confidence."""
        if landmark is None:
            return False
        return landmark.get("visibility", 0) >= threshold

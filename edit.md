Plan: Replace MediaPipe with MMPose/RTMPose                                                                                                                                                                        
                                                                                                                                                                                                                      
 Overview                                                                                                                                                                                                             
                                                                                                                                                                                                                      
 Replace MediaPipe pose estimation with MMPose (using RTMPose model) for better occlusion handling and built-in temporal smoothing. The switch is isolated to a single file with no changes needed to analyzers.      
                                                                                                                                                                                                                      
 ---                                                                                                                                                                                                                  
 Why MMPose?
 ┌────────────────────┬───────────────────┬──────────────────────────────┐
 │      Feature       │     MediaPipe     │        MMPose/RTMPose        │
 ├────────────────────┼───────────────────┼──────────────────────────────┤
 │ License            │ Apache 2.0 (free) │ Apache 2.0 (free)            │
 ├────────────────────┼───────────────────┼──────────────────────────────┤
 │ Temporal smoothing │ ❌ Manual         │ ✅ Built-in (OneEuro filter) │
 ├────────────────────┼───────────────────┼──────────────────────────────┤
 │ Fine-tuning        │ ❌ Not supported  │ ✅ Full support              │
 ├────────────────────┼───────────────────┼──────────────────────────────┤
 │ Occlusion handling │ Poor              │ Better                       │
 ├────────────────────┼───────────────────┼──────────────────────────────┤
 │ Speed              │ ~100ms CPU        │ ~50ms CPU                    │
 └────────────────────┴───────────────────┴──────────────────────────────┘
 ---
 Landmark Index Mapping (COCO → MediaPipe)

 MMPose uses COCO 17-keypoint format. Map to MediaPipe indices:
 ┌───────────┬────────┬───────────┐
 │ Body Part │  COCO  │ MediaPipe │
 ├───────────┼────────┼───────────┤
 │ Shoulders │ 5, 6   │ 11, 12    │
 ├───────────┼────────┼───────────┤
 │ Elbows    │ 7, 8   │ 13, 14    │
 ├───────────┼────────┼───────────┤
 │ Wrists    │ 9, 10  │ 15, 16    │
 ├───────────┼────────┼───────────┤
 │ Hips      │ 11, 12 │ 23, 24    │
 ├───────────┼────────┼───────────┤
 │ Knees     │ 13, 14 │ 25, 26    │
 ├───────────┼────────┼───────────┤
 │ Ankles    │ 15, 16 │ 27, 28    │
 └───────────┴────────┴───────────┘
 Note: COCO doesn't provide Z-depth; set z=0.0 (analyzers primarily use x, y).

 ---
 Files to Modify
 ┌───────────────────────────────────────┬────────────────────────────────────┐
 │                 File                  │               Change               │
 ├───────────────────────────────────────┼────────────────────────────────────┤
 │ apps/api/src/core/pose_estimator.py   │ Replace MediaPipe with MMPose ONNX │
 ├───────────────────────────────────────┼────────────────────────────────────┤
 │ apps/api/requirements.txt             │ Remove mediapipe, add onnxruntime  │
 ├───────────────────────────────────────┼────────────────────────────────────┤
 │ apps/api/tests/test_pose_estimator.py │ Add MMPose-specific tests          │
 └───────────────────────────────────────┴────────────────────────────────────┘
 No changes needed: Analyzers, LandmarkPostProcessor, AnalysisService (interface stays identical)

 ---
 Implementation

 1. Update Dependencies

 # apps/api/requirements.txt
 - mediapipe>=0.10.30
 + onnxruntime>=1.15.0
   opencv-python-headless>=4.9.0
   numpy>=1.26.0

 2. Replace PoseEstimator

 Key changes to apps/api/src/core/pose_estimator.py:

 # Model setup
 MODEL_URL = "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-body7_pt-body7_420e-256x192.onnx"

 # COCO to MediaPipe mapping
 COCO_TO_MEDIAPIPE = {
     5: 11, 6: 12,    # shoulders
     7: 13, 8: 14,    # elbows
     9: 15, 10: 16,   # wrists
     11: 23, 12: 24,  # hips
     13: 25, 14: 26,  # knees
     15: 27, 16: 28,  # ankles
 }

 class OneEuroFilter:
     """Built-in temporal smoothing (same algorithm MMPose uses)."""
     def __init__(self, min_cutoff=0.5, beta=0.007):
         # ... filter implementation

 class PoseEstimator:
     def __init__(self, use_temporal_smoothing=True):
         # Load ONNX model
         self.session = ort.InferenceSession(MODEL_PATH)
         self._filters = {}  # Per-landmark smoothing

     def extract_landmarks(self, video_path: str) -> list[Optional[dict[int, dict]]]:
         # Same return type as before
         # Internally: preprocess → inference → postprocess → smooth

     # Keep identical static methods:
     # get_landmark(), midpoint(), is_visible()

 3. Add Tests

 # tests/test_pose_estimator.py
 def test_coco_to_mediapipe_mapping_complete():
     """All required landmarks are mapped."""

 def test_output_format_matches_mediapipe():
     """Output format identical to MediaPipe."""

 def test_temporal_smoothing_reduces_jitter():
     """OneEuro filter reduces variance."""

 ---
 Model Choice

 RTMPose-m (medium) - Best balance:
 - Input: 256×192
 - Speed: ~10ms GPU, ~50ms CPU
 - Accuracy: 75.3% AP (similar to MediaPipe)
 - Size: ~25MB

 ---
 Verification

 1. Unit tests: Run pytest tests/test_pose_estimator.py
 2. Integration: Analyze a deadlift video, verify:
   - Ankle landmarks no longer jump
   - Scores are reasonable
   - Skeleton overlay renders correctly
 3. Compare: Same video with MediaPipe vs MMPose (optional)

 ---
 Rollback Plan

 Keep MediaPipe in requirements.txt initially. If issues arise:
 # Toggle in analysis_service.py
 USE_MMPOSE = False  # Set to True to use MMPose
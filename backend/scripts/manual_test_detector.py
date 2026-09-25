import sys
sys.path.insert(0, ".")

import cv2
from app.cv.detector import Detector

# Point this at any video you have locally, or 0 for your webcam
cap = cv2.VideoCapture("data/raw/any_video.mp4")
ok, frame = cap.read()
cap.release()

if not ok:
    print("Could not read a frame — check the video path")
    sys.exit(1)

detector = Detector()
results = detector.detect(frame)

print(f"Found {len(results)} relevant object(s):")
for d in results:
    print(f"  {d['class_name']}  conf={d['confidence']:.2f}  bbox={d['bbox']}")
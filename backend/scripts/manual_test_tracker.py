import sys
sys.path.insert(0, ".")

import cv2
from app.cv.tracker import Tracker

cap = cv2.VideoCapture("data/raw/any_video.mp4")
tracker = Tracker()  # one Tracker for the whole video -- this matters, see below

frame_num = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break

    results = tracker.track(frame)
    if results:
        ids = [r["track_id"] for r in results]
        print(f"Frame {frame_num}: track_ids seen = {ids}")

    frame_num += 1
    if frame_num > 60:  # just check the first ~60 frames, don't need the whole video
        break

cap.release()
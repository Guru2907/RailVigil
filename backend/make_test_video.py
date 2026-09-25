# run this once from backend/, e.g. as a throwaway: python make_test_video.py
import cv2
import numpy as np

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter("data/raw/test_upload.mp4", fourcc, 10, (320, 240))
for i in range(30):
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    x = 10 + i * 3
    cv2.rectangle(frame, (x, 100), (x + 40, 140), (255, 255, 255), -1)
    writer.write(frame)
writer.release()
print("done")
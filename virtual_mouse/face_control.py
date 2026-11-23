"""Face-controlled mouse.

Open the mouth to toggle pointer control, wink to click, and close both eyes
to toggle scrolling. Esc quits. The camera frame is mirrored. Eye landmarks
are swapped after the mirror so a wink lines up with the picture the person
sees, which is what the 2020 script did.

The landmark model is not in this repository. Set ``FACE_MODEL_PATH`` or run
``python -m virtual_mouse.download_model``. ``FACE_CAMERA_INDEX`` chooses the
camera (default 0).

Based on face-control.py by Zarka McClung:
https://github.com/michael-mcclung/Blockchain-Virtual-Mouse
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_URL = "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
DEFAULT_MODEL = Path(__file__).resolve().parent / "model" / "shape_predictor_68_face_landmarks.dat"

MOUTH_AR_THRESH = 0.6
MOUTH_AR_CONSECUTIVE_FRAMES = 15
EYE_AR_THRESH = 0.19
EYE_AR_CONSECUTIVE_FRAMES = 15
WINK_AR_DIFF_THRESH = 0.04
WINK_CONSECUTIVE_FRAMES = 10

YELLOW = (0, 255, 255)
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)


def model_path() -> Path:
    override = os.environ.get("FACE_MODEL_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_MODEL


def check_model(path: Path | None = None) -> tuple[bool, str]:
    """Return whether the landmark file is present, plus a message for stderr."""
    location = path if path is not None else model_path()
    if location.is_file() and location.stat().st_size > 0:
        return True, f"Using facial-landmark model {location}"
    message = (
        "The facial-landmark model is not on disk.\n\n"
        f"Expected file:\n  {location}\n\n"
        "The virtual mouse uses dlib's 68-point shape predictor. The file is "
        "about 64 MB compressed and is distributed by the dlib project. This "
        "repository does not include it. Review that project's license before "
        "you download it.\n\n"
        "From the repository root:\n"
        "  python -m virtual_mouse.download_model\n\n"
        "Or download it yourself:\n"
        "  curl -L -o virtual_mouse/model/shape_predictor_68_face_landmarks.dat.bz2 \\\n"
        f"    {MODEL_URL}\n"
        "  bunzip2 -f virtual_mouse/model/shape_predictor_68_face_landmarks.dat.bz2\n"
    )
    return False, message


def camera_index() -> int:
    raw = os.environ.get("FACE_CAMERA_INDEX", "0").strip() or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def _missing_dependency_message(exc: BaseException) -> str:
    return (
        "The virtual mouse needs extra packages that are not installed "
        f"({exc}).\n\n"
        "  pip install -r requirements-mouse.txt\n\n"
        "dlib often needs CMake and a C++ compiler when a wheel is not "
        "available for your platform. The blockchain exchange does not need "
        "these packages.\n"
    )


def _camera_message(index: int) -> str:
    return (
        f"No webcam could be opened (camera index {index}).\n\n"
        "Connect a camera, or set FACE_CAMERA_INDEX to another device number. "
        "This program needs a local webcam and a desktop session. It does not "
        "run in the web demo.\n"
    )


def _loop(video, cv2, dlib, imutils, np, pag, face_utils, predictor, detector) -> int:
    from .utils import direction, eye_aspect_ratio, mouth_aspect_ratio

    (l_start, l_end) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (r_start, r_end) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
    (n_start, n_end) = face_utils.FACIAL_LANDMARKS_IDXS["nose"]
    (m_start, m_end) = face_utils.FACIAL_LANDMARKS_IDXS["mouth"]

    mouth_counter = 0
    eye_counter = 0
    wink_counter = 0
    input_mode = False
    scroll_mode = False
    anchor_point = (0, 0)
    cam_w = 640
    cam_h = 480

    sys.stdout.write(
        "Virtual mouse is running. Esc closes the window.\n"
        "Hold the mouth open to toggle pointer control.\n"
        "Hold one eye closed to click. Hold both eyes closed to toggle scroll.\n"
        "Throw the pointer into a screen corner to abort (PyAutoGUI fail-safe).\n"
    )

    while True:
        ok, frame = video.read()
        if not ok or frame is None:
            sys.stderr.write("The webcam stopped providing frames.\n")
            return 3

        frame = cv2.flip(frame, 1)
        frame = imutils.resize(frame, width=cam_w, height=cam_h)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = detector(gray, 0)

        if len(rects) == 0:
            cv2.imshow("Virtual mouse", frame)
            if (cv2.waitKey(1) & 0xFF) == 27:
                return 0
            continue

        shape = face_utils.shape_to_np(predictor(gray, rects[0]))
        mouth = shape[m_start:m_end]
        left_eye = shape[l_start:l_end]
        right_eye = shape[r_start:r_end]
        nose = shape[n_start:n_end]

        # The frame is mirrored, so swap the eyes to match that view.
        left_eye, right_eye = right_eye, left_eye

        mar = mouth_aspect_ratio(mouth)
        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0
        diff_ear = abs(left_ear - right_ear)
        nose_point = (int(nose[3, 0]), int(nose[3, 1]))

        cv2.drawContours(frame, [cv2.convexHull(mouth)], -1, YELLOW, 1)
        cv2.drawContours(frame, [cv2.convexHull(left_eye)], -1, YELLOW, 1)
        cv2.drawContours(frame, [cv2.convexHull(right_eye)], -1, YELLOW, 1)
        for (x, y) in np.concatenate((mouth, left_eye, right_eye), axis=0):
            cv2.circle(frame, (int(x), int(y)), 2, GREEN, -1)

        if diff_ear > WINK_AR_DIFF_THRESH:
            if left_ear < right_ear and left_ear < EYE_AR_THRESH:
                wink_counter += 1
                if wink_counter > WINK_CONSECUTIVE_FRAMES:
                    pag.click(button="left")
                    wink_counter = 0
            elif right_ear < left_ear and right_ear < EYE_AR_THRESH:
                wink_counter += 1
                if wink_counter > WINK_CONSECUTIVE_FRAMES:
                    pag.click(button="right")
                    wink_counter = 0
            else:
                wink_counter = 0
        elif ear <= EYE_AR_THRESH:
            eye_counter += 1
            if eye_counter > EYE_AR_CONSECUTIVE_FRAMES:
                scroll_mode = not scroll_mode
                eye_counter = 0
        else:
            eye_counter = 0
            wink_counter = 0

        if mar > MOUTH_AR_THRESH:
            mouth_counter += 1
            if mouth_counter >= MOUTH_AR_CONSECUTIVE_FRAMES:
                input_mode = not input_mode
                mouth_counter = 0
                anchor_point = nose_point
        else:
            mouth_counter = 0

        if input_mode:
            cv2.putText(frame, "READING INPUT!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2)
            box_w, box_h = 60, 35
            ax, ay = anchor_point
            cv2.rectangle(frame, (ax - box_w, ay - box_h), (ax + box_w, ay + box_h), GREEN, 2)
            cv2.line(frame, anchor_point, nose_point, BLUE, 2)
            facing = direction(nose_point, anchor_point, box_w, box_h)
            cv2.putText(frame, facing.upper(), (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2)
            drag = 18
            if facing == "right":
                pag.moveRel(drag, 0)
            elif facing == "left":
                pag.moveRel(-drag, 0)
            elif facing == "up":
                pag.scroll(40) if scroll_mode else pag.moveRel(0, -drag)
            elif facing == "down":
                pag.scroll(-40) if scroll_mode else pag.moveRel(0, drag)

        if scroll_mode:
            cv2.putText(frame, "SCROLL MODE IS ON!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2)

        cv2.imshow("Virtual mouse", frame)
        if (cv2.waitKey(1) & 0xFF) == 27:
            return 0


def main() -> int:
    ok, message = check_model()
    if not ok:
        sys.stderr.write(message)
        return 2

    try:
        import cv2
        import dlib
        import imutils
        import numpy as np
        import pyautogui as pag
        from imutils import face_utils
    except ImportError as exc:
        sys.stderr.write(_missing_dependency_message(exc))
        return 2
    except Exception as exc:
        sys.stderr.write(
            "The virtual mouse could not start the desktop libraries "
            f"({exc}). A local desktop session is required.\n"
        )
        return 2

    try:
        predictor = dlib.shape_predictor(str(model_path()))
        detector = dlib.get_frontal_face_detector()
    except Exception as exc:
        sys.stderr.write(f"The facial-landmark model could not be loaded ({exc}).\n")
        return 2

    index = camera_index()
    video = cv2.VideoCapture(index)
    if not video.isOpened():
        video.release()
        sys.stderr.write(_camera_message(index))
        return 3

    try:
        return _loop(video, cv2, dlib, imutils, np, pag, face_utils, predictor, detector)
    except pag.FailSafeException:
        sys.stderr.write("PyAutoGUI fail-safe stopped the virtual mouse.\n")
        return 0
    except cv2.error as exc:
        sys.stderr.write(
            "The camera window could not be opened "
            f"({exc}). A desktop session is required.\n"
        )
        return 4
    finally:
        video.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())

from virtual_mouse import download_model, face_control
from virtual_mouse.utils import direction, eye_aspect_ratio, mouth_aspect_ratio


def test_direction_matches_the_original_rules():
    assert direction((200, 50), (0, 50), 60, 35) == "right"
    assert direction((-200, 50), (0, 50), 60, 35) == "left"
    assert direction((10, 200), (0, 0), 60, 35) == "down"
    assert direction((10, -200), (0, 0), 60, 35) == "up"
    assert direction((10, 10), (0, 0), 60, 35) == "-"
    assert direction((100, 100), (0, 0), 60, 35) == "right"


def test_eye_and_mouth_ratios():
    open_eye = [(0, 0), (1, -1), (2, -1), (3, 0), (2, 1), (1, 1)]
    closed_eye = [(0, 0), (1, 0), (2, 0), (3, 0), (2, 0), (1, 0)]
    assert eye_aspect_ratio(open_eye) > 0.5
    assert eye_aspect_ratio(closed_eye) == 0.0

    mouth = [(0, 0)] * 20
    mouth[12] = (0, 0)
    mouth[16] = (10, 0)
    mouth[13] = (2, -2)
    mouth[19] = (2, 2)
    mouth[14] = (5, -2)
    mouth[18] = (5, 2)
    mouth[15] = (8, -2)
    mouth[17] = (8, 2)
    assert mouth_aspect_ratio(mouth) == 0.6
    assert mouth_aspect_ratio([(0, 0)] * 20) == 0.0


def test_missing_model_message(tmp_path):
    ok, message = face_control.check_model(tmp_path / "missing.dat")
    assert ok is False
    assert "not on disk" in message
    assert "dlib.net" in message
    assert "download_model" in message


def test_mouse_exits_when_the_model_is_missing(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FACE_MODEL_PATH", str(tmp_path / "missing.dat"))
    assert face_control.main() == 2
    assert "not on disk" in capsys.readouterr().err


def test_model_download_constants():
    assert download_model.MODEL_URL == "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
    assert download_model.destination().name == "shape_predictor_68_face_landmarks.dat"
    assert download_model.destination().parent.name == "model"

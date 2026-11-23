"""Download dlib's 68-point facial-landmark model into virtual_mouse/model/.

The file is fetched only when you run this module. It is not committed.
Source: https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
(about 64 MB compressed). Review the dlib project's license before using it.
"""

from __future__ import annotations

import argparse
import bz2
import sys
import tempfile
import urllib.request
from pathlib import Path

MODEL_URL = "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
DESTINATION = Path(__file__).resolve().parent / "model" / "shape_predictor_68_face_landmarks.dat"


def destination() -> Path:
    return DESTINATION


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the dlib 68-point face landmark model.")
    parser.add_argument("--force", action="store_true", help="Replace an existing model file.")
    parser.add_argument("--url", default=MODEL_URL, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    target = destination()
    if target.is_file() and target.stat().st_size > 0 and not args.force:
        sys.stdout.write(f"Model already present at {target}\n")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.write(f"Downloading {args.url}\nThis is the dlib project's file (about 64 MB compressed).\n")

    compressed = Path(tempfile.mkstemp(prefix="shape_predictor_", suffix=".bz2")[1])
    partial = target.with_suffix(".dat.partial")
    try:
        _download(args.url, compressed)
        _decompress(compressed, partial)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        sys.stderr.write(f"The model could not be downloaded ({exc}).\nYou can fetch it manually from {MODEL_URL}\n")
        return 1
    finally:
        compressed.unlink(missing_ok=True)

    partial.replace(target)
    sys.stdout.write(f"Saved {target} ({target.stat().st_size} bytes).\n")
    return 0


def _download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "blockchain-exchange-model-download"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
    if path.stat().st_size < 1_000_000:
        raise RuntimeError("the download was much smaller than the landmark archive")
    with path.open("rb") as handle:
        magic = handle.read(3)
    if magic != b"BZh":
        raise RuntimeError("the download was not a bzip2 file")


def _decompress(source: Path, dest: Path) -> None:
    with bz2.open(source, "rb") as incoming, dest.open("wb") as outgoing:
        while True:
            chunk = incoming.read(1024 * 1024)
            if not chunk:
                break
            outgoing.write(chunk)
    if dest.stat().st_size < 1_000_000:
        raise RuntimeError("the decompressed model was unexpectedly small")


if __name__ == "__main__":
    sys.exit(main())

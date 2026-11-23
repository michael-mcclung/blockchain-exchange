"""``python -m virtual_mouse`` starts the camera loop."""

import sys

from .face_control import main

if __name__ == "__main__":
    sys.exit(main())

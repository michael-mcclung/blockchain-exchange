# Credits

Texas Tech University, Software Engineering I, about 2019–2020.

## Authors

- **Michael McClung** (Mac) — project owner. Wrote the original Tkinter launcher (`SE1_GUI.py`) in [Blockchain-Virtual-Mouse](https://github.com/michael-mcclung/Blockchain-Virtual-Mouse). This repository is his portfolio revival of that project.
- **Zarka McClung** — virtual mouse. Public history of that repository shows commit `5dfc9a3` (“Virtual Mouse Integration”) adding `face-control.py` and `utils.py`, plus the note about where to get the dlib model.
- **Maktm** (git author name Michael Kiros on the original commits) — blockchain exchange. The 2019 Flask app was published at [Maktm/blockchain-exchange](https://github.com/Maktm/blockchain-exchange) and was linked from Mac’s repository as a submodule. It is included here with Michael McClung’s approval.

## Exchange history

The `exchange/` folder was imported with `git subtree`, so Maktm’s commits stay in this repository. They are ancestors of the import commit, including:

- `f85e0e9` — Basic structure of blockchain program
- `95f033b` — Add files for stock exchange
- `f95a8dd` — Update README.md

`git log --oneline` lists those commits. The files in `exchange/` have since been updated so the app runs on Python 3.11+.

## Model file

The virtual mouse expects dlib’s 68-point shape predictor. That file is not committed. It is downloaded from the dlib project when you ask for it: https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2

The original repositories did not include a license file. This revival does not add one and does not claim a new license over their work.

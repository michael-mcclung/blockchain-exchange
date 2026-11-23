# Facial landmark model

The virtual mouse expects dlib's 68-point predictor at:

`virtual_mouse/model/shape_predictor_68_face_landmarks.dat`

The file is about 64 MB compressed (larger once unpacked) and is distributed by the dlib project:

https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2

From the repository root:

```bash
python -m virtual_mouse.download_model
```

Or download it yourself:

```bash
curl -L -o virtual_mouse/model/shape_predictor_68_face_landmarks.dat.bz2 \
  https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
bunzip2 -f virtual_mouse/model/shape_predictor_68_face_landmarks.dat.bz2
```

`FACE_MODEL_PATH` can point at a copy stored somewhere else.

This repository does not commit the model. Check the dlib project's license before you use the file. If the file or a webcam is missing, `python -m virtual_mouse` exits with an explanation instead of crashing.

The original note in [Blockchain-Virtual-Mouse](https://github.com/michael-mcclung/Blockchain-Virtual-Mouse) said the same thing: download `shape_predictor_68_face_landmarks.dat.bz2` from http://dlib.net/files and place the unpacked file in the model folder.

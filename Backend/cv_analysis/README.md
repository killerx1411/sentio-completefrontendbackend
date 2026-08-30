# `cv_analysis` — CV / behavioural-intelligence system

Everything that processes school CCTV footage lives here: frame extraction, face
detection/recognition, emotion, posture, gaze, wellbeing traits, person profiles,
report generation, and the HTTP surface that serves them.

## Running it

```bash
pip install -r ../requirements.txt -r ../requirements-cv.txt

gunicorn -c ../gunicorn_config.py cv_analysis.app:app   # standalone CV service
python -m cv_analysis.app                               # local dev, CV_PORT (5002)
```

The combined deployment (`test_db:app`) mounts the same blueprints onto the
stakeholder/auth app; URLs are identical either way.

## Module map

| Module | Responsibility |
|---|---|
| `libraries.py` | The **only** import site for cv2, DeepFace, MediaPipe, face_recognition, MTCNN. Exposes `*_AVAILABLE` flags and `library_status()`. |
| `config.py` | Paths, thresholds, CV rate limit, `CV_*` environment overrides. |
| `state.py` | In-process `person_database`, `pinned_profiles`, `analysis_cache`, `_db_lock`. |
| `db.py` | Writes to the CV tables `persons`, `videos`, `frames`, `analysis`, `traits`. |
| `pipeline.py` | The analysis pipeline. Knows nothing about auth. |
| `dashboard.py` | Operator dashboard HTML served at `GET /`. |
| `routes.py` | `cv_bp` — root CV routes + `register_cv_blueprints()`. |
| `routes_analysis.py` | `analysis_bp` — scope-filtered report access under `/analysis`. |
| `routes_person.py` | `person_bp` — CV person profiles under `/person`. |
| `app.py` | `create_cv_app()` — standalone CV Flask app. |

## Dependency rule

```
cv_analysis  →  auth        allowed
auth         →  cv_analysis NEVER
```

`tests/test_service_boundary.py` fails the build if the second arrow ever appears.

The CV system reuses the stakeholder auth stack on purpose — same JWTs, same
PostgreSQL permission tables, same row-level scope. There is deliberately **no**
second JWT implementation, user store or role system here.

Five seams point at `auth/`, all listed with their extraction cost in
[`../ARCHITECTURE_SEPARATION.md`](../ARCHITECTURE_SEPARATION.md) §D.

## Data ownership

CV owns and writes: `persons`, `videos`, `frames`, `analysis`, `traits`
(default/public schema), plus `input_videos/`, `profiles/person_database.json`,
`analysis_results/`, `snapshots/`.

CV never writes anything in the `auth_enabler` schema. Identity, roles,
permissions, sessions and audit belong to the auth service.

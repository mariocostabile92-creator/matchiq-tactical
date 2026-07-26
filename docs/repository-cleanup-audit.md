# MatchIQ Repository Cleanup Audit

Date: 2026-07-26

## Scope

Controlled cleanup of the Git repository rooted at:

`C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend`

The cleanup does not change application behavior, backend routes, database
schemas, AI logic, authentication, PWA behavior, or frontend workflows.

## Repository inventory before cleanup

| Item | Initial state | Classification | Action |
| --- | --- | --- | --- |
| `.venv/` | 7,105 files, 261,018,543 bytes | Local Python environment | Remove |
| `__pycache__/` and `*.pyc` | 269 files, 3,036,737 bytes | Generated Python bytecode | Remove |
| `.pytest_cache/` | Not found | Generated test cache | Keep ignored |
| `.env`, `.env.local` | 2 files, 229 bytes | Local secrets/configuration | Remove after recording names only |
| `storage/.jwt_secret` | 1 file, 86 bytes | Local generated secret | Remove |
| `matchiq.db` | 1 file, 724,992 bytes | Local SQLite database | Remove |
| `reports/` | Generated PDFs and test screenshots | Runtime/test output | Remove |
| `research/vision_spike/input/chelsea_burnley_30s.mp4` | Local video fixture | Forbidden source-tree media | Remove |
| `social-assets/` | Untracked user-owned material | Out of cleanup scope | Leave untouched |

None of the local environment, secret, database, cache, video, report, or
model artifacts above were tracked by Git.

## Frontend ownership analysis

Three frontend-like directories exist on disk:

| Path | Files | Size | Runtime status |
| --- | ---: | ---: | --- |
| `C:\Users\Mario\Desktop\matchiq-tactical\frontend` | 3 | 0 bytes | Empty placeholder, outside Git root |
| `C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\frontend` | 27 | 255,966 bytes | Older copy, outside Git root |
| `C:\Users\Mario\Desktop\matchiq-tactical\matchiq-tactical\backend\frontend` | 179 | 2,468,458 bytes | Active frontend |

The active frontend is proven by:

- `app/routers/frontend.py`, which computes `FRONTEND_DIR` from the Git root;
- the static mount in `main.py`;
- all frontend contract and PWA tests, which read `ROOT / "frontend"`.

The two external copies are not served by the application and are not part of
the Git repository. They were not removed automatically because they may be
manual backups or user-owned working copies. Recommended follow-up: archive
them outside the project only after a manual comparison and user confirmation.

## Configuration hardening

- Expanded `.gitignore` for Python environments, caches, local configuration,
  databases, reports, runtime storage, logs, temporary files, Vision Engine
  datasets/videos/weights, and OS metadata.
- Added `.env.example` with documented variable names and safe placeholder
  values.
- No secret values from `.env`, `.env.local`, or `.jwt_secret` were copied.

## Baseline test

Command:

`python -m unittest discover -s tests`

Result before cleanup: 450 tests executed, 448 passed, 2 failed.

Both failures were the expected repository hygiene checks rejecting
`research/vision_spike/input/chelsea_burnley_30s.mp4`:

- `test_vision_spike.VisionSpikeUnitTests.test_40_no_committed_video_or_weights_in_spike`
- `test_vision_spike_v2.VisionSpikeV2Tests.test_26_no_video_in_spike_source`

## Post-cleanup verification

The approved cleanup removed:

- `.venv/`;
- every `__pycache__/` directory and Python bytecode file;
- `.env` and `.env.local`;
- `storage/.jwt_secret`;
- `matchiq.db`;
- generated `reports/`;
- `research/vision_spike/input/chelsea_burnley_30s.mp4`.

The final test environment was created under the operating-system temporary
directory, outside the repository. It installed:

- product dependencies from `requirements.txt`;
- research-only OpenCV/NumPy dependencies from
  `research/vision_spike/requirements.txt`.

Final result:

`Ran 450 tests in 28.565s - OK`

After the test run, regenerated Python caches and the test-created local
`matchiq.db` were removed again.

Final hygiene checks:

- no project `.venv/`;
- no `__pycache__/`, `.pytest_cache/`, `*.pyc`, logs, or temporary files;
- no real `.env` or `.env.local`;
- no local JWT secret;
- no local database;
- no generated reports directory;
- no video or model-weight artifacts under `research/vision_spike`;
- `social-assets/` still exists and was not modified;
- all functional source files and the active frontend remain unchanged.

## Residual notes

- The two frontend copies outside the Git root remain intentionally untouched.
- `social-assets/` remains untracked because it is user-owned material outside
  this cleanup scope.
- The temporary test virtual environment was removed after verification.

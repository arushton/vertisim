# Codebase Sharing and Production Readiness Review

## Scope and confirmed assumptions

This static review covered repository structure, README, configuration, dependency manifests, packaging, Docker/API code, main simulation paths, and available tests. It did not include a full dependency CVE/license scan, a deployed-service test, or validation of simulation results against real-world flight operations.

The intended users are researchers running local simulations. The FastAPI interface is an optional local RL integration, is not reachable outside a trusted machine/network, and is not intended for real-time flight control or operational aviation decisions. The user confirmed that the aircraft performance data has no restrictions on use.

**Structure update:** The package now lives under `src/vertisim/`, tests under `tests/`, and the API under `src/vertisim/api/`. The Dockerfile was changed to run the example simulation instead of the previously broken API container path. The earlier Docker finding below describes the reviewed snapshot; a Docker build remains unverified because the local Docker daemon was unavailable. Other findings have not been reassessed and their paths refer to the reviewed snapshot.

## 1. Blockers to sharing the code

| Severity | Location | Finding and impact | Recommended action | Blocks |
|---|---|---|---|---|
| High | `.github/workflows/codesee-arch-diagram.yml:7,20-22` | A `pull_request_target` workflow passes a repository secret to a third-party action pinned to mutable tag `@v2`. An altered action could expose the token when processing pull requests. | Remove `pull_request_target` if unnecessary, do not pass secrets to untrusted PR runs, and pin the action to a reviewed commit SHA. Rotate the token if exposure is suspected. | Wider sharing and CI |
| Medium | `vertisim/save_output.py:26-34` | PostgreSQL connection credentials are embedded in source. They may be placeholders, but that is unverified. | Remove credentials from source and use environment/secret configuration. Confirm whether they are active and rotate them if so. | Wider sharing until verified |
| Low | `LICENSE`, `requirements.txt`, `setup.py`, `MANIFEST.in` | The project declares MIT and the user confirmed unrestricted use of the aircraft performance data. The provenance and redistribution terms for all other bundled input data and third-party dependencies have not been inventoried. | Record sources and licenses for remaining bundled inputs and produce a dependency license inventory before redistributing a packaged release. | Wider distribution if any asset has restrictions |

## 2. Blockers to production use

| Severity | Location | Finding and impact | Recommended action | Blocks |
|---|---|---|---|---|
| High | `Dockerfile:12-25,31` | The Dockerfile references absent paths (`configs/config_rl.json` and `vertisim/requirements.txt`), copies only the `vertisim/` package although the API is at top-level `api/`, and launches `vertisim.api.main`. The declared container build/run path does not match this repository. | Align Docker build context, config/dependency paths, and API module layout; then validate a clean image build and container startup. | Production deployment |
| High | `vertisim/save_output.py:214-256,436-454` | Route metrics are prepared inside a loop but inserted after it, so only the last route is persisted. The brief summary also overwrites reward for each route instead of aggregating it. This can produce incomplete or misleading research results. | Insert one row per route and define/test aggregate reward semantics. Add multi-route persistence tests. | Production and research-result integrity |
| High | `api/main.py:50-69`, `vertisim/instance_manager.py:8-12,34-57` | The API reports ready before the simulation instance exists. Some endpoints access that instance without initializing it, so request order can cause failures. Calls also mutate one shared simulation without synchronization. | Make readiness reflect actual initialization, initialize consistently, validate endpoint sequencing, and serialize state-changing requests or explicitly enforce single-client operation. | Production RL integration |
| Medium | `vertisim/save_output.py:168,210,258,285,309` | Several SQLite errors are printed and swallowed. Callers may treat a run as successful even when results were not saved. | Use application logging and surface persistence failures to the caller; test permissions, disk-full, and schema-error behavior. | Production and research-result integrity |

## 3. Important improvements

| Severity | Location | Finding and impact | Recommended action | Blocks |
|---|---|---|---|---|
| High | `vertisim/utils/distribution_generator.py:42`, `vertisim/utils/helpers.py:17-31`, `vertisim/sim_setup.py:74` | Simulation setup applies the configured seed, but distribution sampling reseeds from the current time. Identical configurations and configured seeds therefore do not ensure repeatable results. | Use explicit per-simulation random generators, derive and record child seeds, and test that identical seeds reproduce outputs. | Reproducible research |
| High | `vertisim/test_config.py:1-2`, `vertisim/wind/test_wind.py` | `python -m unittest discover -v` runs the wind tests but fails overall because `test_config.py` imports `sim_setup` as a top-level module. Beyond wind math, simulation, persistence, API, and config behavior have little test coverage. | Make the config example non-discoverable as a test or fix its import; add simulation/config/API/persistence tests and run them in CI. | Production confidence and research integrity |
| Medium | `README.md:62-65` | The README says to create `config.json` but references `vertisim/config.json`, which is not supplied. It does not provide a verified example workflow and required-input explanation. | Provide a redistributable example config, exact command, input inventory, and expected outputs. | Wider sharing and reproducibility |
| Medium | `vertisim/utils/read_files.py:18-30`, `api/config.py:4-8` | Input/config paths depend on the process working directory. Running from a different directory or as an installed package may fail to resolve files. | Define config-relative or package-resource path resolution, validate required inputs before simulation, and test invocation outside the repository root. | Wider sharing and reliable runs |
| Medium | `vertisim/wind/wind.py:12-18,111-123` | Boolean `static_wind=True` skips dynamic processor initialization, but the velocity method only handles string static modes before falling through to dynamic access. A boolean static-wind configuration can fail during flight. | Normalize wind modes to a validated enum or handle the boolean mode explicitly; test every supported mode. | Runs using boolean static wind |
| Medium | `requirements.txt`, `setup.py` | There is no lock file; versions are partly unbounded, and the two manifests do not fully align (for example, Shapely is pinned in requirements but lower-bounded in package metadata). Environments may resolve to different dependency sets. | Define supported Python/platform versions, align manifests, generate a tested lock/environment file, and automate dependency security and license checks. | Reproducible research and production |
| Medium | `vertisim/utils/read_files.py:18-30` | Unsupported or missing input paths are not consistently rejected at the boundary; a missing file can fail later inside pandas or simulation setup with limited context. | Validate config schema and all referenced files at startup with actionable path-specific errors. | New-user experience and reliable runs |

## 4. Optional improvements

| Severity | Location | Finding and impact | Recommended action | Blocks |
|---|---|---|---|---|
| Medium, conditional | `api/main.py:16-69`, `Dockerfile:28-31` | The API has no authentication and binds to all interfaces when run directly. This is acceptable only under the confirmed local/trusted-network deployment assumption; accidental exposure would permit simulation control and state/metric reads. | Keep the service bound to loopback or enforce host/network isolation. Add authentication before any broader exposure. | Not a blocker for the confirmed local use; blocker if exposed |
| Low | `vertisim/vertisim.py:529-579` | `get_aircraft_count` is defined twice; the later definition silently replaces the earlier one. | Remove the duplicate and add a linter/static-analysis check. | Neither |
| Low | `README.md` and repository root | New-user setup exists, but there is no contributor guide, configuration reference, troubleshooting guide, or defined support policy. | Document project layout, supported workflows, config fields, test commands, data provenance, and contribution process. | Neither |
| Low | `vertisim/logger.py:41-58` | Logging is file-oriented and lacks documented retention/operational monitoring. This is limited impact for local research but weak for a long-running service. | Define retention and add structured logs and service-level health/metrics if the API becomes a deployed service. | Neither for local use |

## Security summary

| # | Severity | File | Lines | Finding | Confidence |
|---|---|---|---|---|---|
| 1 | 🟠 HIGH | `.github/workflows/codesee-arch-diagram.yml` | 7, 20-22 | Pull-request-target workflow passes a repository secret to a third-party action referenced by mutable tag. | 9/10 |
| 2 | 🟡 MEDIUM | `vertisim/save_output.py` | 26-34 | PostgreSQL credentials are hardcoded; whether they are active needs confirmation. | 10/10 |
| 3 | 🟡 MEDIUM, conditional | `api/main.py` | 16, 29, 38, 69 | Unauthenticated API controls the simulation if reachable; deployment is confirmed to remain local/trusted. | 9/10 |

## Prioritized remediation plan

1. Secure the pull-request workflow and remove/verify the hardcoded database credential.
2. Fix route-level metric persistence and make database write failures explicit.
3. Make seeded simulations reproducible and add CI coverage for config, simulation, API lifecycle, and persistence.
4. Repair the Docker build/run path and document a verified local example workflow.
5. Inventory licenses for remaining bundled data and dependencies; document local-only API assumptions and input provenance.

This review is not a production-readiness certification or an aviation safety case. If the simulator is later used to inform operational aviation decisions, model validation, uncertainty analysis, and domain/regulatory assurance require separate review.

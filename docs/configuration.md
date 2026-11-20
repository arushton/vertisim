# Configuring a simulation

## Start with the supported example

From the repository root, run:

```bash
python -m vertisim.runner --env_config examples/sfo_sjc.json
```

Use [`examples/sfo_sjc.json`](../examples/sfo_sjc.json) as the current reference for a complete configuration. It is an on-demand, one-day, two-vertiport run using the included SFO-SJC network, layout, wind, and passenger schedule.

## What the configuration controls

The JSON is divided into sections that are passed into the simulator:

- `sim_params`: duration in seconds, seed, logging, metrics, and simulation behavior.
- `sim_mode`: selects on-demand, RL, or optimization operation.
- `network_and_demand_params`: network/layout paths, passenger and aircraft schedules, and per-vertiport capacities and demand.
- `airspace_params`: airspace layout, links, and static or data-driven wind settings.
- `passenger_params`: passenger processing times and their distributions.
- `aircraft_params`: aircraft performance, charging, and battery-related assumptions.
- `external_optimization_params`: reward settings, event conditions, and optimization/RL parameters.
- `output_params`: output location and metrics/database behavior.

Keep values and units explicit. Time-valued scenario inputs are generally specified in seconds; the simulator converts them internally. Before interpreting results, review the assumptions relevant to the study, especially aircraft performance, demand, wind, reward coefficients, and initial fleet.

## Input paths and reproducibility

The example's relative input paths are intended to be run from the repository root. When creating a scenario that references files elsewhere, use paths that resolve consistently for all users; avoid absolute paths tied to a particular machine. Keep source inputs unchanged, and write generated results under `output/`.

The example sets `random_seed` to `42`. Preserve the scenario file with reported results and record any changes to its assumptions. A fixed seed makes stochastic runs repeatable within the limits of the simulator and dependency versions; it does not by itself guarantee bit-for-bit reproducibility across environments.

The example's USD reward coefficients are zero. Set values appropriate to the study before interpreting economic rewards.

## Scenario configs versus experiment scripts

A scenario config describes one simulation run. Parameter combinations, repeated seeds, and analysis scripts belong under `experiments/`, rather than in the simulator package. See [`experiments/README.md`](../experiments/README.md) for the status of the archived loop scripts.

The files in `experiments/legacy/` are retained for historical reference and are not supported entry points. Do not copy their settings into new studies without checking them against the current example and simulator.

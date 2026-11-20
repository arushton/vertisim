# Research experiments

Use this directory for scripts and metadata that define research runs: parameter sweeps, repeated seeds, comparisons, and post-run analysis. Keep the simulator implementation in `vertisim/` and keep each individual run's settings in a scenario configuration such as [`examples/sfo_sjc/config.json`](../examples/sfo_sjc/config.json).

## Legacy files

[`legacy/`](legacy/) contains older Python configuration modules and loop runners moved out of the simulator package so they are not mistaken for current setup code.

These files are archival, not supported commands:

- `config.py`, `parameter_config.py`, and `config_ondemand.json` are older scenario/configuration formats.
- `loop_config.py` constructs configuration in Python and calls `SimSetup` with an older constructor interface.
- `loop_runner.py` and `loop_runner_multiprocess.py` depend on the older loop configuration; the multiprocess runner also imports a `loop_input` module that is not present.

The current supported single-run entry point is documented in the root [README](../README.md). Treat the archived code as historical research material until an experiment workflow is deliberately migrated and tested against the current runner.

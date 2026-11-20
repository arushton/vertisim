import json
import tempfile
import unittest
from pathlib import Path

from vertisim.utils.helpers import read_config_file
from vertisim.utils.defaults import DEFAULT_AIRCRAFT_PARAMS, DEFAULT_NETWORK_AND_DEMAND


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "examples" / "sfo_sjc" / "config.json"


class ConfigLoadingTests(unittest.TestCase):
    def test_default_input_paths_resolve_inside_installed_package(self):
        self.assertTrue(
            Path(DEFAULT_NETWORK_AND_DEMAND["vertiport_network_file_path"]).is_file()
        )
        self.assertTrue(
            Path(DEFAULT_NETWORK_AND_DEMAND["vertiport_layout_file_path"]).is_file()
        )
        self.assertTrue(
            Path(DEFAULT_AIRCRAFT_PARAMS["aircraft_energy_consumption_data_folder_path"]).is_dir()
        )

    def test_example_input_paths_resolve_to_scenario_data(self):
        config = read_config_file(str(EXAMPLE_CONFIG))
        scenario_data = EXAMPLE_CONFIG.parent / "data"

        self.assertEqual(
            config["network_and_demand_params"]["vertiport_network_file_path"],
            str((scenario_data / "network/network_SFO_SJC.csv").resolve()),
        )
        self.assertEqual(
            config["network_and_demand_params"]["vertiport_layout_file_path"],
            str((scenario_data / "layout/vertiport_layout_aiaa.xlsx").resolve()),
        )
        self.assertEqual(
            config["network_and_demand_params"]["passenger_schedule_file_path"],
            str((scenario_data / "passenger/demand_SFO_SJC.csv").resolve()),
        )
        self.assertEqual(
            config["airspace_params"]["wind_data_file_path"],
            str((scenario_data / "wind/SJC_SFO_wind_data.csv").resolve()),
        )
        self.assertIsNone(config["aircraft_params"]["aircraft_energy_consumption_data_folder_path"])

    def test_config_paths_resolve_relative_to_config_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_directory = Path(temporary_directory) / "scenario"
            input_directory = config_directory / "inputs"
            input_directory.mkdir(parents=True)
            input_path = input_directory / "network.csv"
            input_path.write_text("vertiport_id\nTEST\n", encoding="utf-8")
            config_path = config_directory / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "network_and_demand_params": {
                            "vertiport_network_file_path": "inputs/network.csv"
                        },
                        "output_params": {"output_folder_path": "output"},
                    }
                ),
                encoding="utf-8",
            )

            config = read_config_file(str(config_path))

        self.assertEqual(
            config["network_and_demand_params"]["vertiport_network_file_path"],
            str(input_path.resolve()),
        )
        self.assertEqual(
            config["output_params"]["output_folder_path"],
            str((config_directory / "output").resolve()),
        )

    def test_missing_config_file_reports_its_path(self):
        missing_path = REPOSITORY_ROOT / "examples" / "missing-config.json"
        with self.assertRaisesRegex(FileNotFoundError, "missing-config.json"):
            read_config_file(str(missing_path))


if __name__ == "__main__":
    unittest.main()

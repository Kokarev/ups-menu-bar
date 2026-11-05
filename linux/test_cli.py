import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cli', Path(__file__).with_name('ups_menu_bar.py'))
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class TelemetryTests(unittest.TestCase):
    def sample(self, **extra):
        return cli.parse_reading(json.dumps(dict({'ups.status': 'OB LB', 'input.voltage': '0', 'ups.load': '25'}, **extra)))

    def test_plain_and_json_agree(self):
        plain = 'ups.status: OB LB\ninput.voltage: 0\nups.load: 25\nbattery.runtime: 0\n'
        self.assertEqual(cli.parse_reading(plain), self.sample(**{'battery.runtime': '0'}))

    def test_missing_and_zero(self):
        self.assertIsNone(self.sample()['battery_runtime_s'])
        self.assertEqual(self.sample(**{'battery.runtime': 0})['battery_runtime_s'], 0)
        self.assertIsNone(self.sample(**{'battery.runtime': 'nan'})['battery_runtime_s'])

    def test_invalid_required_values(self):
        for values in [{'input.voltage': 'nan'}, {'ups.load': 101}, {'ups.load': True}, {'ups.status': ''}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.sample(**values)

    def test_energy_gap_and_unknown_rating(self):
        energy = cli.Energy(400)
        self.assertIsNone(energy.update(self.sample(), 10)['delta_Wh'])
        self.assertAlmostEqual(energy.update(self.sample(), 46)['delta_Wh'], 1)
        energy.gap()
        self.assertIsNone(energy.update(self.sample(), 1000)['delta_Wh'])
        self.assertIsNone(cli.Energy(None).update(self.sample(), 1)['estimated_W'])

    def test_csv_lock_and_header(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'history.csv'
            handle, _ = cli.open_csv(path)
            try:
                with self.assertRaises(BlockingIOError):
                    cli.open_csv(path)
            finally:
                handle.close()
            path.write_text('wrong,header\n')
            with self.assertRaises(ValueError):
                cli.open_csv(path)


if __name__ == '__main__':
    unittest.main()

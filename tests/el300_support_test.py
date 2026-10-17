import inspect
import sys
from types import ModuleType
import unittest

sys.modules.setdefault(
    "homeassistant.components.bluetooth",
    ModuleType("homeassistant.components.bluetooth"),
)

import custom_components.bluetti_bt  # noqa: F401
from bluetti_bt_lib import FieldName, build_device

from custom_components.bluetti_bt.device_reader import DeviceReader


class TestEL300Support(unittest.TestCase):
    def test_el300_is_registered(self):
        device = build_device("EL3002551110023321")

        self.assertIsNotNone(device)
        self.assertEqual(type(device).__name__, "EL300")

        fields = {field.name: field.address for field in device.fields}
        self.assertEqual(fields[FieldName.BATTERY_SOC.value], 102)
        self.assertEqual(fields[FieldName.AC_OUTPUT_POWER.value], 142)
        self.assertEqual(fields[FieldName.AC_INPUT_POWER.value], 146)

    def test_reader_accepts_home_assistant_bluetooth_callback(self):
        parameters = inspect.signature(DeviceReader).parameters

        self.assertIn("ble_device_callback", parameters)

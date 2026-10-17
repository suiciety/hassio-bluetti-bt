import asyncio
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

from custom_components.bluetti_bt.device_reader import DeviceReader, DeviceReaderConfig
from bluetti_bt_lib.registers import WriteableRegister


class EncryptedWriteClient:
    address = "00:11:22:33:44:55"

    def __init__(self, response_address=None):
        self.callback = None
        self.reader = None
        self.plaintext = None
        self.response_address = response_address

    async def start_notify(self, _, callback):
        self.callback = callback

    async def stop_notify(self, _):
        return

    async def disconnect(self):
        return

    async def write_gatt_char(self, characteristic, data):
        key = self.reader.encryption.secure_aes_key
        self.plaintext = self.reader.encryption.aes_decrypt(data, key, None)
        response_plaintext = self.plaintext
        if self.response_address is not None:
            response_plaintext = bytes(WriteableRegister(self.response_address, 1))
        response = self.reader.encryption.aes_encrypt(
            response_plaintext,
            key,
            None,
        )
        await self.callback(characteristic, bytearray(response))


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


class TestEncryptedWrites(unittest.IsolatedAsyncioTestCase):
    async def test_encrypted_switch_write(self):
        device = build_device("EL3002551110023321")
        client = EncryptedWriteClient()
        reader = DeviceReader(
            client.address,
            device,
            asyncio.get_running_loop().create_future,
            DeviceReaderConfig(timeout=5, use_encryption=True),
            ble_client=client,
        )
        client.reader = reader
        reader.encryption.secure_aes_key = bytes.fromhex(
            "00112233445566778899aabbccddeeff"
        )
        reader.encryption.unsecure_aes_key = bytes.fromhex(
            "ffeeddccbbaa99887766554433221100"
        )
        reader.encryption.peer_pubkey = object()

        result = await reader.write(FieldName.CTRL_AC.value, True)

        self.assertTrue(result)
        self.assertEqual(client.plaintext[1], 6)
        self.assertEqual(int.from_bytes(client.plaintext[2:4], "big"), 2011)
        self.assertEqual(int.from_bytes(client.plaintext[4:6], "big"), 1)

    async def test_rejects_acknowledgement_for_another_register(self):
        device = build_device("EL3002551110023321")
        client = EncryptedWriteClient(response_address=2012)
        reader = DeviceReader(
            client.address,
            device,
            asyncio.get_running_loop().create_future,
            DeviceReaderConfig(timeout=5, use_encryption=True),
            ble_client=client,
        )
        client.reader = reader
        reader.encryption.secure_aes_key = bytes.fromhex(
            "00112233445566778899aabbccddeeff"
        )
        reader.encryption.unsecure_aes_key = bytes.fromhex(
            "ffeeddccbbaa99887766554433221100"
        )
        reader.encryption.peer_pubkey = object()

        result = await reader.write(FieldName.CTRL_AC.value, True)

        self.assertFalse(result)

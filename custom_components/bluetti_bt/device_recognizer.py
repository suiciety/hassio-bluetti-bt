import asyncio
import logging
from typing import Any, Callable, List

from bleak.backends.device import BLEDevice
from bluetti_bt_lib.base_devices import BaseDeviceV1, BaseDeviceV2, BluettiDevice
from bluetti_bt_lib.bluetooth.device_recognizer import DeviceRecognizerResult
from bluetti_bt_lib.devices import DEVICE_NAME_RE
from bluetti_bt_lib.fields import FieldName

from .device_reader import DeviceReader, DeviceReaderConfig

_LOGGER = logging.getLogger(__name__)


async def recognize_device(
    mac: str,
    future_builder_method: Callable[[], asyncio.Future[Any]],
    ble_device_callback: Callable[[], BLEDevice | None] | None = None,
) -> DeviceRecognizerResult | None:
    bluetti_devices: List[BluettiDevice] = [
        BaseDeviceV2(),
        BaseDeviceV1(),
    ]

    for bluetti_device in bluetti_devices:
        device_readers = [
            DeviceReader(
                mac,
                bluetti_device,
                future_builder_method,
                DeviceReaderConfig(timeout=15, use_encryption=True),
                ble_device_callback=ble_device_callback,
            ),
            DeviceReader(
                mac,
                bluetti_device,
                future_builder_method,
                DeviceReaderConfig(timeout=8),
                ble_device_callback=ble_device_callback,
            ),
        ]

        for device_reader in device_readers:
            data = await device_reader.read(
                bluetti_device.get_device_type_registers()
            )

            if data is None:
                continue

            type_data = data.get(FieldName.DEVICE_TYPE.value)

            if not isinstance(type_data, str) or not type_data:
                _LOGGER.error("Invalid device type data: %s", type_data)
                continue

            if DEVICE_NAME_RE.match(type_data + "12345678") is None:
                _LOGGER.warning("Device returned unsupported type: %s", type_data)
                continue

            data = await device_reader.read(
                bluetti_device.get_device_sn_registers()
            )

            if data is None:
                return DeviceRecognizerResult(
                    type_data,
                    bluetti_device.get_iot_version(),
                    device_reader.config.use_encryption,
                    "000000000000",
                )

            sn_data = data.get(FieldName.DEVICE_SN.value)

            if not isinstance(sn_data, int):
                return DeviceRecognizerResult(
                    type_data,
                    bluetti_device.get_iot_version(),
                    device_reader.config.use_encryption,
                    "000000000000",
                )

            return DeviceRecognizerResult(
                type_data,
                bluetti_device.get_iot_version(),
                device_reader.config.use_encryption,
                sn_data,
            )

    return None

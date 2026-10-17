import asyncio
import logging
from typing import Any, Callable, List

import async_timeout
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)
from bluetti_bt_lib import DeviceReader as BaseDeviceReader
from bluetti_bt_lib import DeviceReaderConfig
from bluetti_bt_lib.base_devices import BluettiDevice
from bluetti_bt_lib.const import NOTIFY_UUID
from bluetti_bt_lib.registers import ReadableRegisters

try:
    from bleak_retry_connector import close_stale_connections_by_address
except ImportError:
    close_stale_connections_by_address = None


class DeviceReader(BaseDeviceReader):
    def __init__(
        self,
        mac: str,
        bluetti_device: BluettiDevice,
        future_builder_method: Callable[[], asyncio.Future[Any]],
        config: DeviceReaderConfig = DeviceReaderConfig(),
        lock: asyncio.Lock = asyncio.Lock(),
        ble_client: BleakClient | None = None,
        ble_device_callback: Callable[[], BLEDevice | None] | None = None,
    ):
        super().__init__(
            mac,
            bluetti_device,
            future_builder_method,
            config,
            lock,
            ble_client,
        )
        self.ble_device_callback = ble_device_callback
        self.logger = logging.getLogger(
            f"{__name__}.{self.mac.replace(':', '_')}"
        )

    async def read(
        self,
        only_registers: List[ReadableRegisters] | None = None,
        raw: bool = False,
    ) -> dict | None:
        registers = self.bluetti_device.get_polling_registers()
        pack_registers = self.bluetti_device.get_pack_polling_registers()

        if only_registers is not None:
            registers = only_registers
            pack_registers = []

        parsed_data: dict = {}
        read_failed = False

        self.logger.debug("Reading device registers")

        async with self.polling_lock:
            try:
                async with async_timeout.timeout(self.config.timeout):
                    self.logger.debug("Searching for device")

                    if self.ble_client:
                        self.device = None
                    elif self.ble_device_callback:
                        self.device = self.ble_device_callback()
                    else:
                        self.device = await BleakScanner.find_device_by_address(
                            self.mac,
                            timeout=5,
                        )

                    if not self.ble_client and self.device is None:
                        self.logger.error("Device not found")
                        read_failed = True
                    else:
                        self.logger.debug("Connecting to device")

                        if self.ble_client:
                            self.client = self.ble_client
                        else:
                            self.client = await establish_connection(
                                BleakClientWithServiceCache,
                                self.device,
                                self.device.name or "Unknown Device",
                                max_attempts=10,
                                ble_device_callback=self.ble_device_callback,
                            )

                        self.logger.debug("Connected to device")

                        await self.client.start_notify(
                            NOTIFY_UUID,
                            self._notification_handler,
                        )
                        self.has_notifier = True

                        self.logger.debug("Notification handler setup complete")

                        while (
                            self.config.use_encryption
                            and not self.encryption.is_ready_for_commands
                        ):
                            await asyncio.sleep(5)
                            self.logger.debug(
                                "Encryption handshake not finished yet"
                            )

                        for register in registers:
                            body = register.parse_response(
                                await self._async_send_command(register)
                            )

                            if raw:
                                parsed_data[register.starting_address] = body
                            else:
                                parsed_data.update(
                                    self.bluetti_device.parse(
                                        register.starting_address,
                                        body,
                                    )
                                )

                        for pack in range(
                            1,
                            self.bluetti_device.max_packs + 1,
                        ):
                            await self._async_send_command(
                                self.bluetti_device.get_pack_selector(pack)
                            )
                            await asyncio.sleep(3)

                            for register in pack_registers:
                                body = register.parse_response(
                                    await self._async_send_command(register)
                                )

                                if raw:
                                    parsed_data[
                                        register.starting_address
                                    ] = body
                                else:
                                    parsed_data.update(
                                        self.bluetti_device.parse(
                                            register.starting_address,
                                            body,
                                            pack_num=pack,
                                        )
                                    )
            except TimeoutError:
                self.logger.warning("Timeout")
                read_failed = True
            except BleakError as err:
                self.logger.warning("Bleak error: %s", err)
                read_failed = True
            except Exception as err:
                self.logger.warning("Unknown error: %s", err)
                read_failed = True
            finally:
                if self.has_notifier and self.client:
                    try:
                        await self.client.stop_notify(NOTIFY_UUID)
                    except Exception as err:
                        self.logger.debug(
                            "Failed to stop notifier: %s",
                            err,
                        )
                    self.has_notifier = False

                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception as err:
                        self.logger.debug(
                            "Failed to disconnect from device: %s",
                            err,
                        )
                    self.client = None

                self.encryption.reset()
                self.encrypted_buffer.clear()

                if (
                    read_failed
                    and not self.ble_client
                    and close_stale_connections_by_address is not None
                ):
                    try:
                        await close_stale_connections_by_address(self.mac)
                    except Exception as err:
                        self.logger.debug(
                            "Failed to close stale connections: %s",
                            err,
                        )

        if read_failed or not parsed_data:
            return None

        return parsed_data

    async def write(self, field: str, value: Any) -> bool:
        command = self.bluetti_device.build_write_command(field, value)

        if command is None:
            self.logger.error("Field is not writeable: %s", field)
            return False

        write_succeeded = False
        write_failed = False

        async with self.polling_lock:
            try:
                async with async_timeout.timeout(self.config.timeout):
                    if self.ble_client:
                        self.device = None
                    elif self.ble_device_callback:
                        self.device = self.ble_device_callback()
                    else:
                        self.device = await BleakScanner.find_device_by_address(
                            self.mac,
                            timeout=5,
                        )

                    if not self.ble_client and self.device is None:
                        self.logger.error("Device not found")
                        write_failed = True
                    else:
                        if self.ble_client:
                            self.client = self.ble_client
                        else:
                            self.client = await establish_connection(
                                BleakClientWithServiceCache,
                                self.device,
                                self.device.name or "Unknown Device",
                                max_attempts=10,
                                ble_device_callback=self.ble_device_callback,
                            )

                        await self.client.start_notify(
                            NOTIFY_UUID,
                            self._notification_handler,
                        )
                        self.has_notifier = True

                        while (
                            self.config.use_encryption
                            and not self.encryption.is_ready_for_commands
                        ):
                            await asyncio.sleep(1)

                        response = await self._async_send_command(command)
                        if command.is_exception_response(response):
                            self.logger.error(
                                "Device rejected write to %s",
                                field,
                            )
                        elif not command.is_valid_response(response):
                            self.logger.error(
                                "Invalid write response for %s",
                                field,
                            )
                        elif (
                            len(response) != command.response_size()
                            or response != bytes(command)
                        ):
                            self.logger.error(
                                "Write acknowledgement did not match %s",
                                field,
                            )
                        else:
                            write_succeeded = True
            except TimeoutError:
                self.logger.warning("Write timed out")
                write_failed = True
            except BleakError as err:
                self.logger.warning("Bleak write error: %s", err)
                write_failed = True
            except Exception as err:
                self.logger.warning("Unknown write error: %s", err)
                write_failed = True
            finally:
                if self.has_notifier and self.client:
                    try:
                        await self.client.stop_notify(NOTIFY_UUID)
                    except Exception as err:
                        self.logger.debug(
                            "Failed to stop notifier: %s",
                            err,
                        )
                    self.has_notifier = False

                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception as err:
                        self.logger.debug(
                            "Failed to disconnect from device: %s",
                            err,
                        )
                    self.client = None

                self.encryption.reset()
                self.encrypted_buffer.clear()

                if (
                    write_failed
                    and not self.ble_client
                    and close_stale_connections_by_address is not None
                ):
                    try:
                        await close_stale_connections_by_address(self.mac)
                    except Exception as err:
                        self.logger.debug(
                            "Failed to close stale connections: %s",
                            err,
                        )

        return write_succeeded

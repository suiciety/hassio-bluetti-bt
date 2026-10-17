import re

from bluetti_bt_lib import devices
from bluetti_bt_lib.bluetooth import device_recognizer
from bluetti_bt_lib.utils import device_builder

from .el300 import EL300


def register_el300() -> None:
    devices.DEVICES["EL300"] = EL300

    if "EL300" in devices.DEVICE_NAME_RE.pattern:
        return

    pattern = devices.DEVICE_NAME_RE.pattern.replace(
        "|EL30V2",
        "|EL300|EL30V2",
    )
    device_name_re = re.compile(pattern)

    devices.DEVICE_NAME_RE = device_name_re
    device_builder.DEVICE_NAME_RE = device_name_re
    device_recognizer.DEVICE_NAME_RE = device_name_re

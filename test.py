import asyncio
import logging
import time
from pathlib import Path

from src.neuroplay_alt_sdk.native.devices import NeuroPlayDevice
from src.neuroplay_alt_sdk.native.enums import NeuroPlayDevicesEnum
from src.neuroplay_alt_sdk.native.scanner import NeuroPlayScanner

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


async def main():
    device = await NeuroPlayScanner.search_for(
        device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
        device_id=1228,
        device_class=NeuroPlayDevice,
    )

    await device.connect()

    await asyncio.sleep(2)

    start_time = time.perf_counter()

    device.edf_creator.start_recording(Path('.') / 'test.edf')

    await asyncio.sleep(10)

    device.edf_creator.stop_recording()

    end_time = time.perf_counter()

    await device.disconnect()

    print(end_time - start_time)


if __name__ == '__main__':
    asyncio.run(main())

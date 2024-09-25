import asyncio

from src.neuroplay_alt_sdk.native.devices import NeuroPlayDevice
from src.neuroplay_alt_sdk.native.enums import NeuroPlayDevicesEnum
from src.neuroplay_alt_sdk.native.scanner import NeuroPlayScanner



async def main():
    device = await NeuroPlayScanner.search_for(
        device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
        device_id=1232,
        device_class=NeuroPlayDevice,
    )

    await device.connect()

    await asyncio.sleep(4)

    await device.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
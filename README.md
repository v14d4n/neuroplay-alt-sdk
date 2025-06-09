# NeuroPlay Alt SDK

NeuroPlay Alt SDK is an asynchronous Python library for working with NeuroPlay EEG devices (6C, 8Cap). It allows you to search for devices via Bluetooth, connect to them, validate channel quality and record data in EDF or CSV format.

## Maintenance

This project is no longer actively maintained by the original author. However, it remains open source and open for community contributions via pull requests. Feel free to submit improvements or fixes.

## Important Notes

The SDK collects data from all available channels at a fixed sampling rate of 125 Hz. Selective channel reading is not supported. If you want to improve this functionality, you can modify [AbstractNeuroPlayDevice](src/neuroplay_alt_sdk/native/devices/abstract_neuroplay_device.py) class in the library source code. Contributions are welcome :)

## Building from source (with Poetry)
To build the package from source:

```bash
git clone https://github.com/v14d4n/NeuroPlayAltSDK.git
cd NeuroPlayAltSDK
poetry build
```

This will generate `.whl `and `.tar.gz` files in the `dist/` directory:

```
dist/
├── neuroplay_alt_sdk-x.y.z.tar.gz
└── neuroplay_alt_sdk-x.y.z-py3-none-any.whl
```

## Installation

Install from PyPI:

```bash
pip install neuroplay-alt-sdk
```

The library requires Python 3.12 and uses [Bleak](https://github.com/hbldh/bleak) for Bluetooth communication.

## Quick start

```python
import asyncio
from pathlib import Path

from neuroplay_alt_sdk.native.devices import NeuroPlayDevice
from neuroplay_alt_sdk.native.enums import NeuroPlayDevicesEnum
from neuroplay_alt_sdk.native.scanner import NeuroPlayScanner

async def main():
    # Search for a specific device
    device: NeuroPlayDevice = await NeuroPlayScanner.search_for(
        device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
        device_id=1232,
    )

    await device.connect()

    # Check that data from channels is valid
    print(await device.validate_channels())

    # Start recording EEG
    # This will create three files: data.edf, data.csv, annotations.csv
    path_to_edf = Path("./results/data.edf")
    device.edf_creator.start_recording(path_to_edf)

    # Add annotations during recording if needed
    device.edf_creator.write_annotation("some text")

    # Stop recording when done
    device.edf_creator.stop_recording()

    await device.disconnect()

asyncio.run(main())
```

## Core classes

The package exposes several main classes:

- `AbstractNeuroPlayDevice` – abstract class that implements all low-level functionality for devices. 
- `NeuroPlayDevicesEnum` – enumeration of available device models.
- `NeuroPlayScanner` – asynchronous scanner for discovering devices via Bluetooth.
- `NeuroPlayDevice` – high level API for a single NeuroPlay device.
- `EDFCreator` – helper class used by `NeuroPlayDevice` to save data.

### NeuroPlayDevicesEnum
Use `from_string` to convert a device name to the corresponding enum value. Unknown names return `NeuroPlayDevicesEnum.__UNDEFINED`.

### NeuroPlayScanner

`NeuroPlayScanner` is used to search for devices in the Bluetooth network.

```python
device = await NeuroPlayScanner.search_for(
    device_class=NeuroPlayDevice,
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
    timeout=20,
)
```

Iterating over all discovered devices:

```python
devices_set = {
    NeuroPlayDevicesEnum.NEUROPLAY_6C,
    NeuroPlayDevicesEnum.NEUROPLAY_8CAP,
}

async with NeuroPlayScanner(timeout=20,
                            device_class=NeuroPlayDevice,
                            devices_names=devices_set) as scanner:
    async for device in scanner:
        print(device)
```

You can provide your own device class (subclassing `AbstractNeuroPlayDevice`).

```python
class MyCoolNeuroPlayDevice(NeuroPlayDevice):
    ...

device = await NeuroPlayScanner.search_for(
    device_class=MyCoolNeuroPlayDevice,
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
)
```

Manual control of the scanner is also available:

```python
scanner = NeuroPlayScanner(
    device_class=NeuroPlayDevice,
    devices_names={NeuroPlayDevicesEnum.ALL}
)

await scanner.start()

try:
    while True:
        device = await scanner.discover_next(timeout=5)
        print(device)
except asyncio.TimeoutError:
    pass

await scanner.stop()
```

### NeuroPlayDevice

`NeuroPlayDevice` is ready-to-use subclass of `AbstractNeuroPlayDevice` that lets you interact with a NeuroPlay device. You can also write your own subclass if needed. The device is an asynchronous context manager, so you can use it in an `async with` block or call `connect`/`disconnect` manually.

```python
device: NeuroPlayDevice = await NeuroPlayScanner.search_for(
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
    timeout=20,
)

if device:
    async with device:
        await asyncio.sleep(10)
```

Or explicitly:

```python
await device.connect()
await asyncio.sleep(10)
await device.disconnect()
```

The device provides filtered data to `EDFCreator` which writes CSV files and then converts them to EDF when recording stops.

```python
path_to_edf = Path('data.edf')
async with device:
    device.edf_creator.start_recording(path_to_edf)
    await asyncio.sleep(10)
    device.edf_creator.stop_recording()
```

If you only need a CSV file you can use the `csv_data_writer` directly:

```python
path_to_csv = Path('data.csv')
async with device:
    device.edf_creator.csv_data_writer.start_writing(path_to_csv)
    await asyncio.sleep(10)
    device.edf_creator.csv_data_writer.stop_writing()
```

`EDFCreator.save_csv_as_edf` can convert such CSV files to EDF later. The sampling rate for 4/6/8 channel devices is 125 Hz.

```python
path_to_csv = Path('data.csv')
path_to_edf = Path('data.edf')
EDFCreator.save_csv_as_edf(path_to_csv, path_to_edf, sample_frequency=125)
```

Note that the data stream is synchronized in time for `NeuroPlayDevice` using `DataSynchronizer`. If data packets are lost during transmission (e.g., due to Bluetooth issues), the SDK fills the missing values with zeros to maintain the correct timing.
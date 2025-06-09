# Пример использования
Для начала необходимо найти устройство.

```python
device: NeuroPlayDevice = await NeuroPlayScanner.search_for(
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
)
```
По стандарту из метода ```search_for``` класса ```NeuroPlayScanner``` возвращается ```NeuroPlayDevice``` (для подсказок по коду
необходимо явно указать тип), он хранит в себе адрес устройства 
в сети, поэтому подключение не обязательно выполнять сразу после нахождения устройства. Подключаемся как только готовы.
```python
await device.connect()
```
Желательно подождать несколько секунд после подключения, чтобы фильтры настроились. Чтобы проверить валидные ли
данные можно вызвать метод ```validate_channels``` объекта ```NeuroPlayDevice```, который возвращает
```Dict[str, DataStatusEnum]```.
```python
print(await device.validate_channels())
# {'O1': 'VALID', 'T3': 'WARN', 'Fp1': 'NOT_VALID', 'Fp2': 'VALID', 'T4': 'VALID', 'O2': 'VALID'}
```
После чего можем начинать запись.
```python
user = 'SomeNameHere'
path_to_edf = Path().cwd().joinpath('results').joinpath(user).joinpath(f'data.edf')
device.edf_creator.start_recording(path_to_edf)
```
Если во время записи необходимо поставить аннотацию вызываем метод ```write_annotation```.

```python
device.edf_creator.write_annotation('some text')
```
Как только больше нет необходимости записывать данные, запись можно остановить.
```python
device.edf_creator.stop_recording()
```
После сохранения записи, если больше не планируется записывать новые данные, устройство можно отключать.
```python
await device.disconnect()
```

# Основные классы
Библиотека содержит в себе следующие основные классы: ```NeuroPlayDevicesEnum```, ```NeuroPlayScanner```, 
```NeuroPlayDevice```, ```AbstractNeuroPlayDevice```, ```EDFCreator```, ```CSVManipulator```, ```FilterContainer```.

## NeuroPlayDevicesEnum
Enum для девайсов.
```python
class NeuroPlayDevicesEnum(Enum):
    ALL = "NeuroPlay"
    NEUROPLAY_6C = "NeuroPlay-6C"
    NEUROPLAY_8CAP = "NeuroPlay-8Cap"
    __UNDEFINED = ""

    @classmethod
    def from_string(cls, device_name: str) -> 'NeuroPlayDevicesEnum':
        for device in NeuroPlayDevicesEnum:
            if device.value == device_name:
                return device
        return cls.__UNDEFINED
```

Его метод ```from_string``` принимает строку и сравнивает её со всеми своими значениями.
Если строка не совпала, возвращает ```NeuroPlayDevicesEnum.UNDEFINED```. При совпадении возвращает найденный элемент.
Так ```NeuroPlayDevicesEnum.from_string('NeuroPlay-6C')``` вернет ```NeuroPlayDevicesEnum.NEUROPLAY_6C```.

## NeuroPlayScanner
Используется для поиска устройств в BT сети.
### Основное использование
Вернуть первый найденный ```NeuroPlayDevice``` по заданным параметрам.
```python
device = await NeuroPlayScanner.search_for(
    device_class=NeuroPlayDevice,
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
    timeout=20,
)
```

Проитерироваться по всем найденным ```NeuroPlayDevice```.

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
Можно изменить класс девайса на свой, в таком случае сканер будет возвращать девайсы указанного класса. В своем классе
необходимо наследоваться от ```AbstractNeuroPlayDevice```. В примере свой класс назван ```MyCoolNeuroPlayDevice```.
```python
device = await NeuroPlayScanner.search_for(
    device_class=MyCoolNeuroPlayDevice,
    device_type=NeuroPlayDevicesEnum.NEUROPLAY_6C,
    device_id=1232,
)
```
```python
async with NeuroPlayScanner(device_class=MyCoolNeuroPlayDevice) as scanner:
    async for device in scanner:
        print(device)
```

### Ручное управление сканером

Метод ```discover_next``` вызовет ошибку ```asyncio.TimeoutError```, если не найдет новое
устройство по истечению таймаута. Если передать ему ```timeout```, то он будет использовать его вместо
указанного при инициализации класса.

Важно отметить, что scanner хранит в себя все найденные девайсы, по этой причине их надо очищать, если есть
необходимость повторного использования сканера.

```python
scanner = NeuroPlayScanner(
    device_class=NeuroPlayDevice,
    timeout=15, 
    devices_names={NeuroPlayDevicesEnum.ALL}
)

await scanner.start()

devices = []
try:
    while True:
        devices.append(scanner.discover_next(timeout=5))
except asyncio.TimeoutError:
    pass
devices = scanner.discovered_devices
scanner.clear_discovered_devices()

await scanner.stop()
```

## NeuroPlayDevice
Позволяет управлять устройством. Является наследником ```AbstractNeuroPlayDevice```. 
### Основное использование
Следующий код демонстрирует получение данных с устройства на протяжении 10 секунд.
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
Альтернативно это можно сделать следующим образом. Метод ```connect``` выполняет подключение к устройству и пока оно
подключено, объект принимает в свои методы обработчики (```raw_channels_data_handler``` и ```filtered_channels_data_handler```) 
данные с устройства.
```python
await device.connect()

await asyncio.sleep(10)

await device.disconnect()
```
Информация из обработчиков используется для создания EDF файла.
Метод ```start_recording``` свойства ```edf_creator``` начинает запись CSV файла ```data.csv``` в указанной директории
для EDF файла. По остановке записи, с помощью метода ```stop_recording```, из данных записанных в CSV файл
будет создан EDF файл.
```python
path_to_edf = Path('.').joinpath('data.edf')
async with device:
    device.edf_creator.start_recording(path_to_edf)
    await asyncio.sleep(10)
    device.edf_creator.stop_recording()
```
Если нет необходимости преобразовывать CSV файл с данными ЭЭГ в EDF по завершению записи, то можно напрямую использовать свойство
```csv_data_writer``` и его методы ```start_writing``` и ```stop_writing```.

```python
path_to_csv = Path('.').joinpath('data.csv')
async with device:
    device.edf_creator.csv_data_writer.start_writing(path_to_csv)
    await asyncio.sleep(10)
    device.edf_creator.csv_data_writer.stop_writing()
```
После чего с помощью статического метода ```save_csv_as_edf``` класса ```EDFCreator``` можно создать EDF файл из CSV.
Частота дискретизации для 4/6/8 каналов составляет 125 гц.
```python
path_to_csv = Path('.').joinpath('data.csv')
path_to_edf = Path('.').joinpath('data.edf')
sample_frequency = 125
EDFCreator.save_csv_as_edf(path_to_csv, path_to_edf, sample_frequency)
```

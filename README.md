# acoslib

Библиотека для работы с altcos-репозиториями


# Содержание
`acoslib/models` - представления объектов altcos-репозитория

`acoslib/images` - представления для конкретных образов (используется моделью `Image`)

`acoslib/types` - перечесления

`acoslib/utils/*` - вспомогательные функции и классы


# Пример использования

1. Склонируйте mkimage-profiles
```shell
git clone git://git.altlinux.org/gears/m/mkimage-profiles.git
```

2. Склонируйте acoslib и перейдите в нее
```shell
git clone https://github.com/fl0pp5/acoslib2
cd acoslib2
```

3. Экспортируйте необходимые переменные
```shell
export ALTCOS_ROOT=$(pwd)
export STREAMS_ROOT=$ALTCOS_ROOT/builds/streams
export SCRIPTS_ROOT=$ALTCOS_ROOT/scripts
export MKIMAGE_PROFILES_ROOT=$ALTCOS_ROOT/../mkimage-profiles
```
4. Можно приступать.

Создайте конфиг для подветки, например `htop.yml`
```yaml
version: 2.0.0
from: altcos/x86_64/sisyphus:20211207.0.0
actions:
  - rpms:
      - htop
```
Создайте pytnon-скрипт содержащий
```python
import logging
import os

from acoslib import models
from acoslib.types import ImageFormat, Arch, Stream


def main():
    logging.basicConfig(level=logging.DEBUG)
    repository = models.Repository(
        osname="altcos",
        root=os.getenv("ALTCOS_ROOT"),
        stream_root=os.getenv("STREAMS_ROOT"),
        script_root=os.getenv("SCRIPTS_ROOT"),
        mkimage_root=os.getenv("MKIMAGE_PROFILES_ROOT"))

    baseref = models.Reference(
        repository,
        Arch.X86_64,
        Stream.SISYPHUS,
    ).mkprofile().create()

    subref = models.SubReference.from_baseref(
        baseref, name="htop", altconf="altcos.yml",
    ).create()

    models.Image(baseref).create(ImageFormat.QCOW, models.Commit(baseref).all()[-1])
    models.Image(subref).create(ImageFormat.QCOW, models.Commit(subref).all()[-1])


if __name__ == '__main__':
    main()
```

Создаем представление репозитория на основе экспортированных перменных
```python
repository = models.Repository(
    osname="altcos",
    root=os.getenv("ALTCOS_ROOT"),
    stream_root=os.getenv("STREAMS_ROOT"),
    script_root=os.getenv("SCRIPTS_ROOT"),
    mkimage_root=os.getenv("MKIMAGE_PROFILES_ROOT"))
```
Создаем базовую ветку для вышесозданного репозитория
```python
baseref = models.Reference(
    repository,
    Arch.X86_64,
    Stream.SISYPHUS,
).mkprofile().create()
```

Создаем поветку `htop`
```python
subref = models.SubReference.from_baseref(
    baseref, name="htop", altconf="altcos.yml",
).create()
```

Создаем образы базовой и `htop` веток
```python
models.Image(baseref).create(ImageFormat.QCOW, models.Commit(baseref).all()[-1])
models.Image(subref).create(ImageFormat.QCOW, models.Commit(subref).all()[-1])
```

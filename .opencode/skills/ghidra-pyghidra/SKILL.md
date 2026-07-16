---
name: ghidra-pyghidra
description: >
  Guía completa para usar Ghidra 12.x y pyghidra 3.x para análisis binario,
  reverse engineering y scripting en Python nativo con la API de Ghidra.
  Cubre: instalación y configuración, análisis headless, scripting con pyghidra,
  descompilación automatizada, apertura de proyectos, y resolución de problemas comunes.
---

# Ghidra + pyghidra Skill

## Requisitos del entorno

| Componente | Ruta / Versión |
|---|---|
| **Ghidra** | `/opt/ghidra` (v12.1.2) |
| **pyghidra** | v3.1.0 (`pip install pyghidra`) |
| **jpype1** | v1.5.2 (dependencia de pyghidra) |
| **GHIDRA_INSTALL_DIR** | `/opt/ghidra` (variable de entorno) |
| **Java** | OpenJDK 21+ |
| **Python** | 3.13+ |

## Índice

1. [Arrancar Ghidra (GUI)](#1-arrancar-ghidra-gui)
2. [Análisis headless con pyghidra](#2-análisis-headless-con-pyghidra)
3. [API de pyghidra (nueva, recomendada)](#3-api-de-pyghidra-nueva-recomendada)
4. [API legacy (pyhidra)](#4-api-legacy-pyhidra)
5. [Scripting avanzado](#5-scripting-avanzado)
6. [Type stubs para autocompletado](#6-type-stubs-para-autocompletado)
7. [Solución de problemas](#7-solución-de-problemas)
8. [Referencias](#8-referencias)

---

## 1. Arrancar Ghidra (GUI)

### Desde terminal

```bash
cd /opt/ghidra && ./ghidraRun
```

### pyghidra no es necesario para la GUI

pyghidra es una _biblioteca Python_. La GUI de Ghidra funciona independientemente. pyghidra se usa cuando quieres controlar Ghidra desde scripts Python (headless).

---

## 2. Análisis headless con pyghidra

### 2.1. Iniciar Ghidra en modo headless

```python
import pyghidra

# Arranca la JVM e inicializa Ghidra sin interfaz gráfica
pyghidra.start()

# Después de start(), puedes importar cualquier clase de Ghidra/Java
from ghidra.framework import Application
print(Application.getApplicationVersion())  # 12.1.2
```

### 2.2. Abrir un binario directamente

```python
import pyghidra

with pyghidra.open_program("/ruta/al/ejemplo.exe") as flat_api:
    programa = flat_api.getCurrentProgram()
    listing = programa.getListing()
    print(f"Nombre: {programa.getName()}")
    print(f"Lenguaje: {programa.getLanguageID()}")

    # Leer bytes en una dirección
    addr = flat_api.toAddr(0x401000)
    unit = listing.getCodeUnitAt(addr)
    print(f"Instrucción en 0x401000: {unit}")
```

> **Nota**: `open_program()` crea un proyecto Ghidra temporal en el mismo directorio del binario. Se puede controlar con `project_name` y `project_location`.

### 2.3. Abrir proyectos existentes

```python
import pyghidra

pyghidra.start()

# Abrir un proyecto (sin crear)
with pyghidra.open_project("/ruta/proyectos", "MiProyecto") as proyecto:
    # Recorrer los programas del proyecto
    def procesar(domain_file, programa):
        print(f"Procesando: {programa.getName()}")
        # ... análisis ...

    pyghidra.walk_programs(proyecto, procesar)
```

### 2.4. Ejecutar un GhidraScript existente

```python
import pyghidra

pyghidra.start()

with pyghidra.open_project("/ruta/proyectos", "MiProyecto", create=True) as proyecto:
    stdout, stderr = pyghidra.ghidra_script(
        "/ruta/scripts/analisis.py",
        proyecto,
        echo_stdout=True
    )
    print(stdout)
```

---

## 3. API de pyghidra (nueva, recomendada)

`pyghidra 3.x` introdujo una API rediseñada. La API legacy (`open_program`, `run_script`) sigue funcionando pero está **deprecada**.

### 3.1. `pyghidra.start()`

```python
launcher = pyghidra.start(verbose=False, install_dir="/opt/ghidra")
```

Devuelve un `PyGhidraLauncher`. Sin argumentos, usa `GHIDRA_INSTALL_DIR` del entorno.

### 3.2. `pyghidra.open_project()`

```python
# Abre un proyecto. Con create=True lo crea si no existe.
with pyghidra.open_project("/ruta", "Proyecto", create=True) as proj:
    ...
```

### 3.3. `pyghidra.open_filesystem()`

Abre sistemas de archivos que Ghidra entiende (ZIP, ELF, etc.):

```python
with pyghidra.open_filesystem("firmware.zip") as fs:
    for f in fs.files():
        print(f.path)
```

### 3.4. `pyghidra.program_context()`

```python
pyghidra.start()
with pyghidra.open_project("/ruta", "Proyecto") as proj:
    with pyghidra.program_context(proj, "/binarios/muestra.exe") as programa:
        print(f"Nombre: {programa.getName()}")
```

### 3.5. `pyghidra.analyze()`

Ejecuta el análisis automático de Ghidra sobre un programa:

```python
log = pyghidra.analyze(programa)
```

### 3.6. `pyghidra.transaction()`

Todas las modificaciones a un programa deben ir dentro de una transacción:

```python
with pyghidra.transaction(programa, "Mi cambio"):
    # modificar el programa aquí
    pass
```

### 3.7. `pyghidra.program_loader()`

Cargar bytes como programa:

```python
import jpype
import pyghidra

pyghidra.start()
with pyghidra.open_project("/tmp", "Test", create=True) as proj:
    raw = jpype.JArray(jpype.JByte)(b"\x90\x90\xcc\xc3")
    loader = pyghidra.program_loader() \
        .project(proj) \
        .source(raw) \
        .name("test") \
        .loaders("BinaryLoader") \
        .language("DATA:LE:64:default")
    with loader.load() as results:
        results.save(pyghidra.task_monitor())
```

### 3.8. Utilidades

```python
# Obtener propiedades de análisis
props = pyghidra.analysis_properties(programa)

# Obtener metadatos del programa
info = pyghidra.program_info(programa)

# Crear un TaskMonitor con timeout de 30s
monitor = pyghidra.task_monitor(timeout=30)
```

---

## 4. API legacy (pyhidra)

La API de la antiguo `pyhidra` está disponible en `pyghidra` para compatibilidad, pero está deprecada.

### 4.1. `pyghidra.open_program()` (deprecado)

```python
import pyghidra

with pyghidra.open_program(
    "muestra.exe",
    project_name="MiProyecto",
    project_location="/tmp",
    analyze=True,
    language="x86:LE:64:default"
) as flat_api:
    programa = flat_api.getCurrentProgram()
```

| Parámetro | Descripción |
|---|---|
| `binary_path` | Ruta al binario |
| `project_location` | Directorio del proyecto (defecto: mismo dir del binario) |
| `project_name` | Nombre del proyecto (defecto: nombre_binario + `_ghidra`) |
| `analyze` | Ejecutar análisis automático |
| `language` | LanguageID (ej: `x86:LE:64:default`) |
| `loader` | Clase Java del loader específico |
| `program_name` | Nombre del programa dentro del proyecto |
| `nested_project_location` | Si el proyecto tiene estructura anidada (True por defecto) |

### 4.2. `pyghidra.run_script()` (deprecado)

```python
pyghidra.run_script("muestra.exe", "/ruta/script.py", analyze=True)
```

O desde línea de comandos:

```bash
pyghidra muestra.exe /ruta/script.py -- arg1 arg2
```

---

## 5. Scripting avanzado

### 5.1. Obtener funciones y descompilar

```python
import pyghidra

with pyghidra.open_program("muestra.exe") as flat:
    programa = flat.getCurrentProgram()
    fm = programa.getFunctionManager()
    
    for func in fm.getFunctions(True):
        nombre = func.getName()
        cuerpo = func.getBody()
        print(f"{nombre}: 0x{func.getEntryPoint():x} (tamaño: {cuerpo.getNumAddresses()})")
```

### 5.2. Usar el FlatDecompilerAPI

```python
from ghidra.app.decompiler.flatapi import FlatDecompilerAPI

with pyghidra.open_program("muestra.exe") as flat:
    decomp = FlatDecompilerAPI(flat)
    resultado = decomp.decompile(flat.toAddr(0x401000))
    print(resultado)
    decomp.dispose()
```

### 5.3. Buscar referencias cruzadas

```python
from ghidra.program.util import ProgramMemoryUtil
from ghidra.program.model.symbol import RefType

with pyghidra.open_program("muestra.exe") as flat:
    programa = flat.getCurrentProgram()
    addr = flat.toAddr(0x401000)
    
    # Referencias hacia esta dirección
    refs_to = programa.getReferenceManager().getReferencesTo(addr)
    for ref in refs_to:
        print(f"Referencia desde: 0x{ref.getFromAddress():x}")
```

### 5.4. Parchear bytes

```python
with pyghidra.open_program("muestra.exe") as flat:
    programa = flat.getCurrentProgram()
    addr = flat.toAddr(0x401000)
    
    with pyghidra.transaction(programa, "Patch NOP"):
        programa.getMemory().setByte(addr, 0x90)
        # También se puede usar flat
        flat.setByte(addr, 0x90)
```

### 5.5. Manejo de conflictos de nombres (Java vs Python)

Cuando un módulo Python tiene el mismo nombre que un paquete Java, pyghidra permite acceder al paquete Java añadiendo un guion bajo al final:

```python
import pdb      # módulo Python debugger
import pdb_     # paquete Java de Ghidra (PDB)
```

---

## 6. Type stubs para autocompletado

Para tener autocompletado de la API de Ghidra en tu editor (VSCode, PyCharm, etc.):

```bash
# Desde el paquete offline de Ghidra
pip install --no-index -f /opt/ghidra/docs/ghidra_stubs ghidra-stubs --break-system-packages

# O desde internet (especificando la versión exacta de Ghidra)
pip install ghidra-stubs==12.1.2 --break-system-packages
```

Esto instala `ghidra-stubs` y permite que el editor sugiera clases, métodos y parámetros de Ghidra.

---

## 7. Solución de problemas

### 7.1. Error: `externally-managed-environment`

Sistema Debian con PEP 668. Usa `--break-system-packages` en pip:

```bash
pip install pyghidra --break-system-packages
```

O crea un entorno virtual:

```bash
python3 -m venv ~/venvs/ghidra && source ~/venvs/ghidra/bin/activate
```

### 7.2. Error: `GHIDRA_INSTALL_DIR is not set`

pyghidra no encuentra Ghidra:

```bash
export GHIDRA_INSTALL_DIR=/opt/ghidra
```

O pásalo directamente en el código:

```python
pyghidra.start(install_dir="/opt/ghidra")
```

### 7.3. Error al compilar plugin Java

Si ves errores como `package ghidra.python does not exist`:

**Causa**: Tenías instalado `pyhidra` (obsoleto) en lugar de `pyghidra`.

**Solución**:

```bash
pip uninstall pyhidra -y --break-system-packages
pip install pyghidra --break-system-packages
```

pyhidra 1.3.0 **no es compatible** con Ghidra 12.x. Ghidra 12+ incluye pyghidra 3.x nativamente.

### 7.4. Error de JPype: versión incorrecta

pyghidra 3.1.0 requiere **jpype1 == 1.5.2**. Si tienes una versión diferente:

```bash
pip install jpype1==1.5.2 --break-system-packages
```

### 7.5. Ghidra se queda sin memoria

Aumenta la memoria JVM editando `/opt/ghidra/support/launch.properties`:

```properties
VMARGS_LINUX=-Xmx8G -Xss16M
```

O desde pyghidra:

```python
from pyghidra.launcher import HeadlessPyGhidraLauncher
launcher = HeadlessPyGhidraLauncher()
launcher.add_vmargs("-Xmx8G")
launcher.start()
```

### 7.6. ghIDRA no encuentra la JVM

pyghidra busca `JAVA_HOME`. Si no está definido:

```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

pyghidra 3.1.0 también intenta usar `JAVA_HOME` como fallback si java no está en el PATH.

---

## 8. Referencias

- **pyghidra en PyPI**: <https://pypi.org/project/pyghidra/>
- **Código fuente (NSA Ghidra)**: <https://github.com/NationalSecurityAgency/ghidra>
- **Documentación PyGhidra (en Ghidra)**: `/opt/ghidra/Ghidra/Features/PyGhidra/src/main/py/README.md`
- **Paquete offline pyghidra**: `/opt/ghidra/Ghidra/Features/PyGhidra/pypkg/dist/`
- **Ghidra API reference**: `/opt/ghidra/docs/api/index.html`
- **Ghidra Getting Started**: `/opt/ghidra/GhidraDocs/GettingStarted.md`

---

> **Nota importante**: pyhidra (el proyecto original de DC3) fue absorbido por Ghidra bajo el nombre **PyGhidra**. pyhidra 1.3.0 (oct 2024) fue su última versión y solo da soporte hasta Ghidra 11.3/12.0. Para Ghidra 12.1.2+, usa siempre **pyghidra 3.x**.

# GPS Status & Toolbox v11.4.316 — Case Study

**Fechas:** 2026-07-17 (investigacion inicial) / 2026-07-18 (resolucion definitiva)
**Dispositivo:** Bison (Android 10, ARM64, rooteado) y emulador AVD (Android 10, x86_64)
**Objetivo:** Restaurar la importacion de waypoints (GPX) en versiones moddeadas

---

## Resumen (actualizado)

~~GPS Status usa PairipCore (proteccion de Google Play) que ejecuta codigo de importacion dentro de una VM nativa. Reconstruir la logica de importacion en Java puro resulto inviable.~~

**CORRECCION 2026-07-18:** El parser Java puro SI funciona. La importacion de GPX se restauro completamente con dos parches en smali. PairipCore no era necesario: la app tiene un parser Java (`l3/b.t()`) que usa `XmlPullParser` para parsear GPX nativamente. El fallo estaba en un **mapeo incorrecto del tipo de parser** entre `b3.a.G` y `l3.b.t()`.

---

## Versiones analizadas

| Version | Tamaño | .so nativo | Modder | Importacion | Pro |
|---|---|---|---|---|---|
| **Original (Play Store)** | 6.4 MB + splits | `libpairipcore.so` | Ninguno | ✅ via PairipCore VM | ✅ |
| **Farsroid** | 5.3 MB | Ninguno | KillerApplication + sin dialogos | ❌ `doInBackground` corrupto → ✅ **CORREGIDO** | ✅ |
| **Liteapks** | 5.2 MB | Ninguno | KillerApplication + dialogos `ī/íì/` | ❌ `doInBackground` corrupto | ✅ |
| **MOD generico** | 7.0 MB | `liba.so` (OpenSSL 32-bit) | KillerApplication | ❌ mismo `doInBackground` corrupto | ✅ |

---

## Arquitectura de la app original

### Flujo de importacion

```
GPSStatus.onCreate() / onNewIntent() / onActivityResult()
  → b3.a.G(GPSStatus, Uri)
    → detecta extension del archivo (.gpx, .kml, .csv)
    → crea Ll3/b(parser_type) segun formato:
         a=0 para GPX y CSV (BUG: GPX mapea a parser CSV)
         a=1 para KML
    → crea P5/i4 como callback (GPSStatus + ProgressDialog)
    → crea k3/c AsyncTask(a=2, b=Ll3/b parser)
    → crea Ll3/a(uri, contentResolver, callback)
    → ProgressDialog "Importando ubicaciones"
    → AsyncTask.execute(Ll3/a[])
      → doInBackground():
         ORIGINAL: VMRunner.invoke("9x7BjPtyizFuxnyU", params)
         MODS:     codigo basura con move-result-object huerfano
         FIX:      parsing Java directo via l3/b.t()
      → onPostExecute(Integer count):
         0 → toast "No data imported"
         otros → toast de error o refresh
```

### El parser Java: `l3/b.t(InputStream) → ArrayList`

La clase `Ll3/b` extiende `Lb3/a` e implementa `t(InputStream)` con un `packed-switch`:

```smali
# l3/b.smali
packed-switch v0, :pswitch_data
    case 0x0 → :pswitch_2bc    # CSV parser (BufferedReader, split por coma)
    case 0x1 → :pswitch_1af    # KML parser (XmlPullParser)
    default  →                 # GPX parser (XmlPullParser)
.end packed-switch
```

**El bug raiz:** `b3.a.G` pasa `a=0` para GPX, pero `a=0` ejecuta el parser CSV. El parser CSV lee el XML de GPX y no encuentra comas → retorna ArrayList vacio → `onPostExecute` recibe 0 → toast "No data imported".

---

## Parches aplicados (solucion definitiva)

### Parche 1: `k3/c.smali` — Reconstruir `doInBackground`

Reemplaza el codigo basura del modder con una implementacion completa que:

1. Extrae `Ll3/a` de `params[0]` (URI, ContentResolver, callback)
2. **Crea un parser nuevo `Ll3/b(2)`** — el valor 2 cae en el `default` del switch (XmlPullParser para GPX)
3. Abre `InputStream` via `ContentResolver.openInputStream(uri)`
4. Llama a `l3/b.t(InputStream)` → `ArrayList<Ln3/b>`
5. Itera los waypoints y los inserta en la BD via `b3.a.B(Ln3/b)`
6. Retorna `Integer.valueOf(count)`
7. Captura excepciones → retorna 0

```smali
.method public final doInBackground([Ljava/lang/Object;)Ljava/lang/Object;
    .registers 12

    const/4 v0, 0x0
    aget-object v1, p1, v0
    check-cast v1, Ll3/a;                          # ← CAST necesario (sin el → NoSuchFieldError)

    # CREAR parser nuevo con a=2 (XmlPullParser/GPX)
    # NO usar this.b — ese parser tiene a=0 (CSV) cuando b3.a.G detecta .gpx
    new-instance v2, Ll3/b;
    const/16 v7, 0x2
    invoke-direct {v2, v7}, Ll3/b;-><init>(I)V

    # Guardar callback para onPostExecute
    iget-object v3, v1, Ll3/a;->c:Lp5/i4;           # ← tipo exacto, no Object
    iput-object v3, p0, Lk3/c;->c:Ljava/lang/Object;

    :try_start_b
    iget-object v3, v1, Ll3/a;->b:Landroid/content/ContentResolver;
    iget-object v4, v1, Ll3/a;->a:Landroid/net/Uri;
    invoke-virtual {v3, v4}, ...->openInputStream(...);
    move-result-object v3

    invoke-virtual {v2, v3}, Ll3/b;->t(...);        # parsea GPX
    move-result-object v4
    invoke-virtual {v3}, ...->close()V

    # Insertar cada waypoint en la BD
    const/4 v5, 0x0
    invoke-virtual {v4}, ...->iterator()...
    :loop
    invoke-interface {v4}, ...->hasNext()...
    invoke-interface {v4}, ...->next()...
    check-cast v6, Ln3/b;
    invoke-static {v6}, Lb3/a;->B(Ln3/b;)V
    add-int/lit8 v5, v5, 0x1
    goto :loop

    invoke-static {v5}, ...->valueOf(I)...
    return-object v0
    :catch
    invoke-virtual {v0}, ...->printStackTrace()V
    const/4 v0, 0x0
    invoke-static {v0}, ...->valueOf(I)...
    return-object v0
.end method
```

### Parche 2: `b3/a.smali` — Forzar parser cuando no se detecta extension

Cuando el `ContentResolver.query()` no devuelve `_display_name` (ej. MiXplorer, ciertos file managers), `b3.a.G` no puede detectar la extension y `v1` queda `null`. Sin parser, la importacion se salta silenciosamente.

```smali
# b3/a.smali — en :goto_14a, antes del if-eqz v1, :cond_176
:goto_14a
    if-eqz v1, :force_parser_gps      # si v1 ES null → crear parser
    const/4 v12, 0x0
    goto :parser_ready_gps             # si v1 NO es null → seguir

:force_parser_gps
    const/4 v12, 0x3
    new-instance v1, Ll3/b;
    const/16 v10, 0x2                  # a=2 → XmlPullParser (GPX)
    invoke-direct {v1, v10}, Ll3/b;-><init>(I)V

:parser_ready_gps
    if-eqz v1, :cond_176              # si hay parser → crear AsyncTask
```

**Nota:** Este parche es secundario. El parche 1 (crear parser nuevo en `doInBackground`) es el que realmente resuelve el problema porque ignora completamente el parser que viene de `b3.a.G`. El parche 2 solo es relevante para evitar que `b3.a.G` se salte la creacion del AsyncTask cuando la extension no se detecta.

---

## Errores de smali descubiertos durante el desarrollo

Estos errores bloquearon el intento anterior y las primeras 7 iteraciones del fix:

| # | Error | Sintoma | Fix |
|---|---|---|---|
| 1 | `move-result-object` tras `const-string` (original) | `VerifyError` en Android 10 | Reconstruir metodo completo |
| 2 | `aget-object` sin `check-cast` posterior | `NoSuchFieldError: cannot access field from Object` | `check-cast v1, Ll3/a;` |
| 3 | Tipo generico en `iget-object`: `Ll3/a;->c:Ljava/lang/Object;` | `NoSuchFieldError: no field c of type Object` | Tipo exacto: `Ll3/a;->c:Lp5/i4;` |
| 4 | Reusar parser de `this.b` con `a=0` | Parser CSV en vez de GPX → 0 waypoints | Crear parser nuevo con `a=2` |
| 5 | `if-nez` en vez de `if-eqz` en force-parser | Parser no se crea cuando es null | `if-eqz v1, :force_parser` |
| 6 | `.registers N` con `v13`/`v14` solapando parametros | Registros corruptos | Maximo local `v12` en `.registers 15` |

---

## Diferencias emulador vs Bison: por que funcionaba en uno y no en otro

| Aspecto | Emulador (x86_64) | Bison (ARM64) |
|---|---|---|
| URI de prueba | `file:///data/local/tmp/test.gpx` | `content://...` via SAF file picker |
| Deteccion de extension | **Falla** — `file://` URI no pasa por `ContentResolver.query()` con `_display_name` | **Funciona** — el file picker devuelve `content://` con `_display_name` correcto |
| Parser creado por `b3.a.G` | `null` → force-parser crea `Ll3.b(2)` ✅ | `Ll3.b(0)` → parser CSV ❌ |
| `doInBackground` usa parser de `this.b` | `this.b` = `Ll3.b(2)` → XmlPullParser ✅ | `this.b` = `Ll3.b(0)` → CSV parser → 0 waypoints ❌ |
| Resultado | 26 waypoints importados (2 ejecuciones × 13) | Dialogo "Importando" pero 0 waypoints |

**Conclusion:** El emulador funciono "de casualidad" porque la URI `file://` no permitia detectar la extension, forzando el parser generico (`a=2`). En el Bison, el file picker real SI devolvia un `content://` con extension detectable, creando el parser `a=0` (CSV) que no parsea GPX.

**Solucion definitiva:** `doInBackground` ignora completamente `this.b` y crea siempre un parser nuevo con `a=2`, eliminando la dependencia del mapeo incorrecto en `b3.a.G`.

---

## Lecciones aprendidas (actualizado)

1. **PairipCore NO era necesario para la importacion.** La app tiene un parser Java (`l3/b.t()`) con `XmlPullParser` que funciona perfectamente para GPX. PairipCore era solo un wrapper de ofuscacion, no una dependencia funcional.

2. **El `packed-switch` en `l3/b.t()` tiene un bug de diseño del desarrollador original.** GPX y CSV comparten el valor `a=0` en el constructor, pero el switch interno mapea `a=0` exclusivamente a CSV. GPX deberia usar `a≥2`. Este bug probablemente nunca se detecto porque el codigo original usaba `VMRunner.invoke()` (PairipCore) y el parser Java era codigo muerto o fallback no probado.

3. **El tipo de URI importa.** `file://` vs `content://` cambia completamente el flujo de deteccion de extension en `b3.a.G`. Probar con ambas es esencial.

4. **Los errores de smali son acumulativos y silenciosos.** El intento anterior tenia 3-4 bugs simultaneos (sin `check-cast`, tipo generico, `if-nez` invertido, reuso de parser incorrecto). La app no crasheaba pero no importaba datos, haciendo el diagnostico extremadamente dificil.

5. **Verificar la BD es la unica prueba definitiva.** `sqlite3 locations.db "SELECT COUNT(*) FROM locations"` confirmo la importacion real. Los toasts y dialogos no son suficientes.

---

## Archivos del caso

| Archivo | Descripcion |
|---|---|
| `GPS-Status-v11.4.316-fixed.apk` | APK final funcional (Escritorio) |
| `GPS Status v11.4.316 (Premium).apk` | Mod Liteapks original |
| `GPS-Status-Toolbox-Pro-11.4.316(www.farsroid.com).apk` | Mod Farsroid original (base del fix) |
| `/tmp/gpsstatus_smali/dex_out/` | Smali complete del Farsroid mod |
| `/tmp/gpsstatus_smali/dex_out/k3/c.smali` | `doInBackground` parcheado (final) |
| `/tmp/gpsstatus_smali/dex_out/b3/a.smali` | `b3.a.G` con force-parser |
| `/tmp/gpsstatus_v8_signed.apk` | APK v8 (funcional, mismo que el del Escritorio) |

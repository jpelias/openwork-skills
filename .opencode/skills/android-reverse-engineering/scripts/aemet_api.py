#!/usr/bin/env python3
"""
Cliente Python para la API de AEMET (descubierta mediante captura de tráfico).
Usa los mismos endpoints de la app oficial es.aemet v3.1.7

Endpoints:
  /es/apps/prediccion/municipios?req=<base64>  → Predicción horaria y diaria
  /es/api-eltiempo/timeline-avisos/{PB|CAN}     → Timeline de avisos
  /es/api-eltiempo/resumen-lista-avisos/{zona}/{fecha}/-/ → Resumen avisos
  /es/api-eltiempo/avisos-horas/{CAN|PB}/9/     → Avisos por horas
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://www.aemet.es"
HEADERS = {
    "User-Agent": "es.aemet/317 (Linux; Android 10; es_ES; BISON; Cronet/149.0.7827.102)",
    "Accept-Encoding": "gzip, deflate, br",
}

# Req parameters capturados de la app real
REQ_MINAYA       = "WgEFBQBEU09mclEEEgEGRAQSUEUERV5AUUVREyVfVUsHVlhSQkQcEUcOAAUsUUFGSQFTAw"
REQ_VILLACONEJOS = "WgEHDwFHW09mclEEEgEGRAQSUEUERV5AUUVREyVfVUsHVlhSQkQcEUcOAAUsUUFGSQFTAw"

class AemetAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def prediccion_municipio(self, req: str) -> dict:
        """Obtiene predicción horaria y diaria de un municipio."""
        resp = self.session.get(
            f"{BASE_URL}/es/apps/prediccion/municipios",
            params={"req": req}
        )
        resp.raise_for_status()
        return resp.json()

    def timeline_avisos(self, zona: str = "PB") -> dict:
        """Obtiene timeline de avisos (PB=Península+Baleares, CAN=Canarias)."""
        resp = self.session.get(
            f"{BASE_URL}/es/api-eltiempo/timeline-avisos/{zona}"
        )
        resp.raise_for_status()
        return resp.json()

    def resumen_avisos(self, zona: str = "PB", fecha: str = None) -> dict:
        """Resumen de avisos por zona y fecha."""
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d")
        resp = self.session.get(
            f"{BASE_URL}/es/api-eltiempo/resumen-lista-avisos/{zona}/{fecha}/-/"
        )
        resp.raise_for_status()
        return resp.json()

    def avisos_horas(self, zona: str = "PB") -> dict:
        """Avisos por horas para una zona."""
        resp = self.session.get(
            f"{BASE_URL}/es/api-eltiempo/avisos-horas/{zona}/9/"
        )
        resp.raise_for_status()
        return resp.json()

    def formatear_prediccion(self, data: dict) -> str:
        """Formatea la predicción de un municipio en texto legible."""
        nombre = data.get("nombre", "?")
        prov = data.get("provincia", "?")
        out = [f"📍 {nombre} ({prov})\n"]
        
        horas = data.get("arrPrediccionHoras", [])
        if horas:
            out.append("⏰ Predicción por horas:")
            for h in horas[:8]:  # Primeras 8 horas
                fecha, hora, icono, tmax, tmin, v_dir, v_vel, v_rach, lluv, _, hum, *_ = h
                out.append(
                    f"  {hora}:00 | {tmax}°C | 💧{hum}% | 💨{v_dir} {v_vel}km/h | 🌧{lluv}%"
                )
        
        dias = data.get("arrPrediccionDias", [])
        if dias:
            out.append("\n📅 Predicción diaria:")
            for d in dias[:5]:
                fecha, periodo, icono, tmin, tmax, *_ = d
                out.append(f"  {fecha} [{periodo}]: {tmin}°C / {tmax}°C")
        
        return "\n".join(out)

    def formatear_avisos(self, data: dict) -> str:
        """Formatea avisos en texto legible."""
        avisos = data.get("orden_avisos", [])
        if not avisos:
            return "✅ Sin avisos activos"
        
        out = ["⚠️ AVISOS ACTIVOS:"]
        for entry in avisos:
            if len(entry) >= 2 and isinstance(entry[1], dict):
                a = entry[1]
                sev = "🔴" if a.get("Nivel") == 1 else "🟠" if a.get("Nivel") == 2 else "🟡"
                out.append(
                    f"  {sev} {a.get('Severity', '?')}: {a.get('Descrption', '')[:100]}\n"
                    f"     {a.get('Valor', '')} | {a.get('Onset', '')} → {a.get('Expire', '')}"
                )
        return "\n".join(out)


if __name__ == "__main__":
    api = AemetAPI()
    
    print("=" * 60)
    print("PREDICCIÓN MINAYA (Albacete)")
    print("=" * 60)
    data = api.prediccion_municipio(REQ_MINAYA)
    print(api.formatear_prediccion(data))
    
    print("\n" + "=" * 60)
    print("AVISOS HOY (Península + Baleares)")
    print("=" * 60)
    avisos = api.resumen_avisos("PB")
    print(api.formatear_avisos(avisos))
    
    print("\n" + "=" * 60)
    print("TIMELINE AVISOS PB")
    print("=" * 60)
    tl = api.timeline_avisos("PB")
    if tl.get("resumenes_penbal"):
        print(f"  Días: {tl['resumenes_penbal']}")

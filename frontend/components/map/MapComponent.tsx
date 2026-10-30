// components/map/MapComponent.tsx
// Leaflet Map di-render hanya di client (no SSR) karena Leaflet butuh window object
"use client";
import { useEffect, useRef } from "react";
import type { KlasterItem } from "@/lib/api";

interface MapProps {
  data: KlasterItem[];
  onCityClick?: (city: KlasterItem) => void;
}

export default function MapComponent({ data, onCityClick }: MapProps) {
  const mapRef = useRef<any>(null);
  const divRef = useRef<HTMLDivElement>(null);
  const markersLayerRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !divRef.current) return;
    let isCancelled = false;

    // Dynamic import Leaflet (client-only)
    import("leaflet").then((L) => {
      if (isCancelled || !divRef.current) return;

      // Fix icon Leaflet default
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      // Inisialisasi map jika belum dibuat
      if (!mapRef.current) {
        if ((divRef.current as any)._leaflet_id != null) {
          (divRef.current as any)._leaflet_id = null;
        }

        const map = L.map(divRef.current, {
          center: [-2.5, 118],   // Pusat Indonesia
          zoom: 5,
          zoomControl: true,
          attributionControl: false,
        });

        // Base tile — CartoDB Dark Matter (cocok dark mode)
        L.tileLayer(
          "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
          { subdomains: "abcd", maxZoom: 19 }
        ).addTo(map);

        // Layer group untuk marker kota
        const markersGroup = L.layerGroup().addTo(map);
        markersLayerRef.current = markersGroup;
        mapRef.current = map;

        // Legenda Zona
        const legend = new (L as any).Control({ position: "bottomright" });
        legend.onAdd = () => {
          const div = document.createElement("div");
          div.style.cssText = `
            background:#111827;padding:12px 16px;border-radius:12px;
            border:1px solid #1e2d4a;font-family:Inter,sans-serif;
            box-shadow:0 4px 20px rgba(0,0,0,0.5);
          `;
          div.innerHTML = `
            <div style="font-size:11px;font-weight:700;color:#8899bb;margin-bottom:8px;letter-spacing:1px;text-transform:uppercase">LEGENDA ZONA</div>
            <div style="display:flex;flex-direction:column;gap:6px">
              <div style="display:flex;align-items:center;gap:8px">
                <div style="width:12px;height:12px;border-radius:50%;background:#22c55e;box-shadow:0 0 6px #22c55e"></div>
                <span style="font-size:12px;color:#f0f6ff">Aman</span>
              </div>
              <div style="display:flex;align-items:center;gap:8px">
                <div style="width:12px;height:12px;border-radius:50%;background:#f59e0b;box-shadow:0 0 6px #f59e0b"></div>
                <span style="font-size:12px;color:#f0f6ff">Waspada</span>
              </div>
              <div style="display:flex;align-items:center;gap:8px">
                <div style="width:14px;height:14px;border-radius:50%;background:#ef4444;box-shadow:0 0 6px #ef4444"></div>
                <span style="font-size:12px;color:#f0f6ff">Kritis</span>
              </div>
            </div>
          `;
          return div;
        };
        legend.addTo(map);
      }

      // Update marker tiap data berubah
      if (markersLayerRef.current) {
        markersLayerRef.current.clearLayers();

        const zonaConfig: Record<string, { color: string; radius: number }> = {
          "Aman":    { color: "#22c55e", radius: 8  },
          "Waspada": { color: "#f59e0b", radius: 10 },
          "Kritis":  { color: "#ef4444", radius: 12 },
        };

        data.forEach((city) => {
          if (!city.latitude || !city.longitude) return;
          const cfg = zonaConfig[city.status_zona] || { color: "#6b7280", radius: 8 };

          const circle = L.circleMarker([city.latitude, city.longitude], {
            radius:      cfg.radius,
            fillColor:   cfg.color,
            color:       "#fff",
            weight:      1.5,
            opacity:     0.9,
            fillOpacity: 0.85,
          });

          circle.bindPopup(`
            <div style="font-family:Inter,sans-serif;padding:4px 2px;min-width:200px">
              <div style="font-weight:700;font-size:14px;margin-bottom:8px;color:#f0f6ff">
                📍 ${city.nama_kabkota}
              </div>
              <div style="font-size:11px;color:#8899bb;margin-bottom:6px">${city.nama_provinsi}</div>
              <div style="display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;
                background:${cfg.color}22;color:${cfg.color};border:1px solid ${cfg.color}44">
                ${city.status_zona === "Aman" ? "✅" : city.status_zona === "Waspada" ? "⚠️" : "🔴"} 
                ${city.status_zona}
              </div>
              <div style="margin-top:10px;font-size:11px;color:#8899bb">
                Cluster ID: ${city.cluster_id}<br/>
                Update: ${city.tanggal_proses?.slice(0,10)}
              </div>
            </div>
          `);

          if (onCityClick) {
            circle.on("click", () => onCityClick(city));
          }

          circle.addTo(markersLayerRef.current);
        });
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [data, onCityClick]);

  // Hapus map hanya saat unmount
  useEffect(() => {
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  return (
    <>
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        crossOrigin=""
      />
      <div ref={divRef} style={{ width: "100%", height: "100%", borderRadius: 16 }} />
    </>
  );
}

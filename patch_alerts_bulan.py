import sys

target = r"c:\Project Coding\pangan-watcher\backend\app\api\v1\endpoints\alerts.py"
with open(target, "r", encoding="utf-8") as f:
    code = f.read()

old_signature = """def get_alerts(
    status_filter: Optional[str] = Query(
        default=None,
        description="Filter status: 'Baru', 'Ditinjau', atau 'Ditangani'",
    ),
    kode_kabkota: Optional[str] = Query(
        default=None,
        description="Filter per kota/kabupaten",
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):"""

new_signature = """def get_alerts(
    status_filter: Optional[str] = Query(
        default=None,
        description="Filter status: 'Baru', 'Ditinjau', atau 'Ditangani'",
    ),
    kode_kabkota: Optional[str] = Query(
        default=None,
        description="Filter per kota/kabupaten",
    ),
    bulan: Optional[str] = Query(
        default=None,
        description="Filter periode bulan (format YYYY-MM, contoh: 2026-08)",
        example="2026-08",
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):"""

old_cond = """    if kode_kabkota:
        conditions.append("pd.kode_kabkota = :kode_kabkota")
        params["kode_kabkota"] = kode_kabkota"""

new_cond = """    if kode_kabkota:
        conditions.append("pd.kode_kabkota = :kode_kabkota")
        params["kode_kabkota"] = kode_kabkota

    if bulan:
        conditions.append("TO_CHAR(COALESCE(h.tanggal, pd.tanggal_deteksi::date), 'YYYY-MM') = :bulan")
        params["bulan"] = bulan"""

old_count = """    count_query = text(f\"\"\"
        SELECT COUNT(*) FROM peringatan_dini pd
        WHERE {where}
    \"\"\")"""

new_count = """    count_query = text(f\"\"\"
        SELECT COUNT(*) FROM peringatan_dini pd
        LEFT JOIN harga_harian h ON pd.id_harga = h.id_harga
        WHERE {where}
    \"\"\")"""

if old_signature in code and old_cond in code and old_count in code:
    code = code.replace(old_signature, new_signature)
    code = code.replace(old_cond, new_cond)
    code = code.replace(old_count, new_count)
    with open(target, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: alerts.py now supports 'bulan' filter!")
else:
    print("Failed to replace alerts.py")


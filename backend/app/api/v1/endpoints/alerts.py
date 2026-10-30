# ========================================================
# app/api/v1/endpoints/alerts.py
# Endpoint untuk Early Warning System & Peringatan Dini
# ========================================================
import logging
from io import BytesIO, StringIO
from typing import Optional
from fastapi.responses import StreamingResponse, Response
import csv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.services.ews_service import run_ews_detection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["Early Warning System"])


@router.post(
    "/run",
    summary="Jalankan Deteksi Peringatan Dini",
    description=(
        "Menjalankan Early Warning System untuk mendeteksi lonjakan harga "
        "komoditas di setiap kota. Jika harga naik melebihi threshold "
        "(default: 15%), sistem otomatis mencatat peringatan ke database."
    ),
)
def run_ews(
    threshold_pct: float = Query(
        default=15.0,
        ge=1.0, le=100.0,
        description="Persentase lonjakan harga minimum untuk memicu peringatan (default: 15%)",
    ),
    tanggal_akhir: Optional[str] = Query(
        default=None,
        description="Tanggal referensi format YYYY-MM-DD. Kosongkan untuk tanggal terbaru.",
        example="2026-01-28",
    ),
    window_days: int = Query(
        default=7,
        ge=1, le=30,
        description="Jumlah hari untuk menghitung baseline harga sebelumnya (default: 7)",
    ),
    db: Session = Depends(get_db),
):
    """
    Trigger deteksi EWS.

    **Kapan dipakai?**
    - Setiap hari setelah data harga terbaru di-upload
    - Saat demo/sidang untuk menunjukkan deteksi peringatan

    **Contoh peringatan yang dihasilkan:**
    "Beras Premium di Kota Semarang melonjak 18.5% pada 28 Jan 2026"
    """
    logger.info(
        f"Menerima request EWS: threshold={threshold_pct}%, "
        f"tanggal={tanggal_akhir}, window={window_days}d"
    )

    result = run_ews_detection(
        db=db,
        threshold_pct=threshold_pct,
        tanggal_akhir=tanggal_akhir,
        window_days=window_days,
    )

    if result.errors and result.n_checked == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "EWS gagal dijalankan.", "errors": result.errors},
        )

    return {
        "status": "success",
        "message": (
            f"EWS selesai. "
            f"{result.n_alerts_created} peringatan baru dari "
            f"{result.n_checked} kombinasi yang diperiksa."
        ),
        "hasil_ews": result.to_dict(),
    }


@router.get(
    "/",
    summary="Ambil Daftar Peringatan Dini",
    description="Mengambil riwayat peringatan dini untuk ditampilkan di Alert Center frontend.",
)
def get_alerts(
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
):
    """
    Endpoint untuk halaman Alert Center.
    Mengembalikan riwayat peringatan dini dengan informasi lengkap.
    """
    conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if status_filter:
        conditions.append("pd.status = :status_filter")
        params["status_filter"] = status_filter

    if kode_kabkota:
        conditions.append("pd.kode_kabkota = :kode_kabkota")
        params["kode_kabkota"] = kode_kabkota

    if bulan:
        conditions.append("TO_CHAR(COALESCE(h.tanggal, pd.tanggal_deteksi::date), 'YYYY-MM') = :bulan")
        params["bulan"] = bulan

    where = " AND ".join(conditions)

    query = text(f"""
        SELECT
            pd.id_peringatan,
            pd.kode_kabkota,
            k.nama_kabkota,
            p.nama_provinsi,
            pd.nama_komoditas,
            pd.harga_sebelumnya,
            pd.harga_sekarang,
            pd.persentase_lonjakan,
            COALESCE(TO_CHAR(h.tanggal, 'YYYY-MM-DD'), TO_CHAR(pd.tanggal_deteksi, 'YYYY-MM-DD')) AS tanggal_lonjakan,
            pd.status
        FROM peringatan_dini pd
        JOIN kabupaten_kota k  ON pd.kode_kabkota = k.kode_kabkota
        JOIN provinsi p        ON k.kode_provinsi  = p.kode_provinsi
        LEFT JOIN harga_harian h ON pd.id_harga = h.id_harga
        WHERE {where}
        ORDER BY COALESCE(h.tanggal, pd.tanggal_deteksi::date) DESC, pd.persentase_lonjakan DESC
        LIMIT :limit OFFSET :offset
    """)

    count_query = text(f"""
        SELECT COUNT(*) FROM peringatan_dini pd
        LEFT JOIN harga_harian h ON pd.id_harga = h.id_harga
        WHERE {where}
    """)

    rows = db.execute(query, params).fetchall()
    total = db.execute(
        count_query,
        {k: v for k, v in params.items() if k not in ("limit", "offset")}
    ).scalar()

    data = [
        {
            "id_peringatan":       row[0],
            "kode_kabkota":        row[1],
            "nama_kabkota":        row[2],
            "nama_provinsi":       row[3],
            "nama_komoditas":      row[4],
            "harga_sebelumnya":    row[5],
            "harga_sekarang":      row[6],
            "persentase_lonjakan": row[7],
            "tanggal_deteksi":     str(row[8]),
            "status":              row[9],
            # Pesan ringkas untuk ditampilkan di UI
            "pesan": (
                f"Peringatan: {row[4]} di {row[2]} melonjak "
                f"{row[7]:.1f}% pada {str(row[8])[:10]}"
            ),
        }
        for row in rows
    ]

    return {
        "status": "success",
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": data,
    }


@router.patch(
    "/{id_peringatan}/status",
    summary="Update Status Peringatan",
    description="Mengubah status peringatan (Baru -> Ditinjau -> Ditangani).",
)
def update_alert_status(
    id_peringatan: int,
    new_status: Optional[str] = Query(
        default=None,
        description="Status baru: 'Baru', 'Ditinjau', atau 'Ditangani'",
        example="Ditinjau",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Alias parameter untuk status",
    ),
    db: Session = Depends(get_db),
):
    target_status = new_status or status
    allowed_statuses = {"Baru", "Ditinjau", "Ditangani"}
    if not target_status or target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status tidak valid. Pilih salah satu: {allowed_statuses}",
        )

    result = db.execute(
        text("""
            UPDATE peringatan_dini
            SET status = :new_status
            WHERE id_peringatan = :id
            RETURNING id_peringatan
        """),
        {"new_status": target_status, "id": id_peringatan},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peringatan ID {id_peringatan} tidak ditemukan.",
        )

    return {
        "status": "success",
        "message": f"Status peringatan {id_peringatan} diupdate ke '{target_status}'.",
    }


@router.get(
    "/export/excel",
    summary="Ekspor Laporan Peringatan Dini (Excel .xlsx)",
    description="Mengunduh laporan rekapitulasi peringatan dini dalam format file Excel (.xlsx) dengan pilihan kolom kustom, filter status, dan bulan.",
)
def export_alerts_excel(
    status_filter: Optional[str] = Query(default=None, description="Filter status (Baru, Ditinjau, Ditangani)"),
    bulan: Optional[str] = Query(default=None, description="Filter periode bulan YYYY-MM"),
    columns: Optional[str] = Query(default=None, description="Daftar kolom yang ingin diekspor, dipisah koma (contoh: 'no,kabkota,provinsi,komoditas,harga_sekarang,persentase')"),
    db: Session = Depends(get_db),
):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    conditions = ["1=1"]
    params = {}

    if status_filter:
        conditions.append("pd.status = :status_filter")
        params["status_filter"] = status_filter

    if bulan:
        conditions.append("TO_CHAR(COALESCE(h.tanggal, pd.tanggal_deteksi::date), 'YYYY-MM') = :bulan")
        params["bulan"] = bulan

    where = " AND ".join(conditions)

    query = text(f"""
        SELECT
            pd.id_peringatan,
            pd.kode_kabkota,
            k.nama_kabkota,
            p.nama_provinsi,
            pd.nama_komoditas,
            pd.harga_sebelumnya,
            pd.harga_sekarang,
            pd.persentase_lonjakan,
            COALESCE(TO_CHAR(h.tanggal, 'YYYY-MM-DD'), TO_CHAR(pd.tanggal_deteksi, 'YYYY-MM-DD')) AS tanggal_lonjakan,
            pd.status
        FROM peringatan_dini pd
        JOIN kabupaten_kota k ON pd.kode_kabkota = k.kode_kabkota
        JOIN provinsi p       ON k.kode_provinsi  = p.kode_provinsi
        LEFT JOIN harga_harian h ON pd.id_harga = h.id_harga
        WHERE {where}
        ORDER BY tanggal_lonjakan DESC, pd.persentase_lonjakan DESC
    """)

    rows = db.execute(query, params).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Peringatan"
    ws.views.sheetView[0].showGridLines = True

    # Styling Palettes
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue
    title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    meta_font = Font(name="Calibri", size=10, italic=True, color="475569")
    regular_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)

    border_thin = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(top=border_thin, left=border_thin, right=border_thin, bottom=border_thin)

    fill_even = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    status_colors = {
        "Baru": {"font": Font(color="DC2626", bold=True), "fill": PatternFill(start_color="FEE2E2", fill_type="solid")},
        "Ditinjau": {"font": Font(color="D97706", bold=True), "fill": PatternFill(start_color="FEF3C7", fill_type="solid")},
        "Ditangani": {"font": Font(color="16A34A", bold=True), "fill": PatternFill(start_color="DCFCE7", fill_type="solid")},
    }

    # Definisi master opsi kolom
    # key -> (Nama Header, function extractor (row, idx) -> (val, align, font, num_fmt, is_status))
    ALL_COLUMNS = {
        "no": ("No", lambda r, idx: (idx, Alignment(horizontal="center"), regular_font, None, False)),
        "id_peringatan": ("ID Alert", lambda r, idx: (r[0], Alignment(horizontal="center"), regular_font, None, False)),
        "kode_kabkota": ("Kode Wilayah", lambda r, idx: (r[1], Alignment(horizontal="center"), regular_font, None, False)),
        "nama_kabkota": ("Kabupaten / Kota", lambda r, idx: (r[2], Alignment(horizontal="left"), bold_font, None, False)),
        "nama_provinsi": ("Provinsi", lambda r, idx: (r[3], Alignment(horizontal="left"), regular_font, None, False)),
        "nama_komoditas": ("Komoditas Pangan", lambda r, idx: (r[4], Alignment(horizontal="left"), bold_font, None, False)),
        "harga_sebelumnya": ("Harga Baseline (Rp)", lambda r, idx: (float(r[5]) if r[5] is not None else 0.0, Alignment(horizontal="right"), regular_font, "#,##0", False)),
        "harga_sekarang": ("Harga Lonjakan (Rp)", lambda r, idx: (float(r[6]) if r[6] is not None else 0.0, Alignment(horizontal="right"), bold_font, "#,##0", False)),
        "persentase_lonjakan": ("Kenaikan (%)", lambda r, idx: ((float(r[7]) if r[7] is not None else 0.0) / 100.0, Alignment(horizontal="right"), bold_font, "0.0%", False)),
        "tanggal_kejadian": ("Tanggal Kejadian", lambda r, idx: (r[8] or "-", Alignment(horizontal="center"), regular_font, None, False)),
        "status": ("Status Penanganan", lambda r, idx: (r[9] or "Baru", Alignment(horizontal="center"), status_colors.get(r[9] or "Baru", {}).get("font", regular_font), None, True)),
    }

    # Parse filter kolom yang diminta pengguna
    if columns:
        requested_keys = [c.strip().lower() for c in columns.split(",") if c.strip().lower() in ALL_COLUMNS]
        selected_keys = requested_keys if requested_keys else list(ALL_COLUMNS.keys())
    else:
        selected_keys = list(ALL_COLUMNS.keys())

    # Judul Dokumen
    end_col_letter = get_column_letter(max(len(selected_keys), 1))
    ws.merge_cells(f"A1:{end_col_letter}1")
    ws["A1"] = "REKAPITULASI SISTEM PERINGATAN DINI (EWS) KERAWANAN HARGA PANGAN"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 28

    # Sub-Judul / Filter info
    ws.merge_cells(f"A2:{end_col_letter}2")
    ws["A2"] = f"Periode Data: {bulan or 'Semua Periode'} | Filter Status: {status_filter or 'Semua Status'} | Total Kejadian: {len(rows)} data"
    ws["A2"].font = meta_font
    ws["A2"].alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 18

    ws.row_dimensions[3].height = 8 # Spasi kosong

    # Render Header Tabel
    header_row = 4
    ws.row_dimensions[header_row].height = 26

    for col_idx, key in enumerate(selected_keys, 1):
        header_text = ALL_COLUMNS[key][0]
        cell = ws.cell(row=header_row, column=col_idx, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border

    # Render Isi Data Baris
    current_row = 5
    for idx, r in enumerate(rows, 1):
        ws.row_dimensions[current_row].height = 20
        row_fill = fill_even if idx % 2 == 0 else fill_odd

        for col_idx, key in enumerate(selected_keys, 1):
            extractor = ALL_COLUMNS[key][1]
            val, align, font, num_fmt, is_status = extractor(r, idx)

            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.alignment = align
            cell.font = font
            cell.border = cell_border

            if is_status and str(val) in status_colors:
                cell.fill = status_colors[str(val)]["fill"]
            else:
                cell.fill = row_fill

            if num_fmt:
                cell.number_format = num_fmt

        current_row += 1

    # Auto-adjust lebar kolom
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if cell.number_format and ("#,##0" in cell.number_format or "0.0%" in cell.number_format):
                val_str = f"{val_str}     "
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Simpan ke stream BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"rekap_peringatan_pangan_{bulan or 'semua'}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get(
    "/export/csv",
    summary="Ekspor Laporan Peringatan Dini (CSV)",
    description="Mengunduh laporan rekapitulasi peringatan dini dalam format file CSV resmi untuk pembuat kebijakan atau analisis lanjutan.",
)
def export_alerts_csv(
    status_filter: Optional[str] = Query(default=None, description="Filter status (Baru, Ditinjau, Ditangani)"),
    bulan: Optional[str] = Query(default=None, description="Filter periode bulan YYYY-MM"),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params = {}

    if status_filter:
        conditions.append("pd.status = :status_filter")
        params["status_filter"] = status_filter

    if bulan:
        conditions.append("TO_CHAR(COALESCE(h.tanggal, pd.tanggal_deteksi::date), 'YYYY-MM') = :bulan")
        params["bulan"] = bulan

    where = " AND ".join(conditions)

    query = text(f"""
        SELECT
            pd.id_peringatan,
            pd.kode_kabkota,
            k.nama_kabkota,
            p.nama_provinsi,
            pd.nama_komoditas,
            pd.harga_sebelumnya,
            pd.harga_sekarang,
            pd.persentase_lonjakan,
            COALESCE(TO_CHAR(h.tanggal, 'YYYY-MM-DD'), TO_CHAR(pd.tanggal_deteksi, 'YYYY-MM-DD')) AS tanggal_lonjakan,
            pd.status
        FROM peringatan_dini pd
        JOIN kabupaten_kota k ON pd.kode_kabkota = k.kode_kabkota
        JOIN provinsi p       ON k.kode_provinsi  = p.kode_provinsi
        LEFT JOIN harga_harian h ON pd.id_harga = h.id_harga
        WHERE {where}
        ORDER BY tanggal_lonjakan DESC, pd.persentase_lonjakan DESC
    """)

    rows = db.execute(query, params).fetchall()

    output = StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

    # Header CSV
    writer.writerow([
        "ID Peringatan",
        "Kode Wilayah",
        "Kabupaten/Kota",
        "Provinsi",
        "Komoditas Pangan",
        "Harga Baseline (Rp)",
        "Harga Terdeteksi (Rp)",
        "Lonjakan (%)",
        "Tanggal Kejadian",
        "Status Penanganan"
    ])

    for r in rows:
        writer.writerow([
            r[0],
            r[1],
            r[2],
            r[3],
            r[4],
            f"{float(r[5]):.2f}" if r[5] is not None else "0",
            f"{float(r[6]):.2f}" if r[6] is not None else "0",
            f"{float(r[7]):.2f}%" if r[7] is not None else "0%",
            r[8] or "-",
            r[9] or "Baru"
        ])

    csv_data = output.getvalue()
    filename = f"laporan_peringatan_pangan_{bulan or 'semua'}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


"""
Generador de Facturas A/B en PDF.
Uso:
    py 10_generar_factura_pdf.py --cliente 15 --items "RADAR:1,VIBRO:2"
    py 10_generar_factura_pdf.py --demo
"""
import argparse, datetime, os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

load_dotenv()
password = quote_plus(os.getenv('DB_PASSWORD'))
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{password}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# ── Datos de la empresa ───────────────────────────────────────────────────────
EMPRESA = {
    "nombre":    "ELEKTRA S.R.L.",
    "direccion": "San Martín 1234, Santa Fe, Argentina",
    "telefono":  "(0342) 123-4567",
    "email":     "ventas@elektrasrl.com.ar",
    "cuit":      "30-12345678-9",
    "ib":        "123-456789-0",
    "inicio_act": "01/03/2005",
}

AZUL  = colors.HexColor("#1F497D")
GRIS  = colors.HexColor("#F2F2F2")
NEGRO = colors.black
ROJO  = colors.HexColor("#C00000")

# ── Helpers ───────────────────────────────────────────────────────────────────
def pesos(n):  return f"$ {n:>12,.2f}"
def get_cliente(codigo):
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT * FROM clientes WHERE codigo = :c"), {"c": codigo}
        ).fetchone()
    return dict(r._mapping) if r else None

def get_producto(nombre):
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT * FROM productos WHERE UPPER(nombre) = UPPER(:n) LIMIT 1"
        ), {"n": nombre}).fetchone()
    return dict(r._mapping) if r else None

# ── Generador principal ───────────────────────────────────────────────────────
def generar_factura(cliente_codigo, items_raw, numero=None, fecha=None, carpeta="../facturas"):
    cliente = get_cliente(cliente_codigo)
    if not cliente:
        raise ValueError(f"Cliente {cliente_codigo} no encontrado.")

    tipo_iva = (cliente.get("tipo_iva") or "").upper()
    tipo = "A" if "RESPONSABLE" in tipo_iva else "B"
    tasa_iva = 0.21

    if not numero:
        numero = datetime.datetime.now().strftime("%Y%m%d%H%M")
    if not fecha:
        fecha = datetime.date.today()

    # Armar líneas de detalle
    lineas = []
    for item in items_raw:
        nombre, qty = item.split(":")
        qty = float(qty)
        prod = get_producto(nombre.strip())
        if not prod:
            print(f"  Advertencia: producto '{nombre}' no encontrado, se omite.")
            continue
        precio_unit = float(prod["precio_base"])
        subtotal    = precio_unit * qty
        iva_monto   = subtotal * tasa_iva if tipo == "A" else 0
        lineas.append({
            "descripcion": prod["nombre"],
            "cantidad":    qty,
            "precio_unit": precio_unit,
            "subtotal":    subtotal,
            "iva":         iva_monto,
        })

    if not lineas:
        raise ValueError("No se encontraron productos válidos.")

    subtotal_total = sum(l["subtotal"] for l in lineas)
    iva_total      = sum(l["iva"] for l in lineas)
    total_final    = subtotal_total + iva_total

    # ── PDF ──────────────────────────────────────────────────────────────────
    os.makedirs(carpeta, exist_ok=True)
    nombre_archivo = f"FACTURA_{tipo}_{numero}_{cliente['nombre'].replace(' ', '_')[:20]}.pdf"
    ruta = os.path.join(carpeta, nombre_archivo)

    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []
    styles = getSampleStyleSheet()

    def estilo(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    s_titulo    = estilo("titulo",    fontSize=18, textColor=AZUL,  fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_subtitulo = estilo("subtitulo", fontSize=10, textColor=NEGRO, fontName="Helvetica",      alignment=TA_CENTER)
    s_normal    = estilo("normal",    fontSize=9,  textColor=NEGRO, fontName="Helvetica")
    s_bold      = estilo("bold",      fontSize=9,  textColor=NEGRO, fontName="Helvetica-Bold")
    s_right     = estilo("right",     fontSize=9,  textColor=NEGRO, fontName="Helvetica",      alignment=TA_RIGHT)
    s_tipo      = estilo("tipo",      fontSize=36, textColor=AZUL,  fontName="Helvetica-Bold", alignment=TA_CENTER)

    ancho = 180 * mm

    # ── Encabezado ────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(EMPRESA["nombre"], s_titulo),
            Paragraph(f"TIPO", s_subtitulo),
            Paragraph(f"FACTURA", s_subtitulo),
        ],
        [
            Paragraph(EMPRESA["direccion"], s_subtitulo),
            Paragraph(tipo, s_tipo),
            Paragraph(f"N° {numero}", s_bold),
        ],
        [
            Paragraph(f"Tel: {EMPRESA['telefono']}  |  {EMPRESA['email']}", s_subtitulo),
            Paragraph("", s_normal),
            Paragraph(f"Fecha: {fecha.strftime('%d/%m/%Y')}", s_normal),
        ],
        [
            Paragraph(f"CUIT: {EMPRESA['cuit']}  |  IB: {EMPRESA['ib']}", s_subtitulo),
            Paragraph("", s_normal),
            Paragraph(f"Inicio act.: {EMPRESA['inicio_act']}", s_normal),
        ],
    ]
    col_w = [ancho * 0.55, ancho * 0.15, ancho * 0.30]
    tabla_header = Table(header_data, colWidths=col_w)
    tabla_header.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), GRIS),
        ("BOX",          (1, 0), (1, -1), 2, AZUL),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",    (0, -1), (-1, -1), 1, AZUL),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(tabla_header)
    story.append(Spacer(1, 6*mm))

    # ── Datos del cliente ─────────────────────────────────────────────────────
    ciudad_prov = f"{cliente.get('ciudad') or ''}, {cliente.get('provincia') or ''}".strip(", ")
    cliente_data = [
        [Paragraph("<b>CLIENTE</b>", s_bold), "", ""],
        [Paragraph(f"Razón social:", s_bold),
         Paragraph(cliente["nombre"], s_normal),
         Paragraph(f"Tipo IVA: {cliente.get('tipo_iva') or ''}", s_normal)],
        [Paragraph("Dirección:", s_bold),
         Paragraph(f"{cliente.get('direccion') or ''}  –  {ciudad_prov}", s_normal),
         Paragraph(f"CUIT: {cliente.get('cuit') or 'Sin dato'}", s_normal)],
        [Paragraph("Teléfono:", s_bold),
         Paragraph(cliente.get("telefono") or "—", s_normal),
         Paragraph("", s_normal)],
    ]
    tabla_cli = Table(cliente_data, colWidths=[ancho*0.18, ancho*0.55, ancho*0.27])
    tabla_cli.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 1, AZUL),
        ("BACKGROUND",  (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("SPAN",        (0, 0), (-1, 0)),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tabla_cli)
    story.append(Spacer(1, 6*mm))

    # ── Detalle de ítems ──────────────────────────────────────────────────────
    if tipo == "A":
        det_headers = ["Descripción", "Cantidad", "Precio unit.", "Subtotal", "IVA 21%"]
        det_col_w   = [ancho*0.45, ancho*0.1, ancho*0.15, ancho*0.15, ancho*0.15]
    else:
        det_headers = ["Descripción", "Cantidad", "Precio unit.", "Subtotal"]
        det_col_w   = [ancho*0.50, ancho*0.1, ancho*0.20, ancho*0.20]

    det_data = [det_headers]
    for l in lineas:
        fila = [
            Paragraph(l["descripcion"], s_normal),
            Paragraph(f"{l['cantidad']:g}", s_right),
            Paragraph(pesos(l["precio_unit"]), s_right),
            Paragraph(pesos(l["subtotal"]), s_right),
        ]
        if tipo == "A":
            fila.append(Paragraph(pesos(l["iva"]), s_right))
        det_data.append(fila)

    tabla_det = Table(det_data, colWidths=det_col_w, repeatRows=1)
    tabla_det.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN",        (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN",        (0, 0), (0, -1), "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (0, -1), 5),
    ]))
    story.append(tabla_det)
    story.append(Spacer(1, 6*mm))

    # ── Totales ───────────────────────────────────────────────────────────────
    if tipo == "A":
        totales_data = [
            ["", "Subtotal neto:",   pesos(subtotal_total)],
            ["", f"IVA (21%):",      pesos(iva_total)],
            ["", "TOTAL A PAGAR:",   pesos(total_final)],
        ]
    else:
        totales_data = [
            ["", "TOTAL A PAGAR:",   pesos(total_final)],
        ]

    tabla_tot = Table(totales_data, colWidths=[ancho*0.55, ancho*0.25, ancho*0.20])
    tot_style = [
        ("ALIGN",       (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME",    (1, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LINEABOVE",   (1, -1), (-1, -1), 1.5, AZUL),
        ("TEXTCOLOR",   (1, -1), (-1, -1), AZUL),
        ("FONTSIZE",    (1, -1), (-1, -1), 12),
    ]
    tabla_tot.setStyle(TableStyle(tot_style))
    story.append(tabla_tot)

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Gracias por su preferencia  ·  Elektra S.R.L.  ·  Santa Fe, Argentina",
        estilo("pie", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    print(f"Factura generada: {ruta}")
    return ruta

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de facturas PDF")
    parser.add_argument("--cliente", type=int, help="Código de cliente")
    parser.add_argument("--items",   type=str, help='Items: "RADAR:1,VIBRO:2"')
    parser.add_argument("--numero",  type=str, default=None)
    parser.add_argument("--demo",    action="store_true", help="Generar factura de demo")
    args = parser.parse_args()

    if args.demo:
        # Tomar el primer cliente con CUIT cargado
        with engine.connect() as conn:
            demo_cli = conn.execute(text(
                "SELECT codigo FROM clientes WHERE cuit IS NOT NULL LIMIT 1"
            )).scalar()
        generar_factura(
            cliente_codigo=demo_cli,
            items_raw=["RADAR:1", "VIBRO:2", "DANCER FLOWER:3"],
            numero="0001-00000001",
        )
    elif args.cliente and args.items:
        items = [i.strip() for i in args.items.split(",")]
        generar_factura(args.cliente, items, args.numero)
    else:
        parser.print_help()

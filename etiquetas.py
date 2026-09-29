import io
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

def label_pdf(rows):
    width, height = 100*mm, 100*mm
    out=io.BytesIO()
    pdf=canvas.Canvas(out,pagesize=(width,height))
    for row in rows:
        qr=f"EXP|{row['pedido']}|{row['volume']}"
        items=row['codigos'].split('; ')
        pages=[]
        for start in range(0,len(items),3):
            lines=[]
            for item in items[start:start+3]:
                lines.extend(simpleSplit(item,'Helvetica',8,52*mm))
            pages.extend([lines[i:i+7] for i in range(0,len(lines),7)])
        for page, lines in enumerate(pages,1):
            y=height-8*mm
            def draw(value,size=9,bold=False,width_mm=88):
                nonlocal y
                font='Helvetica-Bold' if bold else 'Helvetica'
                pdf.setFont(font,size)
                for line in simpleSplit(str(value),font,size,width_mm*mm):
                    pdf.drawString(6*mm,y,line); y-=4*mm
            draw(f"Pedido: {row['pedido']}",12,True)
            draw(f"Volume: {row['volume']}/{row['total_volumes']}  |  {row['tipo']}")
            draw(f"OS / OC: {row.get('ordem_servico') or 'Não informada'}")
            draw(f"Cliente: {row.get('nome_cliente') or 'Não informado'}",8)
            weight=row.get('peso_bruto')
            draw('Peso bruto: '+(f'{weight:g} kg' if weight is not None else 'Não informado'),9,True)
            y=min(y-2*mm,53*mm)
            draw('Código / quantidade:',8,True)
            for line in lines: draw(line,8,width_mm=52)
            qr_image=QrCodeWidget(qr)
            x0,y0,x1,y1=qr_image.getBounds()
            drawing=Drawing(28*mm,28*mm,transform=[28*mm/(x1-x0),0,0,28*mm/(y1-y0),0,0])
            drawing.add(qr_image)
            renderPDF.draw(drawing,pdf,66*mm,18*mm)
            pdf.setFont('Helvetica',7)
            pdf.drawString(6*mm,9*mm,f'Etiqueta {page}/{len(pages)} do volume' if len(pages)>1 else 'Conferir volume antes da expedição')
            pdf.drawString(6*mm,4*mm,qr)
            pdf.showPage()
    pdf.save()
    return out.getvalue()

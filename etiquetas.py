"""Etiqueta horizontal Zebra: 140 x 50 mm, até três códigos por página."""
import io
from pathlib import Path
from decimal import Decimal
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ASSETS=Path(__file__).parent/'assets'
WIDTH,HEIGHT=140*mm,50*mm

def fonts():
    if 'LabelRegular' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('LabelRegular',str(ASSETS/'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('LabelBold',str(ASSETS/'DejaVuSans-Bold.ttf')))

def fit(text,font,width,size=9,min_size=5):
    while size>min_size and pdfmetrics.stringWidth(str(text),font,size)>width:
        size-=0.25
    if pdfmetrics.stringWidth(str(text),font,size)>width:
        raise ValueError('Texto muito longo para a etiqueta de 140 × 50 mm: '+str(text))
    return size

def label_pdf(rows):
    fonts()
    out=io.BytesIO()
    pdf=canvas.Canvas(out,pagesize=(WIDTH,HEIGHT))
    pdf.setTitle('Etiquetas Gree - 140 x 50 mm')
    for row in rows:
        qr=f"EXP|{row['pedido']}|{row['volume']}"
        items=[]
        for raw in row['codigos'].split(';'):
            code,sep,qty=raw.strip().rpartition(':')
            items.append((code.strip() if sep else raw.strip(),qty.strip() if sep else '-'))
        pages=[items[i:i+3] for i in range(0,len(items),3)] or [[]]
        for page, group in enumerate(pages,1):
            def txt(x,y,text,size=8,bold=False,width=100):
                font='LabelBold' if bold else 'LabelRegular'
                size=fit(text,font,width*mm,size)
                pdf.setFont(font,size);pdf.drawString(x*mm,y*mm,str(text))
            pdf.drawImage(str(ASSETS/'gree_logo.png'),3*mm,40*mm,width=10*mm,height=8*mm,preserveAspectRatio=True,anchor='c',mask='auto')
            txt(14,43,'GREE',13,True,22)
            txt(40,44,'ASSISTÊNCIA TÉCNICA',8,True,49)
            txt(40,40,f"{row['tipo']} · {row['data_pedido'][8:10]}/{row['data_pedido'][5:7]}/{row['data_pedido'][:4]}",6.5,False,49)
            txt(92,43,row['pedido'],12,True,45)
            pdf.setLineWidth(.4);pdf.line(3*mm,38.5*mm,137*mm,38.5*mm)
            customer='Cliente: '+str(row.get('nome_cliente') or 'Não informado')
            client_size=7.5
            lines=simpleSplit(customer,'LabelRegular',client_size,100*mm)
            while len(lines)>2 and client_size>5:
                client_size-=.25;lines=simpleSplit(customer,'LabelRegular',client_size,100*mm)
            if len(lines)>2:raise ValueError('Nome do cliente muito longo para a etiqueta de 140 × 50 mm.')
            for i,line in enumerate(lines):txt(3,35-i*3,line,client_size,False,100)
            txt(3,28,f"OS/OC: {row.get('ordem_servico') or '-'}",7,True,43)
            txt(48,28,f"Volume: {row['volume']}/{row['total_volumes']}",8,True,28)
            weight=row.get('peso_bruto')
            weight_text=format(Decimal(str(weight)).normalize(),'f').replace('.',',')+' kg' if weight is not None else '-'
            txt(78,28,f'P. bruto: {weight_text}',7,True,26)
            pdf.line(3*mm,25.5*mm,103*mm,25.5*mm)
            txt(3,22.5,'CÓDIGO DA PEÇA',6.5,True,77)
            txt(85,22.5,'QUANT.',6.5,True,18)
            for i,(code,qty) in enumerate(group):
                y=18-i*5
                txt(3,y,code,8,True,78)
                txt(85,y,qty,9,True,18)
            txt(3,3.5,f'Etiqueta {page}/{len(pages)} do volume · {qr}',6,False,100)
            widget=QrCodeWidget(qr,barLevel='M')
            x0,y0,x1,y1=widget.getBounds()
            drawing=Drawing(31*mm,31*mm,transform=[31*mm/(x1-x0),0,0,31*mm/(y1-y0),0,0])
            drawing.add(widget);renderPDF.draw(drawing,pdf,106*mm,6*mm)
            txt(109,3.5,'LER PARA EXPEDIR',5.5,True,27)
            pdf.showPage()
    pdf.save()
    return out.getvalue()

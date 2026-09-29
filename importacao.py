"""Leitura da base operacional e do modelo simples, sem dependência da interface."""
import io
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import pandas as pd

COLUMNS = ['pedido', 'volume', 'total_volumes', 'tipo', 'codigos', 'data_pedido']

def header(value):
    value = unicodedata.normalize('NFKD', str(value).replace('º', '').replace('°', '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', value)

def text(value):
    if pd.isna(value): return ''
    value = str(value).strip()
    if value in ('-', 'nan', 'None', 'NaT'): return ''
    return value

def number(value):
    raw = text(value).replace(',', '.')
    num = Decimal(raw)
    if not num.is_finite() or num <= 0 or num != num.to_integral_value():
        raise ValueError('Volume deve ser um inteiro positivo')
    return int(num)

def date_value(value):
    if isinstance(value, (datetime, date)): return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    raw = text(value)
    if not raw: raise ValueError('DATA PEDIDO ausente')
    if re.match(r'^\d{4}-\d{2}-\d{2}', raw): return pd.to_datetime(raw).date().isoformat()
    return pd.to_datetime(raw, dayfirst=True, errors='raise').date().isoformat()

def read_file(content, filename, sheet=None):
    source = io.BytesIO(content)
    if filename.lower().endswith('.csv'):
        try: return pd.read_csv(source, dtype=str, sep=None, engine='python')
        except UnicodeDecodeError:
            source.seek(0)
            return pd.read_csv(source, dtype=str, sep=None, engine='python', encoding='cp1252')
    return pd.read_excel(source, sheet_name=sheet if sheet is not None else 0, dtype=object)

def parse_import(content, filename, sheet=None):
    frame = read_file(content, filename, sheet)
    names = {header(c): c for c in frame.columns}
    simple = all(header(c) in names for c in COLUMNS)
    item_rows = simple and 'quantidade' in names
    operational = all(c in names for c in ['npedido', 'volume', 'qtd']) and any(c in names for c in ['codigodapecas','codigodopecas'])
    if not simple and not operational:
        raise ValueError('Formato não reconhecido. Use a base com Nº PEDIDO, VOLUME, QTD e CODIGO DA PEÇAS ou o modelo simples do app.')
    result = []
    issues = []
    groups = defaultdict(list)
    invalid = set()
    last_volume = {}
    order_meta = defaultdict(lambda: {'tipo': set(), 'datas': set(), 'ordem_servico': set(), 'nome_cliente': set()})
    weights = {}
    def issue(line, pedido, message):
        issues.append({'linha': line, 'pedido': pedido, 'motivo': message})
        if pedido: invalid.add(pedido)
    def get(row, key): return row.get(names.get(key), '')
    def alias(row, *keys):
        return next((get(row, key) for key in keys if text(get(row, key))), '')
    for line, row in enumerate(frame.to_dict('records'), 2):
        pedido = text(get(row, 'pedido' if simple else 'npedido'))
        code = text(get(row, 'codigos' if simple else 'codigodapecas'))
        if operational and not code: code = text(get(row, 'codigodopecas'))
        if not pedido:
            if any(text(v) for v in row.values()): issue(line, '', 'Linha preenchida sem número do pedido; linha não importada')
            continue
        try:
            if '|' in pedido: raise ValueError('Pedido não pode conter | (reservado para QR)')
            tipo = text(get(row, 'tipo')).title()
            if tipo:
                if tipo not in ('Garantia','Venda'): raise ValueError(f'TIPO não suportado: {tipo}. Informe Garantia ou Venda')
                order_meta[pedido]['tipo'].add(tipo)
            for field, keys in [('ordem_servico', ('ordemdeservico','ordemservico','osoc')), ('nome_cliente', ('nomedocliente','nomecliente','credenciado'))]:
                value = text(alias(row, *keys))
                if value: order_meta[pedido][field].add(value)
            raw_date = get(row, 'datapedido')
            if text(raw_date): order_meta[pedido]['datas'].add(date_value(raw_date))
            raw_volume = get(row, 'volume')
            if text(raw_volume):
                volume = number(raw_volume)
                last_volume[pedido] = volume
            elif operational and pedido in last_volume:
                volume = last_volume[pedido]
            else: raise ValueError('VOLUME vazio sem caixa anterior identificada nesse pedido')
            if not code: raise ValueError('Código da peça ausente')
            weight = text(alias(row, 'pesobruto', 'pesobrutokg')).replace(',', '.')
            if weight and (pedido, volume) not in weights:
                try: weight_value = Decimal(weight)
                except InvalidOperation: raise ValueError('Peso bruto inválido; informe kg')
                if not weight_value.is_finite() or weight_value <= 0: raise ValueError('Peso bruto deve ser positivo')
                weights[(pedido,volume)] = weight_value
            if item_rows:
                try: quantity = Decimal(text(get(row, 'quantidade')).replace(',', '.'))
                except InvalidOperation: raise ValueError('Quantidade ausente ou inválida')
                if not quantity.is_finite() or quantity <= 0: raise ValueError('Quantidade deve ser positiva')
            if simple:
                total = number(get(row, 'totalvolumes'))
                if volume > total: raise ValueError('Volume maior que total_volumes')
                groups[pedido].append({'pedido':pedido,'volume':volume,'total_volumes':total,'codigos':code,'codigo':code,'qtd': quantity if item_rows else None,'linha':line})
            else:
                qty = text(get(row, 'qtd')).replace(',', '.')
                try: quantity = Decimal(qty)
                except InvalidOperation: raise ValueError('QTD ausente ou inválida')
                if not quantity.is_finite() or quantity <= 0: raise ValueError('QTD deve ser positiva')
                groups[pedido].append({'pedido':pedido,'volume':volume,'codigo':code,'qtd':quantity,'linha':line})
        except Exception as exc: issue(line, pedido, str(exc))
    for pedido, parts in groups.items():
        if pedido in invalid: continue
        meta = order_meta[pedido]
        if len(meta['tipo']) != 1:
            issue(parts[0]['linha'],pedido,'TIPO ausente ou divergente no pedido'); continue
        if not meta['datas']:
            issue(parts[0]['linha'],pedido,'DATA PEDIDO ausente no pedido'); continue
        if len(meta['datas']) != 1:
            issue(parts[0]['linha'],pedido,'DATA PEDIDO divergente no pedido'); continue
        volumes = {r['volume'] for r in parts}
        total = max(volumes) if operational else parts[0]['total_volumes']
        if simple and ((not item_rows and len(parts) != len(volumes)) or len({r['total_volumes'] for r in parts}) != 1):
            issue(parts[0]['linha'],pedido,'Volume duplicado ou total_volumes divergente'); continue
        if volumes != set(range(1,total+1)):
            missing = sorted(set(range(1,total+1))-volumes)
            issue(parts[0]['linha'],pedido,'Caixas ausentes na sequência: '+', '.join(map(str,missing[:15]))); continue
        conflicts = [key for key in ('ordem_servico','nome_cliente') if len(meta[key]) > 1]
        if conflicts:
            issue(parts[0]['linha'],pedido,'Dados divergentes no pedido: '+', '.join(conflicts)); continue
        for volume in sorted(volumes):
            selected = [r for r in parts if r['volume']==volume]
            if simple and not item_rows: codes = selected[0]['codigos']
            else:
                quantities = defaultdict(Decimal)
                for item in selected: quantities[item['codigo']] += item['qtd']
                codes = '; '.join(f'{code}: {format(qty.normalize(), "f")}' for code,qty in quantities.items())
            result.append(dict(pedido=pedido, volume=volume,total_volumes=total,tipo=next(iter(meta['tipo'])),codigos=codes,data_pedido=next(iter(meta['datas'])),ordem_servico=next(iter(meta['ordem_servico']),''),nome_cliente=next(iter(meta['nome_cliente']),''),peso_bruto=float(weights[(pedido,volume)]) if (pedido,volume) in weights else None))
    return result, issues, 'Base operacional' if operational else ('Uma linha por código' if item_rows else 'Modelo simples')

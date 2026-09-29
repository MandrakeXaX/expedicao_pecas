import io
from pathlib import Path
import re
import hmac
from datetime import date, datetime
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from supabase import create_client
from importacao import parse_import
from etiquetas import label_pdf
from operacoes import dispatch, ExpedicaoNaoConfirmada

st.set_page_config(page_title="Controle de expedição", page_icon="📦", layout="wide")
TZ = ZoneInfo("America/Manaus")
COLUMNS = ["pedido", "volume", "total_volumes", "tipo", "codigos", "data_pedido"]


def config():
    try:
        needed = [k for k in ("SUPABASE_URL", "APP_PASSWORD") if not st.secrets.get(k)]
        if not (st.secrets.get("SUPABASE_SECRET_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")):
            needed.append("SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY)")
    except StreamlitSecretNotFoundError:
        st.title("Configurar acesso à nuvem")
        st.warning("O arquivo .streamlit/secrets.toml ainda não foi criado.")
        st.write("Na pasta do app, copie o arquivo de exemplo e preencha as credenciais do seu projeto Supabase e uma senha de acesso.")
        st.code('Copy-Item .\\.streamlit\\secrets.toml.example .\\.streamlit\\secrets.toml', language="powershell")
        st.info("Use a pasta .streamlit (com ponto no início). Consulte o README e reinicie o app depois de salvar.")
        st.stop()
    if needed:
        st.error("Configure os segredos: " + ", ".join(needed))
        st.stop()


@st.cache_resource
def db():
    key = st.secrets.get("SUPABASE_SECRET_KEY") or st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(st.secrets["SUPABASE_URL"], key)


def login():
    if st.session_state.get("authenticated"):
        return
    with st.form("login"):
        password = st.text_input("Senha de acesso", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        if hmac.compare_digest(password, st.secrets["APP_PASSWORD"]):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()


def all_rows():
    rows = []
    offset = 0
    while True:
        batch = db().table("volumes").select("*").order("id").range(offset, offset + 999).execute().data
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def template():
    return (Path(__file__).parent / "modelo_importacao.xlsx").read_bytes()


@st.cache_data(show_spinner=False)
def normalized_import(content, filename, sheet):
    return parse_import(content, filename, sheet)


def qr_text(row):
    return f"EXP|{row['pedido']}|{row['volume']}"




def decode(upload):
    image = cv2.imdecode(np.frombuffer(upload.getvalue(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return ""
    return cv2.QRCodeDetector().detectAndDecode(image)[0]


def parsed_qr(value):
    match = re.fullmatch(r"EXP\|([^|]+)\|([1-9][0-9]*)", value.strip())
    return (match.group(1), int(match.group(2))) if match else None


def export(rows):
    data = pd.DataFrame(rows)
    if data.empty:
        data = pd.DataFrame(columns=COLUMNS + ["status", "expedido_em", "operador", "foto_path", "dias_aguardando", "ordem_servico", "nome_cliente", "peso_bruto"])
    else:
        data["dias_aguardando"] = data.apply(lambda r: max(0, ((datetime.fromisoformat(r["expedido_em"].replace("Z", "+00:00")).astimezone(TZ).date() if r["expedido_em"] else datetime.now(TZ).date()) - date.fromisoformat(r["data_pedido"])).days), axis=1)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Expedições")
    return out.getvalue(), data


config()
login()
st.title("📦 Controle de expedição")
st.sidebar.caption("Desenvolvido por: Marco Antonio")
if st.sidebar.button("Atualizar dados", use_container_width=True):
    st.rerun()
if st.sidebar.button("Sair"):
    st.session_state.authenticated = False
    st.rerun()
page = st.sidebar.radio("Menu", ["Painel", "Importar pedidos", "Etiquetas", "Executar expedição", "Registros"])
try:
    rows = all_rows()
    st.sidebar.caption("Dados consultados: " + datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S"))
except Exception as exc:
    st.error(f"Falha ao acessar o banco. Confira a configuração e execute schema.sql. Detalhe: {exc}")
    st.stop()

if page == "Importar pedidos":
    st.subheader("Importar pedidos por volume")
    st.write("Importe sua base com Nº PEDIDO, VOLUME, CODIGO DA PEÇAS e QTD, ou o modelo simples. No novo modelo, repita pedido e volume em cada linha, informe um código e sua quantidade. O peso bruto é o peso total da caixa em kg. O app usa o primeiro peso preenchido de cada volume, ignorando campos vazios e valores seguintes.")
    st.download_button("Baixar modelo Excel", template(), "modelo_importacao.xlsx")
    file = st.file_uploader("Planilha CSV ou Excel", type=["csv", "xlsx"])
    if file:
        try:
            sheet = None
            if file.name.lower().endswith('.xlsx'):
                sheets = pd.ExcelFile(io.BytesIO(file.getvalue())).sheet_names
                sheet = st.selectbox("Aba da planilha", sheets)
            incoming, issues, format_name = normalized_import(file.getvalue(), file.name, sheet)
            missing_weight = sum(r.get('peso_bruto') is None for r in incoming)
            if missing_weight:
                st.warning(f"{missing_weight} volume(s) sem peso bruto. A etiqueta indicará peso não informado; preencha peso_bruto para imprimir o peso.")
            existing = {(r["pedido"], r["volume"]): r for r in rows}
            shipped_orders = {r["pedido"] for r in rows if r["status"] == "Expedido"}
            preserved = [r for r in incoming if r["pedido"] in shipped_orders]
            incoming = [r for r in incoming if r["pedido"] not in shipped_orders]
            st.caption(f"{format_name} · {len(set(r['pedido'] for r in incoming))} pedidos válidos · {len(incoming)} volumes disponíveis para importação")
            if preserved:
                st.info(f"{len(set(r['pedido'] for r in preserved))} pedido(s) com expedição já registrada serão preservados e não atualizados.")
            if issues:
                st.warning(f"{len(issues)} inconsistências encontradas. Pedidos com inconsistências foram retirados da importação para evitar etiquetas incompletas.")
                with st.expander("Ver linhas e pedidos que precisam de correção", expanded=True):
                    errors = pd.DataFrame(issues)
                    st.dataframe(errors, hide_index=True)
                    st.download_button("Baixar relatório de inconsistências", errors.to_csv(index=False, sep=';').encode('utf-8-sig'), "inconsistencias_importacao.csv", mime='text/csv')
            st.dataframe(pd.DataFrame(incoming), hide_index=True)
            accepted = st.checkbox("Importar somente os pedidos válidos exibidos acima", value=False) if issues else True
            if incoming and st.button("Importar / atualizar volumes pendentes", type="primary", disabled=not accepted):
                db().table("volumes").upsert(incoming, on_conflict="pedido,volume").execute()
                st.success(f"{len(incoming)} volume(s) importado(s).")
            elif not incoming:
                st.info("Nenhum pedido disponível para importar. Consulte as inconsistências ou os registros já expedidos.")
        except Exception as exc:
            st.error(str(exc))

elif page == "Etiquetas":
    st.subheader("Gerar etiquetas")
    orders = sorted(set(r["pedido"] for r in rows))
    if orders:
        order = st.selectbox("Número do pedido", orders)
        selected = sorted((r for r in rows if r["pedido"] == order), key=lambda r: r["volume"])
        for row in selected:
            st.write(f"Volume {row['volume']}/{row['total_volumes']} · {row['codigos']}")
        if st.button("Gerar etiquetas", type="primary"):
            st.session_state.label_pdf = label_pdf(selected)
            st.session_state.label_order = order
        if st.session_state.get("label_order") == order:
            st.download_button("Baixar etiquetas em PDF", st.session_state.label_pdf, f"etiquetas_{order}.pdf", mime="application/pdf")
    else:
        st.info("Importe uma planilha primeiro.")

elif page == "Executar expedição":
    st.subheader("Ler QR e expedir volume")
    if st.session_state.get("dispatch_message"):
        st.success(st.session_state.pop("dispatch_message"))
    st.write("Use a câmera para fotografar o QR da etiqueta ou digite o conteúdo impresso abaixo dele. A foto da embalagem é obrigatória.")
    mode = st.radio("Como ler a etiqueta?", ["Câmera", "Enviar foto do QR", "Leitor / digitar"], horizontal=True)
    scan = st.camera_input("Ler QR da etiqueta", key="scan") if mode == "Câmera" else (st.file_uploader("Foto do QR", type=["jpg", "jpeg", "png"], key="qr_file") if mode == "Enviar foto do QR" else None)
    decoded = decode(scan) if scan else ""
    if scan and not decoded:
        st.warning("QR não identificado. Aproxime a câmera, ilumine a etiqueta e tente novamente.")
    value = st.text_input("Código da etiqueta", value=decoded, placeholder="EXP|PG123|1")
    key = parsed_qr(value)
    if value and not key:
        st.error("Código inválido. Use o QR gerado pelo app ou o texto EXP|pedido|volume.")
    found = next((r for r in rows if key and (r["pedido"], r["volume"]) == key), None)
    if key and not found:
        st.error("Pedido/volume não localizado na base.")
    if found:
        st.info(f"Pedido {found['pedido']} · volume {found['volume']}/{found['total_volumes']} · {found['tipo']} · {found['codigos']} · {found['status']}")
        if found["status"] == "Pendente":
            operator = st.text_input("Nome do responsável")
            photo_mode = st.radio("Registrar foto do volume", ["Tirar foto", "Enviar foto"], horizontal=True)
            photo = st.camera_input("Foto obrigatória do volume antes da expedição", key=f"photo_{key}") if photo_mode == "Tirar foto" else st.file_uploader("Foto do volume (obrigatória)", type=["jpg", "jpeg", "png"], key=f"photo_file_{key}")
            if st.button("Confirmar expedição", type="primary"):
                if not operator.strip() or not photo:
                    st.error("Informe o responsável e tire a foto do volume.")
                elif len(photo.getvalue()) > 10 * 1024 * 1024:
                    st.error("Foto acima de 10 MB.")
                else:
                    try:
                        with st.spinner("Salvando foto e confirmando expedição…"):
                            dispatch(db(), found["pedido"], found["volume"], operator, photo.getvalue())
                        st.session_state.dispatch_message = f"Pedido {found['pedido']} · volume {found['volume']}: expedição registrada com foto."
                        st.rerun()
                    except (ExpedicaoNaoConfirmada, ValueError) as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Falha ao enviar a foto. Verifique a conexão e o bucket fotos-expedicao no Supabase.")

else:
    for row in rows:
        for field in ('ordem_servico','nome_cliente','peso_bruto'):
            row.setdefault(field, None)
    blob, data = export(rows)
    pending = data[data["status"] == "Pendente"]
    sent = data[data["status"] == "Expedido"]
    if page == "Painel":
        a, b, c = st.columns(3)
        a.metric("Volumes pendentes", len(pending))
        b.metric("Volumes expedidos", len(sent))
        c.metric("Pedidos com pendências", pending["pedido"].nunique())
        st.subheader("Aguardando expedição")
        query = st.text_input("Buscar pedido, cliente ou OS/OC", key="pending_search")
        if query.strip():
            mask = pending[['pedido','nome_cliente','ordem_servico']].fillna('').astype(str).apply(lambda col: col.str.contains(query.strip(),case=False,regex=False)).any(axis=1)
            pending = pending[mask]
        st.download_button("Exportar pendentes exibidos", export(pending.to_dict('records'))[0], "pendentes_expedicao.xlsx")
        st.dataframe(pending[["pedido", "volume", "total_volumes", "tipo", "codigos", "ordem_servico", "nome_cliente", "peso_bruto", "data_pedido", "dias_aguardando"]].sort_values("dias_aguardando", ascending=False), hide_index=True)
    else:
        status = st.selectbox("Filtrar", ["Todos", "Pendente", "Expedido"])
        view = data if status == "Todos" else data[data["status"] == status]
        query = st.text_input("Buscar pedido, cliente ou OS/OC", key="records_search")
        if query.strip():
            mask = view[['pedido','nome_cliente','ordem_servico']].fillna('').astype(str).apply(lambda col: col.str.contains(query.strip(),case=False,regex=False)).any(axis=1)
            view = view[mask]
        st.dataframe(view.drop(columns=["foto_path", "id"], errors="ignore"), hide_index=True)
        st.download_button("Exportar registros filtrados", export(view.to_dict('records'))[0], "expedicoes_filtradas.xlsx")
        st.download_button("Exportar todos os registros (Excel)", blob, "registros_expedicao.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if not sent.empty:
            options = {f"{r['pedido']} · volume {r['volume']} · {r['expedido_em']}": r for r in rows if r["status"] == "Expedido"}
            chosen = st.selectbox("Consultar foto", list(options))
            if st.button("Abrir foto"):
                try:
                    signed = db().storage.from_("fotos-expedicao").create_signed_url(options[chosen]["foto_path"], 60)
                    st.image(signed["signedURL"], caption=chosen)
                except Exception as exc:
                    st.error(f"Falha ao abrir foto: {exc}")

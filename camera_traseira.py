"""Componente local de captura, priorizando a câmera traseira."""
import base64
import io
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

_capture=components.declare_component('camera_traseira',path=str(Path(__file__).parent/'camera_component'))

def rear_camera(label,key):
    value=_capture(label=label,key=key,default=None)
    if not value or not isinstance(value,dict):return None
    raw=value.get('data_url','')
    if not raw.startswith('data:image/jpeg;base64,'):return None
    try:
        content=base64.b64decode(raw.split(',',1)[1],validate=True)
    except Exception:
        st.error('Falha na captura. Tire a foto novamente.');return None
    if len(content)>10*1024*1024:
        st.error('A foto deve ter até 10 MB.');return None
    return io.BytesIO(content)

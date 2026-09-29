"""Operações de expedição com persistência de foto em bucket privado."""
import io
import uuid
from PIL import Image, ImageOps

class ExpedicaoNaoConfirmada(Exception):
    pass


def photo_jpeg(content):
    if len(content) > 10*1024*1024:
        raise ValueError('A foto deve ter até 10 MB.')
    try:
        image=Image.open(io.BytesIO(content))
        image=ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((2400,2400))
        out=io.BytesIO()
        image.save(out,format='JPEG',quality=90)
        return out.getvalue()
    except Exception as exc:
        raise ValueError('A foto não é um arquivo JPEG ou PNG válido.') from exc


def dispatch(client, pedido, volume, operator, photo):
    if not operator.strip(): raise ValueError('Informe o responsável.')
    content=photo_jpeg(photo)
    path=f'{uuid.uuid4().hex}.jpg'
    client.storage.from_('fotos-expedicao').upload(path, content, {'content-type':'image/jpeg'})
    try:
        client.rpc('registrar_expedicao',{'p_pedido':pedido,'p_volume':volume,'p_foto_path':path,'p_operador':operator.strip()}).execute()
    except Exception as exc:
        # Uma falha na resposta pode ocorrer após o banco já ter confirmado a operação.
        # Preserve a foto e consulte o registro antes de permitir nova tentativa.
        try:
            rows=client.table('volumes').select('status,foto_path').eq('pedido',pedido).eq('volume',volume).execute().data
        except Exception:
            raise ExpedicaoNaoConfirmada('A conexão caiu durante a confirmação. A foto foi preservada. Atualize os dados e consulte este volume antes de tentar novamente.') from exc
        if rows and rows[0].get('status')=='Expedido' and rows[0].get('foto_path')==path:
            return path
        if rows and rows[0].get('status')=='Expedido':
            raise ExpedicaoNaoConfirmada('Este volume já foi expedido em outra operação. Atualize os dados para consultar o registro.') from exc
        raise ExpedicaoNaoConfirmada('Não foi possível confirmar a expedição. A foto enviada foi preservada. Atualize os dados e confira o volume antes de tentar novamente.') from exc
    return path

(() => {
  const $ = id => document.getElementById(id);
  let stream = null, initialized = false, requestId = 0;
  function send(type, fields = {}) {
    window.parent.postMessage({isStreamlitMessage: true, type, ...fields}, '*');
  }
  function resize() { send('streamlit:setFrameHeight', {height: document.body.scrollHeight + 8}); }
  function status(text) { $('status').textContent = text; resize(); }
  function stop() {
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    $('video').srcObject = null;
    $('video').hidden = true;
    $('capture').disabled = true;
  }
  async function cameras() {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput');
    const active = stream?.getVideoTracks()[0]?.getSettings().deviceId;
    $('devices').replaceChildren();
    devices.forEach((d, i) => {
      const opt = document.createElement('option');
      opt.value = d.deviceId; opt.textContent = d.label || `Câmera ${i + 1}`;
      opt.selected = d.deviceId === active; $('devices').appendChild(opt);
    });
    $('devices').hidden = devices.length < 2;
    resize();
  }
  async function start(deviceId) {
    const thisRequest = ++requestId;
    stop(); $('preview').hidden = true;
    status('Abrindo câmera…');
    if (!navigator.mediaDevices?.getUserMedia) {
      status('Câmera indisponível no navegador. Use HTTPS e permita a câmera, ou escolha “Tirar foto pelo celular”.'); return;
    }
    try {
      const constraints = deviceId ? {deviceId: {exact: deviceId}} : {facingMode: {ideal: 'environment'}};
      const next = await navigator.mediaDevices.getUserMedia({audio: false, video: {...constraints, width: {ideal: 1600}, height: {ideal: 1200}}});
      if (thisRequest !== requestId) { next.getTracks().forEach(t => t.stop()); return; }
      stream = next; $('video').srcObject = next; $('video').hidden = false;
      await $('video').play(); $('capture').disabled = false;
      const facing = next.getVideoTracks()[0].getSettings().facingMode;
      status(facing === 'environment' ? 'Câmera traseira selecionada. Posicione e capture a foto.' : 'Câmera aberta. Se necessário, escolha outra câmera na lista.');
      await cameras();
    } catch (error) {
      if (thisRequest !== requestId) return;
      stop();
      status(error.name === 'NotAllowedError' ? 'Permita o acesso à câmera nas configurações do navegador, ou use “Tirar foto pelo celular”.' : 'Não foi possível abrir a câmera. Tente outra câmera ou “Tirar foto pelo celular”.');
    }
  }
  function publish(dataUrl) {
    stop(); $('preview').src = dataUrl; $('preview').hidden = false; $('clear').hidden = false;
    status('Foto capturada. Para refazer, escolha Nova captura.');
    send('streamlit:setComponentValue', {value: {data_url: dataUrl, capture_id: Date.now()}, dataType: 'json'});
    resize();
  }
  $('start').onclick = () => start();
  $('capture').onclick = () => {
    const video = $('video');
    if (!video.videoWidth || !video.videoHeight) {status('Aguarde a câmera carregar.');return;}
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 2400 / Math.max(video.videoWidth,video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
    publish(canvas.toDataURL('image/jpeg',.92));
  };
  $('clear').onclick = () => {
    $('preview').hidden = true; $('clear').hidden = true;
    send('streamlit:setComponentValue', {value: null,dataType: 'json'});
    start();
  };
  $('devices').onchange = () => start($('devices').value);
  $('native').onclick = () => { ++requestId; stop(); $('file').value = ''; $('file').click(); };
  $('file').onchange = async () => {
    const file = $('file').files[0]; if (!file) return;
    const url = URL.createObjectURL(file);
    try {
      const image = new Image(); image.src = url; await image.decode();
      const scale = Math.min(1,2400/Math.max(image.naturalWidth,image.naturalHeight));
      const canvas = document.createElement('canvas'); canvas.width = Math.round(image.naturalWidth*scale);canvas.height = Math.round(image.naturalHeight*scale);
      canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);publish(canvas.toDataURL('image/jpeg',.92));
    } catch (_) {status('Não foi possível ler a foto. Escolha JPEG ou PNG.');}
    finally {URL.revokeObjectURL(url);}
  };
  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.data?.type !== 'streamlit:render') return;
    $('label').textContent = event.data.args?.label || 'Câmera';
    if (!initialized) { initialized = true; start(); }
    resize();
  });
  window.addEventListener('pagehide', () => {++requestId;stop();});
  document.addEventListener('visibilitychange', () => {if(document.hidden){++requestId;stop();}});
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(resize).observe(document.body);
  send('streamlit:componentReady', {apiVersion: 1});
  resize();
})();

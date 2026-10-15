let pywebviewReady = false;

function waitForApi() {
  return new Promise(res => {
    const t = setInterval(() => {
      if (window.pywebview && window.pywebview.api) {
        clearInterval(t); pywebviewReady = true; res();
      }
    }, 50);
  });
}

window.onLog = (msg) => {
  const log = document.getElementById('log');
  const line = document.createElement('div');
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
  if (log.children.length > 200) log.removeChild(log.firstChild);
};

window.onClap = (n) => {
  document.body.style.transition = 'background .1s';
  document.body.style.background = '#1e2340';
  setTimeout(() => document.body.style.background = 'var(--bg)', 120);
};

function bindSlider(id, labelId, fmt = v => v.toFixed(2)) {
  const el = document.getElementById(id);
  const label = document.getElementById(labelId);
  el.addEventListener('input', () => label.textContent = fmt(parseFloat(el.value)));
}
bindSlider('threshold', 'thVal');
bindSlider('claps_required', 'clapsVal', v => v.toFixed(0));
bindSlider('clap_window', 'winVal', v => v.toFixed(1));
bindSlider('cooldown', 'cdVal', v => v.toFixed(1));

let actionType = 'app';
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    actionType = tab.dataset.type;
    const inp = document.getElementById('action_target');
    inp.placeholder = actionType === 'url'
      ? 'https://youtube.com'
      : 'notepad.exe или C:/.../app.exe';
  });
});

function collect() {
  return {
    threshold: document.getElementById('threshold').value,
    claps_required: document.getElementById('claps_required').value,
    clap_window: document.getElementById('clap_window').value,
    cooldown: document.getElementById('cooldown').value,
    action_type: actionType,
    action_target: document.getElementById('action_target').value,
  };
}

function apply(cfg) {
  document.getElementById('threshold').value = cfg.threshold;
  document.getElementById('thVal').textContent = (+cfg.threshold).toFixed(2);
  document.getElementById('claps_required').value = cfg.claps_required;
  document.getElementById('clapsVal').textContent = cfg.claps_required;
  document.getElementById('clap_window').value = cfg.clap_window;
  document.getElementById('winVal').textContent = (+cfg.clap_window).toFixed(1);
  document.getElementById('cooldown').value = cfg.cooldown;
  document.getElementById('cdVal').textContent = (+cfg.cooldown).toFixed(1);
  document.getElementById('action_target').value = cfg.action_target;
  actionType = cfg.action_type;
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.dataset.type === actionType));
}

document.getElementById('startBtn').addEventListener('click', async () => {
  await pywebview.api.save_settings(collect());
  await pywebview.api.start();
  document.getElementById('status').textContent = 'on';
  document.getElementById('status').className = 'status on';
  document.getElementById('startBtn').disabled = true;
  document.getElementById('stopBtn').disabled = false;
});

document.getElementById('stopBtn').addEventListener('click', async () => {
  await pywebview.api.stop();
  document.getElementById('status').textContent = 'off';
  document.getElementById('status').className = 'status off';
  document.getElementById('startBtn').disabled = false;
  document.getElementById('stopBtn').disabled = true;
});

document.getElementById('calBtn').addEventListener('click', async () => {
  document.getElementById('calBtn').disabled = true;
  await pywebview.api.calibrate();
});

document.getElementById('testBtn').addEventListener('click', async () => {
  await pywebview.api.save_settings(collect());
  await pywebview.api.test_action();
});

document.getElementById('clearLog').addEventListener('click', () => {
  document.getElementById('log').innerHTML = '';
});

(async () => {
  await waitForApi();
  const cfg = await pywebview.api.get_config();
  apply(cfg);
  window.onLog('Готово к работе');
})();
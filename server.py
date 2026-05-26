import threading
import socket
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Global server state
_server_instance = None
_server_thread = None
_current_image_path = ""
_render_version = 0


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


def set_image_path(path):
    global _current_image_path, _render_version
    _current_image_path = path
    _render_version += 1


def get_viewer_html():
    """Three.js viewer with inverted drag and auto gyro permission popup."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<title>Gyro 360 Preview</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: #0a0a0a;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    touch-action: none; -webkit-user-select: none; user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  #canvas-container { width: 100%; height: 100%; position: relative; }
  canvas { display: block; }

  #hud {
    position: fixed; top: 0; left: 0; right: 0;
    display: flex; align-items: center; justify-content: space-between;
    padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
    background: linear-gradient(to bottom, rgba(0,0,0,0.65), transparent);
    z-index: 100; pointer-events: none;
  }
  #hud-title {
    color: rgba(255,255,255,0.9); font-size: 13px; font-weight: 600;
    letter-spacing: 0.05em; text-transform: uppercase;
  }
  #hud-status {
    display: flex; align-items: center; gap: 6px;
    color: rgba(255,255,255,0.6); font-size: 11px;
  }
  #status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #4ade80; animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

  #controls {
    position: fixed; bottom: 0; left: 0; right: 0;
    display: flex; align-items: center; justify-content: center; gap: 10px;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
    background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
    z-index: 100;
  }
  .ctrl-btn {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: white; border-radius: 20px;
    padding: 10px 18px; font-size: 12px; font-weight: 600;
    letter-spacing: 0.04em; cursor: pointer;
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    transition: all 0.2s; font-family: inherit; text-transform: uppercase;
    -webkit-tap-highlight-color: transparent;
  }
  .ctrl-btn:active { background: rgba(255,255,255,0.25); transform: scale(0.96); }
  .ctrl-btn.active {
    background: rgba(74,222,128,0.25);
    border-color: rgba(74,222,128,0.55);
    color: #4ade80;
  }
  .ctrl-btn.disabled { opacity: 0.4; pointer-events: none; }

  #gyro-popup {
    position: fixed; inset: 0;
    background: rgba(10, 10, 10, 0.92);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 24px; z-index: 400; padding: 40px;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } }

  #gyro-popup .phone-icon {
    width: 80px; height: 80px;
    border: 2px solid #4ade80; border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 40px;
    animation: phoneWiggle 2s ease-in-out infinite;
  }
  @keyframes phoneWiggle {
    0%, 100% { transform: rotate(-8deg); }
    50% { transform: rotate(8deg); }
  }
  #gyro-popup h2 {
    color: white; font-size: 22px; font-weight: 700;
    text-align: center; letter-spacing: -0.01em;
  }
  #gyro-popup p {
    color: rgba(255,255,255,0.65); font-size: 14px;
    text-align: center; max-width: 280px; line-height: 1.5;
  }
  #gyro-popup .actions {
    display: flex; flex-direction: column; gap: 10px;
    width: 100%; max-width: 260px; margin-top: 8px;
  }
  #gyro-popup .btn-primary {
    background: #4ade80; color: #0a0a0a; border: none;
    border-radius: 24px; padding: 16px 32px;
    font-size: 15px; font-weight: 700; cursor: pointer;
    letter-spacing: 0.03em; font-family: inherit;
    box-shadow: 0 8px 24px rgba(74, 222, 128, 0.3);
  }
  #gyro-popup .btn-primary:active { transform: scale(0.97); }
  #gyro-popup .btn-secondary {
    background: transparent; color: rgba(255,255,255,0.5);
    border: none; padding: 12px;
    font-size: 13px; cursor: pointer; font-family: inherit;
    text-decoration: underline; text-underline-offset: 3px;
  }

  #loading {
    position: fixed; inset: 0; background: #0a0a0a;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 16px; z-index: 300;
    transition: opacity 0.4s;
  }
  #loading-ring {
    width: 48px; height: 48px; border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #4ade80; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  #loading p { color: rgba(255,255,255,0.55); font-size: 13px; }

  #refresh-badge {
    position: fixed; top: calc(60px + env(safe-area-inset-top));
    left: 50%; transform: translateX(-50%);
    background: #4ade80; color: #0a0a0a; border-radius: 20px;
    padding: 6px 14px; font-size: 12px; font-weight: 700;
    z-index: 150; display: none; letter-spacing: 0.04em;
    animation: slideDown 0.3s ease;
  }
  @keyframes slideDown { from { opacity: 0; transform: translateX(-50%) translateY(-10px); } }

  #toast {
    position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.85); color: white; padding: 10px 18px;
    border-radius: 16px; font-size: 12px; z-index: 200;
    display: none; backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.15);
    max-width: 80vw; text-align: center;
  }
</style>
</head>
<body>
<div id="loading">
  <div id="loading-ring"></div>
  <p>Loading 360° Preview...</p>
</div>

<div id="gyro-popup" style="display:none;">
  <div class="phone-icon">📱</div>
  <h2>Enable Gyroscope</h2>
  <p>Allow motion access so you can look around by tilting your phone.</p>
  <div class="actions">
    <button class="btn-primary" id="popup-enable">Allow Motion Access</button>
    <button class="btn-secondary" id="popup-skip">Skip — use touch only</button>
  </div>
</div>

<div id="canvas-container"></div>

<div id="hud">
  <div id="hud-title">360° Preview</div>
  <div id="hud-status">
    <div id="status-dot"></div>
    <span id="status-text">Live</span>
  </div>
</div>

<div id="refresh-badge">New render available</div>
<div id="toast"></div>

<div id="controls">
  <button class="ctrl-btn" id="btn-gyro">Enable Gyro</button>
  <button class="ctrl-btn" id="btn-reset">Reset</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function() {
  'use strict';

  let renderer, camera, scene, sphere;
  let isGyroEnabled = false;
  let renderVersion = 0;

  let isDragging = false;
  let lastX = 0, lastY = 0;
  let pointerYaw = 0;
  let pointerPitch = 0;
  const PITCH_LIMIT = Math.PI * 0.49;
  const DRAG_SENSITIVITY = 0.005;

  let gyroYaw = 0, gyroPitch = 0;
  let gyroBaseAlpha = null, gyroBaseBeta = null;
  let smoothGyroYaw = 0, smoothGyroPitch = 0;
  const GYRO_SMOOTH = 0.15;

  function toast(msg, ms) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.style.display = 'block';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.style.display = 'none'; }, ms || 2500);
  }

  function maybeShowGyroPopup() {
    if (typeof DeviceOrientationEvent === 'undefined') return;
    if (typeof DeviceOrientationEvent.requestPermission !== 'function') return;
    if (sessionStorage.getItem('gyro_asked') === '1') return;

    document.getElementById('gyro-popup').style.display = 'flex';

    document.getElementById('popup-enable').addEventListener('click', async () => {
      try {
        const state = await DeviceOrientationEvent.requestPermission();
        sessionStorage.setItem('gyro_asked', '1');
        document.getElementById('gyro-popup').style.display = 'none';
        if (state === 'granted') {
          enableGyro();
        } else {
          toast('Gyroscope denied. You can still use touch.', 4000);
        }
      } catch (err) {
        sessionStorage.setItem('gyro_asked', '1');
        document.getElementById('gyro-popup').style.display = 'none';
        toast('Gyroscope error: ' + err.message, 4000);
      }
    });

    document.getElementById('popup-skip').addEventListener('click', () => {
      sessionStorage.setItem('gyro_asked', '1');
      document.getElementById('gyro-popup').style.display = 'none';
    });
  }

  function init() {
    const container = document.getElementById('canvas-container');

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 0, 0);

    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1);

    const texture = new THREE.TextureLoader().load(
      '/image?v=' + Date.now(),
      function(tex) {
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        hideSplash();
        maybeShowGyroPopup();
      },
      undefined,
      function() {
        hideSplash();
        maybeShowGyroPopup();
        toast('No render available yet — render in Blender first');
      }
    );

    const material = new THREE.MeshBasicMaterial({ map: texture });
    sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    window.addEventListener('resize', onResize);
    setupPointerControls();
    setupGyroButton();
    startPolling();
    animate();
  }

  function hideSplash() {
    const el = document.getElementById('loading');
    if (el) {
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }
  }

  function animate() {
    requestAnimationFrame(animate);

    if (isGyroEnabled) {
      smoothGyroYaw   += (gyroYaw   - smoothGyroYaw)   * GYRO_SMOOTH;
      smoothGyroPitch += (gyroPitch - smoothGyroPitch) * GYRO_SMOOTH;
    }

    const finalYaw   = isGyroEnabled ? (smoothGyroYaw + pointerYaw)   : pointerYaw;
    let   finalPitch = isGyroEnabled ? (smoothGyroPitch + pointerPitch) : pointerPitch;
    finalPitch = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, finalPitch));

    camera.rotation.order = 'YXZ';
    camera.rotation.y = finalYaw;
    camera.rotation.x = finalPitch;
    camera.rotation.z = 0;

    renderer.render(scene, camera);
  }

  function setupPointerControls() {
    const el = renderer.domElement;

    function start(x, y) {
      isDragging = true;
      lastX = x; lastY = y;
    }
    function move(x, y) {
      if (!isDragging) return;
      const dx = x - lastX;
      const dy = y - lastY;
      lastX = x; lastY = y;

      // INVERTED — image follows finger
      pointerYaw   += dx * DRAG_SENSITIVITY;
      pointerPitch += dy * DRAG_SENSITIVITY;
      pointerPitch = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, pointerPitch));
    }
    function end() { isDragging = false; }

    el.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        start(e.touches[0].clientX, e.touches[0].clientY);
        e.preventDefault();
      }
    }, { passive: false });

    el.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1) {
        move(e.touches[0].clientX, e.touches[0].clientY);
        e.preventDefault();
      }
    }, { passive: false });

    el.addEventListener('touchend', end);
    el.addEventListener('touchcancel', end);

    el.addEventListener('mousedown', (e) => start(e.clientX, e.clientY));
    window.addEventListener('mousemove', (e) => move(e.clientX, e.clientY));
    window.addEventListener('mouseup', end);
  }

  function setupGyroButton() {
    const btn = document.getElementById('btn-gyro');

    if (!('DeviceOrientationEvent' in window)) {
      btn.textContent = 'No Gyro';
      btn.classList.add('disabled');
      return;
    }

    btn.addEventListener('click', async () => {
      if (isGyroEnabled) {
        disableGyro();
        return;
      }
      if (typeof DeviceOrientationEvent.requestPermission === 'function') {
        try {
          const state = await DeviceOrientationEvent.requestPermission();
          if (state === 'granted') {
            enableGyro();
          } else {
            toast('Permission denied. Settings > Safari > Motion & Orientation Access', 5000);
          }
        } catch (err) {
          toast('Gyro error: ' + err.message, 4000);
        }
      } else {
        enableGyro();
      }
    });
  }

  function enableGyro() {
    isGyroEnabled = true;
    gyroBaseAlpha = null;
    gyroBaseBeta = null;
    window.addEventListener('deviceorientation', onDeviceOrientation, true);
    const btn = document.getElementById('btn-gyro');
    btn.textContent = 'Gyro ON';
    btn.classList.add('active');
    toast('Gyroscope enabled — tilt your phone');
  }

  function disableGyro() {
    isGyroEnabled = false;
    window.removeEventListener('deviceorientation', onDeviceOrientation, true);
    gyroBaseAlpha = null;
    gyroBaseBeta = null;
    const btn = document.getElementById('btn-gyro');
    btn.textContent = 'Enable Gyro';
    btn.classList.remove('active');
  }

  function onDeviceOrientation(e) {
    if (!isGyroEnabled || isDragging) return;
    if (e.alpha === null || e.alpha === undefined) return;

    const alpha = e.alpha || 0;
    const beta  = e.beta  || 0;
    const gamma = e.gamma || 0;

    if (gyroBaseAlpha === null) {
      gyroBaseAlpha = alpha;
      gyroBaseBeta = beta;
    }

    let dAlpha = alpha - gyroBaseAlpha;
    let dBeta  = beta  - gyroBaseBeta;
    if (dAlpha >  180) dAlpha -= 360;
    if (dAlpha < -180) dAlpha += 360;

    const isLandscape = window.innerWidth > window.innerHeight;
    if (isLandscape) {
      gyroYaw   = -dAlpha * (Math.PI / 180) * 0.85;
      gyroPitch =  gamma  * (Math.PI / 180) * 0.6;
    } else {
      gyroYaw   = -dAlpha * (Math.PI / 180) * 0.85;
      gyroPitch =  dBeta  * (Math.PI / 180) * 0.6;
    }
    gyroPitch = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, gyroPitch));
  }

  function startPolling() {
    setInterval(async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.version > renderVersion) {
          renderVersion = data.version;
          reloadTexture();
        }
      } catch (e) { /* server may be restarting */ }
    }, 2500);
  }

  function reloadTexture() {
    if (!sphere) return;
    const badge = document.getElementById('refresh-badge');
    badge.style.display = 'block';
    setTimeout(() => { badge.style.display = 'none'; }, 3000);

    const loader = new THREE.TextureLoader();
    loader.load('/image?v=' + Date.now(), function(tex) {
      tex.minFilter = THREE.LinearFilter;
      tex.magFilter = THREE.LinearFilter;
      const oldTex = sphere.material.map;
      sphere.material.map = tex;
      sphere.material.needsUpdate = true;
      if (oldTex) oldTex.dispose();
    });
  }

  document.getElementById('btn-reset').addEventListener('click', () => {
    pointerYaw = 0;
    pointerPitch = 0;
    gyroBaseAlpha = null;
    gyroBaseBeta = null;
    toast('View reset');
  });

  function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  window.addEventListener('load', init);
})();
</script>
</body>
</html>'''


class Handler360(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self._serve_viewer()
        elif path == '/image':
            self._serve_image()
        elif path == '/api/status':
            self._serve_status()
        elif path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_viewer(self):
        html = get_viewer_html().encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html)))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(html)

    def _serve_image(self):
        if not _current_image_path or not os.path.exists(_current_image_path):
            self.send_response(404)
            self.end_headers()
            return
        try:
            with open(_current_image_path, 'rb') as f:
                data = f.read()
            ext = os.path.splitext(_current_image_path)[1].lower()
            mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png'}.get(ext, 'image/jpeg')
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def _serve_status(self):
        status = json.dumps({'version': _render_version, 'has_image': bool(_current_image_path)})
        data = status.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)


def start_server(port=8765):
    global _server_instance, _server_thread

    if _server_instance is not None:
        return get_local_ip(), _server_instance.server_address[1]

    ip = get_local_ip()
    for attempt_port in range(port, port + 20):
        try:
            srv = HTTPServer(("0.0.0.0", attempt_port), Handler360)
            _server_instance = srv
            break
        except OSError:
            continue
    else:
        raise RuntimeError(f"Could not find a free port near {port}")

    _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
    _server_thread.start()
    return ip, _server_instance.server_address[1]


def stop_server():
    global _server_instance, _server_thread
    if _server_instance:
        _server_instance.shutdown()
        _server_instance = None
    _server_thread = None


def is_running():
    return _server_instance is not None

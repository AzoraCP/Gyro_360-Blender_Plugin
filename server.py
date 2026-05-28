import threading
import socket
import os
import ssl
import tempfile
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

_server_instance = None
_server_thread = None
_current_image_path = ""
_render_version = 0

# Self-signed TLS cert (valid 10 years). iOS requires HTTPS for
# DeviceOrientationEvent.requestPermission() to ever return 'granted'.
_CERT_PEM = """\
-----BEGIN CERTIFICATE-----
MIIDCzCCAfOgAwIBAgIUfjNIiNBEBu+3r3wmikFCt+LpEIkwDQYJKoZIhvcNAQEL
BQAwFTETMBEGA1UEAwwKMzYwcHJldmlldzAeFw0yNjA1MjgwODE1MzJaFw0zNjA1
MjUwODE1MzJaMBUxEzARBgNVBAMMCjM2MHByZXZpZXcwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQC3ZlTWeh2c0tPuQLgIdWZpzA/xFYN58aVqxlDf4g3X
wV3KArbn0tLISn/q5paS7oi32TZosOH1jbedBiyPKk/KzNTf3JgJGUg0PK7NOGWx
Oi9wpeebHoqCtn8UVIRkzAUbr3Dbiedn9KXqhTk3swihWg8suXBXRc4eqMvnGrJm
GMshdMLaWyS3aAwzMiCFfNwKJzyWnwLflz/UxcI8UGObYPlV5kZGsMuvLZbSEDTL
6s6gLTkqRS522BVK5sLrqFtpbRqC03ekGdeCBnVH5QNSfOW9YeUTVAe1Cj0qdcKe
DHMTDufGJAoPNo2fveOYs61XpTMg6ObuEMiFyJnLukr3AgMBAAGjUzBRMB0GA1Ud
DgQWBBR7+uIICKaEjdCQ8fKXw+rhb+81ezAfBgNVHSMEGDAWgBR7+uIICKaEjdCQ
8fKXw+rhb+81ezAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQBO
xpqNPFsphe2TPNz6DTVu1lGBifCK4wZ7WBkfeCybq+hZQvO74hUAv8usE2l1dG1k
Ibyf/1gjAe69h2R+o8bzMrQvhs/cXLZVUqkAeSD5rbsxLutos0AZjiNCyKkDEnPJ
h5beJULiJHL/uibk73iuCrPeZFERiH30ssf9rr0iJT2vFEPQFyoH3OBt/ycF8kIi
cwkCSbzVOf8wFa+nWJmbfGTJmhKz1lBhSmpaG2dN7FZPijx2g+cb9ZrqM6AyRDBe
jcsYzeeqVs8AWMKG1GXgs/0/dxmQ3RE8oVfdz875ogH7XQssDgq304FK6Nl98Mvo
gEmal/vE1DdtqeW3iNpA
-----END CERTIFICATE-----"""

_KEY_PEM = """\
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC3ZlTWeh2c0tPu
QLgIdWZpzA/xFYN58aVqxlDf4g3XwV3KArbn0tLISn/q5paS7oi32TZosOH1jbed
BiyPKk/KzNTf3JgJGUg0PK7NOGWxOi9wpeebHoqCtn8UVIRkzAUbr3Dbiedn9KXq
hTk3swihWg8suXBXRc4eqMvnGrJmGMshdMLaWyS3aAwzMiCFfNwKJzyWnwLflz/U
xcI8UGObYPlV5kZGsMuvLZbSEDTL6s6gLTkqRS522BVK5sLrqFtpbRqC03ekGdeC
BnVH5QNSfOW9YeUTVAe1Cj0qdcKeDHMTDufGJAoPNo2fveOYs61XpTMg6ObuEMiF
yJnLukr3AgMBAAECggEAPa4L0EonlWuOXS2k9ytMsz4vCly66BMuF9f0sScckrh0
q5D4JMVRoIz1snG0qFvS3UoPM2xxwhzUaNn/uHJ5fXIgEd3lwAGht/fErj5ObSlt
dQxG9XNzD/0Chjraf+/hs+rwINWjXuH3vwTpNmNe/q0EN31yW9edN9B7KxFeeFlB
QaY73BThGxpRdUBnf2luzXywcxNwmnFA1zFRj0LWAKYCB6FfKBJnU8k/N+DF/jtZ
zPRXV3dgWI0dDeWXl/vpsy32qa3c6BcBWuMcl5UpBdgped05+SHMuNchErqQJcKo
hnjMk1KYVeRkroSoJ/Rp8LUzO+jOkG+tPFLS5XlnMQKBgQD3uCNx5w7ig0C5B75O
e4KezRpQ+bVmQ3UjhgH1MetPKZmpyp1+Fw6w8WeoOFCUVySSft359n9mvzhbN1Rf
xd6use6rUAtM8ICXsTRUyJEf2CAILCbesbBla33lLbpDc2f4k/jl3QFGfPIMmKkA
O/naE4oV2XJDxHjyZ5KvRKDxHwKBgQC9h8cAkqekGrlcoQ2UOkK8XMylLxu4rCPW
f3+UNvS3TObWOI9DNzMTIacwFTmGVaePXodyctgBfV7r22VCJ7W/W3lxHnM1v2lt
IzjIq6EMu8BgbhZ/n49VRjdt88sVy0m0xw8A1EAkPCjC60KqX5CbGImYIHL5JLZO
PMekuEWzKQKBgCHxZUnyMyPugCvaV8VBP0CrMfPug2Cj1aUsc5A5atjKBngxfysL
1cOBEIcIUGJDHovEPn5FvGdDxGEbT8BfyId/cgifSy0bt0MR0O3dHaWTY7A6/Ih/
KIB9Hh8NCPy9D34MKIq2oboa3L/FG0Mg9Ldg/gbIaNPIVBpC/uJtMPBZAoGAUwCM
cT7ItgCSHvPVO44MPeuyH8EytbyFcWGi4Kj0oPXHvhdE/l3FO2KoklEpQSBv4kS2
srOCz5w1HruVa9RyLtyDobuBHw+1vvsG2jL3s9jhlhmANuIM5n56tednkCLYI5ht
hKJveK7z9vEK4Aw8CwBC+eF0GJIwWLEbiZK9y4kCgYA1uRGt4exZEtMnPGiRiYHi
+wKLFg3c71rIPCB8og1guyTbhRKr6XJ5LMj6z31GPMVWW1tfEwCBaTrRWPrB6C3N
8rUV7X3p30SnBQajzQlDqdg9oELc5ICJk7JaGjXxgaB6s4xM2ODhd8k7FklCRuW+
LiWFiAmqZHqg0eSjMXDrgQ==
-----END PRIVATE KEY-----"""


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def _make_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    td = tempfile.mkdtemp(prefix='gyro360_')
    cp = os.path.join(td, 'cert.pem')
    kp = os.path.join(td, 'key.pem')
    with open(cp, 'w') as f:
        f.write(_CERT_PEM)
    with open(kp, 'w') as f:
        f.write(_KEY_PEM)
    ctx.load_cert_chain(cp, kp)
    try:
        os.unlink(cp)
        os.unlink(kp)
        os.rmdir(td)
    except Exception:
        pass
    return ctx


def set_image_path(path):
    global _current_image_path, _render_version
    _current_image_path = path
    _render_version += 1


def get_viewer_html():
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
  html, body {
    width: 100%; height: 100%; overflow: hidden;
    background: #0a0a0a;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    -webkit-user-select: none; user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  #pano { position: absolute; width: 100%; height: 100%; }

  #hud {
    position: fixed; top: 0; left: 0; right: 0;
    display: flex; align-items: center; justify-content: space-between;
    padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
    background: linear-gradient(to bottom, rgba(0,0,0,0.65), transparent);
    z-index: 100; pointer-events: none;
  }
  #hud-title { color: rgba(255,255,255,0.9); font-size: 13px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
  #hud-status { display: flex; align-items: center; gap: 6px; color: rgba(255,255,255,0.6); font-size: 11px; }
  #status-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

  #controls {
    position: fixed; bottom: 0; left: 0; right: 0;
    display: flex; align-items: center; justify-content: center; gap: 10px;
    padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
    background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
    z-index: 100;
  }
  .ctrl-btn {
    background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
    color: white; border-radius: 20px; padding: 10px 18px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.04em; cursor: pointer;
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    transition: all 0.2s; font-family: inherit; text-transform: uppercase;
    -webkit-tap-highlight-color: transparent;
  }
  .ctrl-btn:active { background: rgba(255,255,255,0.25); transform: scale(0.96); }
  .ctrl-btn.active { background: rgba(74,222,128,0.25); border-color: rgba(74,222,128,0.55); color: #4ade80; }
  .ctrl-btn.disabled { opacity: 0.4; pointer-events: none; }

  #gyro-popup {
    position: fixed; inset: 0;
    background: rgba(10,10,10,0.92);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 24px; z-index: 400; padding: 40px;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } }
  #gyro-popup .phone-icon {
    width: 80px; height: 80px; border: 2px solid #4ade80; border-radius: 16px;
    display: flex; align-items: center; justify-content: center; font-size: 40px;
    animation: phoneWiggle 2s ease-in-out infinite;
  }
  @keyframes phoneWiggle { 0%, 100% { transform: rotate(-8deg); } 50% { transform: rotate(8deg); } }
  #gyro-popup h2 { color: white; font-size: 22px; font-weight: 700; text-align: center; letter-spacing: -0.01em; }
  #gyro-popup p { color: rgba(255,255,255,0.65); font-size: 14px; text-align: center; max-width: 280px; line-height: 1.5; }
  #gyro-popup .actions { display: flex; flex-direction: column; gap: 10px; width: 100%; max-width: 260px; margin-top: 8px; }
  #gyro-popup .btn-primary {
    background: #4ade80; color: #0a0a0a; border: none; border-radius: 24px;
    padding: 16px 32px; font-size: 15px; font-weight: 700; cursor: pointer;
    letter-spacing: 0.03em; font-family: inherit; box-shadow: 0 8px 24px rgba(74,222,128,0.3);
  }
  #gyro-popup .btn-primary:active { transform: scale(0.97); }
  #gyro-popup .btn-secondary {
    background: transparent; color: rgba(255,255,255,0.5); border: none;
    padding: 12px; font-size: 13px; cursor: pointer; font-family: inherit;
    text-decoration: underline; text-underline-offset: 3px;
  }

  #loading {
    position: fixed; inset: 0; background: #0a0a0a;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 16px; z-index: 300; transition: opacity 0.4s;
  }
  #loading-ring {
    width: 48px; height: 48px; border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #4ade80; border-radius: 50%; animation: spin 0.8s linear infinite;
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
    border-radius: 16px; font-size: 12px; z-index: 200; display: none;
    backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15);
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

<div id="pano"></div>

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

<script src="/marzipano.js"></script>
<script>
(function () {
  'use strict';

  var viewer, geometry, limiter, view, scene;
  var deviceOrientationMethod, controls;
  var gyroEnabled = false;
  var renderVersion = 0;
  var splashHidden = false;

  // ── Utilities ────────────────────────────────────────────────────────────

  function toast(msg, ms) {
    var el = document.getElementById('toast');
    el.textContent = msg;
    el.style.display = 'block';
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.style.display = 'none'; }, ms || 2500);
  }

  function hideSplash() {
    if (splashHidden) return;
    splashHidden = true;
    var el = document.getElementById('loading');
    if (el) {
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }
  }

  // ── Gyroscope ────────────────────────────────────────────────────────────

  function maybeShowGyroPopup() {
    if (typeof DeviceOrientationEvent === 'undefined') return;
    // Non-iOS: enable automatically without a popup
    if (typeof DeviceOrientationEvent.requestPermission !== 'function') {
      doEnableGyro();
      return;
    }
    if (sessionStorage.getItem('gyro_asked') === '1') return;
    document.getElementById('gyro-popup').style.display = 'flex';
  }

  async function requestAndEnableGyro() {
    try {
      var state = await DeviceOrientationEvent.requestPermission();
      sessionStorage.setItem('gyro_asked', '1');
      if (state === 'granted') {
        doEnableGyro();
      } else {
        toast('Permission denied. Go to Settings > Safari > Motion & Orientation Access.', 6000);
      }
    } catch (err) {
      sessionStorage.setItem('gyro_asked', '1');
      toast('Gyro error: ' + err.message, 4000);
    }
  }

  function doEnableGyro() {
    controls.enableMethod('deviceOrientation');
    gyroEnabled = true;
    var btn = document.getElementById('btn-gyro');
    btn.textContent = 'Gyro ON';
    btn.classList.add('active');
    toast('Gyroscope enabled — tilt your phone');
  }

  function doDisableGyro() {
    controls.disableMethod('deviceOrientation');
    gyroEnabled = false;
    var btn = document.getElementById('btn-gyro');
    btn.textContent = 'Enable Gyro';
    btn.classList.remove('active');
  }

  // ── Scene loading ─────────────────────────────────────────────────────────

  function createScene(url, onReady) {
    var source = Marzipano.ImageUrlSource.fromString(url);
    var s = viewer.createScene({
      source: source,
      geometry: geometry,
      view: view,
      pinFirstLevel: true
    });
    s.switchTo({}, onReady || function () {});
    return s;
  }

  function reloadScene() {
    var badge = document.getElementById('refresh-badge');
    badge.style.display = 'block';
    setTimeout(function () { badge.style.display = 'none'; }, 3000);
    scene = createScene('/image?v=' + Date.now());
  }

  // ── Polling for new renders ───────────────────────────────────────────────

  function startPolling() {
    setInterval(async function () {
      try {
        var res = await fetch('/api/status');
        var data = await res.json();
        if (data.version > renderVersion) {
          renderVersion = data.version;
          reloadScene();
        }
      } catch (e) { /* server restarting */ }
    }, 2500);
  }

  // ── Init ─────────────────────────────────────────────────────────────────

  function init() {
    viewer = new Marzipano.Viewer(document.getElementById('pano'), {
      controls: { mouseViewMode: 'drag' }
    });

    geometry = new Marzipano.EquirectGeometry([{ width: 4096 }]);
    limiter  = Marzipano.RectilinearView.limit.traditional(4096, 110 * Math.PI / 180);
    view     = new Marzipano.RectilinearView(
      { yaw: 0, pitch: 0, fov: 90 * Math.PI / 180 }, limiter
    );

    controls = viewer.controls();
    deviceOrientationMethod = new Marzipano.DeviceOrientationControlMethod();
    // Register but start inactive — activated only after iOS permission granted
    controls.registerMethod('deviceOrientation', deviceOrientationMethod, { active: false });

    // Load scene; hide splash when ready
    scene = createScene('/image?v=' + Date.now(), function () {
      hideSplash();
      maybeShowGyroPopup();
    });

    // Popup buttons
    document.getElementById('popup-enable').addEventListener('click', function () {
      document.getElementById('gyro-popup').style.display = 'none';
      requestAndEnableGyro();
    });
    document.getElementById('popup-skip').addEventListener('click', function () {
      sessionStorage.setItem('gyro_asked', '1');
      document.getElementById('gyro-popup').style.display = 'none';
    });

    // Gyro button
    var gyroBtn = document.getElementById('btn-gyro');
    if (!('DeviceOrientationEvent' in window)) {
      gyroBtn.textContent = 'No Gyro';
      gyroBtn.classList.add('disabled');
    } else {
      gyroBtn.addEventListener('click', function () {
        if (gyroEnabled) {
          doDisableGyro();
        } else if (typeof DeviceOrientationEvent.requestPermission === 'function') {
          requestAndEnableGyro();
        } else {
          doEnableGyro();
        }
      });
    }

    // Reset button
    document.getElementById('btn-reset').addEventListener('click', function () {
      view.setParameters({ yaw: 0, pitch: 0, fov: 90 * Math.PI / 180 });
      toast('View reset');
    });

    startPolling();
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
        elif path == '/marzipano.js':
            self._serve_marzipano()
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

    def _serve_marzipano(self):
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(addon_dir, 'marzipano.js')
        if not os.path.exists(js_path):
            self.send_response(404)
            self.end_headers()
            return
        try:
            with open(js_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()


def start_server(port=8765):
    global _server_instance, _server_thread

    if _server_instance is not None:
        return get_local_ip(), _server_instance.server_address[1]

    ip = get_local_ip()
    ssl_ctx = _make_ssl_context()

    for attempt_port in range(port, port + 20):
        try:
            srv = HTTPServer(("0.0.0.0", attempt_port), Handler360)
            srv.socket = ssl_ctx.wrap_socket(srv.socket, server_side=True)
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

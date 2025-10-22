#!/usr/bin/env python3

from flask import Flask, request, jsonify, abort
import uuid
import random
import string
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import threading
import time

app = Flask(__name__)

# --- Configuration ---
CLASS_KEY = "0ter1a_s3cr3t"
SESSION_TTL = 60 * 60 * 2
CAPTCHA_EVERY = 300
IMAGE_SIZE = (400, 200)

sessions = {}
lock = threading.Lock()

# Cleanup
def cleanup_loop():
    while True:
        now = time.time()
        with lock:
            to_delete = [sid for sid, s in sessions.items() if s['expires_at'] < now]
            for sid in to_delete:
                del sessions[sid]
        time.sleep(60)

threading.Thread(target=cleanup_loop, daemon=True).start()

# Helpers
def gen_pin_tp1():
    return f"{random.randint(0, 9999):04d}"

def gen_pin_tp2():
    # 3 chars: digits, lower
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(3))

def gen_pin_tp4():
    # 10 chars: digits, upper, lower
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(10))


def now_ts():
    return time.time()

def create_image_with_pin(pin_text):
    img = Image.new("RGB", IMAGE_SIZE, color=(255,255,255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Avenir.ttc", 60) # Change to system font if not on MacOS
    bbox = draw.textbbox((0, 0), pin_text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((IMAGE_SIZE[0]-w)/2, (IMAGE_SIZE[1]-h)/2), pin_text, fill=(0,0,0), font=font)
    return img

def split_image_to_base64_parts(img, rows=2, cols=4):
    w, h = img.size
    part_w = w // cols
    part_h = h // rows
    parts_b64 = []
    for r in range(rows):
        for c in range(cols):
            box = (c*part_w, r*part_h, (c+1)*part_w, (r+1)*part_h)
            part = img.crop(box)
            buf = io.BytesIO()
            part.save(buf, format="PNG")
            parts_b64.append(base64.b64encode(buf.getvalue()).decode())
    return parts_b64

def require_class_key(data):
    key = data.get("class_key") or request.headers.get("X-Class-Key")
    if key != CLASS_KEY:
        abort(403, "Class key invalid")

# API
@app.route("/new_session", methods=["POST"])
def new_session():
    payload = request.get_json(force=True)
    require_class_key(payload)
    tp = int(payload.get("tp", 1))
    session_id = str(uuid.uuid4())
    now = now_ts()
    sess = {
        "id": session_id,
        "tp": tp,
        "created_at": now,
        "expires_at": now + SESSION_TTL,
        "attempts": 0,
        "attempts_log": [],   # [(ts, attempt, success)]
        "rate_min_bucket": {"ts": now, "count": 0},
        "captcha_store": {},  # captcha_id -> (question, answer, expires_at)
    }
    if tp == 1:
        sess["target"] = gen_pin_tp1()
    elif tp == 2:
        sess["target"] = gen_pin_tp2()
    elif tp == 3:
        sess["target"] = gen_pin_tp2()
        sess["captcha_every"] = CAPTCHA_EVERY
    elif tp == 4:
        pin = gen_pin_tp4() 
        sess["target"] = pin
        img = create_image_with_pin(pin)
        sess["image_parts"] = split_image_to_base64_parts(img, rows=2, cols=4)
    else:
        abort(400, "TP invalide")
    with lock:
        sessions[session_id] = sess
    # Réponse : session_id, consignes sommaires
    return jsonify({
        "session_id": session_id,
        "tp": tp,
        "message": "Session créée localement pour usage pédagogique. Ne partagez pas session_id hors classe.",
        "hints": {
            1: "Code numérique 4 chiffres, 0000..9999.",
            2: "Code 3 caractères mélangés (chiffres, lettres minuscules).",
            3: "Comme TP2. Un captcha de calcul apparaîtra toutes les N tentatives.",
            4: "Récupérez les 8 parties base64 puis recomposez l'image pour lire le code."
        }.get(tp, "")
    }), 201

@app.route("/get_image", methods=["GET"])
def get_image():
    session_id = request.args.get("session_id")
    if not session_id:
        abort(400, "session_id manquant")
    with lock:
        sess = sessions.get(session_id)
    if not sess:
        abort(404, "session inconnue")
    if sess["tp"] != 4:
        abort(400, "Ce endpoint est pour TP4 uniquement")
    return jsonify({
        "session_id": session_id,
        "parts": sess["image_parts"],
        "note": "Chaque élément est une image PNG encodée en base64. Il y a 8 parties (2x4)."
    })

@app.route("/attempt", methods=["POST"])
def attempt():
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    attempt_val = payload.get("attempt")
    captcha_id = payload.get("captcha_id")
    captcha_answer = payload.get("captcha_answer")
    if not session_id or attempt_val is None:
        abort(400, "session_id et attempt requis")
    with lock:
        sess = sessions.get(session_id)
        if not sess:
            abort(404, "session inconnue")
        # TP3 captcha enforcement
        if sess["tp"] == 3:
            if sess["attempts"] > 0 and sess["attempts"] % sess.get("captcha_every", CAPTCHA_EVERY) == 0:
                if not captcha_id:
                    c_id, question = create_captcha_for_session(sess)
                    return jsonify({"captcha_required": True, "captcha_id": c_id, "question": question}), 200
                else:
                    ok = verify_captcha(sess, captcha_id, captcha_answer)
                    if not ok:
                        sess["attempts"] += 1
                        sess["attempts_log"].append((now, attempt_val, False, "bad_captcha"))
                        return jsonify({"success": False, "reason": "captcha incorrect"}), 403
        success = str(attempt_val) == str(sess["target"])
        sess["attempts"] += 1
        sess["attempts_log"].append((now, str(attempt_val), success))
        if success:
            return jsonify({"success": True, "message": "Code correct.", "attempts": sess["attempts"]})
        else:
            return jsonify({"success": False, "message": "Code incorrect.", "attempts": sess["attempts"]}), 200

@app.route("/solve_captcha", methods=["POST"])
def solve_captcha():
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    captcha_id = payload.get("captcha_id")
    captcha_answer = payload.get("captcha_answer")
    if not session_id or not captcha_id:
        abort(400, "session_id et captcha_id requis")
    with lock:
        sess = sessions.get(session_id)
        if not sess:
            abort(404, "session inconnue")
        ok = verify_captcha(sess, captcha_id, captcha_answer)
        if ok:
            return jsonify({"ok": True, "message": "Captcha résolu. Reprenez les essais."})
        else:
            return jsonify({"ok": False, "message": "Captcha incorrect ou expiré."}), 403

# Captcha helpers (simple arithmetic)
def create_captcha_for_session(sess, ttl=300):
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])
    if op == "+":
        ans = a + b
    elif op == "-":
        ans = a - b
    else:
        ans = a * b
    q = f"{a} {op} {b} = ?"
    cid = str(uuid.uuid4())
    sess["captcha_store"][cid] = (q, str(ans), now_ts() + ttl)
    return cid, q

def verify_captcha(sess, cid, answer):
    if not cid or cid not in sess["captcha_store"]:
        return False
    q, ans, exp = sess["captcha_store"][cid]
    if now_ts() > exp:
        del sess["captcha_store"][cid]
        return False
    ok = str(answer).strip() == str(ans)
    # remove captcha after one check
    del sess["captcha_store"][cid]
    return ok

# Minimal info endpoint for teachers to inspect session (read-only)
@app.route("/session_info", methods=["GET"])
def session_info():
    sid = request.args.get("session_id")
    key = request.headers.get("X-Class-Key")
    if key != CLASS_KEY:
        abort(403)
    with lock:
        sess = sessions.get(sid)
        if not sess:
            abort(404)
        # Expose limited pedagogical info
        info = {
            "session_id": sid,
            "tp": sess["tp"],
            "created_at": sess["created_at"],
            "expires_at": sess["expires_at"],
            "attempts": sess["attempts"],
            # target revealed to teacher only
            "target": sess.get("target"),
            "last_attempts": sess["attempts_log"][-10:]
        }
        return jsonify(info)

if __name__ == "__main__":
    print("TP PIN server démarré. Clé de classe par défaut:", CLASS_KEY)
    app.run(host="127.0.0.1", port=5000, debug=False)
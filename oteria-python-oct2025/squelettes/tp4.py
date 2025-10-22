#!/usr/bin/env python3
import requests
import base64
from PIL import Image
import io

# ---------------- Configuration par défaut ----------------
SERVER_URL = "http://127.0.0.1:5000"

# ---------------- Fonctions utilitaires ----------------
# Envoi d'une réponse au serveur web
def send_answer(session_id, attempt, captcha_id=None, captcha_answer=None):
    payload = {
        "session_id": session_id,
        "attempt": attempt
    }
    if captcha_id:
        payload["captcha_id"] = captcha_id
        payload["captcha_answer"] = captcha_answer
    r = requests.post(f"{SERVER_URL}/attempt", json=payload)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text

# Récupération d'une nouvelle session
def api_new_session(tp, class_key, server_url=SERVER_URL):
    payload = {"tp": tp, "class_key": class_key}
    r = requests.post(f"{server_url}/new_session", json=payload)
    if r.status_code in (200, 201):
        j = r.json()
        return j.get("session_id")
    else:
        raise RuntimeError(f"Erreur création session {r.status_code}: {r.text}")

# ---- TP4 : Récupérer 8 parties base64 et reconstituer image ----
# Objectif : Tester toutes les permutations possible de message à 3 caractères
# Pages du cours associés : 
# Pour envoyer une tentative (un code PIN)
# answer = "votre_code_pin"
# send_answer(session_id, answer)
# Pour récupérer l'image
# r = requests.get(f"{SERVER_URL}/get_image", params={"session_id": session_id}).json().get("parts")
def get_pin(session_id, out_path="reconstructed.png"):
    r = requests.get(f"{SERVER_URL}/get_image", params={"session_id": session_id})
    if r.status_code != 200:
        print("Erreur get_image:", r.status_code, r.text)
        return None
    data = r.json()
    parts = data.get("parts") or []
    if len(parts) != 8:
        print("Nombre de parties différent de 8 :", len(parts))
        return None

    # TODO : Décoder chaque partie en image PIL

if __name__ == "__main__":
    session = api_new_session(4, "0ter1a_s3cr3t", server_url=SERVER_URL)    
    get_pin(session)


# Exemple de commentaire
"""
    Exemple de commentaire
    sur plusieurs lignes
"""
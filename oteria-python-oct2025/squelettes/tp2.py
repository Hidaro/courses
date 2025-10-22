#!/usr/bin/env python3

import requests
import itertools

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


# ---------------- TP2: Bruteforce charset 3 caractères ----------------
# Objectif : Tester toutes les permutations possible de message à 3 caractères
# Pages du cours associés : 
# Pour envoyer une tentative (un code PIN)
# answer = "votre_code_pin"
# send_answer(session_id, answer)
def bruteforce(session_id):
    charset = "0123456789abcdefghijklmnopqrstuvwxyz"
    # TODO : Générer et envoyer tout les code PIN de 3 caractères (liste des caractères possibles ci-dessus)
    
    
    # Exemple d'envoi de réponse
    status, resp = send_answer(session_id, answer)
    if status == 200 and isinstance(resp, dict) and resp.get("success") is True:
        print("Trouvé :", pin)
        return pin

if __name__ == "__main__":
    session = api_new_session(2, "0ter1a_s3cr3t", server_url=SERVER_URL)    
    bruteforce(session)
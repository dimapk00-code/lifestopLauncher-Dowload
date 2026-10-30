import os
import sys
import zipfile
import platform
import subprocess
import threading
import requests
import customtkinter as ctk
import minecraft_launcher_lib

if platform.system() == "Linux":
    os.environ["GDK_BACKEND"] = "x11"

# TARGET SERVER CONFIGURATION VIA PLAYIT TUNNEL
SERVER_IP = "domination-worker.tun.ply.gg"
SERVER_PORT = "25565"
TARGET_VERSION = "1.21.11"

# LINK TO YOUR ZIP FILE WITH GAME PACK VIA JSDELIVR
ZIP_URL = "https://jsdelivr.net"

if platform.system() == "Windows":
    MINECRAFT_DIR = os.path.join(os.environ["APPDATA"], ".lifestop_launcher")
elif platform.system() == "Darwin":
    MINECRAFT_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "lifestop_launcher")
else:
    MINECRAFT_DIR = os.path.join(os.path.expanduser("~"), ".lifestop_launcher")

ctk.set_appearance_mode("dark")

LOCALIZATION = {
    "EN": {
        "label": "Enter your nickname:",
        "play": "PLAY",
        "ready": "Status: Ready",
        "download": "Downloading pack from site...",
        "extract": "Extracting game pack...",
        "cmd": "Generating launch command...",
        "launch": "Launching game...",
        "error": "Error: "
    },
    "RU": {
        "label": "Vvedi svoy nikneym:",
        "play": "IGRAT",
        "ready": "Status: Gotov",
        "download": "Zagruzka sborki s sayta...",
        "extract": "Raspakovka sborki...",
        "cmd": "Sozdanie komandy zapuska...",
        "launch": "Zapusk igry...",
        "error": "Oshibka: "
    }
}

class UniversalLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_lang = "EN"
        
        self.title("Lifestop Launcher")
        self.geometry("450x300")
        self.resizable(False, False)
        
        self.lang_btn = ctk.CTkSegmentedButton(self, values=["EN", "RU"], command=self.change_language)
        self.lang_btn.set("EN")
        self.lang_btn.pack(pady=10, padx=10, anchor="ne")
        
        self.label = ctk.CTkLabel(self, text=LOCALIZATION["EN"]["label"], font=("Arial", 14))
        self.label.pack(pady=5)
        
        self.entry = ctk.CTkEntry(self, placeholder_text="Player", width=200)
        self.entry.pack(pady=5)
        
        self.btn = ctk.CTkButton(
            self, 
            text=LOCALIZATION["EN"]["play"], 
            command=self.start, 
            width=200, 
            height=35,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            font=("Arial", 14, "bold")
        )
        self.btn.pack(pady=15)
        
        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.set(0)
        self.progress.pack(pady=5)
        
        self.status = ctk.CTkLabel(self, text=LOCALIZATION["EN"]["ready"], text_color="gray", font=("Arial", 12))
        self.status.pack(pady=5)

    def change_language(self, value):
        self.current_lang = value
        self.label.configure(text=LOCALIZATION[value]["label"])
        self.btn.configure(text=LOCALIZATION[value]["play"])
        self.status.configure(text=LOCALIZATION[value]["ready"])

    def start(self):
        nick = self.entry.get().strip()
        if not nick: return
        self.btn.configure(state="disabled")
        threading.Thread(target=self.run_game, args=(nick,), daemon=True).start()

    def download_and_extract_pack(self, lang):
        if not os.path.exists(MINECRAFT_DIR):
            os.makedirs(MINECRAFT_DIR)
            
        zip_path = os.path.join(MINECRAFT_DIR, "pack.zip")
        
        self.status.configure(text=LOCALIZATION[lang]["download"], text_color="yellow")
        response = requests.get(ZIP_URL, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        if response.status_code == 200:
            downloaded = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    if total_size > 0:
                        downloaded += len(chunk)
                        self.progress.set(downloaded / total_size)
                        
            self.status.configure(text=LOCALIZATION[lang]["extract"], text_color="cyan")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(MINECRAFT_DIR)
            
            os.remove(zip_path)
        else:
            raise Exception("Failed to download package from server")

    def fix_minecraft_language_file(self):
        options_path = os.path.join(MINECRAFT_DIR, "options.txt")
        lang_code = "en_us" if self.current_lang == "EN" else "ru_ru"
        
        lines = []
        if os.path.exists(options_path):
            with open(options_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        lang_found = False
        for i, line in enumerate(lines):
            if line.startswith("lang:"):
                lines[i] = f"lang:{lang_code}\n"
                lang_found = True
                break
        
        if not lang_found:
            lines.append(f"lang:{lang_code}\n")
            
        with open(options_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def run_game(self, nick):
        lang = self.current_lang
        try:
            version_folder = os.path.join(MINECRAFT_DIR, "versions", TARGET_VERSION)
            if not os.path.exists(version_folder):
                self.download_and_extract_pack(lang)
            
            self.fix_minecraft_language_file()
            
            options = {
                "username": nick, 
                "uuid": "", 
                "token": "",
                "customResolution": True,
                "resolutionWidth": "925",   
                "resolutionHeight": "530"
            }
            
            self.status.configure(text=LOCALIZATION[lang]["cmd"], text_color="cyan")
            cmd = minecraft_launcher_lib.command.get_minecraft_command(TARGET_VERSION, MINECRAFT_DIR, options)
            
            if lang == "EN":
                cmd.extend(["--lang", "en_us"])
            else:
                cmd.extend(["--lang", "ru_ru"])
                
            cmd.extend(["--server", SERVER_IP, "--port", SERVER_PORT])
            
            self.status.configure(text=LOCALIZATION[lang]["launch"], text_color="green")
            self.progress.set(1.0)
            
            self.after(1000, self.withdraw)
            subprocess.run(cmd)
            self.after(0, self.restore_launcher)
            
        except Exception as e:
            print(f"[ERROR] Launch failed: {e}")
            self.status.configure(text=f"{LOCALIZATION[lang]['error']}{str(e)}", text_color="red")
            self.btn.configure(state="normal")

    def restore_launcher(self):
        self.deiconify()
        self.btn.configure(state="normal")
        self.status.configure(text=LOCALIZATION[self.current_lang]["ready"], text_color="gray")
        self.progress.set(0)

if __name__ == "__main__":
    app = UniversalLauncher()
    app.mainloop()


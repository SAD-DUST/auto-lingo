import requests, subprocess, time, concurrent.futures, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table

# ================== CONFIG ==================
THREADS = 500
INPUT_FILE = "proxy.txt"
TARGET_PAGE = "https://c3phucu.hungyen.edu.vn/tin-tuc/thoi-khoa-bieu-so-1-ca-chieu.html"
VOTE_API = "https://c3phucu.hungyen.edu.vn/api/vote/store"
VOTE_VIEW_API = "https://c3phucu.hungyen.edu.vn/api/vote"
DATA_FILE = "data.txt"
TIMEOUT = 5
VIEW_REFRESH = 300  # 5 phút
HEADERS = [
    "-H", "User-Agent: Mozilla/5.0",
    "-H", "Accept: */*",
    "-H", "X-Requested-With: XMLHttpRequest",
    "-H", "Content-Type: multipart/form-data; boundary=----geckoformboundary94a1dddf2223cf22c83a97727ab2f4dc",
    "-H", "Origin: https://c3phucu.hungyen.edu.vn",
    "-H", "Referer: https://c3phucu.hungyen.edu.vn/",
    "-H", "Cookie: XSRF-TOKEN=YOUR_XSRF_TOKEN; thpt_phu_cu_session=YOUR_SESSION_COOKIE",
]
# ============================================

console = Console()

# ========== PHẦN 1: CHECK PROXY ==========
def check_proxy(proxy: str) -> str | None:
    proxy = proxy.strip()
    if not proxy:
        return None

    if proxy.startswith("socks4://") or proxy.startswith("socks5://"):
        scheme = proxy.split("://")[0]
        address = proxy.split("://")[1]
        proxies = {scheme: f"{scheme}://{address}"}
    else:
        address = proxy.replace("http://", "").replace("https://", "")
        proxies = {
            "http": f"http://{address}",
            "https": f"http://{address}",
        }

    try:
        r = requests.get(TARGET_PAGE, proxies=proxies, timeout=TIMEOUT, verify=False)
        if r.status_code == 200:
            console.print(f"[green][+] WORKING:[/green] {proxy}")
            return proxy
    except Exception:
        pass
    console.print(f"[red][-] DEAD:[/red] {proxy}")
    return None

def get_alive_proxies():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]

    alive = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        results = list(executor.map(check_proxy, proxies))
    for result in results:
        if result:
            alive.append(result)

    console.print(f"[bold cyan][!] {len(alive)} proxies sống[/bold cyan]")
    return alive

# ========== PHẦN 2: SPAM VOTE ==========
def send_request(proxy: str):
    cmd = [
        "curl", VOTE_API,
        "--proxy", proxy,
        "--compressed",
        "-X", "POST",
        "--data-binary", f"@{DATA_FILE}"
    ] + HEADERS

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            try:
                resp = json.loads(result.stdout.strip())
                if resp.get("message") == ["B\u00ecnh ch\u1ecdn th\u00e0nh c\u00f4ng !"]:
                    return f"[green][+][/green] {proxy} ✅ success"
                else:
                    return f"[red][!][/red] {proxy} ❌ invalid response: {resp}"
            except json.JSONDecodeError:
                return f"[red][!][/red] {proxy} ❌ not JSON: {result.stdout.strip()}"
        else:
            return f"[red][!][/red] {proxy} ❌ failed (exit {result.returncode})"
    except Exception as e:
        return f"[red][!][/red] {proxy} ❌ error: {e}"

def spam_vote(alive):
    if not alive:
        console.print("[red][!] Không có proxy sống[/red]")
        return

    workers = min(100, len(alive))
    console.print(f"[*] Bắn vote với {workers} threads 🧨")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(send_request, proxy): proxy for proxy in alive}
        for future in as_completed(futures):
            console.print(future.result())

# ========== PHẦN 3: SHOW VOTE ==========
def show_votes():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TARGET_PAGE,
    }

    res = requests.get(VOTE_VIEW_API, headers=headers)
    data = res.json()

    for poll in data:
        table = Table(title=f"📊 {poll['question']}", title_style="bold magenta")
        table.add_column("Lựa chọn", style="cyan", no_wrap=True)
        table.add_column("Số phiếu", justify="center", style="yellow")
        table.add_column("Tổng phiếu", justify="center", style="yellow")
        table.add_column("Tỉ lệ", justify="center", style="green")

        for v in poll['votes']:
            table.add_row(
                v['answer'],
                str(v['count']),
                str(v['total']),
                f"{v['percent']:.2f}%"
            )
        console.print(table)

# ========== MAIN LOOP ==========
def main():
    while True:
        console.rule("[bold magenta]🔍 Checking proxies")
        alive = get_alive_proxies()

        console.rule("[bold magenta]🚀 Spamming votes")
        spam_vote(alive)
        console.rule("[bold magenta]🚀 Spamming votes p.2")
        spam_vote(alive)
        console.rule("[bold magenta]🚀 Spamming votes p.3")
        spam_vote(alive)
        console.rule("[bold magenta]🚀 Spamming votes p.4")
        spam_vote(alive)

        console.rule("[bold magenta]📺 Showing results")
        show_votes()

        console.print(f"[blue]⏳ Đợi {VIEW_REFRESH/60:.0f} phút rồi chơi tiếp...[/blue]")
        time.sleep(VIEW_REFRESH)

if __name__ == "__main__":
    main()

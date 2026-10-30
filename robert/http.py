import random, time, requests
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "eth.blockscout.com", "optimism.blockscout.com", "gnosis.blockscout.com",
    "polygon.blockscout.com", "base.blockscout.com", "arbitrum.blockscout.com",
    "scroll.blockscout.com", "zksync.blockscout.com", "linea.blockscout.com",
    "api.ethplorer.io", "api.blockchair.com",
    "eth.drpc.org", "ethereum-rpc.publicnode.com",
    "gateway.tenderly.co", "eth-pokt.nodies.app", "eth.meowrpc.com", "api.coingecko.com", "mempool.space",
    "arb1.arbitrum.io", "mainnet.base.org", "polygon-rpc.com", "mainnet.optimism.io",
}
MAX_BYTES = 5_000_000
TIMEOUT = (5, 20)

class HttpError(RuntimeError): pass

def _check(url):
    p = urlparse(url)
    if p.scheme != "https":
        raise HttpError(f"non-https blocked: {url}")
    if p.hostname not in ALLOWED_HOSTS:
        raise HttpError(f"host not allowlisted: {p.hostname}")

def get(url, params=None, retries=3):
    _check(url)
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT,
                             verify=True, stream=True,
                             headers={"User-Agent": "robert/0.1 (+open-source)"})
            if r.status_code in (429, 500, 502, 503, 504):
                raise HttpError(f"retryable {r.status_code}")
            r.raise_for_status()
            chunks, total = [], 0
            for c in r.iter_content(65536):
                total += len(c)
                if total > MAX_BYTES:
                    raise HttpError("response too large")
                chunks.append(c)
            return b"".join(chunks)
        except Exception as e:
            last = e
            time.sleep((2 ** i) + random.random())
    raise HttpError(f"GET failed after {retries}: {last}")

def post_json(url, payload, retries=3):
    _check(url)
    last = None
    for i in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=TIMEOUT, verify=True,
                              headers={"User-Agent": "robert/0.1 (+open-source)"})
            if r.status_code in (429, 500, 502, 503, 504):
                raise HttpError(f"retryable {r.status_code}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep((2 ** i) + random.random())
    raise HttpError(f"POST failed after {retries}: {last}")



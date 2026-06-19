"""Pre-warm the shared (Redis) cache so user-facing endpoints serve instantly.

Runs as a decoupled service (see docker-compose.coolify.yml `cache-warmer`),
independent of the web process. It calls the API's own endpoint functions —
each populates the cache via `_cache_set`, which writes through to Redis. So
after a redeploy the cache is warm before the first user hits it, and the slow
yfinance round-trips happen here in the background instead of in a request.

Usage:
    python -m scripts.warm_cache            # one pass, then exit
    python -m scripts.warm_cache --loop 300 # forever, every 300 s
"""
from __future__ import annotations

import argparse
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s warmer: %(message)s")
log = logging.getLogger("warmer")


def warm_once() -> None:
    from scripts import api

    t0 = time.time()
    ok = 0

    # Shared/market-wide endpoints (no args)
    for name, fn in (
        ("ticker_banner", api.ticker_banner),
        ("dashboard_overview", api.dashboard_overview),
        ("hot_stocks", api.market_hot_stocks),
    ):
        try:
            fn()
            ok += 1
            log.info("warmed %s", name)
        except Exception as e:  # noqa: BLE001 — never let one failure stop the pass
            log.warning("warm %s failed: %s", name, e)

    # Per-ticker Analyzer endpoints for the watchlist (detail + default 3mo chart)
    for tkr in api._WATCHLIST_TICKERS:
        try:
            api.stock_detail(tkr)
            ok += 1
            log.info("warmed detail %s", tkr)
        except Exception as e:  # noqa: BLE001
            log.warning("warm detail %s failed: %s", tkr, e)
        try:
            api.stock_chart(tkr, "3mo")
            ok += 1
            log.info("warmed chart %s", tkr)
        except Exception as e:  # noqa: BLE001
            log.warning("warm chart %s failed: %s", tkr, e)

    log.info("pass done: %d warmed in %.1fs", ok, time.time() - t0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm the market-tools cache")
    parser.add_argument("--loop", type=int, default=0,
                        help="seconds between passes; 0 = single pass then exit")
    args = parser.parse_args()

    if args.loop <= 0:
        warm_once()
        return

    log.info("warmer loop started (every %d s)", args.loop)
    while True:
        try:
            warm_once()
        except Exception as e:  # noqa: BLE001 — keep the loop alive no matter what
            log.error("pass crashed: %s", e)
        time.sleep(args.loop)


if __name__ == "__main__":
    main()

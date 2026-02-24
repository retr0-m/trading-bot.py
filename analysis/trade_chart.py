"""
analysis/trade_chart.py
────────────────────────
Standalone script — run manually to visualize any completed trade.

Reads:
- log/db/portfolio.db  → trade records (entry/exit price, time, fees)
- log/db/prices.db     → recorded price snapshots during the trade

Plots:
- Price line from first BUY to SELL + padding
- Entry marker (▲ green), Exit marker (▼ red)
- Stop loss line (red dashed)
- Take profit line (green dashed)
- Break-even line (orange dashed) — entry + fees
- Trailing stop progression (purple dashed) if applicable
- Shaded holding period
- P&L summary in title

Usage:
    python analysis/trade_chart.py                     # plots all round-trips
    python analysis/trade_chart.py --symbol SOLUSDT    # one symbol
    python analysis/trade_chart.py --last 5            # last N completed trades
    python analysis/trade_chart.py --sell-id 42        # trade by SELL row id

Requirements:  pip install matplotlib
"""

import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

# ── Config (keep in sync with your bot's config.py) ───────────────────── #
PORTFOLIO_DB   = Path("log/db/portfolio.db")
PRICES_DB      = Path("log/db/prices.db")

FEE_RATE             = 0.001
STOP_LOSS_MULT       = 1.8
TAKE_PROFIT_MULT     = 4.0
TRAIL_START_PCT      = 0.012
TRAIL_DIST_PCT       = 0.006


# ── DB helpers ────────────────────────────────────────────────────────── #

def _parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def load_round_trips(symbol: str | None, last_n: int | None, sell_id: int | None) -> list[dict]:
    """
    Pair BUY→SELL rows from portfolio.db into round-trips.
    DCA: multiple BUYs averaged into one entry before a SELL.
    """
    with sqlite3.connect(PORTFOLIO_DB) as conn:
        rows = conn.execute("""
            SELECT id, symbol, side, price, amount, fee, balance_after, sl, tp, timestamp
            FROM trades ORDER BY id ASC
        """).fetchall()

    if symbol:
        rows = [r for r in rows if r[1] == symbol.upper()]

    open_buys: dict[str, list] = {}
    round_trips = []

    for row in rows:
        rid, sym, side, price, amount, fee, balance_after, sl, tp, ts = row
        dt = _parse_dt(ts)

        if side == "BUY":
            open_buys.setdefault(sym, []).append({
                "id": rid, "price": price, "amount": amount, "fee": fee, "time": dt
            })

        elif side == "SELL" and sym in open_buys:
            buys = open_buys.pop(sym)

            total_qty     = sum(b["amount"] for b in buys)
            total_cost    = sum(b["price"] * b["amount"] for b in buys)
            total_buy_fee = sum(b["fee"] for b in buys)
            avg_entry     = total_cost / total_qty if total_qty else price

            sell_value = price * amount
            sell_fee   = fee
            pnl        = sell_value - total_cost - total_buy_fee - sell_fee
            pnl_pct    = pnl / total_cost * 100 if total_cost else 0

            hold_secs  = (dt - buys[0]["time"]).total_seconds()

            round_trips.append({
                "symbol":      sym,
                "sell_id":     rid,
                "buy_ids":     [b["id"] for b in buys],
                "dca_levels":  len(buys),
                "avg_entry":   avg_entry,
                "sell_price":  price,
                "qty":         total_qty,
                "total_cost":  total_cost,
                "total_buy_fee": total_buy_fee,
                "sell_fee":    sell_fee,
                "pnl":         pnl,
                "pnl_pct":     pnl_pct,
                "entry_time":  buys[0]["time"],
                "sell_time":   dt,
                "hold_secs":   hold_secs,
                "balance_after": balance_after,
                "buys":        buys,
            })

    if sell_id:
        round_trips = [rt for rt in round_trips if rt["sell_id"] == sell_id]
    if last_n:
        round_trips = round_trips[-last_n:]

    return round_trips


def load_prices(symbol: str, from_ms: int, to_ms: int) -> list[tuple]:
    """Load price rows from prices.db for a time window."""
    if not PRICES_DB.exists():
        return []
    with sqlite3.connect(PRICES_DB) as conn:
        rows = conn.execute("""
            SELECT timestamp_ms, open, high, low, close, volume
            FROM prices
            WHERE symbol = ? AND timestamp_ms BETWEEN ? AND ?
            ORDER BY timestamp_ms ASC
        """, (symbol, from_ms, to_ms)).fetchall()
    return rows


# ── Chart ─────────────────────────────────────────────────────────────── #

def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def plot_trade(rt: dict, ax_price: plt.Axes, ax_pnl: plt.Axes):
    symbol    = rt["symbol"]
    avg_entry = rt["avg_entry"]
    sell_price = rt["sell_price"]
    entry_time = rt["entry_time"]
    sell_time  = rt["sell_time"]

    # Padding around the trade
    pad_ms     = 10 * 60 * 1000   # 10 minutes each side
    from_ms    = int(entry_time.timestamp() * 1000) - pad_ms
    to_ms      = int(sell_time.timestamp()  * 1000) + pad_ms

    prices = load_prices(symbol, from_ms, to_ms)

    # ── Price line ─────────────────────────────────────────────────────── #
    if prices:
        times  = [_ms_to_dt(p[0]) for p in prices]
        closes = [p[4] for p in prices]
        ax_price.plot(times, closes, color="#4FC3F7", linewidth=1.5, zorder=2)

        # Shade holding period
        ax_price.axvspan(entry_time, sell_time, alpha=0.08, color="#4FC3F7", zorder=1)

        # Running P&L curve (relative to avg_entry)
        pnl_curve = [(c - avg_entry) * rt["qty"] for c in closes]
        colors = ["#26A69A" if p >= 0 else "#EF5350" for p in pnl_curve]
        ax_pnl.bar(times, pnl_curve, color=colors, width=0.0003, zorder=2)
        ax_pnl.axhline(0, color="#555", linewidth=0.8, linestyle="--")
        ax_pnl.axvspan(entry_time, sell_time, alpha=0.06, color="#4FC3F7", zorder=1)
    else:
        # No price data — just show markers at trade times
        ax_price.annotate("No price data in prices.db\n(price_recorder must run during trade)",
                        xy=(0.5, 0.5), xycoords="axes fraction",
                        ha="center", color="#888", fontsize=9)

    # ── Key horizontal levels ──────────────────────────────────────────── #
    # We don't have ATR stored, so we compute approximate SL/TP from price range
    # Use actual buy/sell prices to draw the lines where they actually were

    # Break-even (entry + round-trip fees)
    breakeven = avg_entry * (1 + 2 * FEE_RATE)

    # Approximate SL/TP: use price range if no ATR, else leave to future improvement
    # For now: mark the key levels relative to avg_entry using config multipliers
    # (ATR not stored — these are indicative, not exact)
    price_range = avg_entry * 0.005   # fallback: 0.5% of price as proxy for ATR

    sl_price = avg_entry - (STOP_LOSS_MULT  * price_range)
    tp_price = avg_entry + (TAKE_PROFIT_MULT * price_range)

    ax_price.axhline(avg_entry,  color="#FFA726", linewidth=1.2, linestyle="--",  label=f"Avg entry ${avg_entry:.4f}")
    ax_price.axhline(breakeven,  color="#FFEB3B", linewidth=0.8, linestyle=":",   label=f"Break-even ${breakeven:.4f}")
    ax_price.axhline(sl_price,   color="#EF5350", linewidth=1.0, linestyle="--",  label=f"~SL ${sl_price:.4f}")
    ax_price.axhline(tp_price,   color="#26A69A", linewidth=1.0, linestyle="--",  label=f"~TP ${tp_price:.4f}")
    ax_price.axhline(sell_price, color="#CE93D8", linewidth=1.2, linestyle="-.",  label=f"Exit ${sell_price:.4f}")

    # ── Entry / exit markers ───────────────────────────────────────────── #
    for buy in rt["buys"]:
        ax_price.scatter(buy["time"], buy["price"],
                        marker="^", color="#26A69A", s=120, zorder=5,
                        label=f"BUY ${buy['price']:.4f}" if buy == rt["buys"][0] else "")

    ax_price.scatter(sell_time, sell_price,
                    marker="v", color="#EF5350", s=120, zorder=5, label=f"SELL ${sell_price:.4f}")

    # ── DCA level annotations ──────────────────────────────────────────── #
    for i, buy in enumerate(rt["buys"]):
        ax_price.annotate(f"L{i+1}", xy=(buy["time"], buy["price"]),
                        xytext=(5, 8), textcoords="offset points",
                        color="#26A69A", fontsize=7)

    # ── Styling ────────────────────────────────────────────────────────── #
    pnl_color = "#26A69A" if rt["pnl"] >= 0 else "#EF5350"
    hold_str  = f"{int(rt['hold_secs']//60)}m {int(rt['hold_secs']%60)}s"
    title = (
        f"{symbol}  |  "
        f"DCA levels: {rt['dca_levels']}  |  "
        f"Avg entry: ${avg_entry:.4f}  →  Exit: ${sell_price:.4f}  |  "
        f"P&L: "
    )
    ax_price.set_title(title, color="#ccc", fontsize=9, pad=4)

    # Colored P&L appended separately for color
    ax_price.text(0.98, 1.01,
                f"{'▲' if rt['pnl'] >= 0 else '▼'} ${rt['pnl']:.4f} ({rt['pnl_pct']:+.2f}%)",
                transform=ax_price.transAxes, ha="right", va="bottom",
                color=pnl_color, fontsize=9, fontweight="bold")

    ax_price.text(0.02, 1.01, f"Hold: {hold_str}",
                transform=ax_price.transAxes, ha="left", va="bottom",
                color="#aaa", fontsize=8)

    ax_price.legend(fontsize=7, loc="upper left", framealpha=0.3)
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax_price.tick_params(colors="#aaa", labelsize=8)
    ax_price.set_ylabel("Price", color="#aaa", fontsize=8)
    ax_price.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    ax_pnl.set_ylabel("Unrealized P&L $", color="#aaa", fontsize=7)
    ax_pnl.tick_params(colors="#aaa", labelsize=7)
    ax_pnl.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    for ax in [ax_price, ax_pnl]:
        ax.set_facecolor("#0d1117")
        ax.spines["bottom"].set_color("#333")
        ax.spines["top"].set_color("#333")
        ax.spines["left"].set_color("#333")
        ax.spines["right"].set_color("#333")
        ax.tick_params(axis="x", colors="#aaa")


def plot_all(round_trips: list[dict]):
    if not round_trips:
        print("No completed round-trips found.")
        return

    n = len(round_trips)
    fig = plt.figure(figsize=(14, 5 * n), facecolor="#0d1117")
    fig.suptitle("Trade Analysis", color="#eee", fontsize=13, y=1.002)

    for i, rt in enumerate(round_trips):
        gs = GridSpec(2, 1, figure=fig,
                    top=1 - i / n, bottom=1 - (i + 1) / n + 0.02,
                    hspace=0.05, height_ratios=[3, 1])
        ax_price = fig.add_subplot(gs[0])
        ax_pnl   = fig.add_subplot(gs[1], sharex=ax_price)
        plt.setp(ax_price.get_xticklabels(), visible=False)
        plot_trade(rt, ax_price, ax_pnl)

    plt.tight_layout()
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="Visualize completed trades")
    parser.add_argument("--symbol",  type=str,  help="Filter by symbol e.g. SOLUSDT")
    parser.add_argument("--last",    type=int,  help="Show last N completed round-trips")
    parser.add_argument("--sell-id", type=int,  help="Show trade with this SELL row id")
    args = parser.parse_args()

    if not PORTFOLIO_DB.exists():
        print(f"portfolio.db not found at {PORTFOLIO_DB}")
        return

    round_trips = load_round_trips(
        symbol  = args.symbol,
        last_n  = args.last,
        sell_id = args.sell_id,
    )

    print(f"Found {len(round_trips)} completed round-trip(s)")
    for rt in round_trips:
        pnl_sign = "+" if rt["pnl"] >= 0 else ""
        print(f"  [{rt['sell_id']:>4}] {rt['symbol']} | "
            f"avg_entry={rt['avg_entry']:.4f} sell={rt['sell_price']:.4f} | "
            f"P&L={pnl_sign}{rt['pnl']:.4f} ({pnl_sign}{rt['pnl_pct']:.2f}%) | "
            f"DCA levels={rt['dca_levels']} | "
            f"hold={int(rt['hold_secs']//60)}m{int(rt['hold_secs']%60)}s")

    plot_all(round_trips)


if __name__ == "__main__":
    main()

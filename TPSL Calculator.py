import os
import time
import msvcrt
from datetime import datetime
import subprocess
import sys
import platform

# First-time pip installer
try:
    import MetaTrader5 as mt5
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
    import MetaTrader5 as mt5

# Terminal Colors
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"

# Console Setup (Windows)
if platform.system() == "Windows":
    os.system("chcp 65001 >nul")
    os.system("mode con: cols=80 lines=40")
    os.system("title MT5 TP/SL CALCULATOR")

SHOW_DETAILS = False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_loading_bar():
    bar = "Connecting to MetaTrader 5\n["
    print(bar, end="", flush=True)
    for i in range(10):
        time.sleep(0.05)
        print("█", end="", flush=True)
    print("] Connected!")
    time.sleep(0.3)
    clear_screen()

def get_trades():
    positions = mt5.positions_get()
    account = mt5.account_info()
    balance = account.balance if account else 0.0

    today = datetime.now().date()
    start = int(datetime.combine(today, datetime.min.time()).timestamp())
    end = int(datetime.combine(today, datetime.max.time()).timestamp())
    history = mt5.history_orders_get(start, end)

    wins, losses, pnl_today = 0, 0, 0.0
    if history:
        closed = {}
        for order in history:
            if order.state == mt5.ORDER_STATE_FILLED:
                pid = order.position_id
                if pid not in closed:
                    closed[pid] = 0.0
                deals = mt5.history_deals_get(position=pid)
                for deal in deals:
                    if start <= deal.time <= end and deal.entry == mt5.DEAL_ENTRY_OUT:
                        closed[pid] += deal.profit
        for p in closed.values():
            pnl_today += p
            wins += p > 0
            losses += p < 0
    return positions, wins, losses, pnl_today, balance

def print_summary(positions, wins, losses, pnl_today, balance):
    print("\n====== SUMMARY ======\n")
    buy, sell, tp_total, sl_total = 0, 0, 0.0, 0.0
    for pos in positions:
        info = mt5.symbol_info(pos.symbol)
        if not info or info.point == 0: continue
        pt, tv = info.point, info.trade_tick_value
        tp, sl, op, vol = pos.tp, pos.sl, pos.price_open, pos.volume
        typ = pos.type
        if typ == 0: buy += 1
        else: sell += 1
        if tp > 0:
            dist = abs(tp - op) / pt
            val = dist * tv * vol
            if (typ == 0 and tp < op) or (typ == 1 and tp > op): val *= -1
            tp_total += val
        if sl > 0:
            dist = abs(sl - op) / pt
            val = dist * tv * vol
            if (typ == 0 and sl > op) or (typ == 1 and sl < op): val *= -1
            else: val *= -1
            sl_total += val

    risk_pct = abs(sl_total / balance * 100) if balance else 0
    perf = GREEN if pnl_today >= 0 else RED
    print(f"Trades Summary     : BUY = {buy}    |   SELL = {sell}")
    print(f"{GREEN}TP Target         : ${tp_total:.2f}{RESET}")
    print(f"{RED}SL Risk           : ${sl_total:.2f}{RESET}")
    print(f"Risk on Account   : {risk_pct:.2f}%")
    print(f"Account Balance   : ${balance:.2f}")
    print(f"{perf}Today's P&L       : {wins}W-{losses}L | ${pnl_today:.2f}{RESET}")
    print("\n↑ Up = Details   ↓ Down = Summary   Enter = Refresh")

def print_details(positions):
    print("\n====== DETAILS ======\n")
    for pos in positions:
        info = mt5.symbol_info(pos.symbol)
        if not info: continue
        pt, tv = info.point, info.trade_tick_value
        sym, vol, typ = pos.symbol, pos.volume, pos.type
        op, tp, sl, cur = pos.price_open, pos.tp, pos.sl, pos.profit
        trade = "BUY" if typ == 0 else "SELL"
        print(f"{sym} | {trade} | Volume: {vol:.2f}")
        print(f"Current P&L       : ${cur:.2f}")
        if tp > 0:
            dist = abs(tp - op) / pt
            val = dist * tv * vol
            if (typ == 0 and tp < op) or (typ == 1 and tp > op): val *= -1
            print(f"{GREEN}TP Target         : ${val:.2f}{RESET}")
        else:
            print("TP Target         : Not Set")
        if sl > 0:
            dist = abs(sl - op) / pt
            val = dist * tv * vol
            if (typ == 0 and sl > op) or (typ == 1 and sl < op): val *= -1
            else: val *= -1
            print(f"{RED}SL Risk           : ${val:.2f}{RESET}")
        else:
            print("SL Risk           : Not Set")
        if tp > 0 and sl > 0:
            rr = abs(tp - op) / abs(sl - op)
            print(f"R/R Ratio         : {rr:.2f}")
        print()
    print("↑ Up = Details   ↓ Down = Summary   Enter = Refresh")

def run():
    global SHOW_DETAILS
    print_loading_bar()
    last_action = None
    while True:
        clear_screen()
        positions, wins, losses, pnl_today, balance = get_trades()
        if not positions:
            print("No open trades found.")
            input("\nPress Enter to exit...")
            break
        if last_action == 'refreshed':
            clear_screen()
            last_action = None
        if SHOW_DETAILS:
            print_details(positions)
        else:
            print_summary(positions, wins, losses, pnl_today, balance)
        key = wait_for_key()
        if key == 'up': SHOW_DETAILS = True
        elif key == 'down': SHOW_DETAILS = False
        elif key == 'enter': last_action = 'refreshed'

def wait_for_key():
    key = msvcrt.getch()
    if key == b'\xe0':
        arrow = msvcrt.getch()
        if arrow == b'H': return 'up'
        if arrow == b'P': return 'down'
    elif key == b'\r': return 'enter'
    return None

# Connect & Run
if not mt5.initialize():
    print("Failed to connect to MetaTrader 5.")
    print(f"Error: {mt5.last_error()}")
    input("\nPress Enter to exit...")
else:
    run()
    mt5.shutdown()

import MetaTrader5 as mt5
import time
import msvcrt
import os
import sys
from datetime import datetime, timedelta

# Terminal colors
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
WHITE = "\033[97m"

# Globals
SHOW_DETAILS = False
REFRESH_DELAY = 0.005

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def color(val):
    if val > 0: return GREEN
    elif val < 0: return RED
    else: return WHITE

def print_loading():
    print("Connecting to MetaTrader 5\n[", end="", flush=True)
    for _ in range(10):
        print("█", end="", flush=True)
        time.sleep(0.08)
    print("] Connected!")
    time.sleep(0.3)
    clear_screen()

def get_today_range_utc():
    """Return today's 00:00 to 23:59 in UTC timestamps based on local time."""
    now_local = datetime.now()
    local_start = datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0)
    local_end = datetime(now_local.year, now_local.month, now_local.day, 23, 59, 59)

    offset = datetime.now() - datetime.utcnow()
    start_utc = local_start - offset
    end_utc = local_end - offset
    return start_utc, end_utc

def get_trade_data():
    positions = mt5.positions_get()
    account = mt5.account_info()
    balance = account.balance if account else 0.0

    wins, losses, pnl_today = 0, 0, 0.0
    start_utc, end_utc = get_today_range_utc()

    orders = mt5.history_orders_get(start_utc, end_utc)

    if orders:
        closed_positions = {}
        for order in orders:
            if order.state == mt5.ORDER_STATE_FILLED:
                pid = order.position_id
                if pid not in closed_positions:
                    closed_positions[pid] = 0.0
                deals = mt5.history_deals_get(position=pid)
                for deal in deals:
                    deal_time = datetime.utcfromtimestamp(deal.time)
                    if deal.entry == mt5.DEAL_ENTRY_OUT and start_utc <= deal_time <= end_utc:
                        closed_positions[pid] += deal.profit
        for profit in closed_positions.values():
            pnl_today += profit
            if profit > 0:
                wins += 1
            elif profit < 0:
                losses += 1

    return positions or [], wins, losses, pnl_today, balance

def print_summary(positions, wins, losses, pnl_today, balance):
    print("\n====== SUMMARY ======\n")
    buy, sell, total_tp, total_sl, cur_pl = 0, 0, 0.0, 0.0, 0.0

    for pos in positions:
        info = mt5.symbol_info(pos.symbol)
        if not info: continue
        pt, tv = info.point, info.trade_tick_value
        op, tp, sl, vol, typ = pos.price_open, pos.tp, pos.sl, pos.volume, pos.type

        cur_pl += pos.profit
        if typ == mt5.ORDER_TYPE_BUY: buy += 1
        else: sell += 1

        if tp > 0:
            dist = abs(tp - op) / pt
            val = dist * tv * vol
            if (typ == mt5.ORDER_TYPE_BUY and tp < op) or (typ == mt5.ORDER_TYPE_SELL and tp > op):
                val *= -1
            total_tp += val

        if sl > 0:
            dist = abs(sl - op) / pt
            val = dist * tv * vol * -1
            total_sl += val

    risk_pct = abs(total_sl / balance * 100) if balance else 0
    print(f"Trades Summary     : BUY = {buy}   | SELL = {sell}")
    print(f"{color(cur_pl)}Total Current P&L : ${cur_pl:.2f}{RESET}")
    print(f"{GREEN}TP Target         : ${total_tp:.2f}{RESET}")
    print(f"{RED}SL Risk           : ${total_sl:.2f}{RESET}")
    print(f"Risk on Account   : {risk_pct:.2f}%")
    print(f"Account Balance   : ${balance:.2f}")
    print(f"{color(pnl_today)}Today's P&L       : {wins}W-{losses}L | ${pnl_today:.2f}{RESET}")
    print("\nTAB = Toggle Summary/Details")

def print_details(positions):
    print("\n====== DETAILS ======\n")
    if not positions:
        print("No open trades.")
        return

    for pos in positions:
        info = mt5.symbol_info(pos.symbol)
        if not info: continue
        pt, tv = info.point, info.trade_tick_value
        sym, vol, typ = pos.symbol, pos.volume, pos.type
        op, tp, sl, cur = pos.price_open, pos.tp, pos.sl, pos.profit
        trade_type = "BUY" if typ == mt5.ORDER_TYPE_BUY else "SELL"

        print(f"{sym} | {trade_type} | Volume: {vol:.2f}")
        print(f"{color(cur)}Current P&L       : ${cur:.2f}{RESET}")

        if tp > 0:
            dist = abs(tp - op) / pt
            val = dist * tv * vol
            if (typ == mt5.ORDER_TYPE_BUY and tp < op) or (typ == mt5.ORDER_TYPE_SELL and tp > op):
                val *= -1
            print(f"{color(val)}TP Target         : ${val:.2f}{RESET}")
        else:
            print("TP Target         : Not Set")

        if sl > 0:
            dist = abs(sl - op) / pt
            val = dist * tv * vol * -1
            print(f"{color(val)}SL Risk           : ${val:.2f}{RESET}")
        else:
            print("SL Risk           : Not Set")

        if tp > 0 and sl > 0:
            rr = abs(tp - op) / abs(sl - op)
            print(f"R/R Ratio         : {rr:.2f}")
        print()

def run_loop():
    global SHOW_DETAILS
    print_loading()

    while True:
        clear_screen()
        positions, wins, losses, pnl_today, balance = get_trade_data()

        if SHOW_DETAILS:
            print_details(positions)
        else:
            print_summary(positions, wins, losses, pnl_today, balance)

        for _ in range(100):
            if msvcrt.kbhit():
                if msvcrt.getch() == b'\t':
                    SHOW_DETAILS = not SHOW_DETAILS
                    break
            time.sleep(REFRESH_DELAY)

# Initialize and run
if not mt5.initialize():
    clear_screen()
    print(f"{RED}❌ Failed to connect to MetaTrader 5.{RESET}")
    print("Make sure MT5 is running and logged in.")
    input("Press Enter to exit...")
    sys.exit()
else:
    try:
        run_loop()
    except Exception as e:
        print(f"{RED}Unexpected error: {e}{RESET}")
        input("Press Enter to exit...")
    finally:
        mt5.shutdown()

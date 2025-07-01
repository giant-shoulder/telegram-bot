import asyncio
from datetime import datetime
from config import CHECK_INTERVAL, LONG_TERM_PERIOD
from strategies.utils.streak import get_streak_advisory
from utils import is_weekend
from db import connect_to_db, close_db_connection, store_rate, get_recent_rates
from fetcher import get_usdkrw_rate
from notifier import send_telegram, send_start_message
from strategies import (
    analyze_bollinger,
    analyze_jump,
    analyze_crossover,
    analyze_combo
)

async def run_watcher():
    await send_start_message()

    conn = await connect_to_db()
    prev_rate = None
    prev_short_avg, prev_long_avg = None, None
    upper_streak = 0
    lower_streak = 0
    prev_upper_level = 0
    prev_lower_level = 0

    try:
        while True:
            if is_weekend():
                print(f"[{datetime.now()}] ⏸️ 주말, 알림 일시 정지 중...")
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            rate = get_usdkrw_rate()
            if rate:
                print(f"[{datetime.now()}] 📈 환율: {rate}")
                await store_rate(conn, rate)
                rates = await get_recent_rates(conn, LONG_TERM_PERIOD)

                # 전략별 분석
                b_status, b_msg = analyze_bollinger(rates, rate, prev=prev_rate)
                j_msg = analyze_jump(prev_rate, rate)
                c_msg, prev_short_avg, prev_long_avg = analyze_crossover(
                    rates, prev_short_avg, prev_long_avg
                )

                # streak 추적
                if b_status == "upper_breakout":
                    upper_streak += 1
                    lower_streak = 0
                elif b_status == "lower_breakout":
                    lower_streak += 1
                    upper_streak = 0
                else:
                    upper_streak = 0
                    lower_streak = 0

                # 단일 전략 메시지 전송
                for msg in [b_msg, j_msg, c_msg]:
                    if msg:
                        await send_telegram(msg)

                # streak 기반 추가 경고 판단 (✅ 복합 조건 없어도 수행됨)
                new_upper_level, new_lower_level, streak_msg = get_streak_advisory(
                    upper_streak, lower_streak,
                    cross_msg=c_msg,
                    jump_msg=j_msg,
                    prev_upper=prev_upper_level,
                    prev_lower=prev_lower_level
                )

                if streak_msg:
                    await send_telegram(f"🧭 *동일 신호 반복 알림:*\n{streak_msg}")
                    prev_upper_level = new_upper_level
                    prev_lower_level = new_lower_level

                # 복합 전략 분석 및 메시지 전송
                result = analyze_combo(
                    b_status, b_msg, j_msg, c_msg,
                    upper_streak, lower_streak,
                    prev_upper_level, prev_lower_level
                )

                if result:
                    prev_upper_level = result["new_upper_level"]
                    prev_lower_level = result["new_lower_level"]
                    await send_telegram(result["message"])

                prev_rate = rate
            else:
                print(f"[{datetime.now()}] ❌ 환율 조회 실패")

            await asyncio.sleep(CHECK_INTERVAL)

    finally:
        await close_db_connection(conn)
        print(f"[{datetime.now()}] 🛑 워처 종료, DB 연결 닫힘")

if __name__ == "__main__":
    asyncio.run(run_watcher())
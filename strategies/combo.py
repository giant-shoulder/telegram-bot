from strategies.utils.signal_utils import get_signal_score, get_signal_direction, generate_combo_header
from strategies.utils.streak import get_streak_advisory
from strategies.utils.score_bar import get_score_bar

def analyze_combo(
    b_status: str,
    b_msg: str,
    j_msg: str,
    c_msg: str,
    e_msg: str,  # ✅ 예상범위 메시지
    upper_streak: int,
    lower_streak: int,
    prev_upper_level: int,
    prev_lower_level: int
):
    """
    활성화된 전략 메시지를 기반으로:
    - 전략 간 공통 해석
    - 종합 점수 산정
    - 방향성 판단 (매수/매도/충돌/무신호)
    - 반복 돌파 기반 추가 경고
    를 통합적으로 수행해 메시지로 반환합니다.
    """

    signals = {
        "📊 볼린저 밴드": b_msg,
        "⚡ 급변 감지": j_msg,
        "🔁 이동평균선 크로스": c_msg,
        "📡 예상 환율 레인지 이탈": e_msg
    }
    active_signals = {k: v for k, v in signals.items() if v}
    if len(active_signals) < 2:
        return None

    score = get_signal_score(active_signals)
    direction = get_signal_direction(active_signals.values())

    # 헤더 및 액션 메시지
    header = generate_combo_header(
        score=score,
        matched=len(active_signals),
        total=len(signals),
        direction=direction
    )
    action = {
        "buy": (
            "🟢 *매수 진입 타이밍으로 판단됩니다.*\n"
            "📉 *시장이 과도하게 하락했거나, 반등 신호가 감지되었습니다.*\n"
            "💡 추세 전환, 저점 반등 가능성을 고려한 진입 타이밍입니다."
        ),
        "sell": (
            "🔴 *매도 고려 타이밍으로 판단됩니다.*\n"
            "📈 *시장이 과열되었거나, 하락 전환 신호가 감지되었습니다.*\n"
            "💡 피크 도달 또는 고점 차익 실현 구간일 수 있습니다."
        ),
        "conflict": (
            "⚠️ *전략 간 방향성이 상충됩니다.*\n"
            "💡 서로 다른 시그널이 동시에 감지되어, 섣부른 진입보다는 관망이 권장됩니다."
        ),
        "neutral": (
            "ℹ️ *명확한 방향성이 없습니다.*\n"
            "💡 시장 상황을 조금 더 지켜보는 것이 좋겠습니다."
        )
    }.get(direction, "해석 오류")

    # 상세 전략 메시지 정리
    signal_details = "\n\n".join([f"{k}\n{v}" for k, v in active_signals.items()])
    score_bar = get_score_bar(score, direction)

    # 연속 돌파에 대한 추가 경고 판단
    new_upper, new_lower, streak_msg = get_streak_advisory(
        upper_streak, lower_streak,
        cross_msg=c_msg,
        jump_msg=j_msg,
        prev_upper=prev_upper_level,
        prev_lower=prev_lower_level
    )

    # 메시지 조합
    message = (
        f"{header}\n\n"
        f"{signal_details}\n\n"
        f"{action}\n\n"
        f"🧮 신호 점수: *{score}점*\n"
        f"{score_bar}"
    )
    if streak_msg:
        message += f"\n\n🧭 *추가 참고:*\n{streak_msg}"

    return {
        "message": message,
        "type": direction,
        "score": score,
        "new_upper_level": new_upper,
        "new_lower_level": new_lower
    }
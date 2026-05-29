# ui/components.py
import streamlit as st

def showcase_examples_card():
    st.markdown("### ✨ 프롬프트 개선 사례 (Before → After)")

    examples = [
        {
            "bad": "for문 예제 보여줘.",
            "good": "파이썬 초보자를 위해, for문으로 1부터 5까지 출력하는 예제 코드를 작성하고 각 줄이 하는 일을 한 줄씩 설명해 주세요.",
            "tip": "목표(예제) + 범위(1~5) + 출력(코드) + 설명(각 줄)"
        },
        {
            "bad": "이 코드 왜 안돼?",
            "good": "아래 파이썬 코드의 오류 원인을 2가지 이상 설명하고, 수정된 코드와 예상 출력 예시를 제시해 주세요.\n\n[코드]\n(여기에 코드를 붙여넣기)",
            "tip": "입력(코드) + 요구(원인 2개) + 출력(수정 코드+예상 출력)"
        },
        {
            "bad": "변수를 쉽게 설명해줘.",
            "good": "중학생 수준을 대상으로, 파이썬 변수 개념을 '사과 개수' 같은 일상 비유로 5문장 이내로 설명하고 간단한 예제 코드 1개를 포함해 주세요.",
            "tip": "대상(중학생) + 길이(5문장) + 예제(1개)"
        },
        {
            "bad": "입력받아서 계산하는 코드 만들어줘",
            "good": "사용자로부터 두 정수 a, b를 입력받아 합/차/곱/몫(정수 나눗셈)을 출력하는 파이썬 코드를 작성해 주세요. b=0일 때는 나눗셈을 건너뛰고 안내 문구를 출력해 주세요. 입력/출력 예시도 포함해 주세요.",
            "tip": "조건(0 나눗셈) + 출력 항목(합/차/곱/몫) + 예시"
        },
    ]

    if "showcase_idx" not in st.session_state:
        st.session_state.showcase_idx = 0

    idx = st.session_state.showcase_idx
    ex = examples[idx]

    # 카드 컨테이너
    with st.container(border=True):
        st.markdown("**Before (모호한 프롬프트)**")
        st.markdown(f"> {ex['bad']}")

        st.markdown("**After (개선된 프롬프트)**")
        st.code(ex["good"], language="text")

        st.info(f"✅ 개선 포인트: {ex['tip']}")

        c1, c2, c3, c4 = st.columns([1, 1, 2, 2], vertical_alignment="center")
        with c1:
            if st.button("◀ 이전", key="prev_case", use_container_width=True):
                st.session_state.showcase_idx = (idx - 1) % len(examples)
                st.rerun()
        with c2:
            if st.button("다음 ▶", key="next_case", use_container_width=True):
                st.session_state.showcase_idx = (idx + 1) % len(examples)
                st.rerun()
        with c3:
            st.caption(f"{idx+1} / {len(examples)}")
        with c4:
            st.caption("공식: 대상 + 목표 + 조건/범위 + 출력형식")

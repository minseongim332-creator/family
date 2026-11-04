"""성적 로드맵 | 실행: streamlit run app.py
5등급 평균을 9등급 척도로 선형 변환하는 학습 계획용 시뮬레이터.
실제 석차등급/백분위/대학별 환산을 복원하는 프로그램이 아닙니다.
성적은 서버 파일이나 외부 데이터베이스에 저장하지 않습니다.
"""
from decimal import Decimal, ROUND_HALF_UP
from math import floor
import streamlit as st

SEMESTERS = ['1학년 1학기', '1학년 2학기', '2학년 1학기', '2학년 2학기', '3학년 1학기']
MODES = [
    ('균형 달성형', '매 학기 일정한 페이스로', 'equal'),
    ('점진 상승형', '처음에는 여유 있게, 점점 더 높은 성적으로', 'rise'),
    ('초반 집중형', '초반에 집중하고, 뒤에는 부담을 줄이기', 'front'),
]


def to_units(value):
    """소수 둘째 자리까지의 등급을 정수 단위로 변환."""
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def convert_grade(grade):
    if not 1 <= grade <= 5:
        raise ValueError('5등급제 평균은 1~5 사이여야 합니다.')
    return (2 * to_units(grade) - 100) / 100


def distribute(total_units, count, mode):
    """합계와 1~9 경계를 보존하는 0.01등급 단위 로드맵.
    최대 앞뒤 차이 2등급. 경계 근처에서는 차이를 자동 축소.
    """
    if count <= 0 or mode not in {'equal', 'rise', 'front'}:
        raise ValueError('학기 수 또는 모드를 확인하세요.')
    if not 100 * count <= total_units <= 900 * count:
        raise ValueError('실현 불가능한 남은 학기 합계입니다.')
    mean = total_units / count
    amplitude = min(100.0, mean - 100, 900 - mean)
    if count == 1 or mode == 'equal':
        values = [mean] * count
    else:
        weights = [1 - 2 * i / (count - 1) for i in range(count)]
        sign = 1 if mode == 'rise' else -1
        values = [mean + sign * amplitude * w for w in weights]
    rounded = [floor(v + 1e-9) for v in values]
    residual = total_units - sum(rounded)
    order = sorted(range(count), key=lambda i: (-(values[i] - rounded[i]), i))
    for i in order[:residual]:
        rounded[i] += 1
    # 같은 값의 반올림 순서가 상승/완화 방향을 뒤집지 않게 정렬.
    if mode == 'rise':
        rounded.sort(reverse=True)
    elif mode == 'front':
        rounded.sort()
    assert sum(rounded) == total_units
    assert all(100 <= v <= 900 for v in rounded)
    return rounded


def plan_status(completed, target):
    remaining = 5 - len(completed)
    done_sum = sum(to_units(convert_grade(g)) for g in completed)
    required = to_units(target) * 5 - done_sum
    if remaining == 0:
        return {'remaining': 0, 'sum': done_sum, 'required': required, 'status': 'finished'}
    minimum, maximum = 100 * remaining, 900 * remaining
    status = 'impossible' if required < minimum else 'secured' if required > maximum else 'feasible'
    return {'remaining': remaining, 'sum': done_sum, 'required': required,
            'planned': max(minimum, min(maximum, required)), 'status': status}


def render():
    st.set_page_config(page_title='성적 로드맵', page_icon='🎯', layout='wide', initial_sidebar_state='expanded')
    st.markdown('''<style>
    .stApp { background: #f6f8fc; color: #18243a; }
    .block-container { max-width: 1120px; padding-top: 2rem; }
    [data-testid="stSidebar"] { background: #eef2fa; }
    .st-key-summary { position: sticky; top: 3.6rem; z-index: 99;
      background: #ffffff; border: 1px solid #dce4f1; border-radius: 18px;
      padding: 16px 22px; box-shadow: 0 6px 22px #17356712; }
    .summary-label { color: #42536c; font-size: 14px; font-weight: 600; }
    .summary-value { color: #3455c5; font-size: 34px; font-weight: 800; line-height: 1.3; }
    .summary-note { color: #526079; font-size: 12px; margin-top: 4px; }
    h1, h2, h3 { color: #18243a; }
    @media(max-width: 640px) {
      .st-key-summary { top: 3.4rem; padding: 12px 14px; }
      .summary-value { font-size: 27px; }
    }
    </style>''', unsafe_allow_html=True)

    with st.sidebar:
        st.title('🎯 성적 로드맵')
        st.caption('입력은 간단하게 · 계획은 구체적으로')
        st.subheader('01  성적이 나온 학기')
        n = st.selectbox('어디까지 성적이 나왔나요?', range(6),
                         format_func=lambda x: '아직 성적이 없어요' if x == 0 else SEMESTERS[x - 1] + '까지',
                         index=2, key='completed_count')
        st.subheader('02  학기 평균 입력')
        st.caption('5등급제 평균 · 소수 둘째 자리 · 낮을수록 좋은 성적')
        grades = []
        for i in range(n):
            grade = st.number_input(SEMESTERS[i], min_value=1.0, max_value=5.0,
                                    value=None, step=0.01, format='%.2f', key=f'grade_{i}',
                                    placeholder='예: 2.50')
            grades.append(grade)
        if n == 0:
            st.info('성적 입력 없이 5개 학기 전체를 계획합니다.')
        st.subheader('03  최종 목표')
        target = st.number_input('목표 평균 (9등급 환산 척도)', min_value=1.0, max_value=9.0,
                                 value=3.0, step=0.01, format='%.2f', key='target')
        st.caption('3학년 1학기까지 총 5개 학기 평균입니다. 입력 즉시 다시 계산됩니다.')
        st.divider()
        st.caption('별도 로그인·저장 없음. 입력 성적을 파일이나 데이터베이스로 기록하지 않습니다.')

    ready = all(g is not None for g in grades)
    current = sum(convert_grade(g) for g in grades) / n if ready and n else None
    with st.container(key='summary'):
        value = f'{current:.2f} 등급' if current is not None else '성적 입력 대기' if n else '새 학기부터 시작'
        st.markdown(f'''<div class="summary-label">현재 평균 · 9등급 척도 환산값</div>
        <div class="summary-value">{value}</div>
        <div class="summary-note">단순 선형 환산 · 실제 석차/대입 환산 아님 · 목표 {target:.2f} · 남은 {5-n}학기</div>''', unsafe_allow_html=True)

    st.title('목표까지, 나만의 학기별 계획')
    st.write('같은 목표도 도달하는 방법은 다릅니다. 나에게 맞는 학습 페이스를 선택하세요.')
    st.warning('이 앱은 학습 계획용 시뮬레이터입니다. 5등급제 평균만으로 실제 9등급제 성적을 알아낼 수 없습니다. 아래 수치는 공식 환산 성적이 아닙니다.')

    with st.expander('환산 방식과 계산 가정 확인하기'):
        st.markdown('''**단순 척도 환산:** `9등급 환산값 = 2 × 5등급제 평균 − 1`

- 1.00 → 1.00 / 2.00 → 3.00 / 3.00 → 5.00 / 4.00 → 7.00 / 5.00 → 9.00
- 이는 두 척도의 양 끝을 맞춘 **앱의 임의 선형 모델**입니다. 석차 비율을 반영한 등가 환산이 아닙니다.
- 예를 들어 5등급제 1등급이라고 실제 9등급제 1등급인 것은 아닙니다.
- 모든 학기를 같은 비중(각 20%)으로 반영합니다. 과목별 학점·단위 수, 대학별 가중치 및 제외 과목은 반영하지 않습니다.
- 학기 평균에는 성취도 A~E가 아닌 **5등급제 석차등급 평균**을 입력하세요.
- 목표 달성은 최종 평균이 목표값 **이하**인 경우입니다. 낮은 숫자가 더 좋은 성적입니다.
- 점진 상승형은 뒤로 갈수록 등급 숫자가 작아집니다. 초반 집중형은 반대입니다.
- 차등 모드의 첫 학기와 마지막 학기 차이는 최대 2.00등급(9등급 척도)이며, 1~9 경계를 넘지 않도록 자동 축소됩니다. 이는 학습 능력 예측이 아닌 배분 규칙입니다.
- 내부 계산과 계획은 9등급 척도 0.01단위 합계를 보존합니다. 5등급 참고값은 역환산 후 표시 반올림한 값입니다.

배경 참고: [교육부 발표를 소개한 정책브리핑](https://www.korea.kr/news/policyNewsView.do?newsId=148921172)의 5등급 구간 비율은 10·24·32·24·10%입니다. 이 출처는 **앱의 선형 환산 공식을 제시하거나 보증하지 않습니다.**''')

    if not ready:
        st.info('왼쪽 입력창에서 선택한 학기까지의 평균을 모두 입력하면 3가지 로드맵이 표시됩니다. 휴대폰에서는 왼쪽 위 사이드바 버튼을 눌러주세요.')
        return

    state = plan_status(grades, target)
    r, done_sum = state['remaining'], state['sum']
    if r == 0:
        actual = done_sum / 500
        st.subheader('5개 학기 성적 입력 완료')
        if actual <= target + 1e-9:
            st.success(f'최종 환산 평균 {actual:.2f}등급으로 목표 {target:.2f}등급을 달성했습니다.')
        else:
            st.warning(f'최종 환산 평균 {actual:.2f}등급입니다. 목표 {target:.2f}등급에는 도달하지 못했고, 계획할 남은 학기가 없습니다.')
    else:
        best, worst = (done_sum + 100*r)/500, (done_sum + 900*r)/500
        c1, c2, c3 = st.columns(3)
        c1.metric('남은 학기', f'{r}학기')
        c2.metric('최종 목표 · 9등급 척도', f'{target:.2f}')
        c3.metric('가능한 최선의 최종 평균', f'{best:.2f}')
        if state['status'] == 'impossible':
            st.error(f'현재 모델에서는 목표 달성이 불가능합니다. 남은 학기 모두 1.00등급이어도 최종 평균은 {best:.2f}입니다. 아래는 목표 달성안이 아닌 최선의 대안입니다.')
        elif state['status'] == 'secured':
            st.success(f'이미 목표 이하의 최종 평균이 보장됩니다. 남은 학기 모두 9.00등급이어도 {worst:.2f}입니다. 목표 숫자와 정확히 같게 만들 수는 없지만 더 좋은 결과를 얻습니다.')
        else:
            st.success(f'남은 {r}개 학기에 필요한 평균은 {state["required"] / (100*r):.3f}등급입니다 (9등급 환산 척도).')
        if r == 1:
            st.info('남은 학기가 1개라 세 모드의 계획이 같습니다.')
        elif state['planned'] in (100*r, 900*r):
            st.info('성적 범위의 끝값에서는 배분 여지가 없어 세 모드가 같습니다.')
        tabs = st.tabs([item[0] for item in MODES])
        for tab, (name, tagline, mode) in zip(tabs, MODES):
            with tab:
                st.subheader(name)
                st.caption(tagline)
                path = distribute(state['planned'], r, mode)
                rows = []
                running = done_sum
                for j, units in enumerate(path):
                    running += units
                    grade9 = units / 100
                    rows.append({'학기': SEMESTERS[n+j], '목표 · 9등급 환산': f'{grade9:.2f}',
                                 '5등급제 참고값 ≈': f'{(grade9+1)/2:.2f}',
                                 '예상 누적 · 9등급 환산': f'{running / (100*(n+j+1)):.3f}'})
                st.table(rows)
                final = (done_sum + sum(path)) / 500
                st.markdown(f'**이 계획의 최종 평균: {final:.3f}등급** · 목표 {target:.2f}등급')
                st.caption('각 학기에 표의 등급 또는 그보다 좋은 성적을 받는 계획입니다. 5등급제 참고값은 반올림된 근삿값이므로 정확한 검산은 9등급 환산 열을 기준으로 합니다.')
                if mode == 'equal':
                    st.caption('0.01단위로 균등 분배하므로 학기 사이에 최대 0.01 차이가 있을 수 있습니다.')

    if grades:
        with st.expander('입력한 성적 확인'):
            st.table([{'학기': SEMESTERS[i], '입력 · 5등급제': f'{g:.2f}',
                       '9등급 척도 환산': f'{convert_grade(g):.2f}'} for i, g in enumerate(grades)])
    st.divider()
    st.caption('성적 로드맵 · 공부 계획을 돕는 참고 도구이며 입시 결과나 성적 향상을 보장하지 않습니다.')


if __name__ == '__main__':
    render()

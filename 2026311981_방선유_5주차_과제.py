# BB84 프로토콜 시뮬레이터
# 2026311981 방선유
# 실행: 큐비트 수, 도청 여부, 도청 확률, 노이즈 확률을 입력한다.
import random


DEFAULT_EVE_RATE = 0.5  # 도청 확률을 입력하지 않으면 사용하는 기본값
DEFAULT_NOISE_RATE = 0.01  # 노이즈 확률 입력의 기본값: 1%
ERROR_THRESHOLD = 0.11  # 학습용 오류율 기준이며 도청의 확정 판정은 아니다.
BASES = ("+", "x")  # 서로 다른 두 측정 기저


def measure(bit, sent_basis, measurement_basis):
    """같은 기저에서는 원래 비트, 다른 기저에서는 무작위 비트를 반환한다."""
    if sent_basis == measurement_basis:
        return bit
    return random.randint(0, 1)


def simulate(qubit_count, eve_enabled, eve_rate=DEFAULT_EVE_RATE, noise_rate=0):
    """비트와 기저로 상태를 표현하고, 전송 노이즈를 비트 반전으로 모델링한다."""
    if qubit_count < 1:
        raise ValueError("큐비트 수는 1 이상이어야 합니다.")
    if not 0 <= eve_rate <= 1:
        raise ValueError("도청 확률은 0~1 사이여야 합니다.")
    if not 0 <= noise_rate <= 1:
        raise ValueError("노이즈 확률은 0~1 사이여야 합니다.")

    alice_bits = [random.randint(0, 1) for _ in range(qubit_count)]
    alice_bases = [random.choice(BASES) for _ in range(qubit_count)]
    bob_bases = [random.choice(BASES) for _ in range(qubit_count)]
    bob_bits = []
    eve_bases = []
    eve_bits = []
    noise_positions = []

    for i in range(qubit_count):
        sent_bit = alice_bits[i]
        sent_basis = alice_bases[i]
        eve_basis = "-"
        eve_bit = "-"
        if eve_enabled and random.random() < eve_rate:
            eve_basis = random.choice(BASES)
            eve_bit = measure(sent_bit, sent_basis, eve_basis)
            # Eve가 측정한 비트와 기저로 새 상태를 만들어 Bob에게 보낸다.
            sent_bit, sent_basis = eve_bit, eve_basis
        # Eve의 재전송 이후, Bob에게 도착하기 전에 상태의 비트를 뒤집는다.
        if random.random() < noise_rate:
            sent_bit = 1 - sent_bit
            noise_positions.append(i)
        eve_bases.append(eve_basis)
        eve_bits.append(eve_bit)
        bob_bits.append(measure(sent_bit, sent_basis, bob_bases[i]))

    # 기저만 공개 비교하고, 기저가 일치하는 위치를 키 후보로 남긴다.
    sifted = [i for i in range(qubit_count) if alice_bases[i] == bob_bases[i]]
    # 후보가 하나뿐이면 모두 검사하며, 최종 키는 생성하지 못한다.
    sample_count = max(1, len(sifted) // 2) if sifted else 0
    checked = set(random.sample(sifted, sample_count))
    errors = sum(alice_bits[i] != bob_bits[i] for i in checked)
    error_rate = errors / sample_count if sample_count else None
    # 공개한 검사 비트는 키로 재사용하지 않는다. 원래 전송 순서를 유지한다.
    remaining = [i for i in sifted if i not in checked]
    alice_key = "".join(str(alice_bits[i]) for i in remaining)
    bob_key = "".join(str(bob_bits[i]) for i in remaining)

    return {
        "eve_rate": eve_rate if eve_enabled else 0,
        "noise_rate": noise_rate, "noise_positions": noise_positions,
        "alice_bits": alice_bits, "alice_bases": alice_bases,
        "bob_bits": bob_bits, "bob_bases": bob_bases,
        "eve_bits": eve_bits, "eve_bases": eve_bases,
        "sifted": sifted, "checked": checked, "remaining": remaining,
        "errors": errors, "error_rate": error_rate,
        "alice_key": alice_key, "bob_key": bob_key,
        "suspected": error_rate is not None and error_rate > ERROR_THRESHOLD,
    }


def show_result(result):
    """전송 과정, 표본 오류율, 검사 후 남은 키를 출력한다."""
    count = len(result["alice_bits"])
    sifted_set = set(result["sifted"])
    print("\n[전송 과정: 최대 40개 표시]")
    print("번호 | Alice(비트/기저) | Eve(비트/기저) | Bob(비트/기저) | 처리")
    for i in range(min(count, 40)):
        if i in result["checked"]:
            status = "검사"
        elif i in sifted_set:
            status = "키 후보"
        else:
            status = "기저 불일치"
        print(
            f"{i + 1:4} | {result['alice_bits'][i]}/{result['alice_bases'][i]}"
            f"               | {result['eve_bits'][i]}/{result['eve_bases'][i]}"
            f"             | {result['bob_bits'][i]}/{result['bob_bases'][i]}"
            f"             | {status}"
        )
    if count > 40:
        print(f"... 나머지 {count - 40}개는 표시를 생략합니다.")

    intercepted = sum(basis != "-" for basis in result["eve_bases"])
    print("\n[검사 결과]")
    print(f"설정한 도청 확률: {result['eve_rate']:.2%}")
    print(f"노이즈 확률: {result['noise_rate']:.2%} / 반전된 큐비트: {len(result['noise_positions'])}개")
    print(f"전송 큐비트: {count}개 / 실제 도청: {intercepted}개")
    print(f"기저 일치: {len(result['sifted'])}개")
    print(f"검사 비트: {len(result['checked'])}개 / 오류: {result['errors']}개")
    if result["error_rate"] is None:
        print("오류율: 계산 불가 / 판정: 검사할 비트가 부족합니다.")
        print("최종 공유 키: 생성 불가. 큐비트 수를 늘려 다시 실행하세요.")
        return

    print(f"검사 오류율: {result['error_rate']:.2%}")
    print(f"도청 의심 기준: 오류율 {ERROR_THRESHOLD:.0%} 초과 (학습용)")
    if result["suspected"]:
        print("판정: 도청 의심 또는 높은 노이즈. 오류율이 기준을 초과했습니다.")
    else:
        print("판정: 오류율이 기준 이하입니다. 도청 부재를 보장하지는 않습니다.")

    print("\n[검사 비트를 제거한 키 후보]")
    print(f"Alice: {result['alice_key'] or '(없음)'}")
    print(f"Bob  : {result['bob_key'] or '(없음)'}")
    if result["suspected"]:
        print("최종 공유 키: 폐기 (도청 의심 또는 높은 노이즈)")
    elif not result["alice_key"]:
        print("최종 공유 키: 생성 불가 (남은 비트 없음)")
    elif result["alice_key"] != result["bob_key"]:
        # 전체 비교는 학습용 관찰 결과이며 실제 프로토콜의 도청 판정이 아니다.
        print("시뮬레이터 관찰: 오류율은 기준 이하이지만 남은 두 키가 다릅니다.")
        print("최종 공유 키: 불일치 (이 프로그램은 오류 정정을 구현하지 않습니다.)")
    else:
        print(f"최종 공유 키 (학습용): {result['alice_key']}")
        print(f"키 길이: {len(result['alice_key'])}비트")


def read_qubit_count():
    while True:
        try:
            count = int(input("전송할 큐비트 수 (1~100000): "))
            if 1 <= count <= 100000:
                return count
        except ValueError:
            pass
        print("1~100000 사이의 정수를 입력하세요.")


def read_eve_enabled():
    while True:
        answer = input("도청자 Eve를 포함할까요? (y/n): ").strip().lower()
        if answer in ("y", "yes", "예", "네"):
            return True
        if answer in ("n", "no", "아니오", "아니요"):
            return False
        print("y 또는 n을 입력하세요.")


def read_probability(label, default):
    """백분율로 입력받은 확률을 0~1 범위로 바꾼다."""
    while True:
        answer = input(f"{label} (0~100%, Enter: {default:.0%}): ").strip()
        if not answer:
            return default
        try:
            percent = float(answer)
            if 0 <= percent <= 100:
                return percent / 100
        except ValueError:
            pass
        print("0~100 사이의 숫자를 입력하세요. 예: 25 또는 12.5")


def read_eve_rate():
    return read_probability("Eve의 도청 확률", DEFAULT_EVE_RATE)


def main():
    print("=== BB84 프로토콜 시뮬레이터 ===")
    print("기저: +, x / 도청 확률과 전송 노이즈 확률을 설정할 수 있습니다.")
    print("기저가 일치한 비트 중 절반(최소 1개)을 무작위로 검사합니다.")
    print("학습용 모델로, 실제 양자 장비나 오류 정정·프라이버시 증폭은 사용하지 않습니다.")
    try:
        count = read_qubit_count()
        eve_enabled = read_eve_enabled()
        eve_rate = read_eve_rate() if eve_enabled else 0
        noise_rate = read_probability("전송 노이즈 확률", DEFAULT_NOISE_RATE)
        show_result(simulate(count, eve_enabled, eve_rate, noise_rate))
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 중단되어 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()

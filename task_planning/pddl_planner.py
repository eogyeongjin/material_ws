#!/usr/bin/env python3
import subprocess
import argparse

# PDDL domain/problem 파일을 불러와 외부 플래너를 실행하고 결과 플랜을 출력하는 스켈레톤 코드

def parse_args():
    parser = argparse.ArgumentParser(description="PDDL 플래너 실행기 스켈레톤")
    parser.add_argument("--domain", required=True, help="domain.pddl 경로")
    parser.add_argument("--problem", required=True, help="problem.pddl 경로")
    parser.add_argument("--planner", default="/path/to/planner", help="플래너 실행 파일 경로")
    return parser.parse_args()


def run_planner(planner_exec, domain_file, problem_file):
    """
    외부 플래너를 호출하여 raw 출력 결과를 반환
    """
    cmd = [planner_exec, domain_file, problem_file]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"플래너 실행 오류: {result.stderr}")
        raise RuntimeError("플래너 실행 실패")
    return result.stdout


def parse_plan(raw_output):
    """
    플래너 출력(raw_output)에서 action 시퀀스를 파싱하여 리스트로 반환
    (플래너에 따라 parsing 로직을 수정)
    """
    plan = []
    for line in raw_output.splitlines():
        # 예시: "0: (move robot room1 room2) [1]"
        line = line.strip()
        if line and line[0].isdigit():
            # 콜론 기준으로 나눈 뒤 액션 부분만 추출
            action = line.split(':', 1)[1].strip()
            plan.append(action)
    return plan


def main():
    args = parse_args()
    raw = run_planner(args.planner, args.domain, args.problem)
    plan = parse_plan(raw)

    print("생성된 플랜:")
    for idx, act in enumerate(plan, start=1):
        print(f"{idx}. {act}")


if __name__ == "__main__":
    main()

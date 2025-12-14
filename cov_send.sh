#!/bin/bash
# udp_listener.sh

PORT=9999
KEYWORD="RUN"
PASSWORD="1234"
CORE_CPU1_NAME="c2a-example-mob"
EXIT_NOTICE_PORT=7777
CHECK_INTERVAL=2

echo "▶ Listening on UDP port ${PORT}..."

# 함수: core-cpu1 종료 감지 및 메시지 전송
check_core_cpu1() {
    local was_running=0
    while true; do
        if pgrep -x "$CORE_CPU1_NAME" > /dev/null; then
            was_running=1
        else
            if [[ $was_running -eq 1 ]]; then
                echo "⚠️ ${CORE_CPU1_NAME} 종료 감지됨. 종료 메시지 전송 중..."
                echo "Crash Detected" | nc -u -w1 10.0.2.1 "$EXIT_NOTICE_PORT"
                was_running=0  # 다시 시작하면 감지하도록 초기화
            fi
        fi
        sleep "$CHECK_INTERVAL"
    done
}

# 백그라운드에서 종료 감지 루프 실행
check_core_cpu1 &

# UDP 수신 루프
while true; do
    nc -u -l -p "${PORT}" | while IFS= read -r LINE; do
        echo "Received: ${LINE}"
        if [[ "${LINE}" == *"${KEYWORD}"* ]]; then
            echo "⚠️ Detected keyword '${KEYWORD}' in message!"
            echo "$PASSWORD" | sudo -S ./share_cov_dir_setting.sh
            ./coverage_logger.sh
        fi
    done
done
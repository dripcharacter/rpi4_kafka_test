#!/bin/bash

echo "test success" >> /home/wsms8646/rpi4_kafka_test/result.txt

_EXEC_PATH="kafka_produce.py"
_EXEC_DIR="/home/wsms8646/rpi4_kafka_test/kafka_produce.py"
function PID_CHECK() {
        RUNNING_STAT=$(ps ax | grep $_EXEC_PATH | grep -v watchdog.sh | grep -v rotatelogs | grep -v grep | awk '{print $3}')

        echo $RUNNING_STAT
        if [[ "$RUNNING_STAT" =~ ^[RS] ]]; then
                echo "[$1] Process is running."
        else
                echo "[$1] Process is stopped."
                nohup python -u $_EXEC_DIR &
                # Wait for running.
                sleep 3
        fi
}

while true; do
        sleep 3
        PID_CHECK "$_EXEC_PATH" "$_EXEC_DIR"
done

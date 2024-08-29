import cv2
import av
import os
import time
import uuid
import queue
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from concurrent.futures import ThreadPoolExecutor


def get_last_offset(server_ip, server_port, topic_name):
    consumer = KafkaConsumer(bootstrap_servers=f"{server_ip}:{server_port}")
    partitions = consumer.partitions_for_topic(topic_name)
    last_offset = 0
    if partitions is not None:
        for partition in partitions:
            tp = TopicPartition(topic_name, partition)
            consumer.assign([tp])
            consumer.seek_to_end(tp)
            offset = consumer.position(tp)
            last_offset = max(last_offset, offset)
    consumer.close()
    return last_offset

def capture_frames(frame_queue: queue.Queue, threshold_time):
    while True:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Failed to open camera")
            continue
        cur_fps=cap.get(cv2.CAP_PROP_FPS)
        cur_frame_num=0
        start_time=time.time()
        while True:
            if ((time.time()-start_time)*cur_fps-cur_frame_num) > threshold_time * cur_fps:
                print("restart the camera")
                break
            ret, frame = cap.read()
            cur_frame_num+=1
            if not ret:
                print(f"cv2.VideoCapture error")
                break
            frame_queue.put(frame)
        cap.release()

def encode_and_send(frame_queue, server_ip, server_port, topic_name, cur_fps, frame_size, threshold_time):
    producer = KafkaProducer(
        bootstrap_servers=f"{server_ip}:{server_port}",
        max_request_size=5242880
    )
    cur_offset=get_last_offset(server_ip, server_port, topic_name)
    while True:
        cur_time=time.time()
        frames = []
        start_time = time.time()
        while time.time() - start_time < threshold_time:
            try:
                frame = frame_queue.get(timeout=0.1)
                frames.append(frame)
                if len(frames) >= cur_fps * threshold_time:
                    break
            except queue.Empty:
                continue

        if not frames:
            continue

        output_file = str(uuid.uuid4()) + '.mp4'
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter(output_file, fourcc, cur_fps, frame_size)

        for frame in frames:
            out.write(frame)

        out.release()

        with open(output_file, 'rb') as video_file:
            video_data = video_file.read()
            cur_offset+=1
            producer.send(topic=topic_name, key=str(cur_offset).encode('utf-8'), value=video_data)

        producer.flush()

        os.remove(output_file)
        print(f"encoding+producing time/cur_offset: {time.time()-cur_time}/{cur_offset}")


def produce_video_stream(server_ip, server_port, topic_name, threshold_time):
    frame_queue = queue.Queue()
    cap = cv2.VideoCapture(0)
    cur_fps=cap.get(cv2.CAP_PROP_FPS)
    frame_size=(int(cap.get(3)), int(cap.get(4)))
    cap.release()

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(capture_frames, frame_queue, threshold_time)
        executor.submit(encode_and_send, frame_queue, server_ip, server_port, topic_name, cur_fps, frame_size, threshold_time)

if __name__=="__main__":
    produce_video_stream("piai_kafka.aiot.town", "9092", "TF-CAM-TEST", 5)
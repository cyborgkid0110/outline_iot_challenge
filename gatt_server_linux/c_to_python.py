import global_var
import zmq
# Tạo một ngữ cảnh ZeroMQ
context = zmq.Context()

# Tạo một socket kiểu PULL
socket = context.socket(zmq.PULL)
socket.connect("tcp://localhost:5432")

# Nhận dữ liệu
while True:
    message = socket.recv_string()
    data = message.split(',')
    data = [int(i) for i in data]

    if data[0] == 0:
        global_var.fan_id_target = data[1]
        global_var.set_speed_target = data[2]
        global_var.fan_control_signal = True
    else:
        global_var.ac_id_target = data[1]
        global_var.state_target = data[2]
        global_var.set_temp_target = data[3]
        global_var.ac_control_signal = True

    print("Received data from C:", data)
fan_id_target= None
ac_id_target= None
set_speed_target= None
set_temp_target= None
state_target= None
fan_control_signal= None
ac_control_signal = None

sensor_data_global = None
save_sensor_data_signal = False

energy_data_global = None
save_energy_data_signal = False 

def set_fan_control_signal(value):
    global fan_control_signal
    fan_control_signal = value

def get_fan_control_signal():
    global fan_control_signal
    return fan_control_signal

def set_ac_control_signal(value):
    global ac_control_signal
    ac_control_signal = value

def get_ac_control_signal():
    global ac_control_signal
    return ac_control_signal
import os
import yaml
import time
import struct
import ctypes
import platform
import subprocess
import numpy as np
from numpy.ctypeslib import ndpointer


path = os.path.dirname(os.path.abspath(__file__))

if platform.system() == 'Windows':
    NITdll = ctypes.CDLL(os.path.join(path, 'Tachyon_acq.dll'))
else:
    NITdll = ctypes.cdll.LoadLibrary(os.path.join(path, 'libtachyon_acq.so'))


# Camera management
_open_camera = NITdll.open_camera
_open_camera.restype = ctypes.c_int

_set_active_camera = NITdll.set_active_camera
_set_active_camera.argtypes = [ctypes.c_int]
_set_active_camera.restype = ctypes.c_int

_get_camera_info = NITdll.get_camera_info
_get_camera_info.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
_get_camera_info.restype = ctypes.c_int

_close_camera = NITdll.close_camera
_close_camera.restype = ctypes.c_int

_reset_camera = NITdll.reset_camera
_reset_camera.restype = ctypes.c_int

_usb_error = NITdll.usb_error
_usb_error.restype = ctypes.c_char_p

# Camera operation
_start = NITdll.start
_start.restype = ctypes.c_int

_stop = NITdll.stop
_stop.restype = ctypes.c_int

_read_frame = NITdll.read_frame
_read_frame.argtypes = [ndpointer(ctypes.c_uint8), ndpointer(ctypes.c_int16)]
_read_frame.restype = ctypes.c_int

_calibrate = NITdll.calibrate
_calibrate.argtypes = [ctypes.c_int, ctypes.c_int]
_calibrate.restype = ctypes.c_int

_stop_calibration = NITdll.stop_calibration
_stop_calibration.restype = ctypes.c_int

_close_shutter = NITdll.close_shutter
_close_shutter.restype = ctypes.c_int

_open_shutter = NITdll.open_shutter
_open_shutter.restype = ctypes.c_int

# Camera configuration
_set_integration_time = NITdll.set_integration_time
_set_integration_time.argtypes = [ctypes.c_float]
_set_integration_time.restype = ctypes.c_int

_set_wait_time = NITdll.set_wait_time
_set_wait_time.argtypes = [ctypes.c_float]
_set_wait_time.restype = ctypes.c_int

_set_bias = NITdll.set_bias
_set_bias.argtypes = [ctypes.c_float]
_set_bias.restype = ctypes.c_int

_set_vth = NITdll.set_Vth
_set_vth.argtypes = [ctypes.c_int]
_set_vth.restype = ctypes.c_int

_set_timeout = NITdll.set_timeout
_set_timeout.argtypes = [ctypes.c_int]
_set_timeout.restype = ctypes.c_int


class Tachyon():
    def __init__(self, model=1024, config='tachyon.yml'):
        self.connected = False
        self.open()
        camera_info = self.get_camera_info()
        if camera_info[0] == 'TACHYON 1024 NEW_INFRARED_TECHN':
            subprocess.call(['java', '-cp', 'FWLoader.jar',
                             'FWLoader', '-c', '-uf', 'nit_tachyon_32_HS.bit'])
            model = 1024
        elif camera_info[0] == 'TACHYON 6400 NEW_INFRARED_TECHN':
            model = 6400
        print camera_info
        self.model = model
        self.size = int(np.sqrt(model))
        self.configure(config)

    def open(self):
        """Opens a connection with a TACHYON camera."""
        if not self.connected:
            if _open_camera() > 0:  # Returns the number of cameras
                self.connected = True
        return self.connected

    def close(self):
        """Closes a connection with a TACHYON camera."""
        if self.connected:
            if _close_camera() > 0:
                time.sleep(0.1)
                self.connected = False
        return not self.connected

    def get_camera_info(self):
        """Returns camera info: description, serial, and manufacturer."""
        if self.connected:
            description = ctypes.create_string_buffer(256)
            serial_number = ctypes.create_string_buffer(256)
            manufacturer = ctypes.create_string_buffer(256)
            _get_camera_info(description, serial_number, manufacturer)
            return description.value, serial_number.value, manufacturer.value
        else:
            return None

    def configure(self, filename):
        with open(filename, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
        int_time = float(cfg['configuration']['int_time'])
        wait_time = float(cfg['configuration']['wait_time'])
        bias = float(cfg['configuration']['bias'])
        vth_value = int(cfg['configuration']['vth_value'])
        timeout = int(cfg['configuration']['timeout'])
        self.set_configuration(int_time, wait_time, bias, vth_value, timeout)

    def set_configuration(self, int_time, wait_time, bias, vth_value, timeout):
        """Puts configuration values of the camera."""
        if self.connected:
            self.int_time = _set_integration_time(int_time)
            self.wait_time = _set_wait_time(wait_time)
            self.bias = _set_bias(bias)
            self.vth_value = _set_vth(vth_value)
            self.timeout = _set_timeout(timeout)

    def calibrate(self, target=100, auto_off=1):
        """Performs an offset calibration for dark current correction."""
        if self.connected:
            for k in range(3000):
                if k == 100:
                    _close_shutter()
                if k == 600:
                    _calibrate(target, auto_off)
                if k == 2600:
                    _stop_calibration()
                if k == 2700:
                    _open_shutter()
                image, header = self.read_frame()

    def start_calibration(self, target=100, auto_off=1):
        """Starts the calibration process."""
        if self.connected:
            _close_shutter()
            time.sleep(0.5)
            _calibrate(target, auto_off)
            time.sleep(0.1)

    def stop_calibration(self):
        """Stops the calibration process."""
        if self.connected:
            _stop_calibration()
            time.sleep(0.1)
            _open_shutter()
            time.sleep(0.5)

    def connect(self):
        if self.connected:
            self.flush_buffer()
            init = _start()
            if not init:
                _open_shutter()
                time.sleep(0.5)
                return True
            else:
                return False
        return False

    def disconnect(self):
        if self.connected:
            end = _stop()
            if end < 0:
                return False
            else:
                _close_shutter()
                time.sleep(0.5)
                return True
        return False

    def flush_buffer(self):
        self.disconnect()
        frame = ()
        while frame is not None:
            frame = self.read_frame()
        time.sleep(0.5)

    def read_frame(self):
        header = np.zeros(64, dtype=np.uint8)
        image = np.zeros(self.model, dtype=np.int16)
        i = _read_frame(header, image)
        if i < 0:
            if i == -116:
                print 'ERROR: (Timeout) Waiting for images.'
            return None
        else:
            return image.reshape(self.size, self.size), header

    def parse_header(self, header):
        print header.view(dtype=np.dtype([('Header_ID', '<u4'),
                                          ('Frame_counter', 'a4'),
                                          ('Microseconds_counter_high', '<u4'),
                                          ('Microseconds_counter_low', '<u4'),
                                          ('Buffer_status', '<i4'),
                                          ('Reserved', '<i4'),
                                          ('Status', '<i4'),
                                          ('Bias_status', '<i4'),
                                          ('REGS', 'a32')]))
        print "Internal frame counter", struct.unpack('I', struct.pack(
            'BBBB', header[6], header[7], header[4], header[5]))


if __name__ == '__main__':
    from nitdat import LUT_IRON
    import matplotlib.pyplot as plt

    tachyon = Tachyon()
    tachyon.connect()

    tachyon.calibrate(24)

    for k in range(5000):
        image, header = tachyon.read_frame()
    tachyon.disconnect()

    print image

    plt.figure()
    plt.imshow(LUT_IRON[image], interpolation='none')
    plt.show()

    tachyon.close()
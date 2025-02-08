import smbus2
import time
import math

class MPU9250:
    # MPU9250 I2C address
    MPU9250_ADDR = 0x68  # MPU9250 I2C address when AD0 is low
    MAGNETOMETER_ADDR = 0x0C  # Magnetometer I2C address (part of MPU9250)
    
    # Register addresses
    PWR_MGMT_1 = 0x6B
    ACCEL_XOUT_H = 0x3B
    GYRO_XOUT_H = 0x43
    MAGNETOMETER_DATA_ADDR = 0x03  # Magnetometer data starts from this register

    def __init__(self, bus_number=1):
        # Initialize I2C bus (assuming I2C 1)
        self.bus = smbus2.SMBus(bus_number)
        self.previous_yaw = 0.0
        self.initial_yaw = None
        self.last_time = time.time()
        self.initialize_mpu9250()

    def read_word(self, register, device=MPU9250_ADDR):
        high = self.bus.read_byte_data(device, register)
        low = self.bus.read_byte_data(device, register + 1)
        value = (high << 8) + low
        if value >= 0x8000:  # Two's complement
            value -= 0x10000
        return value

    def initialize_mpu9250(self):
        # Wake up MPU9250 by writing 0 to PWR_MGMT_1 register
        self.bus.write_byte_data(self.MPU9250_ADDR, self.PWR_MGMT_1, 0)
        time.sleep(0.1)

    def get_accel_data(self):
        scale = 9.80665 / 16384.0
        ax = self.read_word(self.ACCEL_XOUT_H) * scale
        ay = self.read_word(self.ACCEL_XOUT_H + 2) * scale
        az = self.read_word(self.ACCEL_XOUT_H + 4) * scale 
        return ax, ay, az

    def get_rel_accel_data(self):
        # Get raw accelerometer data
        ax, ay, az = self.get_accel_data()
        g = 9.80665
        az -= g
        # Get the latest yaw, pitch, and roll values
        roll, pitch, yaw = self.get_sensor_data()

        # Store the initial yaw at startup
        if self.initial_yaw is None:
            self.initial_yaw = yaw

        # Compute the yaw offset from the initial orientation
        yaw_offset = yaw - self.initial_yaw
        yaw_rad = math.radians(yaw_offset)

        # Rotate acceleration to align with the initial orientation (in the X-Y plane)
        ax_rel = ax * math.cos(yaw_rad) - ay * math.sin(yaw_rad)  # Forward in initial direction
        ay_rel = ax * math.sin(yaw_rad) + ay * math.cos(yaw_rad)  # Perpendicular to initial yaw
        az_rel = az  # Keep vertical aligned with gravity

        return ax_rel, ay_rel, az_rel


    def get_gyro_data(self):
        gx = self.read_word(self.GYRO_XOUT_H)
        gy = self.read_word(self.GYRO_XOUT_H + 2)
        gz = self.read_word(self.GYRO_XOUT_H + 4)
        return gx, gy, gz

    def get_magnetometer_data(self):
        mx = self.read_word(self.MAGNETOMETER_DATA_ADDR, device=self.MAGNETOMETER_ADDR)
        my = self.read_word(self.MAGNETOMETER_DATA_ADDR + 2, device=self.MAGNETOMETER_ADDR)
        mz = self.read_word(self.MAGNETOMETER_DATA_ADDR + 4, device=self.MAGNETOMETER_ADDR)
        return mx, my, mz

    def calculate_orientation(self, ax, ay, az, gx, gy, gz, dt):
        # Normalize accelerometer data
        accel_norm = math.sqrt(ax**2 + ay**2 + az**2)
        ax /= accel_norm
        ay /= accel_norm
        az /= accel_norm

        # Calculate Roll and Pitch from accelerometer data
        roll = math.atan2(ay, az) * 180 / math.pi
        pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2)) * 180 / math.pi

        # Integrate gyroscope data to calculate yaw
        gyro_z = gz / 131.0  # Convert to degrees per second (assuming 250 dps scale)
        yaw = self.previous_yaw + gyro_z * dt

        return roll, pitch, yaw

    def update_yaw(self, dt):
        # Update yaw based on the gyroscope data
        ax, ay, az = self.get_accel_data()
        gx, gy, gz = self.get_gyro_data()

        # Calculate roll, pitch, and yaw
        roll, pitch, yaw = self.calculate_orientation(ax, ay, az, gx, gy, gz, dt)

        # Update previous yaw for next iteration
        self.previous_yaw = yaw

        return roll, pitch, yaw

    def get_sensor_data(self):
        current_time = time.time()
        dt = current_time - self.last_time  # Time difference in seconds

        roll, pitch, yaw = self.update_yaw(dt)

        self.last_time = current_time

        return roll, pitch, yaw

if __name__ == "__main__":
    # Create an instance of the MPU9250 class
    mpu = MPU9250()

    while True:
        # Get the sensor data (roll, pitch, yaw)
        roll, pitch, yaw = mpu.get_sensor_data()

        # Output the results
        print(f"Roll: {roll:.2f}, Pitch: {pitch:.2f}, Yaw: {yaw:.2f}")

        time.sleep(0.01)  # 100Hz update rate

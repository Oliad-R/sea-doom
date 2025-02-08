from settings import *


class Camera:
    def __init__(self, position, yaw, pitch, roll=0):
        self.position = glm.vec3(position)
        self.yaw = glm.radians(yaw)
        self.pitch = glm.radians(pitch)
        self.roll = glm.radians(roll)

        self.up = glm.vec3(0, 1, 0)
        self.right = glm.vec3(1, 0, 0)
        self.forward = glm.vec3(0, 0, -1)

        self.m_proj = glm.perspective(V_FOV, ASPECT_RATIO, NEAR, FAR)
        self.m_view = glm.mat4()

    def update(self):
        self.update_vectors()
        self.update_view_matrix()

    def update_view_matrix(self):
        roll_matrix = glm.rotate(glm.mat4(1.0), self.roll, self.forward)
        up = glm.vec3(roll_matrix * glm.vec4(self.up, 1.0))
        self.m_view = glm.lookAt(self.position, self.position + self.forward, up)

    def update_vectors(self):
        self.forward.x = glm.cos(self.yaw) * glm.cos(self.pitch)
        self.forward.y = glm.sin(self.pitch)
        self.forward.z = glm.sin(self.yaw) * glm.cos(self.pitch)

        self.forward = glm.normalize(self.forward)
        self.right = glm.normalize(glm.cross(self.forward, glm.vec3(0, 1, 0)))
        self.up = glm.normalize(glm.cross(self.right, self.forward))

    def rotate_pitch(self, delta_y):
        self.pitch -= delta_y
        self.pitch = glm.clamp(self.pitch, -PITCH_MAX, PITCH_MAX)

    def rotate_yaw(self, delta_x):
        self.yaw += delta_x

    def rotate_roll(self, delta_roll):
        self.roll += delta_roll
        #self.roll = glm.clamp(self.roll, glm.radians(-90), glm.radians(90))

    def move_left(self, velocity):
        return -self.right.xz * velocity

    def move_right(self, velocity):
        return self.right.xz * velocity

    def move_up(self, velocity):
        self.position += self.up * velocity

    def move_down(self, velocity):
        self.position -= self.up * velocity

    def move_forward(self, velocity):
        return self.forward.xz * velocity

    def move_back(self, velocity):
        return -self.forward.xz * velocity

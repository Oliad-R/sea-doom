from itertools import cycle
from camera import Camera
from settings import *
import random
import math

def g(x):
    B = 30
    T = 0.1
    return x*min(1, 1/(1 + math.exp(-1*B*(math.fabs(x) - T))))


class PlayerAttribs:
    def __init__(self):
        self.health = PLAYER_INIT_HEALTH
        self.ammo = PLAYER_INIT_AMMO
        self.weapons = {ID.KNIFE_0: 1, ID.PISTOL_0: 0, ID.RIFLE_0: 0}
        self.weapon_id = ID.KNIFE_0
        self.num_level = 0


    def update(self, player):
        self.health = player.health
        self.ammo = player.ammo
        self.weapons = player.weapons
        self.weapon_id = player.weapon_id


class Player(Camera):
    def __init__(self, eng, position=PLAYER_POS, yaw=0, pitch=0, roll=0):
        self.app = eng.app
        self.eng = eng
        self.sound = eng.sound
        self.play = eng.sound.play
        super().__init__(position, yaw, pitch, roll)

        # these maps will update when instantiated LevelMap
        self.door_map, self.wall_map, self.item_map = None, None, None

        # attribs
        self.health = self.eng.player_attribs.health
        self.ammo = self.eng.player_attribs.ammo
        #
        self.tile_pos: Tuple[int, int] = None

        # weapon
        self.weapons = self.eng.player_attribs.weapons
        self.weapon_id = self.eng.player_attribs.weapon_id
        self.weapon_cycle = cycle(self.eng.player_attribs.weapons.keys())
        #
        self.is_shot = False
        #
        self.key = None

        #new variables
        self.prev_shot_value = 1
        self.prev_shot_time = 0

        self.toggle_index = 0
        self.prev_toggle_value = 1
        self.prev_toggle_time = 0
        self.roll, self.pitch, self.yaw = mpu.get_sensor_data()

        self.prev_pitch = 0 
        self.prev_roll = 0
        self.prev_yaw = 0


    def handle_events(self, event):
        # door interaction
        if GPIO.input(DOOR_PIN) == 0:
            self.interact_with_door()

        if event.type == pg.KEYDOWN:
            if event.key == KEYS['INTERACT']:
                self.interact_with_door()

            # switch weapon by keys
            if event.key == KEYS['WEAPON_1']:
                self.switch_weapon(weapon_id=ID.KNIFE_0)
            elif event.key == KEYS['WEAPON_2']:
                self.switch_weapon(weapon_id=ID.PISTOL_0)
            elif event.key == KEYS['WEAPON_3']:
                self.switch_weapon(weapon_id=ID.RIFLE_0)

        if GPIO.input(TOGGLE_PIN) != self.prev_toggle_value:
            if GPIO.input(TOGGLE_PIN) == 0 and (time.time() - self.prev_toggle_time) >= 0.05:
                if self.toggle_index == 0:
                    self.switch_weapon(weapon_id=ID.KNIFE_0)
                elif self.toggle_index == 1:
                    if self.weapons[ID.PISTOL_0]==1:
                        self.switch_weapon(weapon_id=ID.PISTOL_0)
                    else:
                        self.toggle_index = -1
                        self.switch_weapon(weapon_id=ID.KNIFE_0)
                elif self.toggle_index == 2:
                    if self.weapons[ID.PISTOL_0]==1:
                        self.switch_weapon(weapon_id=ID.RIFLE_0)
                    else:
                        self.toggle_index = -1
                        self.switch_weapon(weapon_id=ID.KNIFE_0)
                    
            self.toggle_index = (self.toggle_index + 1) % 3
            self.prev_toggle_value = GPIO.input(TOGGLE_PIN)
            self.prev_toggle_time = time.time()
            print(self.toggle_index)


        # weapon by mouse wheel
        if event.type == pg.MOUSEWHEEL:
            weapon_id = next(self.weapon_cycle)
            if self.weapons[weapon_id]:
                self.switch_weapon(weapon_id=weapon_id)

        # shooting
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.do_shot()
    
        if GPIO.input(SHOOT_PIN) != self.prev_shot_value:
            if GPIO.input(SHOOT_PIN) == 0 and (time.time() - self.prev_shot_time) >= 0.1:
                self.do_shot()
                self.prev_shot = time.time()

            self.prev_shot_value = GPIO.input(SHOOT_PIN)

    def update(self):
        self.mouse_control()
        self.keyboard_control()
        super().update()

        # Player state updates
        self.check_health()
        self.update_tile_position()
        self.pick_up_item()

        # Get latest sensor readings
        roll, pitch, yaw = mpu.get_sensor_data()

        # Smoothing and Scaling
        alpha = 0.25  # Smoothing factor (lower = more stable, higher = more responsive)
        scale = 0.02  # Adjusted scaling for realistic motion tracking

        # Invert and scale sensor values for game compatibility
        yaw *= -scale
        roll *= -scale
        pitch *= scale

        # Compute delta changes to avoid drift
        delta_yaw = - self.prev_yaw + yaw
        delta_roll = - self.prev_roll + roll
        delta_pitch = - self.prev_pitch + pitch

        # Apply a dead zone to ignore small, insignificant changes (reduces drift)
        #dead_zone = 0.1  
        #if abs(delta_yaw) < dead_zone: delta_yaw = 0
        #if abs(delta_roll) < dead_zone: delta_roll = 0
        #if abs(delta_pitch) < dead_zone: delta_pitch = 0
        delta_yaw = g(delta_yaw)
        delta_roll = g(delta_roll)
        delta_pitch = g(delta_pitch)

        # Apply smoothing filter
        roll0 = self.prev_roll + (alpha * delta_roll)
        pitch0 = self.prev_pitch + (alpha * delta_pitch)
        yaw0 = self.prev_yaw + (alpha * delta_yaw)

        # Update player orientation
        self.yaw = yaw0
        self.pitch = pitch0
        self.roll = roll0

        # Store previous values for the next update
        self.prev_pitch = self.pitch
        self.prev_yaw = self.yaw
        self.prev_roll = self.roll

        # Debug Output (Optional)
        #print(f"Roll: {self.roll:.2f}, Pitch: {self.pitch:.2f}, Yaw: {self.yaw:.2f}")


    def check_health(self):
        if self.health <= 0:
            self.play(self.sound.player_death)
            #
            pg.time.wait(2000)
            self.eng.player_attribs = PlayerAttribs()
            self.eng.new_game()

    def check_hit_on_npc(self):
        if WEAPON_SETTINGS[self.weapon_id]['miss_probability'] > random.random():
            return None

        if npc_pos := self.eng.ray_casting.run(
                start_pos=self.position,
                direction=self.forward,
                max_dist=WEAPON_SETTINGS[self.weapon_id]['max_dist'],
                npc_to_player_flag=False
        ):
            npc = self.eng.level_map.npc_map[npc_pos]
            npc.get_damage()

    def switch_weapon(self, weapon_id):
        if self.weapons[weapon_id]:
            self.weapon_instance.weapon_id = self.weapon_id = weapon_id

    def do_shot(self):
        if self.weapon_id == ID.KNIFE_0:
            self.is_shot = True
            self.check_hit_on_npc()
            #
            self.play(self.sound.player_attack[ID.KNIFE_0])

        elif self.ammo:
            consumption = WEAPON_SETTINGS[self.weapon_id]['ammo_consumption']
            if not self.is_shot and self.ammo >= consumption:
                self.is_shot = True
                self.check_hit_on_npc()
                #
                self.ammo -= consumption
                self.ammo = max(0, self.ammo)
                #
                self.play(self.sound.player_attack[self.weapon_id])

    def update_tile_position(self):
        self.tile_pos = int(self.position.x), int(self.position.z)

    def pick_up_item(self):
        if self.tile_pos not in self.item_map:
            return None

        item = self.item_map[self.tile_pos]
        #
        if item.tex_id == ID.MED_KIT:
            self.health += ITEM_SETTINGS[ID.MED_KIT]['value']
            self.health = min(self.health, MAX_HEALTH_VALUE)
        #
        elif item.tex_id == ID.AMMO:
            self.ammo += ITEM_SETTINGS[ID.AMMO]['value']
            self.ammo = min(self.ammo, MAX_AMMO_VALUE)
        #
        elif item.tex_id == ID.PISTOL_ICON:
            if not self.weapons[ID.PISTOL_0]:
                self.weapons[ID.PISTOL_0] = 1
                self.switch_weapon(weapon_id=ID.PISTOL_0)
        #
        elif item.tex_id == ID.RIFLE_ICON:
            if not self.weapons[ID.RIFLE_0]:
                self.weapons[ID.RIFLE_0] = 1
                self.switch_weapon(weapon_id=ID.RIFLE_0)
        #
        elif item.tex_id == ID.KEY:
            self.key = 1
        #
        self.play(self.sound.pick_up[item.tex_id])
        #
        del self.item_map[self.tile_pos]

    def interact_with_door(self):
        pos = self.position + self.forward
        int_pos = int(pos.x), int(pos.z)

        if int_pos not in self.door_map:
            return None

        door = self.door_map[int_pos]
        #
        if self.key and door.tex_id == ID.KEY_DOOR:
            #
            door.is_closed = not door.is_closed
            self.play(self.sound.player_missed)
            # next level
            pg.time.wait(300)
            #
            self.eng.player_attribs.update(player=self)
            self.eng.player_attribs.num_level += 1
            self.eng.player_attribs.num_level %= NUM_LEVELS
            self.eng.new_game()
        else:
            door.is_moving = True
            self.play(self.sound.open_door)

    def mouse_control(self):
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        if mouse_dx:
            self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        if mouse_dy:
            self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)

    def keyboard_control(self):
        key_state = pg.key.get_pressed()
        vel = PLAYER_SPEED * self.app.delta_time
        next_step = glm.vec2()
        #

        if GPIO.input(FORWARD_PIN) == 0:
            next_step += self.move_forward(vel)
        if GPIO.input(BACKWARD_PIN) == 0:
            next_step += self.move_back(vel)

        if key_state[KEYS['FORWARD']]:
            next_step += self.move_forward(vel)
        if key_state[KEYS['BACK']]:
            next_step += self.move_back(vel)
        if key_state[KEYS['STRAFE_R']]:
            next_step += self.move_right(vel)
        if key_state[KEYS['STRAFE_L']]:
            next_step += self.move_left(vel)
        self.move(next_step=next_step)

    def keyboard_control2(self):
        ax, ay, az = mpu.get_accel_data()
        #print(ax, ay, az)
        #key_state = pg.key.get_pressed()
        vel = (PLAYER_SPEED) * self.app.delta_time

        next_step = glm.vec2()
        #if key_state[KEYS['FORWARD']]:
        scale = 0.01
        if ax > 0:
            next_step += self.move_forward(vel*ax*scale)
        #if key_state[KEYS['BACK']]:
        else:
            next_step += self.move_back(vel*-1*ax*scale)
        if ay > 0:
        #if key_state[KEYS['STRAFE_R']]:
            next_step += self.move_right(vel*ay*scale)
        #if key_state[KEYS['STRAFE_L']]:
        else:
            next_step += self.move_left(vel*-1*ay*scale)
        #

    def move(self, next_step):
        if not self.is_collide(dx=next_step[0]):
            self.position.x += next_step[0]

        if not self.is_collide(dz=next_step[1]):
            self.position.z += next_step[1]

    def is_collide(self, dx=0, dz=0):
        int_pos = (
            int(self.position.x + dx + (
                PLAYER_SIZE if dx > 0 else -PLAYER_SIZE if dx < 0 else 0)
                ),
            int(self.position.z + dz + (
                PLAYER_SIZE if dz > 0 else -PLAYER_SIZE if dz < 0 else 0)
                )
        )
        # check doors
        if int_pos in self.door_map:
            return self.door_map[int_pos].is_closed
        # check walls
        return int_pos in self.wall_map
    

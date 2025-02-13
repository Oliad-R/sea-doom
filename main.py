import sys
import moderngl as mgl
from engine import Engine
from settings import *

     
class Game:
    def __init__(self):
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VERSION)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VERSION)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)

        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

        self.clock = pg.time.Clock()
        self.target_fps = 60
        self.delta_time = 0
        self.time = 0

        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

        self.is_running = True
        self.fps_value = 0

        self.engine = Engine(self)

        self.anim_trigger = False
        self.anim_event = pg.USEREVENT + 0
        pg.time.set_timer(self.anim_event, SYNC_PULSE)

        self.sound_trigger = False
        self.sound_event = pg.USEREVENT + 1
        pg.time.set_timer(self.sound_event, 750)

        #GPIO Init Code
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SHOOT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(DOOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(TOGGLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(FORWARD_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BACKWARD_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


    def update(self):
        self.engine.update()
        #
        self.delta_time = self.clock.tick(60)
        self.time = pg.time.get_ticks() * 0.001
        self.fps_value = int(self.clock.get_fps())
        pg.display.set_caption(f'{self.fps_value}')

        #TESTING VALUES ONLY
        #print("PIN", SHOOT_PIN, ":", GPIO.input(SHOOT_PIN))
        #print("PIN", DOOR_PIN, ":",GPIO.input(DOOR_PIN))
        #print("PIN", TOGGLE_PIN, ":",GPIO.input(TOGGLE_PIN))
        #print(mpu.get_sensor_data())

    def render(self):
        self.ctx.clear(color=BG_COLOR)
        self.engine.render()
        pg.display.flip()
    def handle_events(self):
        self.anim_trigger, self.sound_trigger = False, False
    
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                self.is_running = False
            #
            if event.type == self.anim_event:
                self.anim_trigger = True
            #
            if event.type == self.sound_event:
                self.sound_trigger = True
            #
            self.engine.handle_events(event=event)

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
        pg.quit()
        sys.exit()


if __name__ == '__main__':
    game = Game()
    game.run()

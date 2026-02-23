import math
import random
from dataclasses import dataclass
import numpy as np
import arcade
from pyglet.graphics import Batch

# Окно и цвета
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
SCREEN_TITLE = "Clover sim"
# GRAVITY = 1.2
# LIN_AIR_DRAG = 0.9
# ANG_AIR_DRAG = 0.9
# GROUND_FRICTION = 7
# THRUST = 63
# ANG_THRUST = 1

GRAVITY = 35

LIN_AIR_DRAG = 0.9
ANG_AIR_DRAG = 0.9
GROUND_FRICTION = 14.0

THRUST = 70
ANG_THRUST = 1

GRAB_RADIUS = 100
BALL_ELASTICITY = 0.7
BALL_STOP_BOUNCE = 2.1
BALL_SLOW = 0.8


class Game(arcade.Window):
    def __init__(self, width, height, title):
        super().__init__(width, height, title, fullscreen=True)

        joysticks = arcade.get_joysticks()

        if joysticks:
            self.joystick = joysticks[0]
            self.joystick.open()
        else:
            self.joystick = None

        self.armed_sound = arcade.load_sound("sounds/armed.wav")
        self.armed_sound_loop = arcade.load_sound("sounds/armed_loop.wav")
        self.fly_sound = arcade.load_sound("sounds/fly.wav")

        self.player_list = arcade.SpriteList()
        points = [
            (-48, 30),
            (47, 30),
            (47, 3),
            (22, -30),
            (-22, -30),
            (-48, 3)
        ]
        self.player = arcade.Sprite("images/player.png", center_x=96, center_y=68)
        self.player_list.append(self.player)

        self.ball_list = arcade.SpriteList()
        self.ball = arcade.Sprite("images/ball.png", center_x=96, center_y=57)
        self.ball_list.append(self.ball)
        self.ball_grabbed = False

        tile_map = arcade.load_tilemap("levels/untitled.tmx", scaling=1)
        self.walls = tile_map.sprite_lists["walls"]
        ball_solid = tile_map.sprite_lists["ball_solid"]
        only_ball = tile_map.sprite_lists["only_ball"]
        self.no_ball = tile_map.sprite_lists["no_ball"]
        self.with_ball = tile_map.sprite_lists["with_ball"]
        self.slow_ball = tile_map.sprite_lists["slow_ball"]
        collision = tile_map.sprite_lists["collision"]
        self.player_collision = arcade.SpriteList()
        self.player_collision.extend(collision)
        self.player_collision.extend(only_ball)
        self.player_collision.extend(self.with_ball)
        self.ball_collision = arcade.SpriteList()
        self.ball_collision.extend(collision)
        self.ball_collision.extend(ball_solid)

        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player, walls=self.player_collision, gravity_constant=0)

        self.batch = Batch()
        self.text_arm = arcade.Text(f"DISARMED",
                                     16, 1040, arcade.color.RED, 20, batch=self.batch)

        self.camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()

        self.bg = arcade.load_texture("images/bg.jpeg")

        self.fly_sound_plyer = arcade.play_sound(self.fly_sound, volume=0, loop=True)

        self.grounded = False
        self.prev_btn_3 = False
        self.armed = False
        self.prev_btn_7 = False


    # Логика
    def on_update(self, dt):
        if self.joystick.buttons[7] and not self.prev_btn_7:
            self.armed = not self.armed
        self.prev_btn_7 = self.joystick.buttons[7]
        if self.armed:
            acc_axis = (-self.joystick.y + 1) / 2
            acceleration = acc_axis * THRUST
            roll_axis = self.joystick.x
            roll = roll_axis * ANG_THRUST
            self.fly_sound_plyer.volume = max(0.1, min(acc_axis + abs(roll_axis), 0.7))
            self.text_arm.text = ""
        else:
            acceleration = 0
            roll = 0
            self.fly_sound_plyer.volume = 0
            self.text_arm.text = "DISARMED"

        self.player.change_angle += roll
        self.player.change_angle *= ANG_AIR_DRAG
        self.player.angle += self.player.change_angle * dt
        self.player.angle = self.player.angle % 360



        angle = math.radians(self.player.angle)
        self.player.change_x += math.sin(angle) * acceleration * dt
        self.player.change_y += math.cos(angle) * acceleration * dt
        self.player.change_y -= GRAVITY * dt
        self.player.change_x -= LIN_AIR_DRAG * self.player.change_x * dt
        self.player.change_y -= LIN_AIR_DRAG * self.player.change_y * dt
        if self.grounded:
            self.player.change_x -= GROUND_FRICTION * self.player.change_x * dt
            self.player.change_y -= GROUND_FRICTION * self.player.change_y * dt

        self.player.center_y += self.player.change_y -1
        if arcade.check_for_collision_with_list(self.player, self.player_collision):
            self.grounded = True
        else:
            self.grounded = False
        self.player.center_y -= self.player.change_y -1



        if (not self.prev_btn_3 and not self.ball_grabbed and self.joystick.buttons[3] and
                (not arcade.check_for_collision_with_list(self.player, self.no_ball)) and
                ((self.player.center_x - self.ball.center_x) ** 2 + (self.player.center_y - self.ball.center_y) ** 2) ** 0.5 < GRAB_RADIUS):

            self.ball_grabbed = True
            for i in self.with_ball:
                if i in self.player_collision:
                    self.player_collision.remove(i)
            for i in self.no_ball:
                if i not in self.player_collision:
                    self.player_collision.append(i)
        elif self.ball_grabbed and not self.joystick.buttons[3]:
            self.ball_grabbed = False
            for i in self.with_ball:
                if i not in self.player_collision:
                    self.player_collision.append(i)
            for i in self.no_ball:
                if i in self.player_collision:
                    self.player_collision.remove(i)
            self.ball.change_x = self.player.change_x
            self.ball.change_y = self.player.change_y
        self.prev_btn_3 = self.joystick.buttons[3]

        self.physics_engine.update()

        if self.ball_grabbed:
            self.ball.center_x = self.player.center_x - math.sin(angle) * 24
            self.ball.center_y = self.player.center_y - math.cos(angle) * 24
        else:
            self.ball.change_y -= GRAVITY * dt
            self.ball.change_x -= LIN_AIR_DRAG * self.ball.change_x * dt
            self.ball.change_y -= LIN_AIR_DRAG * self.ball.change_y * dt

            if arcade.check_for_collision_with_list(self.ball, self.slow_ball):
                self.ball.change_x *= BALL_SLOW
                self.ball.change_y *= BALL_SLOW

            self.ball.center_x += self.ball.change_x
            if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                self.ball.center_x -= self.ball.change_x
                self.ball.change_x = -self.ball.change_x * BALL_ELASTICITY
                self.ball.center_x += self.ball.change_x
                if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                    self.ball.change_x = 0
                    self.ball.center_x -= self.ball.change_x

            self.ball.center_y += self.ball.change_y
            if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                self.ball.center_y -= self.ball.change_y
                self.ball.change_y = -self.ball.change_y * BALL_ELASTICITY
                if abs(self.ball.change_y) < BALL_STOP_BOUNCE:
                    self.ball.change_y = 0
                self.ball.center_y += self.ball.change_y
                if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                    self.ball.change_y = 0
                    self.ball.center_y -= self.ball.change_y

        self.camera.position = (max(SCREEN_WIDTH // 2, min(self.player.center_x, 12000 - SCREEN_WIDTH // 2)),
                                max(SCREEN_HEIGHT // 2, min(self.player.center_y, 4800 - SCREEN_HEIGHT // 2)))

    def on_draw(self):
        self.clear()
        arcade.draw_texture_rect(self.bg, arcade.rect.XYWH((max(SCREEN_WIDTH // 2, min(self.player.center_x, 12000 - SCREEN_WIDTH // 2))  - 6000) * -0.523 + 960, SCREEN_HEIGHT // 2, self.bg.width * 2, SCREEN_HEIGHT))

        self.camera.use()
        self.walls.draw()
        self.ball_list.draw()
        self.player_list.draw()

        self.gui_camera.use()
        self.batch.draw()


def setup_game(width, height, title):
    game = Game(width, height, title)
    return game


def main():
    window = setup_game(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    main()
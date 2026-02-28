import math
import sys

import arcade
from arcade.gui import UIManager, UIAnchorLayout, UIBoxLayout, UIFlatButton
from pyglet.graphics import Batch

# Окно и цвета
SCREEN_WIDTH, SCREEN_HEIGHT = 1366, 768
SCREEN_TITLE = "Clover sim"

GRAVITY = 35 # 35

LIN_AIR_DRAG = 0.9 # 0.9
ANG_AIR_DRAG = 0.9
GROUND_FRICTION = 14.0

THRUST = 70 # 70
ANG_THRUST = 1

GRAB_RADIUS = 100
BALL_ELASTICITY = 0.7 # 0.7
BALL_STOP_BOUNCE = 2.1
BALL_SLOW = 0.8

BUTTON_STYLE = {
        "normal": UIFlatButton.UIStyle(
            font_size=16,
            font_name=("calibri", "arial"),
            font_color=arcade.color.BLACK,
            bg=arcade.color.YELLOW,
            border=arcade.color.WHITE,
            border_width=2,
        ),
        "hover": UIFlatButton.UIStyle(
            font_size=16,
            font_name=("calibri", "arial"),
            font_color=arcade.color.WHITE,
            bg=arcade.color.DARK_YELLOW,
            border=(77, 81, 87, 255),
            border_width=2,
        ),
        "press": UIFlatButton.UIStyle(
            font_size=16,
            font_name=("calibri", "arial"),
            font_color=arcade.color.BLACK,
            bg=arcade.color.WHITE,
            border=arcade.color.WHITE,
            border_width=2,
        ),
        "disabled": UIFlatButton.UIStyle(
            font_size=16,
            font_name=("calibri", "arial"),
            font_color=arcade.color.WHITE,
            bg=arcade.color.GRAY,
            border=None,
            border_width=2,
        )
    }


SILVER_TIME = 180
GOLD_TIME = 120


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLUE_GRAY  # Фон для меню

        self.game_view = GameView(self)

        self.manager = UIManager()
        self.manager.enable()  # Включить, чтоб виджеты работали

        # Layout для организации — как полки в шкафу
        self.anchor_layout = UIAnchorLayout()  # Центрирует виджеты
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)  # Вертикальный стек

        flat_button = UIFlatButton(text="Начать игру", width=400, height=50, style=BUTTON_STYLE)
        flat_button.on_click = self.start  # Не только лямбду, конечно
        self.box_layout.add(flat_button)
        flat_button = UIFlatButton(text="Выйти", width=400, height=50, style=BUTTON_STYLE)
        flat_button.on_click = self.exit  # Не только лямбду, конечно
        self.box_layout.add(flat_button)

        self.anchor_layout.add(self.box_layout)  # Box в anchor
        self.manager.add(self.anchor_layout)  # Всё в manager

    def on_draw(self) -> None:
        self.clear()
        self.manager.draw()

    def start(self, _=None) -> None:
        self.window.show_view(self.game_view)  # Переключаем

    def exit(self, _=None) -> None:
        sys.exit()


class GameView(arcade.View):
    def __init__(self, menu_view: MenuView):
        super().__init__()

        self.menu_view = menu_view
        self.pause_view = PauseView(self, menu_view)

        joysticks = arcade.get_joysticks()

        if joysticks:
            self.joystick = joysticks[0]
            self.joystick.open()
        else:
            self.joystick = None

        self.armed_sound = arcade.load_sound("sounds/armed.wav")
        self.armed_sound_loop = arcade.load_sound("sounds/armed_loop.wav")
        self.fly_sound = arcade.load_sound("sounds/fly.wav")
        self.bounce_sound = arcade.load_sound("sounds/bounce.wav")

        self.player_list = arcade.SpriteList()
        # points = [
        #     (-48, 30),
        #     (47, 30),
        #     (47, 3),
        #     (22, -30),
        #     (-22, -30),
        #     (-48, 3)
        # ]
        self.player = arcade.Sprite("images/player.png", center_x=96, center_y=98)
        self.player_list.append(self.player)

        self.ball_list = arcade.SpriteList()
        self.ball = arcade.Sprite("images/ball.png", center_x=96, center_y=50)
        self.ball_list.append(self.ball)
        self.ball_grabbed = False

        tile_map = arcade.load_tilemap("levels/untitled.tmx", scaling=1)
        self.walls = tile_map.sprite_lists["walls"]
        ball_solid = tile_map.sprite_lists["ball_solid"]
        only_ball = tile_map.sprite_lists["only_ball"]
        self.no_ball = tile_map.sprite_lists["no_ball"]
        self.with_ball = tile_map.sprite_lists["with_ball"]
        self.slow_ball = tile_map.sprite_lists["slow_ball"]
        self.finish = tile_map.sprite_lists["finish"]
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
                                     16, 16, arcade.color.RED, 20, batch=self.batch)
        self.text_timer = arcade.Text(f"00:00.00",
                                    16, 16, arcade.color.WHITE, 20, batch=self.batch)

        self.camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()

        self.bg = arcade.load_texture("images/bg.jpeg")

        self.fly_sound_plyer = arcade.play_sound(self.fly_sound, volume=0, loop=True)

        self.grounded = False
        self.prev_btn_3 = False
        self.armed = False
        self.prev_btn_7 = False
        self.timer = 0
        self.started = False
        self.ended = False
        self.end_timer = 0


    # Логика
    def on_update(self, dt: float) -> None:
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
            if not self.started:
                self.started = True
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
                volume = min(abs(self.ball.change_x) * 0.01, 1)
                if volume > 0.035:
                    arcade.play_sound(self.bounce_sound, volume=volume)
                self.ball.center_x -= self.ball.change_x
                self.ball.change_x = -self.ball.change_x * BALL_ELASTICITY
                self.ball.center_x += self.ball.change_x
                if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                    self.ball.change_x = 0
                    self.ball.center_x -= self.ball.change_x

            self.ball.center_y += self.ball.change_y
            if arcade.check_for_collision_with_list(self.ball, self.ball_collision):
                volume = min(abs(self.ball.change_y) * 0.05, 1)
                if volume > 0.035:
                    arcade.play_sound(self.bounce_sound, volume=volume)
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

        if self.started:
            self.timer += dt
            minutes = str(int(self.timer) // 60)
            if len(minutes) == 0:
                minutes = "00"
            elif len(minutes) == 1:
                minutes = "0" + minutes
            seconds = int(self.timer) % 60
            if seconds == 0:
                seconds = "00"
            elif seconds < 10:
                seconds = "0" + str(seconds)
            ms = str(round(self.timer % 1, 3))[2:]
            self.text_timer.text = f"{minutes}:{seconds}.{ms}"
        if self.started and arcade.check_for_collision_with_list(self.ball, self.finish):
            self.started = False
            self.ended = True
        if self.ended:
            self.end_timer += dt
            if self.end_timer > 3:
                end_view = EndView(self.menu_view, self.timer)
                self.window.show_view(end_view)

    def on_draw(self) -> None:
        self.clear()
        arcade.draw_texture_rect(self.bg, arcade.rect.XYWH((max(SCREEN_WIDTH // 2, min(self.player.center_x, 12000 - SCREEN_WIDTH // 2))  - 6000) * ((self.bg.width * (SCREEN_HEIGHT / self.bg.height) // 2 - SCREEN_WIDTH // 2) / (SCREEN_WIDTH // 2 - 6000)) + SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, self.bg.width * (SCREEN_HEIGHT / self.bg.height), SCREEN_HEIGHT))

        self.camera.use()
        self.walls.draw()
        self.ball_list.draw()
        self.player_list.draw()

        self.gui_camera.use()
        self.batch.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if key == arcade.key.ESCAPE:
            self.window.show_view(self.pause_view)


class PauseView(arcade.View):
    def __init__(self, game_view: GameView, menu_view: MenuView) -> None:
        super().__init__()
        self.game_view = game_view  # Сохраняем, чтобы вернуться
        self.menu_view = menu_view
        self.manager = UIManager()
        self.manager.enable()  # Включить, чтоб виджеты работали

        # Layout для организации — как полки в шкафу
        self.anchor_layout = UIAnchorLayout()  # Центрирует виджеты
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)  # Вертикальный стек

        flat_button = UIFlatButton(text="Продолжить", width=200, height=50, color=arcade.color.BLUE)
        flat_button.on_click = self.resume  # Не только лямбду, конечно
        self.box_layout.add(flat_button)

        flat_button = UIFlatButton(text="Начать заново", width=200, height=50, color=arcade.color.BLUE)
        flat_button.on_click = self.restart  # Не только лямбду, конечно
        self.box_layout.add(flat_button)

        flat_button = UIFlatButton(text="Главное меню", width=200, height=50, color=arcade.color.BLUE)
        flat_button.on_click = self.main_menu  # Не только лямбду, конечно
        self.box_layout.add(flat_button)

        self.anchor_layout.add(self.box_layout)  # Box в anchor
        self.manager.add(self.anchor_layout)  # Всё в manager

    def on_draw(self) -> None:
        self.clear()
        self.manager.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if key == arcade.key.ESCAPE:
            self.resume()  # Возвращаемся в игру

    def resume(self, _=None) -> None:
        self.window.show_view(self.game_view)

    def restart(self, _=None) -> None:
        game_view = GameView(self.menu_view)
        self.window.show_view(game_view)

    def main_menu(self, _=None) -> None:
        self.window.show_view(self.menu_view)


class EndView(arcade.View):
    def __init__(self, menu_view: MenuView, time: float) -> None:
        super().__init__()

        self.menu_view = menu_view

        if time <= GOLD_TIME:
            self.trophy_texture = arcade.load_texture("images/cup_gold.png")
        elif time <= SILVER_TIME:
            self.trophy_texture = arcade.load_texture("images/cup_silver.png")
        else:
            self.trophy_texture = arcade.load_texture("images/cup_bronze.png")

        self.manager = UIManager()
        self.manager.enable()  # Включить, чтоб виджеты работали

        # Layout для организации — как полки в шкафу
        self.anchor_layout = UIAnchorLayout()  # Центрирует виджеты
        self.box_layout = UIBoxLayout(vertical=True, space_between=10)  # Вертикальный стек

        flat_button = UIFlatButton(text="Начать заново", width=400, height=50, style=BUTTON_STYLE)
        flat_button.on_click = self.restart  # Не только лямбду, конечно
        self.box_layout.add(flat_button)
        flat_button = UIFlatButton(text="Главное меню", width=400, height=50, style=BUTTON_STYLE)
        flat_button.on_click = self.main_menu  # Не только лямбду, конечно
        self.box_layout.add(flat_button)

        self.anchor_layout.add(self.box_layout, align_y=-200)  # Box в anchor
        self.manager.add(self.anchor_layout)  # Всё в manager

    def on_draw(self) -> bool | None:
        self.clear()
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, arcade.color.AERO_BLUE)
        arcade.draw_texture_rect(self.trophy_texture, arcade.rect.XYWH(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 0.7, self.trophy_texture.width, self.trophy_texture.height))
        self.manager.draw()

    def main_menu(self, _=None) -> None:
        self.menu_view.game_view = GameView(self.menu_view)
        self.window.show_view(self.menu_view)


    def restart(self, _=None) -> None:
        game_view = GameView(self.menu_view)
        self.window.show_view(game_view)


def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
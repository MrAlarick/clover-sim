import random
from dataclasses import dataclass
import numpy as np
import arcade

# Окно и цвета
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700
SCREEN_TITLE = "Falling Stars"
GRAVITY = 2500
LIN_AIR_DRAG = 1.8
ANG_AIR_DRAG = 12
GROUND_FRICTION = 10
THRUST = 4200
ANG_THRUST = 1400
YAW_THRUST = 900


@dataclass
class InputState:
    acceleration: float = 0
    roll: float = 0
    pitch: float = 0
    yaw: float = 0


@dataclass
class Player:
    rot = [1, 0, 0, 0] # global
    pos = np.array([0, 0, 0], dtype=np.float64) # global
    lve = np.array([0, 0, 0], dtype=np.float64)
    lac = np.array([0, 0, 0], dtype=np.float64)
    ave = np.array([0, 0, 0], dtype=np.float64)
    aac = np.array([0, 0, 0], dtype=np.float64)
    grounded = False


def quat_normalize(q):
    return q / np.linalg.norm(q)

def quat_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quat_rotate(q, v):
    qv = np.array([0.0, *v])
    return quat_multiply(
        quat_multiply(q, qv),
        np.array([q[0], -q[1], -q[2], -q[3]])
    )[1:]

def quat_from_axis_angle(axis, angle):
    axis = axis / np.linalg.norm(axis)
    half = angle * 0.5
    return np.array([
        np.cos(half),
        *(axis * np.sin(half))
    ])

def apply_local_velocity(
    rotation,               # quaternion [w,x,y,z]
    local_velocity,         # np.array(3)
):
    """Convert local linear velocity to world space"""
    return quat_rotate(rotation, local_velocity)

def apply_local_angular_velocity(
    rotation,               # quaternion [w,x,y,z]
    local_angular_velocity  # np.array(3), NOT scaled by dt
):
    """Apply local angular velocity direction (unit step)"""
    mag = np.linalg.norm(local_angular_velocity)
    if mag == 0.0:
        return rotation

    axis = local_angular_velocity / mag
    dq = quat_from_axis_angle(axis, mag)
    return quat_normalize(quat_multiply(rotation, dq))

def apply_global_velocity(q, v):
    return quat_multiply(quat_multiply(np.array([q[0], -q[1], -q[2], -q[3]]), np.array([0.0, *v])), q)[1:]


class PhysicsEngine3D:
    def __init__(self, input_state: InputState,
                 player: Player,
                 player_x: arcade.Sprite,
                 player_y: arcade.Sprite,
                 player_z: arcade.Sprite,
                 collision_x: arcade.SpriteList,
                 collision_y: arcade.SpriteList,
                 collision_z: arcade.SpriteList):
        self.input = input_state
        self.player = player
        self.player_x = player_x
        self.player_y = player_y
        self.player_z = player_z
        self.collision_x = collision_x
        self.collision_y = collision_y
        self.collision_z = collision_z

    def update(self, dt: float):
        # Physics
        self.player.aac[:] = 0
        self.player.aac[0] += self.input.roll * ANG_THRUST
        self.player.aac[1] += self.input.pitch * ANG_THRUST
        self.player.aac[2] += self.input.yaw * YAW_THRUST

        self.player.ave += self.player.aac * dt
        self.player.ave -= self.player.ave * ANG_AIR_DRAG * dt

        self.player.rot = apply_local_angular_velocity(self.player.rot, self.player.ave * dt)

        self.player.lac[:] = 0
        self.player.lac[2] += self.input.acceleration * THRUST
        drag = GROUND_FRICTION if self.player.grounded else LIN_AIR_DRAG
        self.player.lac[0] -= self.player.lve[0] * drag
        self.player.lac[1] -= self.player.lve[1] * drag
        self.player.lac[2] -= self.player.lve[2] * LIN_AIR_DRAG
        self.player.lve += self.player.lac * dt
        self.player.lve -= apply_global_velocity(self.player.rot, np.array([0, 0, GRAVITY])) * dt

        # Collision
        dx, dy, dz = apply_local_velocity(self.player.rot, self.player.lve) * dt

        self.player_z.center_x = self.player.pos[0] + dx
        self.player_y.center_x = self.player.pos[0] + dx
        self.player_z.center_y = self.player.pos[1]
        self.player_x.center_x = self.player.pos[1]
        self.player_x.center_y = self.player.pos[2]
        self.player_y.center_y = self.player.pos[2]

        if not arcade.check_for_collision_with_list(
                self.player_z, self.collision_z
        ):
            self.player.pos[0] += dx
        else:
            self.player.lve[0] = 0

        self.player_z.center_x = self.player.pos[0]
        self.player_z.center_y = self.player.pos[1] + dy
        self.player_x.center_x = self.player.pos[1] + dy
        self.player_y.center_x = self.player.pos[0]

        if not arcade.check_for_collision_with_list(
                self.player_z, self.collision_z
        ):
            self.player.pos[1] += dy
        else:
            self.player.lve[1] = 0

        self.player_x.center_x = self.player.pos[1]
        self.player_x.center_y = self.player.pos[2] + dz
        self.player_y.center_y = self.player.pos[2] + dz
        self.player_z.center_y = self.player.pos[1]

        if not arcade.check_for_collision_with_list(
                self.player_x, self.collision_x
        ):
            self.player.pos[2] += dz
        else:
            self.player.lve[2] = 0



class Game(arcade.Window):
    def __init__(self, width, height, title):
        super().__init__(width, height, title)
        self.input = InputState()
        self.player = Player()
        self.player_x = arcade.Sprite("images/player_z_old.png")
        self.player_x_list = arcade.SpriteList()
        self.player_x_list.append(self.player_x)

        self.player_y = arcade.Sprite("images/player_z_old.png")
        self.player_y_list = arcade.SpriteList()
        self.player_y_list.append(self.player_y)

        self.player_z = arcade.Sprite("images/player_z_old.png")
        self.player_z_list = arcade.SpriteList()
        self.player_z_list.append(self.player_z)

        tile_map_x = arcade.load_tilemap("levels/untitled_x.tmx", scaling=1)
        self.wall_list_x = tile_map_x.sprite_lists["walls"]
        self.collision_x = tile_map_x.sprite_lists["collision"]

        tile_map_y = arcade.load_tilemap("levels/untitled_y.tmx", scaling=1)
        self.wall_list_y = tile_map_y.sprite_lists["walls"]
        self.collision_y = tile_map_y.sprite_lists["collision"]

        tile_map_z = arcade.load_tilemap("levels/untitled_z.tmx", scaling=1)
        self.wall_list_z = tile_map_z.sprite_lists["walls"]
        self.collision_z = tile_map_z.sprite_lists["collision"]

        self.physics_engine = PhysicsEngine3D(self.input, self.player,
                                              self.player_x, self.player_y, self.player_z,
                                              self.collision_x, self.collision_y, self.collision_z)

        self.camera_x = arcade.camera.Camera2D(arcade.XYWH(0, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.camera_y = arcade.camera.Camera2D(arcade.XYWH(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT))
        self.camera_z = arcade.camera.Camera2D(arcade.XYWH(0, SCREEN_HEIGHT // 2, SCREEN_WIDTH // 2, SCREEN_HEIGHT))


    # Логика
    def on_update(self, dt):
        self.physics_engine.update(dt)
        self.camera_x.position = self.player_x.position
        self.camera_y.position = self.player_y.position
        self.camera_z.position = self.player_z.position

    def on_draw(self):
        self.clear()

        self.camera_x.use()
        self.wall_list_x.draw()
        self.player_x_list.draw()

        self.camera_y.use()
        self.wall_list_y.draw()
        self.player_y_list.draw()

        self.camera_z.use()
        self.wall_list_z.draw()
        self.player_z_list.draw()




def setup_game(width=800, height=600, title="Falling Stars"):
    game = Game(width, height, title)
    return game


def main():
    window = setup_game(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    main()
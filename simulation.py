"""sun earth simulation"""

import io
import csv
import math
import types
import random
import argparse
import operator
import tqdm
import colour
import pygame

# Force = collections.namedtuple("Force", ("x", "y"))
# Position = collections.namedtuple("Position", ("x", "y"))
# Direction = collections.namedtuple("Direction", ("x", "y"))

CONSTANTS = types.SimpleNamespace(
    G=6.672e-11,
    AU=1.496e+11
)

FACTORS = types.SimpleNamespace(
    E=1e+18, P=1e+15, T=1e+12,
    G=1e+9, M=1e+6, k=1e+3,
    h=1e+2, da=1e+1,
    d=1e-1, c=1e-2,
    m=1e-3, my=1e-6, n=1e-9,
    p=1e-12, f=1e-15, a=1e-18
)


class Position():
    """A position or position-like thing."""
    def __init__(self, x_or_tuple=None, y=None, x=None):
        if x_or_tuple is x is y is None:
            self.x = self.y = 0  # pylint: disable=invalid-name
        elif isinstance(x_or_tuple, (tuple, list)):
            self.x, self.y = x_or_tuple
        elif isinstance(x_or_tuple, Position):
            self.x, self.y = x_or_tuple.x_y
        else:
            if x_or_tuple is not None:
                self.x = x_or_tuple
            else:
                self.x = x
            self.y = y

    def __add__(self, other):
        return self._calculate(other, operator.add)

    def __sub__(self, other):
        return self._calculate(other, operator.sub)

    def __mul__(self, other):
        return self._calculate(other, operator.mul)

    def __truediv__(self, other):
        return self._calculate(other, operator.truediv)

    def __pow__(self, other):
        return self._calculate(other, operator.pow)

    def _calculate(self, other, operation):
        if isinstance(other, Position):
            return Position(operation(self.x, other.x),
                            operation(self.y, other.y))
        elif isinstance(other, (int, float)):
            return Position(operation(self.x, other),
                            operation(self.y, other))
        elif isinstance(other, (tuple, list)):
            return Position(operation(self.x, other[0]),
                            operation(self.y, other[1]))
        else:
            raise NotImplementedError

    def __iter__(self):
        return iter((self.x, self.y))

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "Position(x={:e}, y={:e})".format(self.x, self.y)

    def invert_y(self):
        """Reverse y in position. Because pygame has reverse y axis."""
        return Position(x_or_tuple=self.x, y=self.y * -1)

    @property
    def x_y(self):
        """return the coordinates"""
        return (self.x, self.y)


class Vector(Position):
    """Like a position, but has direction and strength/speed"""
    def __init__(self, x_or_tuple=None, y=None,  # pylint: disable=R0913
                 x=None, strength=None, direction=None):
        if strength is None and direction is None:
            super().__init__(x_or_tuple, y, x)
            self.strength = math.sqrt(self.x ** 2 + self.y ** 2)
            self.direction = math.atan2(self.x, self.y)
        else:
            self.strength = strength
            self.direction = direction
            xpart = math.sin(self.direction)
            ypart = math.cos(self.direction)
            super().__init__(x=xpart * strength, y=ypart * strength)
        # print(self.direction)

    def translate_direction(self):
        """Translate radiant to cardinal direction."""
        xpart = math.sin(self.direction)
        ypart = math.cos(self.direction)
        if ypart > 0:
            print("oben  ", end='')
        else:
            print("unten ", end='')
        if xpart > 0:
            print("rechts")
        else:
            print("links")


Direction = Vector
Force = Vector


class Canvas():
    """scale class"""
    def __init__(self):
        self.scale_factor = 100
        self.screen = None
        # self.offset = Position(0, 0)
        # self.offset = Position(*[i / 2 for i in screen.get_size()])
        self.focus = Position(0, 0)
        self.offset = Position(-600, -400)

    # @property
    # def offset(self):
    #     """offset relative to focus"""
    #     return self.focus - Position(600, 400).invert_y()

    @property
    def scale(self):
        """Get the scale to convert from space xy to screen xy."""
        return self.scale_factor / CONSTANTS.AU

    def __call__(self):
        return self.scale

    def zoom(self, step):
        """Zoom outside or inside."""
        current_zoom = self.scale_factor
        self.scale_factor = current_zoom + step / 100 * current_zoom
        # self.scale_factor = max(min(self.scale_factor + step, 1000000), 5)

    # def move_offset(self, pos_x, pos_y):
    #     """move the plot window around"""
    #     factor = 1e10
    #     pos_x *= factor
    #     pos_y *= factor
    #     # self.offset = Position(self.offset.x + pos_x * factor,
    #     #                        self.offset.y + pos_y * factor)
    #     self.offset = self.offset + (pos_x, pos_y)

    def move_focus(self, pos_x, pos_y):
        """Move the window center around."""
        factor = self.offset.x * -0.005 / self.scale
        pos_x *= factor
        pos_y *= factor
        self.focus += (pos_x, pos_y)

    def is_visible(self, position, size=0):
        """Determine whether a thing would be visible."""
        # return True
        size /= self.scale  # size is in pixel
        in_x = (self.focus.x + self.offset.x / self.scale - size <=
                position.x <=
                self.focus.x - self.offset.x / self.scale + size)
        in_y = (self.focus.y + self.offset.y / self.scale - size <=
                position.y <=
                self.focus.y - self.offset.y / self.scale + size)
        # if name == "earth":
        # print("{:+e} {:+e} {}".format(self.focus.y + self.offset2.y
        #                               , position.y, in_y))
        # print("{:+e} {:+e}".format(self.focus.x, self.focus.y))
        return in_x and in_y

    def get_position(self, position, size=(0, 0)):
        """Convert position in space into screen coordinates."""
        size = Position(size[0] / 2, size[1] / 2)
        relative_to_focus = position - self.focus   # space coordinates
        position_on_canvas = (relative_to_focus * self.scale -
                              self.offset.invert_y() - size.invert_y())
        return position_on_canvas.invert_y().x_y
        # return ((self.offset + position - self.focus) * self.scale).x_y

    def place_object(self, thing):
        """Draw an object on the screen."""
        color = [i * 255 for i in thing.color.rgb]
        size = (20, 20)
        if thing.name == "luna":
            size = (5, 5)
        if self.is_visible(thing.position, max(size)):
            position = self.get_position(thing.position, size)
            pygame.draw.ellipse(self.screen, color, (position, size))


class MyColor(colour.Color):
    """Subclass for better rgb out"""
    def rgb_dec(self):
        """Decimal rgb values"""
        return tuple([i * 255 for i in self.rgb])


class Celestial():
    """Celestial Body"""

    direction = Direction(None, None)
    position = Position(None, None)
    force = Force(None, None)
    mass = None
    velocity = Direction(None, None)
    pending_force_update = None
    turtle = None
    name = None
    color = None

    def gravitation_force(self, other):
        """Force between two celestial bodies"""
        force = ((CONSTANTS.G * self.mass * other.mass) /
                 (self.distance(other) ** 2))
        return force

    def distance(self, other):
        """Get the distance of two bodies"""
        # distance = math.sqrt((self.position.x - other.position.x) ** 2 +
        #                      (self.position.y - other.position.y) ** 2)
        distance = math.sqrt(sum((self.position - other.position) ** 2))
        return distance

    def direction_angle(self):
        """Get the angle of the body as radiant."""
        return math.atan2(self.velocity, self.velocity)

    def angle_between_two(self, other):
        """angle between the position of two bodies."""
        # angle = math.atan2(other.position.y - self.position.y,
        #                    other.position.x - self.position.x)
        minus = other.position - self.position
        angle = math.atan2(minus.y, minus.x)
        return angle

    def directed_force(self, other):
        """Force in x and y direction."""
        # if self.name == "earth": ipdb.set_trace()
        angle = self.angle_between_two(other)
        grav_force = self.gravitation_force(other)
        return Force(math.cos(angle) * grav_force,
                     math.sin(angle) * grav_force)

    def ekin(self):
        """Get kinetic energy"""
        return 0.5 * self.mass * self.velocity ** 2

    def interact(self, others):
        """Interact with a list of others"""
        total_force_x = total_force_y = 0.0
        for other in others:
            if self == other:
                continue
            forces = self.directed_force(other)
            total_force_x += forces.x
            total_force_y += forces.y
        self.pending_force_update = Force(total_force_x, total_force_y)

    def update(self, timestep):
        """Apply pending change to object"""
        # force_x, force_y = self.pending_force_update
        # vel_x, vel_y = self.velocity
        # vel_x += force_x / self.mass * TIMESTEP
        # vel_y += force_y / self.mass * TIMESTEP
        # # Update positions
        # pos_x, pos_y = self.position
        # pos_x += vel_x * TIMESTEP
        # pos_y += vel_y * TIMESTEP
        # # vel_abs_old = math.sqrt(self.velocity.x ** 2 +
        # #                         self.velocity.y ** 2)
        # # vel_abs_new = math.sqrt(vel_x ** 2 + vel_y ** 2)
        # # if self.name == "earth":
        # #     print(math.sqrt(vel_x ** 2 + vel_y ** 2))
        # # multiplicator = (vel_abs_old / vel_abs_new)**2
        # # if self.name == "earth": print(multiplicator)
        # self.position = Position(pos_x, pos_y)
        # self.velocity = Direction(vel_x, vel_y)
        # # body.goto(body.px*SCALE, body.py*SCALE)
        # # body.dot(3)

        self.velocity += self.pending_force_update / self.mass * timestep
        self.position += self.velocity * timestep
        self.pending_force_update = None


class Planet(Celestial):
    """Planet!"""

    def __init__(self, name, mass, position=(0, 0),
                 velocity=(0, 0), color="black"):
        # pylint: disable=too-many-arguments
        self.name = name
        self.mass = mass  # kilogramm
        self.position = Position(*position)
        # self.distance = 1.496e+11  # meter
        # self.velocity = velocity  # meter pro sekunde = 108000 kmh
        self.velocity = Position(*velocity)
        self.color = color
        # myturtle = turtle.Turtle()
        # myturtle.penup()
        # myturtle.hideturtle()
        # myturtle.pencolor(color)
        # self.turtle = myturtle

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ("Planet(name={self.name!r}, mass={self.mass!r}, "
                "position={self.position!r}, velocity={self.velocity!r}"
                ")".format(self=self))


class Sun(Celestial):
    """Sonne!"""

    def __init__(self):
        self.mass = 1.989 * 10**30  # kilogramm


def pygameinit():
    """nix"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    animation_timer = pygame.time.Clock()
    pygame.display.set_caption("Sol system simulator")
    return screen, animation_timer


def get_starting_info(distance, speed, primary=None):
    """Start a planet on a random location on it's orbit"""
    if primary is None:
        primary_p = Position(0, 0)
        primary_v = Direction(0, 0)
    else:
        primary_p = primary.position
        primary_v = primary.velocity
    radiant = random.random() * math.pi * 2
    # radiant = math.pi * 2 * (3/4)
    x_factor = math.sin(radiant)
    y_factor = math.cos(radiant)
    direction = (radiant - math.pi / 2)
    return (primary_p + Position(x_factor, y_factor) * distance,
            primary_v + Direction(strength=speed, direction=direction))


def append_planets(celestials):
    """append planets randomly"""
    col = MyColor
    celestials.append(Planet(
        "sun", mass=1.989e+30, color=col("yellow")))
    # data = get_starting_info(distance=5.791e+10, speed=4.736e+4)
    data = get_starting_info(distance=5.791e+10, speed=4.736e+4)
    celestials.append(Planet(
        "merkur", mass=6.41693e+23, color=col("darkred"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=1.082e+11, speed=3.502e+4)
    celestials.append(Planet(
        "venus", mass=4.867e+24, color=col("orange"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=1.496e+11, speed=2.978e+4)
    celestials.append(Planet(
        "earth", mass=5.972e+24, color=col("blue"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(3.84400e+8, 1e+3, celestials[-1])
    celestials.append(Planet(
        "luna", mass=7.34767309e+22, color=col("white"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=2.279e+11, speed=2.41e+4)
    celestials.append(Planet(
        "mars", mass=6.41693e+23, color=col("red"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=7.785e+11, speed=1.3e+4)
    celestials.append(Planet(
        "jupiter", mass=1.89813e+27, color=col("brown"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=1.434e+12, speed=9.64e+3)
    celestials.append(Planet(
        "saturn", mass=5.68319e+26, color=col("maroon"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=2.8781e+12, speed=6.8e+3)
    celestials.append(Planet(
        "uranus", mass=8.68103e+25, color=col("lightgreen"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=4.495e+12, speed=5.43e+3)
    celestials.append(Planet(
        "neptun", mass=1.0241e+26, color=col("lightblue"),
        position=data[0], velocity=data[1]))
    data = get_starting_info(distance=5.049e+12, speed=5.515e+3)
    celestials.append(Planet(
        "pluto", mass=1.309e+22, color=col("grey"),
        position=data[0], velocity=data[1]))


def append_planets_old(celestials):
    """append the celestial bodies to list"""
    col = MyColor
    celestials.append(Planet(
        "sun", mass=1.989e+30, color=col("yellow")))
    celestials.append(Planet(
        "merkur", mass=6.41693e+23, position=(5.791e+10, 1),
        velocity=(1, 4.736e+4), color=col("darkred")))
    celestials.append(Planet(
        "venus", mass=4.867e+24, position=(1.082e+11, 1),
        velocity=(1, 3.502e+4), color=col("orange")))
    celestials.append(Planet(
        "earth", mass=5.972e+24, position=(1.496e+11, 1),
        velocity=(1, 2.978e+4), color=col("blue")))
    celestials.append(Planet(
        "mars", mass=6.41693e+23, position=(2.279e+11, 1),
        velocity=(0, 2.41e+4), color=col("red")))
    celestials.append(Planet(
        "jupiter", mass=1.89813e+27, position=(7.785e+11, 1),
        velocity=(0, 1.3e+4), color=col("brown")))
    celestials.append(Planet(
        "saturn", mass=5.68319e+26, position=(1.434e+12, 1),
        velocity=(0, 9.64e+3), color=col("maroon")))
    celestials.append(Planet(
        "uranus", mass=8.68103e+25, position=(2.871e+12, 1),
        velocity=(0, 6.8e+3), color=col("lightgreen")))
    celestials.append(Planet(
        "neptun", mass=1.0241e+26, position=(4.495e+12, 1),
        velocity=(0, 5.43e+3), color=col("lightblue")))
    celestials.append(Planet(
        "pluto", mass=1.309e+22, position=(5.049e+12, 1),
        velocity=(0, 5.515e+3), color=col("grey")))


class EventHandler():
    """Event Handler"""

    def __init__(self, canvas):
        self.canvas = canvas
        self.held = set()
        self.held_delay = {}
        self.followmode = False
        self.follownum = 0

    def check_events(self):
        """Check for events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            elif event.type == pygame.KEYDOWN:
                # print(event)
                self.held.add(event.key)
                self.held_delay[event.key] = 0
                self.handle_single_key(event)
            elif event.type == pygame.KEYUP:
                self.held.remove(event.key)
                self.held_delay[event.key] = 0
        if self.held:
            self.handle_continuous_keys()

    def handle_single_key(self, event):
        """handle keys on keydown event."""
        key = event.key
        if key == pygame.K_f:
            self.followmode = not self.followmode
        elif self.followmode and key in (pygame.K_w, pygame.K_UP):
            self.follownum += 1
        elif self.followmode and key in (pygame.K_s, pygame.K_DOWN):
            self.follownum -= 1
        elif key == pygame.K_ESCAPE:
            exit()

    def handle_continuous_keys(self):
        """handle keys that act continuous."""
        shift = pygame.K_LSHIFT in self.held
        ctrl = pygame.K_LCTRL in self.held
        factor = 3 if shift else 1/3 if ctrl else 1
        for key in self.held:
            if not self.followmode:
                # if self.held_delay[key] == 0:
                if key in (pygame.K_w, pygame.K_UP):  # up
                    # self.canvas.move_offset(0, 5 * factor)
                    self.canvas.move_focus(0, 5 * factor)
                elif key in (pygame.K_s, pygame.K_DOWN):  # down
                    # self.canvas.move_offset(0, -5 * factor)
                    self.canvas.move_focus(0, -5 * factor)
                elif key in (pygame.K_d, pygame.K_RIGHT):  # right
                    # self.canvas.move_offset(-5 * factor, 0)
                    self.canvas.move_focus(5 * factor, 0)
                elif key in (pygame.K_a, pygame.K_LEFT):  # left
                    # self.canvas.move_offset(5 * factor, 0)
                    self.canvas.move_focus(-5 * factor, 0)
            if key in (pygame.K_e, pygame.K_KP_PLUS):
                self.canvas.zoom(2 * factor)
            elif key in (pygame.K_q, pygame.K_KP_MINUS):
                self.canvas.zoom(-2 * factor)
        for key in self.held:
            self.held_delay[key] = (self.held_delay[key] + 1) % 5


def parse_args():
    """Use argparse."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--duration", type=int, default=365*10, help=""
                        "Number of simulation steps")
    parser.add_argument("-t", "--timestep", type=int, default=60*60*24, help=""
                        "Number of Seconds calculated in one simulation step.")
    parser.add_argument("-i", "--interstep", type=int, default=10, help=""
                        "Number of sub-iterations before redrawing.")
    parser.add_argument("--hide", action="store_true", help="don't show the "
                        "screen. Useful when logging a position")
    parser.add_argument("-l", "--logplanet", type=str, default=None, help=""
                        "Name of a planet to be logged")
    arguments = parser.parse_args()
    arguments.timestep /= arguments.interstep
    return arguments

    # INTERSTEP = 10
    # TIMESTEP = (24 * 60 * 60) / INTERSTEP
    # DISPLAY = False
    # LOG_POSITION = True


def main():
    """docstring"""

    def simulation_step(current_step=0, interstep=10,
                        log=None, timestep=86400):
        """Do a simulation iteration."""
        for istep in range(interstep):
            for celestial in celestials:
                celestial.interact(celestials)
            for celestial in celestials:
                celestial.update(timestep)
                if bool(log) and celestial.name == log:
                    writer.writerow([current_step * interstep + istep,
                                     celestial.position.x,
                                     celestial.position.y])

    def draw_step(eventhandler):
        """Draw the current stakte to the pygame convas"""
        for idx, celestial in enumerate(celestials):
            canvas.place_object(celestial)
            # if (eventhandler.followmode and
            #         idx == eventhandler.follownum % len(celestials) - 1):
            if eventhandler.followmode and idx == 2:
                canvas.focus = celestials[eventhandler.follownum
                                          % len(celestials)].position

    arguments = parse_args()

    # turtle.delay(0)  # pylint: disable=no-member
    # turtle.bgcolor("#000000")  # pylint: disable=no-member
    celestials = []
    append_planets(celestials)
    file = io.StringIO()
    writer = csv.writer(file, lineterminator="\n")
    if not arguments.hide:
        canvas = Canvas()
        screen, timer = pygameinit()
        canvas.screen = screen
        eventhandler = EventHandler(canvas)
        for step in range(arguments.duration):
            eventhandler.check_events()
            simulation_step(step, arguments.interstep,
                            arguments.logplanet, arguments.timestep)
            screen.fill(MyColor("#141414").rgb_dec())
            draw_step(eventhandler)
            timer.tick(60)
            pygame.display.update()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit()
    else:
        for step in tqdm.tqdm(range(arguments.duration), ascii=True, ncols=80):
            simulation_step(step, arguments.interstep,
                            arguments.logplanet, arguments.timestep)
    if bool(arguments.logplanet):
        with open("simulation_out.csv", "w") as csv_file:
            csv_file.write(file.getvalue())

    #
    #
    # for celestial in celestials:
    #     celestial.draw()
    # for _ in tqdm.tqdm(range(400), ascii=True, ncols=80):
    #     for event in pygame.event.get():
    #         if event.type == pygame.QUIT:
    #             break
    #     for celestial in celestials:
    #         # print("interact")
    #         # ipdb.set_trace()
    #         celestial.interact(celestials)
    #     for celestial in celestials:
    #         # print("calculating")
    #         # ipdb.set_trace()
    #         celestial.update()
    #         # print("draw")
    #         celestial.draw()
    # input("Done!!!")
    # print(earth.gravitation_force(sun))
    # print(earth.distance(sun))


if __name__ == '__main__':
    main()

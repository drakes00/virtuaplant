#!/usr/bin/env python

#########################################
# Imports
#########################################
# - Logging
import  logging

# - Multithreading
import asyncio

# - World Simulator
import  sys, random, time
import  pygame
from    pygame.locals       import *
from    pygame.color        import *
import  pymunk

# - World communication
from    modbus              import ServerModbus as Server
from    modbus              import ClientModbus as Client

#########################################
# Logging
#########################################
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

#########################################
# PLC
#########################################
PLC_SERVER_IP   = "127.0.0.1"
PLC_SERVER_PORT = 5020

PLC_RW_ADDR = 0x0
PLC_TAG_RUN = 0x0

PLC_RO_ADDR	= 0x3E8
PLC_TAG_LEVEL   = 0x1
PLC_TAG_CONTACT = 0x2
PLC_TAG_MOTOR   = 0x3
PLC_TAG_NOZZLE  = 0x4

#########################################
# MOTOR actuator
#########################################
MOTOR_SERVER_IP     = "127.0.0.1"
MOTOR_SERVER_PORT   = 5021

MOTOR_RW_ADDR = 0x0
MOTOR_TAG_RUN = 0x0

#########################################
# NOZZLE actuator
#########################################
NOZZLE_SERVER_IP    = "127.0.0.1"
NOZZLE_SERVER_PORT  = 5022

NOZZLE_RW_ADDR = 0x0
NOZZLE_TAG_RUN = 0x0

#########################################
# LEVEL sensor
#########################################
LEVEL_SERVER_IP     = "127.0.0.1"
LEVEL_SERVER_PORT   = 5023

LEVEL_RO_ADDR = 0x0
LEVEL_TAG_SENSOR = 0x0

#########################################
# CONTACT sensor
#########################################
CONTACT_SERVER_IP   = "127.0.0.1"
CONTACT_SERVER_PORT = 5024

CONTACT_RO_ADDR = 0x0
CONTACT_TAG_SENSOR = 0x0

#########################################
# World code
#########################################
# "Constants"
WORLD_SCREEN_WIDTH              = 600
WORLD_SCREEN_HEIGHT             = 350
FPS                             = 50.0
WORLD_BASE_Y_OFFSET             = 40
WORLD_BASE_HEIGHT               = 20
WORLD_CONTACT_SENSOR_X_OFFSET   = 200
WORLD_LEVEL_SENSOR_X_OFFSET     = 155
WORLD_LEVEL_SENSOR_Y_OFFSET     = 120
WORLD_BOTTLE_X_OFFSET           = 100
WORLD_BOTTLE_Y_OFFSET           = WORLD_BASE_Y_OFFSET + WORLD_BASE_HEIGHT//2
WORLD_NOZZLE_X_OFFSET           = 170
WORLD_NOZZLE_Y_OFFSET           = 180

# Global Variables
global bottles
bottles = []
global plc, motor, nozzle, level, contact
plc     = {}
motor   = {}
nozzle  = {}
level   = {}
contact = {}

import pymunk
import random
from pygame.color import THECOLORS

def to_pygame(p):
    """Convert pymunk coordinates to pygame coordinates."""
    return int(p.x), int(-p.y + WORLD_SCREEN_HEIGHT)

# Shape functions
def velocity_limit(body, gravity, damping, dt):
    # Apply default physics (gravity)
    pymunk.Body.update_velocity(body, gravity, damping, dt)

    # Limit horizontal speed but allow gravity to act naturally
    max_x_speed = 1  # Limit side movement
    max_y_speed = 120  # Limit downward speed (optional)

    body.velocity = (
        max(-max_x_speed, min(body.velocity.x, max_x_speed)),  # Restrict sideways speed
        min(body.velocity.y, max_y_speed)  # Allow gravity, but limit downward speed
    )

def add_ball(space):
    mass = 0.01
    radius = 3
    inertia = pymunk.moment_for_circle(mass, 0, radius, (0,0))
    x = random.randint(170, 171)

    body = pymunk.Body(mass, inertia)
    body.velocity_func = velocity_limit  # Use modified function
    body.position = x, 180

    shape = pymunk.Circle(body, radius, (0,0))
    shape.collision_type = 0x6  # liquid

    space.add(body, shape)
    return shape

def draw_ball(screen, ball, color=THECOLORS['blue']):
    p = to_pygame(ball.body.position)  # Apply to_pygame here!
    pygame.draw.circle(screen, color, p, int(ball.radius), 2)

def add_bottle_in_sensor(space):
    radius = 2
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (10, WORLD_BOTTLE_Y_OFFSET)  # Move here!


    shape = pymunk.Circle(body, radius, (0, 0))
    shape.collision_type = 0x8  # 'bottle_in'
    
    space.add(body, shape)
    return shape

def add_level_sensor(space):
    radius = 3
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (WORLD_LEVEL_SENSOR_X_OFFSET, WORLD_LEVEL_SENSOR_Y_OFFSET)

    shape = pymunk.Circle(body, radius, (0, 0))
    shape.collision_type = 0x5  # level_sensor

    space.add(body, shape)
    return shape

def add_contact_sensor(space):
    radius = 2
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (WORLD_CONTACT_SENSOR_X_OFFSET, WORLD_BOTTLE_Y_OFFSET)

    shape = pymunk.Circle(body, radius, (0, 0))
    shape.collision_type = 0x1  # switch

    space.add(body, shape)
    return shape

def add_nozzle_actuator(space):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)  # Nozzle is likely static
    body.position = (WORLD_NOZZLE_X_OFFSET, WORLD_NOZZLE_Y_OFFSET)

    shape = pymunk.Poly.create_box(body, (15, 20))
    
    space.add(body, shape)
    return shape

def add_base(space):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)  # Use STATIC for a stationary object
    body.position = (WORLD_SCREEN_WIDTH/2, WORLD_BASE_Y_OFFSET)

    shape = pymunk.Poly.create_box(body, (WORLD_SCREEN_WIDTH, WORLD_BASE_HEIGHT))
    shape.friction = 1.0
    shape.collision_type = 0x7  # base

    space.add(body, shape)  # Add both body and shape together

    return shape

def add_bottle(space):
    mass = 10
    inertia = 0xFFFFFFFFF

    body = pymunk.Body(mass, inertia)
    body.position = (WORLD_BOTTLE_X_OFFSET, WORLD_BOTTLE_Y_OFFSET)

    l1 = pymunk.Segment(body, (-150, 0), (-100, 0), 2.0)
    l2 = pymunk.Segment(body, (-150, 0), (-150, 100), 2.0)
    l3 = pymunk.Segment(body, (-100, 0), (-100, 100), 2.0)

    # Glass friction
    l1.friction = 0.94
    l2.friction = 0.94
    l3.friction = 0.94

    # Set collision types for sensors
    l1.collision_type = 0x2 # bottle_bottom
    l2.collision_type = 0x3 # bottle_right_side
    l3.collision_type = 0x4 # bottle_left_side

    space.add(l1, l2, l3, body)

    return l1,l2,l3

def add_new_bottle(arbiter, space, *args, **kwargs):
    global bottles

    bottles.append(add_bottle(space))

    log.debug("Adding new bottle")

    return False

def draw_polygon(screen, shape):
    world_vertices = [shape.body.local_to_world(v) for v in shape.get_vertices()]
    fpoints = [to_pygame(p) for p in world_vertices]  # Apply to_pygame after world conversion
    pygame.draw.polygon(screen, THECOLORS['black'], fpoints)


def draw_lines(screen, lines, color=THECOLORS['dodgerblue4']):
    """Draw the lines"""
    for line in lines:
        body = line.body
        pv1 = body.position + line.a.rotated(body.angle)
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = to_pygame(pv1)  # Apply to_pygame here
        p2 = to_pygame(pv2)  # Apply to_pygame here
        pygame.draw.lines(screen, color, False, [p1, p2])

# Collision handlers
def no_collision(space, arbiter, *args, **kwargs):
    return False

def level_ok(space, arbiter, *args, **kwargs):
    global level

    log.debug("Level reached")
    plc['level'].write(LEVEL_RO_ADDR + LEVEL_TAG_SENSOR, 1)  # Level Sensor Hit, Bottle Filled

    return False

def no_level(space, arbiter, *args, **kwargs):
    global level

    log.debug("No level")
    plc['level'].write(LEVEL_RO_ADDR + LEVEL_TAG_SENSOR, 0)

    return False

def bottle_in_place(space, arbiter, *args, **kwargs):
    global contact

    log.debug("Bottle in place")
    plc['contact'].write(CONTACT_RO_ADDR + CONTACT_TAG_SENSOR, 1)

    return False

def no_bottle(space, arbiter, *args, **kwargs):
    global contact

    log.debug("No Bottle")
    plc['contact'].write(CONTACT_RO_ADDR + CONTACT_TAG_SENSOR, 0)
    
    return False

async def runWorld():
    pygame.init()

    screen = pygame.display.set_mode((WORLD_SCREEN_WIDTH, WORLD_SCREEN_HEIGHT))

    pygame.display.set_caption("Bottle-Filling Factory - World View - VirtuaPlant")
    clock = pygame.time.Clock()

    running = True

    space = pymunk.Space()
    space.gravity = (0.0, -900.0)

    # Contact sensor with bottle bottom
    handler = space.add_collision_handler(0x1, 0x2)
    handler.begin = no_collision

    # Contact sensor with bottle left side
    handler = space.add_collision_handler(0x1, 0x3)
    handler.begin = no_bottle

    # Contact sensor with bottle right side
    handler = space.add_collision_handler(0x1, 0x4)
    handler.begin = bottle_in_place

    # Contact sensor with ground
    handler = space.add_collision_handler(0x1, 0x7)
    handler.begin = no_collision

    # Level sensor with bottle left side
    handler = space.add_collision_handler(0x5, 0x3)
    handler.begin = no_level

    # Level sensor with bottle right side
    handler = space.add_collision_handler(0x5, 0x4)
    handler.begin = no_collision

    # Level sensor with water
    handler = space.add_collision_handler(0x5, 0x6)
    handler.begin = level_ok

    # Level sensor with ground
    handler = space.add_collision_handler(0x5, 0x7)
    handler.begin = no_collision

    # Bottle in with bottle sides and bottom
    handler = space.add_collision_handler(0x8, 0x2)
    handler.begin = no_collision
    handler.separate=add_new_bottle
    handler = space.add_collision_handler(0x8, 0x3)
    handler.begin = no_collision
    handler = space.add_collision_handler(0x8, 0x4)
    handler.begin = no_collision

    base            = add_base(space)
    nozzle_actuator = add_nozzle_actuator(space)
    contact_sensor  = add_contact_sensor(space)
    level_sensor    = add_level_sensor(space)
    bottle_in       = add_bottle_in_sensor(space)
    
    global bottles
    bottles.append(add_bottle(space))

    balls = []

    ticks_to_next_ball = 1

    fontBig     = pygame.font.SysFont(None, 40)
    fontMedium  = pygame.font.SysFont(None, 26)
    fontSmall   = pygame.font.SysFont(None, 18)

    # Reset simulation in case stopped and reloanched
    global plc
    plc['level'].write(LEVEL_RO_ADDR + LEVEL_TAG_SENSOR, 0)
    plc['contact'].write(CONTACT_RO_ADDR + CONTACT_TAG_SENSOR, 0)

    while running:
        global motor, nozzle

        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False

        screen.fill(THECOLORS["white"])

        # Manage plc
        # Read remote/local variables
        tag_level   = plc['level'].read(LEVEL_RO_ADDR + LEVEL_TAG_SENSOR)
        tag_contact = plc['contact'].read(CONTACT_RO_ADDR + CONTACT_TAG_SENSOR)
        tag_run     = plc['server'].read(PLC_RW_ADDR + PLC_TAG_RUN) 

        # Manage PLC programm
        # Motor Logic
        if (tag_run == 1) and ((tag_contact == 0) or (tag_level == 1)):
            tag_motor = 1
        else:
            tag_motor = 0
        
        # Nozzle Logic 
        if (tag_run == 1) and ((tag_contact == 1) and (tag_level == 0)):
            tag_nozzle = 1
        else:
            tag_nozzle = 0
        
        # Write remote/local variables
        plc['motor'].write(MOTOR_RW_ADDR + MOTOR_TAG_RUN, tag_motor)
        plc['nozzle'].write(NOZZLE_RW_ADDR + NOZZLE_TAG_RUN, tag_nozzle)
        
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_LEVEL, tag_level)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_CONTACT, tag_contact)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_MOTOR, tag_motor)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_NOZZLE, tag_nozzle)
        
        # Manage nozzle actuator : filling bottle
        if plc['nozzle'].read(NOZZLE_RW_ADDR + NOZZLE_TAG_RUN) == 1:
            ball_shape = add_ball(space)
            balls.append(ball_shape)
        
        # Manage motor : move the bottles
        if plc['motor'].read(MOTOR_RW_ADDR + MOTOR_TAG_RUN) == 1:
            for bottle in bottles:
                # bottle[0].body.position.x += 0.25
                current_position = bottle[0].body.position
                new_position = pymunk.Vec2d(current_position.x + 0.25, current_position.y)
                bottle[0].body.position = new_position
        
        # Draw water balls
        # Remove off-screen balls
        balls_to_remove = []
        for ball in balls:
            if ball.body.position.y < 0 or ball.body.position.x > WORLD_SCREEN_WIDTH+150:
                balls_to_remove.append(ball)
            else:
                draw_ball(screen, ball)
        
        for ball in balls_to_remove:
            space.remove(ball, ball.body)
            balls.remove(ball)
        
        # Draw bottles
        for bottle in bottles:
            if bottle[0].body.position.x > WORLD_SCREEN_WIDTH+150: #or bottle[0].body.position.y < -150:
                for segment in bottle:
                    space.remove(segment)
        
                space.remove(bottle[0].body)
                bottles.remove(bottle)
        
                continue
            draw_lines(screen, bottle)
        
        # Draw the base and nozzle actuator
        draw_polygon(screen, base)
        draw_polygon(screen, nozzle_actuator)
        
        # Draw the contact sensor 
        draw_ball(screen, contact_sensor, THECOLORS['green'])
        
        # Draw the level sensor
        draw_ball(screen, level_sensor, THECOLORS['red'])
        
        title           = fontMedium.render(str("Bottle-filling factory"), 1, THECOLORS['deepskyblue'])
        name            = fontBig.render(str("VirtuaPlant"), 1, THECOLORS['gray20'])
        instructions    = fontSmall.render(str("(press ESC to quit)"), 1, THECOLORS['gray'])
        
        screen.blit(title, (10, 40))
        screen.blit(name, (10, 10))
        screen.blit(instructions, (WORLD_SCREEN_WIDTH-115, 10))
        
        space.step(1/FPS)
        pygame.display.flip()
        # breakpoint()
        # await asyncio.sleep(1/FPS)

        
async def main():
    global plc

    plc = {
        'motor': Client(MOTOR_SERVER_IP, port=MOTOR_SERVER_PORT),
        'nozzle': Client(NOZZLE_SERVER_IP, port=NOZZLE_SERVER_PORT),
        'level': Client(LEVEL_SERVER_IP, port=LEVEL_SERVER_PORT),
        'contact': Client(CONTACT_SERVER_IP, port=CONTACT_SERVER_PORT),
        'server': Client(PLC_SERVER_IP, port=PLC_SERVER_PORT),
    }

    # 🚀 Now start the world simulation (after everything is ready)
    await runWorld()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.debug("Shutting down servers...")
        sys.exit(0)

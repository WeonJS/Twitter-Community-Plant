import time
import json
import math
import random
import tweepy
import pygame

CONSUMER_KEY = '<nope>'
CONSUMER_KEY_SECRET = '<nope>'
ACCESS_TOKEN = '<nope>'
ACCESS_TOKEN_SECRET = '<nope>'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_KEY_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# CONSTANTS
GROWTH_FOLLOWER_REQUIREMENT = 10
BOT_ACCOUNT_HANDLE = "@CommunityPlant"
COOLDOWN_TIME_HOURS = 24
SECONDS_IN_HOUR = 3600
POST_SAMPLE_SIZE = 3
GROWTH_ANGLE_RANGE = 30
GROWTH_ANGLE_OFFSET = 20
SCR_W = 1200
SCR_H = 1200
INITIAL_BRANCH_LENGTH = 200
MINIMUM_BRANCH_LENGTH = 40
INITIAL_BRANCH_WIDTH = 40
SUBSEQUENT_BRANCH_MULT = 0.9
BRANCH_COLOR = (92, 72, 32)
LEAF_COLOR = (56, 143, 66, 200)
SKY_FILL = (62, 178, 209)
INITIAL_LEAF_SIZE = 100
SUBSEQUENT_LEAF_MULT = 1.2
MOOD_SCALAR = 10
MAX_HEALTH = 100
MIN_HEALTH = 0

# get most recent non-reply tweets
recent_posts = []
for p in api.user_timeline(BOT_ACCOUNT_HANDLE):
    if p.in_reply_to_status_id is None:
        recent_posts.append(p)
        if len(recent_posts) == POST_SAMPLE_SIZE:
            break

interactions = 0
for p in recent_posts:
    interactions += (p.retweet_count + p.favorite_count)
interactions /= POST_SAMPLE_SIZE


# PLANT DATA
PLANT_DATA_PATH = './plant_data.json'


def get_followers():
    return api.get_user(BOT_ACCOUNT_HANDLE).followers_count

FOLLOWER_ENGAGEMENT_RATIO = interactions / get_followers()

def die():
    set_data("alive", False)
    api.update_status("I died :(")
    rebirth()



def rebirth():
    set_data("alive", True)
    set_data("health", 100)
    set_data("followers_at_birth", get_followers())
    set_data("generations", [[TreeNode(SCR_W/2, SCR_H - 100, None, True).__dict__]])


class TreeNode:
    def __init__(self, x, y, parent, root):
        self.pos = {"x": x, "y": y}
        self.parent = parent
        self.root = root


def add_tree_generation():
    tree_generation_data = get_data("generations")
    latest_generation = list(reversed(tree_generation_data))[0]
    new_generation = []
    gen_branch_length = INITIAL_BRANCH_LENGTH * math.pow(SUBSEQUENT_BRANCH_MULT, len(tree_generation_data) + 1) + MINIMUM_BRANCH_LENGTH
    for point in latest_generation:
        chance = random.randint(0, 10)
        if random.randint(0, 10) > 5:
            rand_angle1 = GROWTH_ANGLE_RANGE
        else:
            rand_angle1 = -GROWTH_ANGLE_RANGE

        rand_angle1 += random.randint(-GROWTH_ANGLE_OFFSET, GROWTH_ANGLE_OFFSET)
        x_diff_ang1 = int(gen_branch_length * (math.sin(math.radians(rand_angle1))))
        y_diff_ang1 = int(gen_branch_length * (math.cos(math.radians(rand_angle1))))
        node1 = TreeNode(point["pos"]["x"]+x_diff_ang1, point["pos"]["y"]-y_diff_ang1, point, False)
        new_generation.append(node1.__dict__)
        if chance < 5:
            rand_angle2 = -rand_angle1
            rand_angle2 += random.randint(-GROWTH_ANGLE_OFFSET, GROWTH_ANGLE_OFFSET)
            x_diff_ang2 = int(gen_branch_length * (math.sin(math.radians(rand_angle2))))
            y_diff_ang2 = int(gen_branch_length * (math.cos(math.radians(rand_angle2))))
            node2 = TreeNode(point["pos"]["x"]+x_diff_ang2, point["pos"]["y"]-y_diff_ang2, point, False)
            new_generation.append(node2.__dict__)
    tree_generation_data.append(new_generation)
    set_data("generations", tree_generation_data)


# GENERATE IMAGE OF PLANT BASED ON TWITTER DATA
def generate_image():
    # setup pygame
    pygame.init()
    #making screen a pygame.Surface will enable image editing without visual display (like an AWS server) :D
    # screen = pygame.display.set_mode((SCR_W, SCR_H), pygame.SRCALPHA, 32)
    screen = pygame.Surface((SCR_W, SCR_H), pygame.SRCALPHA, 32)
    screen.fill(SKY_FILL)
    # rebirth()
    # get twitter data
    followers = get_followers()
    delta_followers = max(min(followers - get_data("followers_at_birth"), math.inf), 0)

    # health calculations
    health = get_data("health")
    set_data("health", max(min(get_data("health") + (MOOD_SCALAR * ((interactions - (FOLLOWER_ENGAGEMENT_RATIO * followers)) / (FOLLOWER_ENGAGEMENT_RATIO * followers))), MAX_HEALTH), MIN_HEALTH))

    if health == 0:
        die()

    stored_generation_tree_data = get_data("generations")

    # how many generations should be in the generation tree (+1 for the root)
    expected_generation_count = int(delta_followers / GROWTH_FOLLOWER_REQUIREMENT) + 1

    # generations to add onto the already existing generation tree
    needed_generations = max(min(expected_generation_count - len(stored_generation_tree_data), math.inf), 0)

    for i in range(0, needed_generations):
        add_tree_generation()

    # draw branches
    generations = get_data("generations")
    for gen in generations:
        for point in gen:
            if point["root"] != True:
                parent = point["parent"]
                pygame.draw.line(screen, BRANCH_COLOR, (point["pos"]["x"], point["pos"]["y"]), (parent["pos"]["x"], parent["pos"]["y"]), int(INITIAL_BRANCH_WIDTH * math.pow(SUBSEQUENT_BRANCH_MULT, generations.index(gen))))

    # add leaves to last and second to last generations
    if len(list(reversed(generations))) > 1:
        latest_gen = list(reversed(generations))[0]
        leaves_size = int(INITIAL_LEAF_SIZE * math.pow(SUBSEQUENT_LEAF_MULT, len(generations)))
        leaves_img = pygame.image.load("leaves.png")
        leaves_dead_level = abs((2.55 * (get_data("health") - MAX_HEALTH)))
        leaves_img.fill((leaves_dead_level, 0, 0), special_flags=pygame.BLEND_ADD)
        leaves_img = pygame.transform.scale(leaves_img, (leaves_size, leaves_size))
        for pnt in latest_gen:
            screen.blit(leaves_img, (int(pnt["pos"]["x"]-100), int(pnt["pos"]["y"]-100)))
        if len(list(reversed(generations))) != 2:
            second_latest_gen = list(reversed(generations))[1]
            for p2 in second_latest_gen:
                screen.blit(leaves_img, (int(p2["pos"]["x"]-100), int(p2["pos"]["y"]-100)))

    # pot
    pot_img = pygame.image.load("pot.png")
    screen.blit(pot_img, (int(SCR_W / 2 - 60), SCR_H - 110))

    pygame.image.save(screen, "tree.png")
    pygame.quit()

    
# MAKE POST
def make_post():
    generate_image()
    upload_result = api.media_upload("./tree.png")
    sts = "#plant #tree #gardening #python"
    api.update_status(status=sts, media_ids=[upload_result.media_id_string])


# PLANT DATA JSON ACCESSORS
def get_data(key):
    with open(PLANT_DATA_PATH) as df:
        data = json.load(df)
        return data[key]


def set_data(key, val):
    with open(PLANT_DATA_PATH) as data_file:
        data = json.load(data_file)
        data[key] = val
    with open(PLANT_DATA_PATH, 'w') as data_file:
        json.dump(data, data_file)

make_post()

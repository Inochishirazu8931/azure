import os, sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# importing all required modules and aliasing them
import pygame, math
import random as r
from pygame import gfxdraw as gfx
from datetime import datetime
from pathlib import Path


def resource_path(relative_path): # useful for compiling
	base_path = Path(getattr(sys, '_MEIPASS', Path.cwd()))
	return str(base_path / relative_path)

# setting colour variables
BLACK        = (0x0, 0x0, 0x0)
WHITE        = (0xbb, 0xbb, 0xbb)
DARKEST_GREY = (0x12+10, 0x12+4, 0x12+8)
DARKER_GREY  = (0x20+10, 0x20+4, 0x20+8)
BLUE         = (0x01, 0x21, 0x91)
RED          = (0xff, 0x00, 0x00)

# command line arg checks (currently disabled)
arg = sys.argv[1] if len(sys.argv) > 1 else None
match arg:
	# case '-f': flags = pygame.NOFRAME
	case _:    flags = pygame.NOFRAME | pygame.FULLSCREEN  # Default
screen = pygame.display.set_mode(flags=flags, vsync=1)
WSX, WSY = screen.get_size()
# NOFARME removes window border & controls, FULLSCREEN does fullscreen, SCALED makes sure the graphics scale with window size

pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
# fancy mouse

#---------------------------------FONTS--------------------------------------------

pygame.font.init()
# using the font 'ASfont' as the game font
font_path = Path("fonts") / "AlumniSansSC.ttf"
ASfont = {size: pygame.font.Font(resource_path(font_path), size) for size in (20, 40, 60)}

def textbox(font, string, rect_alignment, color=WHITE, alignment='center'):
	"""Write text on the screen at a given co-ordinates"""
	text = font.render(string, True, color)
	rect = text.get_rect()
	setattr(rect, alignment, rect_alignment)
	screen.blit(text, rect)

textbox(ASfont[60], "Loading assets...", [WSX/2, WSY/2])
pygame.display.flip()
#---------------------------------IMAGES------------------------------------------

# importing the background image which will be looped later
background_path = Path("assets") / "background_tile.png"
background_tile = pygame.transform.smoothscale_by(pygame.image.load(resource_path(str(background_path))).convert_alpha(), 0.32)
bg_length = int(250*.32)

def load_scaled_image(base_path, subpath, scale=1.0, flip_left=False):
	"""load an image, scale it, and optionally flip it"""
	full_path = resource_path(str(Path(base_path) / subpath))
	img = pygame.image.load(full_path).convert_alpha()
	scaled_img = pygame.transform.scale_by(img, scale)
	return pygame.transform.flip(scaled_img, flip_left, False) if flip_left else scaled_img

# configuration for all images
IMAGE_CONFIGS = {
	# UI Elements
	"heart":          {"path": "assets/ui_elements/heart.png",         "scale": 2},
	"heart_shadow":   {"path": "assets/ui_elements/heart_shadow.png",  "scale": 2},
	"bullet":         {"path": "assets/ui_elements/bullet.png",        "scale": 1.6},
	"bullet_shadow":  {"path": "assets/ui_elements/bullet_shadow.png", "scale": 1.6},
	
	# enemies
	"enemy_basic_r":           {"path": "assets/enemies/basic.png",           "scale": 0.3},
	"enemy_shooter_r":         {"path": "assets/enemies/shooter.png",         "scale": 0.225},
	"enemy_exploder_r":        {"path": "assets/enemies/exploder.png",        "scale": 0.3},
	"enemy_exploder_primed_r": {"path": "assets/enemies/exploder_primed.png", "scale": 0.3},
	"boss_r":                  {"path": "assets/enemies/boss.png",            "scale": 0.45},
	"boss_primed_r":           {"path": "assets/enemies/boss_primed.png",     "scale": 0.45},
}

images = {}
# loading the images
for name, config in IMAGE_CONFIGS.items():
	images[name] = load_scaled_image("", config["path"], config["scale"])
	
	# auto-generate left-facing variants (for enemies)
	if name.endswith("_r"):
		left_name = name.replace("_r", "_l")
		images[left_name] = load_scaled_image("", config["path"], config["scale"], flip_left=True)

images['enemy_exploder_primed_r'].set_alpha(0)
images['enemy_exploder_primed_l'].set_alpha(0)

# player image loader
def player_loader(path):
	return pygame.transform.scale_by(pygame.image.load(resource_path(path)).convert_alpha(),1.75)

# configuration for all player animations
PLAYER_ANIMATIONS = {
	"walk": {
		"up":        "walk/walk_up/walk_up{x}.png",
		"right_up":  "walk/walk_right_up/walk_right_up{x}.png",
		"right_down":"walk/walk_right_down/walk_right_down{x}.png",
		"down":      "walk/walk_down/walk_down{x}.png",
		"left_down": "walk/walk_left_down/walk_left_down{x}.png",
		"left_up":   "walk/walk_left_up/walk_left_up{x}.png",
	},
	"idle": {
		"up":        "idle/idle_up/idle_up{x}.png",
		"right_up":  "idle/idle_right_up/idle_right_up{x}.png",
		"right_down":"idle/idle_right_down/idle_right_down{x}.png",
		"down":      "idle/idle_down/idle_down{x}.png",
		"left_down": "idle/idle_left_down/idle_left_down{x}.png",
		"left_up":   "idle/idle_left_up/idle_left_up{x}.png",
	}
}

# load all animations dynamically
images_player = {
	anim_type: {
		direction: [player_loader(f"assets/sprites/{template.format(x=x)}")
			for x in range(8)
		]
		for direction, template in directions.items()
	}
	for anim_type, directions in PLAYER_ANIMATIONS.items()
}

#------------------------------GLOBALS---------------------------------------------

# global variables
player_speed = 2
enemy_shoot_cooldown = 300

global_dx = 0
global_dy = 0
global_offset = [0, 0]

projectile_speed = 10
player_projectile_speed = 15
enemy_projectile_speed = 3

enemy_speed = 1.2

mouse_left_held = False
mouse_right_click = False

player_projectiles = []
enemy_projectiles = []
adversaries = []
explosions = []
active_boss = None
boss_max_health = 1000

explosion_drawings = []

level_time = 0
timec = 0

state = 'start'
score = 0

reloadtrig = False

#-----------------------------FUNCS------------------------------------------------

def clamp(n, minn, maxn):
	"""Forces a number to be between a set min and max value"""
	if n < minn: return minn
	elif n > maxn: return maxn
	else: return n

def vector_converter(num, angle):
	"""Returns a list with x & y offset from a vector quantity"""
	return [num*math.cos(angle), num*math.sin(angle)]

#-----------------------------UPGRADES---------------------------------------------

# upgrade functions
def upgradeFireRate():
	player.max_cooldown -= 2
def upgradeDamage():
	global player_speed
	player.damage += 1.5
	player_speed -= .1
def upgradeHealth():
	if player.health < player.max_health:
		player.health += 1
	else:
		player.max_health += 1
def upgradeAmmo():
	player.max_rounds += 2
	player.reload_length += .15
def upgradeReloadRate():
	player.reload_length -= .1
def upgradeSpeed():
	global player_speed
	player_speed += .2

upgrade_list = (
	('Fire Rate',   upgradeFireRate,   'Increases the rate the', 'bullets are fired at by 10%'),
	('Damage',      upgradeDamage,     'Increases damage dealt by 10%', 'but decreases move speed by 5%'),
	('Health',      upgradeHealth,     'Increases max hp by 1', 'if at full, heals otherwise'),
	('Ammo',        upgradeAmmo,       'Increases maximum rounds', 'by 2 but slows reloads by 15%'),
	('Reload Rate', upgradeReloadRate, 'Increases reloading speed', 'by 10% of base speed'),
	('Speed',       upgradeSpeed,      'Increases player speed', 'by 10% of base speed')
)

current_upgrades = []

def required_exp(): return 250*player.level**1.4+2000

def upgrade_check():
	global state, current_upgrades
	if player.exp >= required_exp():
		state = 'upgrade'
		player.exp -= required_exp()
		player.level += 1
		current_upgrades = r.sample(upgrade_list, k=3)

def upgrade_picker():
	global state, player_shoot_cooldown
	if pygame.Rect(WSX/4-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
		current_upgrades[0][1]()
	elif pygame.Rect(WSX/4*2-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
		current_upgrades[1][1]()
	elif pygame.Rect(WSX/4*3-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
		current_upgrades[2][1]()
	else: return
	state = 'play'

#--------------------------------PRIMARY-FUNCS-------------------------------------

def UPDATE():
	"""GAME LOGIC"""
	global level_time, timec, score, active_boss, state
	level_time += 1/60

	if int(level_time) > timec:
		score += 10
		timec = level_time

	player.update()

	upgrade_check()

	# writes the current global offset(distance moved) from the original start point
	global_offset[0] += global_dx
	global_offset[1] += global_dy

	# updates the player projectiles
	try:
		for i in range(len(player_projectiles)):
			player_projectiles[i].update()
			if player_projectiles[i].delete:
					del player_projectiles[i]
	except IndexError: # To avoid end of list error
		pass

	if active_boss:
		active_boss.update()
		if active_boss.delete:
			active_boss = None

	# updates enemies
	try:
		for i in range(len(adversaries)):
			for explosion in explosions:
				if math.sqrt((explosion[0]-adversaries[i].rect.center[0])**2+(explosion[1]-adversaries[i].rect.center[1])**2)<=explosion[2]:
					adversaries[i].health -= 20
					adversaries[i].knockback = vector_converter(10,
						math.atan2(adversaries[i].rect.center[1]-explosion[1],adversaries[i].rect.center[0]-explosion[0]))
			adversaries[i].update()
			if adversaries[i].delete:
					del adversaries[i]
	except IndexError: # To avoid end of list error
		pass

	# updates the enemy projectiles
	try:
		for i in range(len(enemy_projectiles)):
			enemy_projectiles[i].update()
			if enemy_projectiles[i].delete:
					del enemy_projectiles[i]
	except IndexError: # To avoid end of list error
		pass

	try:
		for i in range(len(explosions)):
			if explosions[i][3]:
				del explosions[i]
			else:
				explosions[i][3] = 1
	except IndexError:
		pass

	for i in range(len(explosion_drawings)):
		explosion_drawings[i][0] += global_dx
		explosion_drawings[i][1] += global_dy

	# enemy spawn mechanic
	if level_time < 15:
		pass
	elif level_time < 45:
		pass
	else:
		pass

	# if len(adversaries) < 0: # testing
	rng = r.randint(0, 80 + len(adversaries)*2 - clamp(round(level_time*.08), 0, 5)*4)
	if rng < 5:
		x = r.randint(-100, WSX+100)
		y = r.randint(-100, WSY+100)

		if x < 20 or x > WSX-20 or y < 20 or y > WSY-20:
			if rng < 3:
				adversaries.append(Enemy(x, y))
			elif rng < 4:
				adversaries.append(rangedEnemy(x, y))
			else:
				adversaries.append(exploderEnemy(x, y))

	if not active_boss and level_time >= 120: active_boss = Boss(300, -50)

def DRAW():
	"""DRAWING CODE"""
	global current_upgrades

	screen.fill(DARKEST_GREY)

	# draws a looping background taking into account the global offset
	# only draws the minimum number of tiles required in order to not waste resources
	for x in range(-bg_length, WSX, bg_length):
		for y in range(-bg_length, WSY, bg_length):
			screen.blit(background_tile, (x + global_offset[0]%bg_length, y + global_offset[1]%bg_length))

	gfx.box(screen, (0, 0, WSX, WSY), (0, 0, 0, 100))

	# draws the player bullets
	for bullet in player_projectiles:
		bullet.render()

	# draws the player
	player.render()

	if active_boss: active_boss.render()

	# draws the enemies
	for enemy in adversaries:
		enemy.render()

	# draws the enemy bullets
	for bullet in enemy_projectiles:
		bullet.render()

	# drawing the explosions
	try:
		for i in range(len(explosion_drawings)):
			thickness = (40-abs(explosion_drawings[i][2]-40))/5
			for j in range(round(thickness)):
				gfx.aacircle(screen,
					round(explosion_drawings[i][0]),
					round(explosion_drawings[i][1]),
					round(explosion_drawings[i][2]+j-thickness/2),
					WHITE)
				if explosion_drawings[i][2] >= 80:
					del explosion_drawings[i]
			explosion_drawings[i][2] += 8
	except IndexError: # To avoid end of list error
		pass

	if active_boss:
		gfx.box(screen, [WSX/4, 60, round(active_boss.health/boss_max_health*WSX/2), 8], RED)
		for i in range(2):
			gfx.rectangle(screen, [WSX/4-1-i, 59-i, WSX/2+2+i, 10+i], WHITE)

	# draws a screen border
	rects = [(0, 0, WSX, 40), # top
			(0, 40, 20, WSY-40), # left
			(WSX-20, 40, 20, WSY-40), # right
			(20, WSY-20, WSX-40, 20)] # bottom
	for rect in rects:
		gfx.box(screen, rect, DARKEST_GREY)

	rects = [(20, 40, WSX-40, 10), # top
			(20, 50, 10, WSY-80), # left
			(WSX-30, 50, 10, WSY-80), # right
			(20, WSY-30, WSX-40, 10)] # bottom
	for rect in rects:
		gfx.box(screen, rect, DARKER_GREY)

	# draws UI elements
	# drawing the reload bar
	if player.reloading:
		gfx.rectangle(screen, (WSX/2-15, WSY/2-18, 30, 6), WHITE)
		gfx.box(screen, (
			WSX/2-15, WSY/2-18,
			30*((player.reload_length*60-player.reload_timer)/(player.reload_length*60)
				), 6), WHITE)
	# drawing the hearts
	for i in range(player.max_health):
		screen.blit(images['heart_shadow'], (20+i*25,5))
	for i in range(player.health):
		screen.blit(images['heart'], (20+i*25,5))

	# drawing the rounds
	if player.max_rounds <= 16:
		for i in range(player.max_rounds):
			screen.blit(images['bullet_shadow'], (WSX-50-i*12, 7))
		for i in range(player.rounds):
			screen.blit(images['bullet'], (WSX-50-i*12, 7))
	else:
		textbox(ASfont[20], f"{player.rounds:02d}/{player.max_rounds}", (WSX-45, 23), alignment='midright')
		screen.blit(images['bullet'], (WSX-50, 7))

	textbox(ASfont[20], str(score), (WSX/2, 15))

	gfx.rectangle(screen, (WSX/6, 25, WSX*2/3, 10), WHITE)
	gfx.box(screen, (WSX/6, 25, WSX*2/3*player.exp/(required_exp()), 10), WHITE)

	# adds a semi-transparent layer when paused
	if state != 'play': gfx.box(screen, (0, 0, WSX, WSY), (0, 0, 0, 100))
	
	if state in 'pause':
		textbox(ASfont[40], 'Paused', (WSX/2, WSY/4))
		textbox(ASfont[20], 'Press [SPACE] to resume', (WSX/2, WSY/4*3-25))
		textbox(ASfont[20], 'Press [Esc] to exit to main menu', (WSX/2, WSY/4*3))
	elif state in 'upgrade':
		textbox(ASfont[60], 'Pick an upgrade', (WSX/2, 200))
		for i in range(3):
			gfx.box(screen, (WSX/4*(i+1)-150, WSY/2-60, 300, 120), (0x20+10, 0x20+4, 0x20+8, 200))
			textbox(ASfont[40], current_upgrades[i][0], (WSX/4*(i+1), WSY/2-30), (255, 160, 160))
			textbox(ASfont[20], current_upgrades[i][2], (WSX/4*(i+1), WSY/2+5))
			textbox(ASfont[20], current_upgrades[i][3], (WSX/4*(i+1), WSY/2+25))
		if pygame.Rect(WSX/4-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
			gfx.box(screen, (WSX/4-150, WSY/2-60, 300, 120), (255, 255, 255, 10))
		elif pygame.Rect(WSX/4*2-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
			gfx.box(screen, (WSX/4*2-150, WSY/2-60, 300, 120), (255, 255, 255, 10))
		elif pygame.Rect(WSX/4*3-150, WSY/2-60, 300, 120).collidepoint(mouse_pos):
			gfx.box(screen, (WSX/4*3-150, WSY/2-60, 300, 120), (255, 255, 255, 10))
	# adds a semi-transparent red layer when dead
	elif state in ['death', 'win']:
		textbox(ASfont[60], "You Died" if state == 'death' else "You Win", (WSX/2, WSY/4), color=(255, 150, 150) if state == 'death' else (150, 255, 150))
		textbox(ASfont[40], f"Final Score: {str(score)}", (WSX/2, WSY/5*2))
		textbox(ASfont[20], 'Press [SPACE] to go back to main menu', (WSX/2, WSY/4*3))
	elif state == 'start':
		screen.fill((0x8+10, 0x8+4, 0x8+8))
		textbox(ASfont[60], 'Press [SPACE] to start game', (WSX/2, WSY/3))
		instructions = [
			'Use [WASD]/↑←↓→ to move',
			'Use mouse to aim and LMB to shoot',
			'Reload pressing RMB or [r]',
			'Pause game with [SPACE]'
			'',
			'Kill enemies to earn points and experience',
			'Survive and defeat the boss'
			'',
			'Press [Esc] to quit game'
		]
		for i in range(len(instructions)):
			textbox(ASfont[20], instructions[i], (WSX/2, WSY/3*2+i*25))

#---------------------------------CLASSES------------------------------------------

class Player(pygame.sprite.Sprite):
	# the main player class
	def __init__(self):
		super().__init__() # initialises the Sprite class

		self.rect = pygame.Rect(WSX/2-10, WSY/2-10, 20, 40) # hitbox
		self.speed = player_speed

		self.image = images_player['idle']['down'][0]
		self.animation_state = "idle"  # 'idle' or 'walk'
		self.frame = 0
		self.direction = 'down'

		self.knockback_speed = 7
		self.knockback = [0,0]

		self.exp = 0
		self.level = 1

		# health variables
		self.max_health = 5
		self.health = self.max_health
		self.invincibility = 0

		# gun variables
		self.damage = 15
		self.max_rounds = 12
		self.rounds = self.max_rounds
		self.reloading = False
		self.reload_timer = 0
		self.reload_length = 1 # second(s)
		self.max_cooldown = 20
		self.shoot_cooldown = self.max_cooldown
		self.spread = 12 # 10ths of a degree on either side

	def update(self):
		global state, global_dx, global_dy, explosions # grabbing the global variables

		global_dx = 0
		global_dy = 0

		#------------------MOVEMENT---------------------

		# movement detection
		moving_right = (keys[pygame.K_d] or keys[pygame.K_RIGHT])
		moving_left  = (keys[pygame.K_a] or keys[pygame.K_LEFT])
		moving_up    = (keys[pygame.K_w] or keys[pygame.K_UP])
		moving_down  = (keys[pygame.K_s] or keys[pygame.K_DOWN])

		x_movement = (moving_right != moving_left)
		y_movement = (moving_up != moving_down)

		# slows player down when shooting
		self.speed = player_speed/3 if mouse_left_held and not self.reloading else player_speed

		# only one direction movement
		if x_movement != y_movement:
			if moving_right:
				self.direction = 'right_down'
				global_dx = - self.speed
			elif moving_left:
				self.direction = 'left_down'
				global_dx = self.speed
			elif moving_down:
				self.direction = 'down'
				global_dy = - self.speed
			elif moving_up:
				self.direction = 'up'
				global_dy = self.speed

		# diagonal movement
		elif x_movement and y_movement:
			if moving_right:
				global_dx = - self.speed / math.sqrt(2)
				if moving_up:
					self.direction = 'right_up'
					global_dy = self.speed / math.sqrt(2)
				elif moving_down:
					self.direction = 'right_down'
					global_dy = - self.speed / math.sqrt(2)
			elif moving_left:
				global_dx = self.speed / math.sqrt(2)
				if moving_up:
					self.direction = 'left_up'
					global_dy = self.speed / math.sqrt(2)
				elif moving_down:
					self.direction = 'left_down'
					global_dy = - self.speed / math.sqrt(2)

		if abs(self.knockback[0]) > .5 and abs(self.knockback[1]) > .5:
			global_dx -= self.knockback[0]
			global_dy -= self.knockback[1]
			self.knockback = [x/1.1 for x in self.knockback]

		#-----------------SHOOTING----------------------

		# reload start
		if (mouse_right_click or reloadtrig) and not self.reloading and self.rounds != self.max_rounds:
			self.reloading = True
			self.reload_timer = self.reload_length * 60

		# update reload counter
		if self.reloading:
			self.reload_timer -= 1

			if self.reload_timer <= 0:
				self.reloading = False
				self.rounds = self.max_rounds

		# shooting
		elif mouse_left_held:
			if self.shoot_cooldown <= 0:
				dx = mouse_pos[0] - self.rect.center[0]
				dy = mouse_pos[1] - self.rect.center[1]

				theta = math.atan2(dy, dx)
				theta += math.radians(r.randint(-self.spread, self.spread)*.1)*2 if x_movement or y_movement else math.radians(r.randint(-self.spread, self.spread)*.1)
				player_projectiles.append(playerProjectile(self.rect.center[0], self.rect.center[1], theta, self.damage))
				self.rounds -= 1

				if self.rounds == 0:
					self.reloading = True
					self.reload_timer = self.reload_length * 60

				self.shoot_cooldown = self.max_cooldown
		
		self.shoot_cooldown -= 1

		#-----------------COLLISION---------------------

		if self.invincibility:
			self.invincibility -= 1

		if explosions and not self.invincibility:
			for explosion in explosions:
				if math.sqrt((explosion[0]-WSX/2)**2+(explosion[1]-WSY/2)**2)<=explosion[2]:
					self.invincibility = 90
					self.health -= 2
					self.knockback = vector_converter(self.knockback_speed*2, math.atan2(WSY/2-explosion[1],WSX/2-explosion[0]))

		# collision check for enemies and projectiles
		hit = self.rect.collideobjects(adversaries, key=lambda enemy : enemy.rect)
		if not hit: hit = self.rect.collideobjects(enemy_projectiles, key=lambda bullet : bullet.enemy_hitbox)
		if hit and not self.invincibility:
			self.invincibility = 60
			self.health -= 1
			if isinstance(hit, Enemy):
				self.knockback = vector_converter(self.knockback_speed, math.atan2(WSY/2-hit.rect.center[1],WSX/2-hit.rect.center[0]))
			elif isinstance(hit, enemyProjectile):
				self.knockback = hit.knockback
				enemy_projectiles.remove(hit)
		
		if self.health <= 0:
			state = 'death'

		#------------------ANIMATION--------------------
		
		# determine animation type and speed
		is_moving = (x_movement or y_movement)
		self.animation_state = "walk" if is_moving else "idle"
		
		# set animation speed (slower when shooting)
		speed = 6 if (mouse_left_held and not self.reloading) else 12

		# update frame counter (loops after 8 frames)
		self.frame += 1 / 60 * speed
		self.frame %= 8

		# get current animation frame
		self.image = images_player[self.animation_state][self.direction][int(self.frame)]

	def render(self): # drawing the player
		self.image.set_alpha(abs(7.5-self.invincibility%15)*34)
		screen.blit(self.image, (self.rect.x-32, self.rect.y-35))
		# gfx.filled_circle(screen, round(WSX/2), round(WSY/2), 150, [255, 0, 0, 20])
		# gfx.box(screen, self.rect, [0, 0, 255, 50])

class Projectile(pygame.sprite.Sprite):
	# base projectile object for all uses
	def __init__(self, x, y, theta):
		super().__init__()
		self.x = x
		self.y = y

		self.v = vector_converter(projectile_speed, theta)

		self.enemy_hitbox = pygame.Rect(self.x, self.y, 4, 4)
		self.player_hitbox = []

		self.delete = False

		self.knockback = vector_converter(5, theta)

	def update(self): # movement
		global global_dx
		global global_dy

		self.x += self.v[0] + global_dx
		self.y += self.v[1] + global_dy

		if self.x > WSX or self.x < 0 or self.y > WSY or self.y < 0:
			self.delete = True

class playerProjectile(Projectile):
	def __init__(self, x, y, theta, damage):
		super().__init__(x, y, theta)
		self.v = vector_converter(player_projectile_speed, theta)
		self.damage = damage

	def update(self):
		super().update()
		vx = self.v[0] / (player_projectile_speed / 5)
		vy = self.v[1] / (player_projectile_speed / 5)
		self.player_hitbox = [ # quadrilateral hitbox
		(self.x-vx+vy/3, self.y-vy-vx/3),
		(self.x+vx+vy/3, self.y+vy-vx/3),
		(self.x+vx-vy/3, self.y+vy+vx/3),
		(self.x-vx-vy/3, self.y-vy+vx/3)]

	def render(self):
		if len(self.player_hitbox) < 4: return # scraps buggy hitboxes
		gfx.aapolygon(screen, self.player_hitbox, WHITE)
		gfx.filled_polygon(screen, self.player_hitbox, WHITE)

class enemyProjectile(Projectile):
	def __init__(self, x, y, theta):
		super().__init__(x, y, theta)
		self.v = vector_converter(enemy_projectile_speed, theta)

	def update(self):
		super().update()
		self.enemy_hitbox.center = (self.x, self.y)

	def render(self):
		gfx.filled_circle(screen, round(self.x), round(self.y), 5, RED)
		gfx.aacircle(screen, round(self.x), round(self.y), 5, RED)
		gfx.arc(screen, round(self.x), round(self.y), 2, 10, 80, WHITE)
		gfx.arc(screen, round(self.x), round(self.y), 3, 10, 80, WHITE)

class Enemy(pygame.sprite.Sprite):
	# basic enemy object
	def __init__(self, x, y):
		super().__init__()
		self.rect = pygame.Rect(x, y, 16, 22)
		self.dirx = 'right'
		self.knockback = [0,0]
		self.speed = enemy_speed

		self.health = 25
		self.points = 100

		self.delete = False

	def processes(self): # common enemy functions
		global score, global_dx, global_dy

		# knockback handling
		if abs(self.knockback[0]) > .5 and abs(self.knockback[1]) > .5:
			self.rect.x += self.knockback[0]
			self.rect.y += self.knockback[1]
			self.knockback = [x/1.1 for x in self.knockback]

		# damage check using point based collision for quadrilateral hitboxes
		for n in range(len(player_projectiles)):
			for i in range(4):
				if self.rect.collidepoint(player_projectiles[n].player_hitbox[i]):
					self.health -= player_projectiles[n].damage
					self.knockback = player_projectiles[n].knockback
					player_projectiles.pop(n)

		if self.health <= 0:
			self.delete = True
			score += self.points
			player.exp += self.points

		# prevent enemy stacking
		comrades = [enemy for enemy in adversaries if enemy != self]

		collisions = self.rect.collideobjectsall(comrades, key=lambda comrade : comrade.rect)
		if collisions:
			for comrade in collisions:
				if self.rect.center[0] > comrade.rect.center[0]:
					self.rect.x += 1
				else:
					self.rect.x -= 1
				if self.rect.center[1] > comrade.rect.center[1]:
					self.rect.y += 1
				else:
					self.rect.y -= 1

	def update(self):
		self.processes()

		# player tracking
		dx = WSX/2 - self.rect.center[0]
		dy = WSY/2 - self.rect.center[1]
		theta = math.atan2(dy, dx)
		self.v = vector_converter(self.speed, theta)

		self.rect.x += self.v[0] + global_dx
		self.rect.y += self.v[1] + global_dy

		self.dirx = 'right' if dx >= 0 else 'left'


	def render(self):
		if self.dirx == 'right': screen.blit(images['enemy_basic_r'], (self.rect.x-12, self.rect.y-5))
		else: screen.blit(images['enemy_basic_l'], (self.rect.x-5, self.rect.y-5))
		# gfx.box(screen, self.rect, [0, 255, 0, 50])

class rangedEnemy(Enemy):
	def __init__(self, x, y):
		super().__init__(x, y)
		self.rect = pygame.Rect(x, y, 16, 20)

		self.shoot_cooldown = enemy_shoot_cooldown/2

		self.health = 35
		self.points = 150

	def update(self):
		self.processes()

		# shooting
		if not self.shoot_cooldown:
			dx = WSX/2 - self.rect.center[0]
			dy = WSY/2 - self.rect.center[1]

			theta = math.atan2(dy, dx)
			enemy_projectiles.append(enemyProjectile(self.rect.center[0], self.rect.center[1], theta))

			self.shoot_cooldown = enemy_shoot_cooldown

		self.shoot_cooldown -= 1

		dx = WSX/2 - self.rect.center[0]
		dy = WSY/2 - self.rect.center[1]
		if dx**2+dy**2 >= 120**2: # prevents getting too close to player
			theta = math.atan2(dy, dx)
			self.v = vector_converter(self.speed, theta)
		else:
			self.v = [0, 0]

		self.rect.x += self.v[0] + global_dx
		self.rect.y += self.v[1] + global_dy

		self.dirx = 'right' if dx >= 0 else 'left'

	def render(self):
		if self.dirx == 'right': screen.blit(images['enemy_shooter_r'], (self.rect.x-12, self.rect.y-4))
		else: screen.blit(images['enemy_shooter_l'], (self.rect.x-5, self.rect.y-5))
		# gfx.box(screen, self.rect, [0, 255, 0, 50])

class exploderEnemy(Enemy):
	def __init__(self, x, y):
		super().__init__(x, y)
		self.rect = pygame.Rect(x, y, 20, 18)
		self.primed_sprites = [images['enemy_exploder_primed_r'].copy(), images['enemy_exploder_primed_l'].copy()]

		self.speed = enemy_speed*1.4

		self.primed = False
		self.ticks = 40
		self.explosion_radius = 80

		self.health = 20
		self.points = 200

	def update(self):
		self.processes()

		# player tracking
		dx = WSX/2 - self.rect.center[0]
		dy = WSY/2 - self.rect.center[1]

		if dx**2+dy**2 <= 80**2:
			self.primed = True
			self.v = [0,0]

		if not self.primed:
			theta = math.atan2(dy, dx)
			self.v = vector_converter(self.speed, theta)
		else:
			self.ticks -= 1
			for image in self.primed_sprites: image.set_alpha(abs(20-self.ticks%20)*4)

		if self.ticks == 0 or self.delete:
			explosions.append([self.rect.center[0], self.rect.center[1], self.explosion_radius, 0])
			explosion_drawings.append([self.rect.center[0], self.rect.center[1], 1])
			self.delete = True

		self.rect.x += self.v[0] + global_dx
		self.rect.y += self.v[1] + global_dy

		self.dirx = 'right' if dx >= 0 else 'left'

	def render(self):
		if self.dirx == 'right':
			screen.blit(images['enemy_exploder_r'], (self.rect.x-4, self.rect.y-5))
			screen.blit(self.primed_sprites[0], (self.rect.x-4, self.rect.y-5))
		else:
			screen.blit(images['enemy_exploder_l'], (self.rect.x-3, self.rect.y-5))
			screen.blit(self.primed_sprites[1], (self.rect.x-4, self.rect.y-5))
		# gfx.box(screen, self.rect, [0, 255, 0, 100])
		# gfx.filled_circle(screen, self.rect.center[0], self.rect.center[1], self.explosion_radius, [255, 0, 0, 50])

class Boss(Enemy):
	def __init__(self, x, y):
		super().__init__(x, y)
		self.rect = pygame.Rect(x, y, 80, 80)
		self.primed_sprites = [images['boss_primed_r'], images['boss_primed_l']]
		for image in self.primed_sprites: image.set_alpha(0)

		self.health = boss_max_health
		self.points = 5000

		self.spawn_timeout = 480
		self.dash_timeout = 0
		self.after_dash = 60
		self.dash_theta = 0
		self.charging = False
		self.dash_velocity = [0,0]

	def update(self):
		global score, global_dx, global_dy, state

		# knockback handling
		if abs(self.knockback[0]) > .5 and abs(self.knockback[1]) > .5:
			self.rect.x += self.knockback[0]
			self.rect.y += self.knockback[1]
			self.knockback = [x/1.1 for x in self.knockback]

		if abs(self.dash_velocity[0]) > .5 and abs(self.dash_velocity[1]) > .5:
			self.rect.x += self.dash_velocity[0]
			self.rect.y += self.dash_velocity[1]
			self.dash_velocity = [x/1.05 for x in self.dash_velocity]

		# damage check using point based collision for quadrilateral hitboxes
		try:
			for n in range(len(player_projectiles)):
				for i in range(4):
					if self.rect.collidepoint(player_projectiles[n].player_hitbox[i]):
						self.health -= player_projectiles[n].damage
						self.knockback = [knock*.2 for knock in player_projectiles[n].knockback]
						player_projectiles.pop(n)
		except IndexError:
			pass

		if self.health <= 0:
			self.delete = True
			score += self.points
			player.exp += self.points
			state = 'win'

		# prevent enemy stacking
		comrades = [enemy for enemy in adversaries if enemy != self]

		"""collisions = self.rect.collideobjectsall(comrades, key=lambda comrade : comrade.rect)
		if collisions:
			for comrade in collisions:
				if self.rect.center[0] > comrade.rect.center[0]:
					self.rect.x += 1
				else:
					self.rect.x -= 1
				if self.rect.center[1] > comrade.rect.center[1]:
					self.rect.y += 1
				else:
					self.rect.y -= 1"""

		dx = WSX/2 - self.rect.center[0]
		dy = WSY/2 - self.rect.center[1]

		if self.dash_timeout:
			self.dash_timeout -= 1
		elif self.after_dash < 60:
			self.after_dash += 1

		if self.after_dash == 30:
			for i in range(5): adversaries.append(exploderEnemy(self.rect.center[0]+r.randint(-10, 10), self.rect.center[1]+r.randint(-10, 10)))
			for i in range(3): adversaries.append(rangedEnemy(self.rect.center[0]+r.randint(-10, 10), self.rect.center[1]+r.randint(-10, 10)))

		if self.charging:
			for image in self.primed_sprites: image.set_alpha(abs(15-self.dash_timeout%30)*25)
			if not self.dash_timeout:
				self.dash_velocity = vector_converter(self.speed*20, self.dash_theta)
				self.charging = False
				self.after_dash = 0
				for image in self.primed_sprites: image.set_alpha(0)
		elif self.after_dash == 60:
			if dx**2+dy**2 >= 180**2:
				theta = math.atan2(dy, dx)
				self.v = vector_converter(self.speed, theta)
			else:
				self.v = [0, 0]
				self.charging = True
				self.dash_timeout = 60
				self.dash_theta = math.atan2(dy, dx)
		else:
			self.v = [0, 0]

		self.rect.x += self.v[0] + global_dx
		self.rect.y += self.v[1] + global_dy

		self.dirx = 'right' if dx >= 0 else 'left'

	def render(self):
		if self.dirx == 'right':
			screen.blit(images['boss_r'], (self.rect.x-25, self.rect.y-5))
			screen.blit(images['boss_primed_r'], (self.rect.x-25, self.rect.y-5))
		else:
			screen.blit(images['boss_l'], (self.rect.x, self.rect.y-5))
			screen.blit(images['boss_primed_l'], (self.rect.x, self.rect.y-5))
		# gfx.box(screen, self.rect, [0, 255, 0, 50])

#----------------------------------------------------------------------------------

done = False
clock = pygame.time.Clock()

player = Player()

#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------

while not done:
	"""time1 = datetime.now().microsecond"""

	mouse_right_click = False
	reloadtrig = False

	for event in pygame.event.get():
		if event.type == pygame.QUIT: done = True

		if event.type == pygame.MOUSEBUTTONDOWN:
			if event.button == 1:
				mouse_left_held = True
			if event.button == 3:
				mouse_right_click = True
		if event.type == pygame.MOUSEBUTTONUP:
			if event.button == 1:
				mouse_left_held = False

		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				if state == 'start':
					done = True
				elif state == 'pause':
					player = Player()
					player_projectiles = []
					enemy_projectiles = []
					adversaries = []
					explosions = []
					explosion_drawings = []
					active_boss = None
					score = 0
					level_time = 0
					global_dx = 0
					global_dy = 0
					global_offset = [0, 0]
					state = 'start'
				elif state == 'play': state = 'pause'

			if event.key == pygame.K_SPACE:
				if state in ['play', 'pause']:
					state = 'pause' if state == 'play' else 'play'
				elif state in ['death', 'win']:
					player = Player()
					player_projectiles = []
					enemy_projectiles = []
					adversaries = []
					explosions = []
					explosion_drawings = []
					active_boss = None
					score = 0
					level_time = 0
					global_dx = 0
					global_dy = 0
					global_offset = [0, 0]
					state = 'start'
				elif state == 'start': state = 'play'

			if event.key == pygame.K_r: reloadtrig = True


		if state == 'upgrade' and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			upgrade_picker()


	mouse_pos = pygame.mouse.get_pos()
	keys = pygame.key.get_pressed()

	#-----------------------------------------------

	if state == 'play': UPDATE()
	DRAW()

	#-----------------------------------------------
	
	textbox(ASfont[20], str(round(clock.get_fps())), (WSX, WSY), color=RED, alignment='bottomright')

	pygame.display.flip()

	clock.tick(60)

	"""time2 = datetime.now().microsecond
				time_gap = (1 - time1 * 0.000001) - (1 - time2 * 0.000001)
				if time_gap >= 0:
					dt = time_gap * 60
				else:
					dt = 1"""
pygame.quit()
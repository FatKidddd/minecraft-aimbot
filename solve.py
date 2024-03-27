# Require system configs:
# need to disable enhance pointer precision to remove mouse acceleration
import argparse
import numpy as np
import cv2
import mss
import time
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyboardListener

def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
	dim = None
	(h, w) = image.shape[:2]

	if width is None and height is None:
		return image
	if width is None:
		r = height / float(h)
		dim = (int(w * r), height)
	else:
		r = width / float(w)
		dim = (width, int(h * r))

	return cv2.resize(image, dim, interpolation=inter)

def get_points_from_image(screenshot, center_mouse_coords, top_left_ss_coords):
	# Filter strictly black - dark grey pixels based on colour channels absolute difference
	diff_thres = 4
	b, g, r = cv2.split(screenshot)
	diff_rg = np.abs(r - g)
	diff_gb = np.abs(g - b)
	diff_br = np.abs(b - r)
	same_difference_mask = np.logical_and(\
			np.abs(diff_rg-diff_gb) <= diff_thres,\
			np.abs(diff_gb-diff_br) <= diff_thres)
	gray_ss = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
	filtered_img = np.zeros_like(gray_ss)
	filtered_img[same_difference_mask] = gray_ss[same_difference_mask]

	# Filter based on max gray-scale value
	max_value = 40
	thresh_img = np.where(filtered_img <= max_value, filtered_img, 0)
	_, thresh_img = cv2.threshold(thresh_img, 5, 255, cv2.THRESH_BINARY)

	# Find objects based on connected pixels
	cnts = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnts = cnts[0] if len(cnts) == 2 else []

	points = []
	for c in cnts:
		x, y, w, h = cv2.boundingRect(c)
		if w >= 20 and h >= 30:
			cx, cy = x+w//2, y+h//2
			cmx, cmy = center_mouse_coords
			offx, offy = top_left_ss_coords
			dx, dy = cx-(cmx-offx), cy-(cmy-offy)
			points.append([dx, dy])
			# cv2.rectangle(screenshot, (x, y), (x + w, y + h), (40, 0, 0), 2)

	# Display
	global display_feed, layout_window_width, layout_base_x, layout_base_y
	if display_feed:
		filtered_img = ResizeWithAspectRatio(filtered_img, width=layout_window_width)
		thresh_img = ResizeWithAspectRatio(thresh_img, width=layout_window_width)

		cv2.namedWindow('filtered')
		cv2.namedWindow('thresh')
		cv2.moveWindow('filtered', layout_base_x+layout_window_width, layout_base_y)
		cv2.moveWindow('thresh', layout_base_x, layout_base_y+layout_window_width)

		cv2.imshow('filtered', filtered_img)
		cv2.imshow('thresh', thresh_img)

	return points

def screend_to_moused(screend):
	dx, dy = screend
	return int(dx/2.2), int(dy/2.2)

def moused_to_screend(moused):
	dx, dy = moused
	return int(dx*2.2), int(dy*2.2)

def remove_shot_at_targets_from_selection(points, past_shots):
	mouse_delta_threshold = 20 # previously with the wrong cursor center bug was 25 and 1 for 310 waves, 30 and 1.5 for 450 waves
	time_threshold = 1 # reduced to this amount
	now = time.time()
	for i in range(len(past_shots)-1, -1, -1):
		if past_shots[i][0] + time_threshold < now:
			past_shots.pop(i)

	shootable_points = []
	for screen_delta in points:
		should_add = True
		mx, my = screend_to_moused(screen_delta)
		for _, x2, y2 in past_shots:
			if (x2-mx)**2+(y2-my)**2 <= mouse_delta_threshold**2:
				should_add = False
				break
		if should_add:
			shootable_points.append(screen_delta)
	return shootable_points


def move(mouse_delta, past_shots, total_mouse_delta):
	x, y = mouse_delta
	for i in range(len(past_shots)):
		past_shots[i][1] -= x
		past_shots[i][2] -= y
	total_mouse_delta -= mouse_delta
	mouse.move(x, y)

def solve(move_delay=0.4):
	with mss.mss() as sct:
		mon2 = sct.monitors[-1]
		margin_top = 170
		margin_left = 350

		total_mouse_delta = np.array([0, 0])
		past_shots = []

		top = mon2['top'] + margin_top # fixed bug related to wrong cursor center
		left = mon2['left'] + margin_left
		monitor = { 
			'top': top,
			'left': left,
			'width': 1920 - int(abs(margin_left) * 1.3),
			'height': 1080 - int(abs(margin_top) * 2.3),
		}
		center_mouse_coords = None
		top_left_ss_coords = [left, top]

		global initialised
		while True:
			if initialised == 0:
				return
			elif initialised == -1:
				center_mouse_coords = None
			elif initialised == 1:
				if center_mouse_coords == None:
					center_mouse_coords = [mouse.position[0], mouse.position[1]]
					print(center_mouse_coords)
					print(top_left_ss_coords)
				else:

					if not (total_mouse_delta[0] == 0 and total_mouse_delta[1] == 0):
						move(total_mouse_delta, past_shots, total_mouse_delta)
						time.sleep(move_delay)

					im = sct.grab(monitor)
					screenshot = np.delete(np.array(im, dtype=np.uint8), 3, axis=2)
					# cv2.imshow('ss', screenshot)

					# if cv2.waitKey(1) & 0xff == ord('q'):
					# 	return
					# else:
					points = get_points_from_image(screenshot, center_mouse_coords, top_left_ss_coords)
					shootable_points = remove_shot_at_targets_from_selection(points, past_shots)
					if len(shootable_points) > 0:
						screen_deltas = np.diff([[0, 0]] + shootable_points, axis=0)
						for screen_delta in screen_deltas:
							move(screend_to_moused(screen_delta), past_shots, total_mouse_delta)
							time.sleep(move_delay)
							mouse.press(Button.right)
							mouse.release(Button.right)
							past_shots.append([time.time(), 0, 0])
def on_press(key):
	global initialised
	if key == Key.f4:
		print('esc')
		initialised = 0
		
		return 0
	if key == Key.f6:
		initialised = -initialised
		if initialised == 1:
			print('initiated')
		else:
			print('stopped')

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Example script to parse float arguments.")
	parser.add_argument("move_delay", type=float, help="A floating-point number argument")
	args = parser.parse_args()

	# Display config
	layout_window_width = 700
	layout_base_x, layout_base_y = 10, 10
	display_feed = False
	initialised = -1

	keyboard = KeyboardController()
	mouse = MouseController()

	with KeyboardListener(on_press=on_press):
		solve(args.move_delay)

# in order of recency
# i think it may be shooting a spot too quickly before the server registers that the bottle is there? i have no idea, but i don't think i can figure out why

# 27/3/24 it's shoot some random bottle that is rendered for like a split second like on the extreme left and right where bottles don't spawn, 
# maybe they made this to prevent bots? it happens in the middle of the bottles rendering, then it will flash
# or maybe im seeing things??? 
# let's try to use delay time for first see
# maybe i lower my fps to 30 instead of 60 previously
# seems like the screenshot dimensions affect the movement drastically, i assume because im treating the center half the ss width and height which is not true
# lets fix this based on absolute positioning since in the game the mouse position will always be constant


# old:
# with 0.1 movement, 0.8 wait for bottles to load, it will die towards the end when about 8 bottles appear, but they disappear fast and in order i think?
# bot shoots like first 2 and then because of the wait time then its too slow

# move if got nothing to shoot or can't shoot
# if (first_see_time is None) or first_see_time + wait_load > time.time():
# move to center only if not already at center

# shoot only when bottles are finished loading
# if (first_see_time is not None) and first_see_time + wait_load > time.time():
# 	continue
	# control when to shoot after seeing
	# if first_see_time is None:
	# 	first_see_time = time.time()
	# else:
	# first_see_time = None
# Past notes
# keep shooting until got nothing
# try increase this somemore, problem is the bottles r there already but it wont shoot them
# to prevent shooting same spot again? but the remove targets should counteract this already, i guess its one frame faster since it skips capture image


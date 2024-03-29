Aimbot destroying Wynncraft / Minecraft server's target practice challenge. Cleared 500/500 waves.

## Demo vid:
https://github.com/FatKidddd/minecraft-aimbot/assets/58980435/161116e1-5e17-448a-a0b8-187c2d632bca

## Context:
Each wave, player has to shoot down all target bottle(s) within short amount of time

#### Image processing
- Screenshot frame
- Filter using bottle outline - just shades of black
	- Using lower and upper bound mask only results in too much noise. Compared each rgb channel because something like [40, 38, 39] is more convincingly black than [0, 10, 0] because the former is just a lighter shade of black while the latter is basically very dark green
	- Filter max grayscale value <= around 40
- Find contours by connected pixels
- Bound rectangles with a minimum size requirement to get positions of bottles

- Briefly tried basic morphological transformations and wasn't effective but could work

#### Movement algorithm
- Main problem with shooting: 
	- Shooting target takes time before target disappears, ~0.5-0.8 seconds + some inconsistent server lag, so double shooting needs to be prevented

- Movement details:
	- Number of pixels on screen = number of mouse pixels moved * some constant factor - so can move and shoot once position determined
	- Mouse movements are 100% accurate with 0.1s delay for the game to process mouse inputs

- Movement algo:
	- Return to center there is nothing or nothing that hasn't already been shot at - to get a full view of all possible target spawn locations
	- Time-based memory to determine which targets to shoot at
		- Track all positions that were shot at up to 1 second ago through storing cumulative mouse movements
		- If tracked position and actual observed position of target is within distance threshold, target has been shot at before so don't add to list of shootable bottles
	- Shoot all shootable bottles in screenshot

#### Settings
- Disable "Enhance pointer precision" setting to remove 'leftover' movements
- FOV normal
- GUI smallest to remove interfering elements

#### Struggles
- When testing mouse movement accuracy, I found that mouse movements can sometimes be inaccurate even with 0.3s delay, but I probably tested this wrongly
- This led to a lot of unnecessary movement calibration fixes that wasted time
- Image processing technique was originally not as good, and because garbage in, garbage out, a lot of unnecessary calibration fixes were made

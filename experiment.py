__author__ = "Brett Feltmate"

import klibs
from klibs import Params
from klibs.KLDraw import *
import klibs.KLTimeKeeper as tk
#  Below are some commonly required additional libraries; uncomment as needed.

# import os
import time
# from PIL import Image
# import sdl2
# import sdl2.ext
# import numpy
import math
# import aggdraw
import random

Params.default_fill_color = (255, 155, 87, 255) # TODO: rotate through seasons

# Debug level is partially implemented and should, for now, be ignored. Future releases of KLIBs will respect this feature
Params.debug_level = 3

Params.collect_demographics = False
Params.practicing = False
Params.eye_tracking = True
Params.eye_tracker_available = False

Params.blocks_per_experiment = 1
Params.trials_per_block = 1
Params.practice_blocks_per_experiment = None
Params.trials_per_practice_block = None

LEFT = "left"
RIGHT = "right"
DOUBLE = "double"


class IOR_Reward(klibs.Experiment):
	thick_rect = None
	thick_rect_border = 15 # pixels
	thin_rect = None
	thin_rect_border = 2
	square_border_colour = [255, 255, 255]
	star_size = 3
	star_size_px = None
	star_border = 5
	square_size = 5 # degrees of visual angle
	square_size_px = None # pixels
	square_loc = []
	response_window = 2
	cue_onset_duration = 1
	cue_presentation_duration = 1


	# Runtime vars (ie. defined on a per-trial or per-block basis)
	high_value_color = None  # block-level var
	low_value_color = None	 # block-level var
	left_bandit = None
	right_bandit = None


	def __init__(self, *args, **kwargs):
		super(IOR_Reward, self).__init__(*args, **kwargs)
		# broadly, this method is just defining parameters, graphical objects, reference info
		# that will be needed throughout the experiment
		
		# initialize the pixel size of the boxes, which are otherwise defined in deg of visual angle
		self.square_size_px = deg_to_px(self.square_size)
		
		# initialize the pixel size of the star/asterisk, which are otherwise defined in deg of visual angle
		self.star_size_px = deg_to_px(self.star_size)
		
		# define the general form of your boxes & star/asterisk for later use in the trial 
		# (note that these are Drawbjects, rather than images; they can be blitted as though they were
		# images because KLIBs is smart like that, but, being objects, they can also be modified
		# during run time without having to be recreated
		self.thick_rect = Rectangle(self.square_size_px, stroke=[self.thick_rect_border, self.square_border_colour])
		self.thin_rect = Rectangle(self.square_size_px, stroke=[self.thin_rect_border, self.square_border_colour])
		self.star = Circle(self.star_size_px, fill=[255,255,255])
		
		# establish the locations where boxes will be blit throughout the experiment
		self.square_locs = [ [Params.screen_x // 4 * a, Params.screen_c[1] ] for a in range(1,4)]

	def setup(self):
		Params.key_maps['TestProject_response'] = klibs.KeyMap('TestProject_response', [], [], [])

	def block(self, block_num):
		self.assign_colors()

	def trial_prep(self, trial_factors):
		self.fill()
		self.blit(Circle(75, fill=[255,255,255]), 5, Params.screen_c)
		self.draw_neutral_boxes()
		self.flip()

	def trial(self, trial_factors):
		# present the neutral boxes prior to cuing
		cue_onset = tk.CountDown(self.cue_onset_duration)
		while cue_onset.counting():
			self.fill()
			self.blit(Circle(75, fill=[255,255,255]), 5, Params.screen_c)
			self.draw_neutral_boxes()
			pump()
			self.flip()
		cue_presenting = tk.CountDown(self.cue_presentation_duration)

		# assign graphics to cued location
		left_box = self.thick_rect
		right_box = self.thin_rect
		if trial_factors[4] == RIGHT:
			left_box = self.thin_rect
			right_box = self.thick_rect

		if trial_factors[4] == DOUBLE:
			left_box = self.thick_rect
			right_box = self.thick_rect

		# present cue
		while cue_presenting.counting():
			self.fill()
			self.blit(left_box, 5, self.square_locs[0])
			self.blit(right_box, 5, self.square_locs[2])
			self.blit(Circle(75, fill=[255, 255, 255]), 5, Params.screen_c)

		self.draw_bandits(trial_factors[2])
		bandit_presenting = tk.CountDown(self.response_window)
		while bandit_presenting.counting():
			self.fill()
			self.blit(self.left_bandit, 5, self.square_locs[0])
			self.blit(self.right_bandit, 5, self.square_locs[2])
			self.flip()

		return {}

	def trial_clean_up(self, trial_factors):
		self.thin_rect.fill = [0, 0, 0, 0]

	def clean_up(self):
		pass

	def assign_colors(self):
		self.high_value_color = []
		self.low_value_color = []
		for i in range(0,3):
			self.high_value_color.append(random.choice(range(0, 256)))
		for i in range(0, 3):
			self.low_value_color.append(random.choice(range(0, 256)))

	def draw_neutral_boxes(self):
		self.blit(self.thin_rect, 5, self.square_locs[0])
		self.blit(self.thin_rect, 5, self.square_locs[2])

	def draw_bandits(self, high_value_loc):
		if high_value_loc == LEFT:
			self.thin_rect.fill = self.high_value_color
			self.left_bandit = self.thin_rect.render()
			self.thin_rect.fill = [0,0,0,0]
			self.right_bandit= self.thin_rect.render()
		if high_value_loc == RIGHT:
			self.thin_rect.fill = self.high_value_color
			self.right_bandit = self.thin_rect.render()
			self.thin_rect.fill = [0, 0, 0, 0]
			self.left_bandit = self.thin_rect.render()


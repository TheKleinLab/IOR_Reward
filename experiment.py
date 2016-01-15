__author__ = "Brett Feltmate"

import klibs
from klibs import Params
from klibs.KLDraw import *
import klibs.KLTimeKeeper as tk
from klibs.KLResponseCollectors import *
# Below are some commonly required additional libraries; uncomment as needed.

# import os
import time
# from PIL import Image
# import sdl2
# import sdl2.ext
# import numpy
import math
# import aggdraw
import random

Params.default_fill_color = [165, 165, 165, 255] # TODO: rotate through seasons

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
	star_color = [255,255,255,255]
	star_size = 3
	star_size_px = None
	square_size = 4 # degrees of visual angle
	square_size_px = None # pixels
	left_box_loc = None
	right_box_loc = None
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
		# ar = self.audio.create_listener(1000)
		# print ar.get_ambient_level(5)
		# kpr = KeyPressCollector( klibs.KLKeyMap.KeyMap('test', ['z'], ['z'], [sdl2.SDLK_z]), self, interrupt=True)
		# kpr.run()
		# print kpr.response

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
		self.thick_rect = Rectangle(self.square_size_px, stroke=[self.thick_rect_border, self.square_border_colour, STROKE_OUTER])
		self.thin_rect = Rectangle(self.square_size_px, stroke=[self.thin_rect_border, self.square_border_colour, STROKE_OUTER])
		self.star = Asterisk(self.star_size_px, self.star_color)

		# establish the locations where boxes will be blit throughout the experiment
		self.left_box_loc, self.right_box_loc = [ [Params.screen_x // 4 * a, Params.screen_c[1] ] for a in [1,3]]

	def setup(self):
		Params.key_maps['TestProject_response'] = klibs.KeyMap('TestProject_response', [], [], [])
		self.rc.keypress_listener.interrupts = True
		self.rc.display_callback = self.display_refresh
		self.rc.response_window = self.response_window
		if not Params.development_mode:
			self.rc.audio_listener.calibrate()
		else:
			self.rc.audio_listener.threshold_valid = True
			self.rc.audio_listener.threshold = 50
			self.rc.audio_listener.calibrated = True


	def block(self, block_num):
		self.assign_colors()

	def trial_prep(self, trial_factors):
		self.present_neutral_boxes(True)

	def trial(self, trial_factors):
		self.present_neutral_boxes()
		self.present_cues(trial_factors[4])
		self.prepare_bandits(trial_factors[2])

		self.rc.collect()

		return {
		"block_num": Params.block_number,
		"trial_num": Params.trial_number,
		"audio_response_time": self.rc.responses['audio'][0][1],
		"audio_timed_out": self.rc.responses['audio'][0][1] == TIMEOUT,
		"keypress_response_time": self.rc.responses['keypress'][0][1],
		"keypress_timed_out": self.rc.responses['keypress'][0][1] == TIMEOUT,
		"keypress_response": self.rc.responses['keypress'][0][0],
		"trial_type": trial_factors[1],
		"high_value_loc": trial_factors[2],
		"probe_loc": trial_factors[3],
		"cue_loc": trial_factors[4]
		}

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


	def prepare_bandits(self, high_value_loc):
		if high_value_loc == LEFT:
			self.thin_rect.fill = self.high_value_color
			self.left_bandit = self.thin_rect.render()
			self.thin_rect.fill = self.low_value_color
			self.right_bandit= self.thin_rect.render()
		if high_value_loc == RIGHT:
			self.thin_rect.fill = self.high_value_color
			self.right_bandit = self.thin_rect.render()
			self.thin_rect.fill = self.low_value_color
			self.left_bandit = self.thin_rect.render()

	def present_cues(self, cue_condition):
	# assign graphics to cued location
		left_box = self.thick_rect if cue_condition in [LEFT, DOUBLE] else self.thin_rect
		right_box = self.thick_rect if cue_condition in [RIGHT, DOUBLE] else self.thin_rect

		# present cue
		cue_presentation = tk.CountDown(self.cue_presentation_duration)
		while cue_presentation.counting():
			self.fill()
			self.blit(left_box, 5, self.left_box_loc)
			self.blit(right_box, 5, self.right_box_loc)
			self.blit(self.star, 5, Params.screen_c)
			self.flip()

	def present_neutral_boxes(self, pre_trial_blit=False):
		cue_onset = tk.CountDown(self.cue_onset_duration)
		while cue_onset.counting():
			pump()
			self.fill()
			self.blit(self.star, 5, Params.screen_c)
			self.blit(self.thin_rect, 5, self.left_box_loc)
			self.blit(self.thin_rect, 5, self.right_box_loc)
			self.flip()
			if pre_trial_blit:
				cue_onset.finish()

	def display_refresh(self):
		self.fill()
		self.blit(self.left_bandit, 5, self.left_box_loc)
		self.blit(self.right_bandit, 5, self.right_box_loc)
		self.blit(self.star, 5, Params.screen_c)
		self.flip()
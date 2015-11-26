__author__ = "Brett Feltmate"

import klibs
from klibs import Params
from klibs.KLDraw import *

#  Below are some commonly required additional libraries; uncomment as needed.

# import os
import time
# from PIL import Image
# import sdl2
# import sdl2.ext
# import numpy
import math
# import aggdraw
# import random

Params.default_fill_color = (100, 100, 100, 255) # TODO: rotate through seasons

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



class IOR_Reward(klibs.Experiment):
	thick_rect = None
	thick_rect_border = 5 # pixels 
	thin_rect = None
	thin_rect_border = 2
	square_border_colour = [255, 255, 255]
	star_size = 3
	star_size_px = None
	star_border = 5
	square_size = 5 # degrees of visual angle
	square_size_px = None # pixels
	square_loc = []

	def __init__(self, *args, **kwargs):
		super(TestProject, self).__init__(*args, **kwargs)
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
		pass

	def trial_prep(self, trial_factors):
		pass

	def trial(self, trial_factors):
		start = now()
		while now() - start < 3:
			self.fill()
			for l in self.square_locs:
				self.blit(self.thick_rect, position=l, registration=5)
				self.blit(self.star, 5, self.square_locs[ int(math.floor(now() - start))])
			self.flip()
		return {}

	def trial_clean_up(self, trial_factors):
		pass

	def clean_up(self):
		pass

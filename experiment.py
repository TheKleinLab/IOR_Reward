__author__ = "Brett Feltmate"

import klibs
from klibs import Params
from klibs.KLExceptions import *
from klibs.KLDraw import *
import klibs.KLTimeKeeper as tk
from klibs.KLResponseCollectors import *
from klibs.KLKeyMap import KeyMap
import random

Params.default_fill_color = [65, 65, 65, 255]
Params.debug_level = 3
Params.collect_demographics = False
Params.practicing = False
Params.eye_tracking = True
Params.eye_tracker_available = False

Params.blocks_per_experiment = 1
Params.trials_per_block = 10
Params.practice_blocks_per_experiment = None
Params.trials_per_practice_block = None

LEFT = "left"
RIGHT = "right"
DOUBLE = "double"
PROBE = "probe"
BOTH = "both"
BANDIT = "bandit"
HIGH = "high"
LOW = "low"
BLUE = [0, 0, 255, 255]
RED = [255, 0, 0, 255]

class IOR_Reward(klibs.Experiment):
	thick_rect = None
	thick_rect_border = 15 					# pixels
	thin_rect = None
	thin_rect_border = 2
	square_border_colour = [255, 255, 255]
	star_color = [255, 255, 255, 255]
	muted_star_color = [100, 100, 100, 255]
	star_size = 0.75
	star_size_px = None
	square_size = 4 						# degrees of visual angle
	square_size_px = None 					# pixels
	left_box_loc = None
	right_box_loc = None
	star_loc = None
	probe_loc = None
	response_window = 2
	cue_onset_duration = 1
	cue_presentation_duration = 1
	pre_response_window_min = 150
	pre_response_window_max = 250
	high_bandit_payout_min = 8
	high_bandit_payout_max = 12
	low_bandit_payout_min = 3
	low_bandit_payout_max = 7
	penalty = -5

	# Runtime vars (ie. defined on a per-trial or per-block basis)
	high_value_color = None  				# block-level var
	low_value_color = None	 				# block-level var
	left_bandit = None
	right_bandit = None


	def __init__(self, *args, **kwargs):
		super(IOR_Reward, self).__init__(*args, **kwargs)
		self.square_size_px = deg_to_px(self.square_size)
		self.star_size_px = deg_to_px(self.star_size)
		self.thick_rect = Rectangle(self.square_size_px, stroke=[self.thick_rect_border, self.square_border_colour, STROKE_OUTER])
		self.thin_rect = Rectangle(self.square_size_px, stroke=[self.thin_rect_border, self.square_border_colour, STROKE_OUTER])
		self.neutral_box = self.thin_rect.render()
		self.star = Asterisk(self.star_size_px, self.star_color)
		self.star_muted = Asterisk(self.star_size_px, self.muted_star_color)
		self.star_loc = self.probe_loc
		self.left_box_loc, self.right_box_loc = [ [Params.screen_x // 4 * a, Params.screen_c[1] ] for a in [1,3]]
		self.probe = Circle(int(0.75 * self.square_size_px), None, self.square_border_colour).render()

	def setup(self):
		fix_x_1 = Params.screen_c[0] - self.star_size_px //2
		fix_y_1 = Params.screen_c[1] - self.star_size_px //2
		fix_x_2 = Params.screen_c[0] + self.star_size_px //2
		fix_y_2 = Params.screen_c[1] + self.star_size_px //2
		self.eyelink.add_gaze_boundary('fixation', [(fix_x_1, fix_y_1), (fix_x_2, fix_y_2)], EL_RECT_BOUNDARY)
		self.rc.uses([RC_AUDIO, RC_KEYPRESS])
		self.rc.keypress_listener.interrupts = True
		self.rc.keypress_listener.min_response_count = 1
		self.rc.response_window = self.response_window
		self.rc.keypress_listener.key_map = KeyMap('bandit_response', ['/','z'], ['/','z'], [sdl2.SDLK_SLASH, sdl2.SDLK_z])
		self.rc.display_callback = self.display_refresh
		if not Params.development_mode:
			self.rc.audio_listener.calibrate()
			print Params.tk.export()
		else:
			self.rc.audio_listener.threshold_valid = True
			self.rc.audio_listener.threshold = 300
			self.rc.audio_listener.calibrated = True
		self.text_manager.add_style("score up", 48, [75,210,100,255])
		self.text_manager.add_style("score down", 48, [210,75,75,255])
		self.text_manager.add_style("timeout", 48, [255,255,255,255])

	def block(self, block_num):
		if self.high_value_color in [RED, None]:
			self.high_value_color = BLUE
			self.low_value_color = RED
		elif self.high_value_color is BLUE:
			self.high_value_color = RED
			self.low_value_color = BLUE

	def trial_prep(self, trial_factors):
		self.clear()
		# If probed trial, establish location of probe (default: left box)
		if trial_factors[0] == PROBE or BOTH:
			self.prepare_bandits(trial_factors[2])
			if trial_factors[2] == RIGHT:
				self.probe_loc = self.right_box_loc
		if trial_factors[0] == BANDIT:
			self.prepare_bandits(trial_factors[2])
		self.rc.display_args = [trial_factors[1], trial_factors[3]]
		self.eyelink.drift_correct()
		self.present_neutral_boxes()

	def trial(self, trial_factors):
		self.present_neutral_boxes()
		self.present_cues(trial_factors[4])
		self.prepare_bandits(trial_factors[2])
		ctoa = self.time_from_range(self.pre_response_window_min, self.pre_response_window_max)
		pre_response_window = self.time_from_range(100, 200)
		if trial_factors[1] == PROBE:  # ensure probe presentation shares same delay as the bandit's pre-response time
			ctoa += pre_response_window
		ctoa = Params.tk.countdown(ctoa)
		while ctoa.counting():
			self.present_neutral_boxes()
		if trial_factors[1] in [BANDIT, BOTH]:
			pre_response_window = Params.tk.countdown(pre_response_window)
			while pre_response_window.counting():
				self.display_refresh(trial_factors[1], trial_factors[3], False)
		self.rc.collect()
		response = self.rc.keypress_listener.responses[0][0]
		print self.rc.audio_listener.responses[0]

		if trial_factors[1] in (BANDIT, BOTH):
			if response == "z":
				response = LEFT
			elif response == "/":
				response = RIGHT
			else:
				response = False
			if response and response == trial_factors[3]:
				score = self.bandit_payout(HIGH) if response == trial_factors[2] else self.bandit_payout(LOW)
				verb = "won"
			elif response:
				score = self.penalty
				verb = "lost"
			else:
				score = None

			if score:
				message = "You {0} {1} points!\n Press any key to continue.".format(verb, score)
				style = "score up" if score > 0 else "score down"
			else:
				message = "Timed out; trial recycled.\n Press any key to continue."
				style = "timeout"
			self.fill()
			self.message(message, style, registration=5,  location=Params.screen_c, flip=True)
			self.any_key()



		return {
		"block_num": Params.block_number,
		"trial_num": Params.trial_number,
		"audio_response_time": self.rc.audio_listener.responses[0][1],
		"audio_timed_out": self.rc.audio_listener.responses[0][1] == TIMEOUT,
		"keypress_response_time": self.rc.keypress_listener.responses[0][1],
		"keypress_timed_out": self.rc.keypress_listener.responses[0][1] == TIMEOUT,
		"keypress_response": self.rc.keypress_listener.responses[0][0],
		"trial_type": trial_factors[1],
		"high_value_loc": trial_factors[2],
		"probe_loc": trial_factors[3],
		"cue_loc": trial_factors[4]
		}

	def trial_clean_up(self, trial_id,  trial_factors):
		self.thin_rect.fill = [0, 0, 0, 0]

	def clean_up(self):
		pass

	def time_from_range(self, min_val, max_val):
		return random.choice(range(min_val, max_val, 1)) / 1000.0

	def bandit_payout(self, bandit):
		min_val = self.high_bandit_payout_min if bandit == HIGH else self.low_bandit_payout_min
		max_val = self.high_bandit_payout_max if bandit == HIGH else self.low_bandit_payout_max
		return random.choice(range(min_val, max_val, 1))


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
		self.thin_rect.fill = Params.default_fill_color

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
			if not Params.eye_tracker_available:
				self.blit(cursor())
			self.flip()
			if not self.eyelink.within_boundary('fixation'):
				raise TrialException("Eyes must remain at fixation")

	def present_neutral_boxes(self, pre_trial_blit=False):
		cue_onset = tk.CountDown(self.cue_onset_duration)
		while cue_onset.counting():
			self.ui_request()
			self.fill()
			self.blit(self.star, 5, Params.screen_c)
			self.blit(self.neutral_box, 5, self.left_box_loc)
			self.blit(self.neutral_box, 5, self.right_box_loc)
			if not Params.eye_tracker_available:
				self.blit(cursor())
			self.flip()
			if not self.eyelink.within_boundary('fixation'):
				raise TrialException("Eyes must remain at fixation")
			if pre_trial_blit:
				cue_onset.finish()

	def display_refresh(self, trial_type, probe_loc, mute_star=True):
		self.fill()
		probe_loc = self.left_box_loc
		if probe_loc == RIGHT:
			probe_loc = self.right_box_loc
		if trial_type in (BANDIT, BOTH):
			self.blit(self.left_bandit, 5, self.left_box_loc)
			self.blit(self.right_bandit, 5, self.right_box_loc)
		else:
			self.blit(self.neutral_box, 5, self.left_box_loc)
			self.blit(self.neutral_box, 5, self.right_box_loc)
		if trial_type in [PROBE, BOTH] and mute_star:
			self.blit(self.probe, 5, probe_loc)

		if mute_star:
			self.blit(self.star_muted, 5, Params.screen_c)
		else:
			self.blit(self.star, 5, Params.screen_c)
		self.flip()
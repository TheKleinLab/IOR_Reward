__author__ = "Brett Feltmate"
# works with, at least, KLIBs commit: 113282ae9cdbfb9d66e2eae7a071e546fc0d54bf

import klibs
from klibs import Params
from klibs.KLExceptions import *
from klibs.KLDraw import *
import klibs.KLTimeKeeper as tk
from klibs.KLResponseCollectors import *
from klibs.KLKeyMap import KeyMap
import random

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
GREEN = [0, 255, 0, 255]
PURPLE = [95,25,130,255]

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
	response_window = 2000
	cue_onset_duration = 1000
	cue_presentation_duration = 350
	cotoa_min = 700
	cotoa_max = 1000
	pbra = 1000								# probe-bandit response asynchrony
	bpoa = 1000								# bandit-probe onset asynchrony
	post_selection_wait = 1000				#
	feedback_exposure_period = 1000
	high_bandit_payout_baseline = 12
	low_bandit_payout_baseline = 5
	high_bandit_messages = []				# messages are pre-rendered to save time between trials
	low_bandit_messages = []
	bandit_payout_variance = 1
	penalty = -5
	cboa_key = None
	cpoa_key = None
	low_penalty_msg = None
	low_reward_msg = None
	high_reward_msg = None
	bandit_timeout_msg = None
	probe_timeout_msg = None
	fixation_fail_msg = None

	# Runtime vars (ie. defined on a per-trial or per-block basis)
	high_value_color = None  				# block-level var
	low_value_color = None	 				# block-level var
	left_bandit = None
	right_bandit = None
	collecting_response_for = None
	log_cboa = None
	low_payout = 5
	high_payout = 10
	prob_loc = None
	high_value_loc = None


	def __init__(self, *args, **kwargs):
		super(IOR_Reward, self).__init__(*args, **kwargs)
		Params.default_color = [255, 255, 255, 255]
		self.debug.display_location = "LEFT"
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
		fix_x_1 = (Params.screen_c[0] - self.star_size_px //2) - 60
		fix_y_1 = (Params.screen_c[1] - self.star_size_px //2) - 60
		fix_x_2 = (Params.screen_c[0] + self.star_size_px //2) + 60
		fix_y_2 = (Params.screen_c[1] + self.star_size_px //2) + 60
		self.eyelink.add_gaze_boundary('fixation', [(fix_x_1, fix_y_1), (fix_x_2, fix_y_2)], EL_RECT_BOUNDARY)
		self.text_manager.add_style("score up", 48, [75,210,100,255], anti_alias=True)
		self.text_manager.add_style("score down", 48, [210,75,75,255], anti_alias=True)
		self.text_manager.add_style("timeout", 48, [255,255,255,255])
		self.rc.audio_listener.calibrate()
		probe_timeout_text = "No response detected; trial recycled. \nPlease answer louder or faster. \nPress space to continue."
		bandit_text = "You {0} {1} points!\n Press any key to continue."
		self.probe_timeout_msg = self.message(probe_timeout_text, 'timeout', blit=False)
		self.bandit_timeout_msg = self.message("Timed out; trial recycled.\n Press any key to continue.","timeout", blit=False)
		self.fixation_fail_msg = self.message("Eyes moved. Please keep your eyes on the asterisk.", 'timeout', location=Params.screen_c, registration=5, blit=False)
		self.low_penalty_msg = self.message(bandit_text.format("lost", self.low_payout), "score down", blit=False)
		for i in range(self.low_bandit_payout_baseline - self.bandit_payout_variance, self.low_bandit_payout_baseline + self.bandit_payout_variance):
			self.low_bandit_messages.append([i, self.message(bandit_text.format("won", i), "score up", blit=False)])
		for i in range(self.high_bandit_payout_baseline - self.bandit_payout_variance, self.high_bandit_payout_baseline + self.bandit_payout_variance):
			self.high_bandit_messages.append([i,self.message(bandit_text.format("won", i), "score up", blit=False)])
		self.low_reward_msg = self.message(bandit_text.format("won", self.low_payout), "score up", blit=False)
		self.high_reward_msg = self.message(bandit_text.format("won", self.high_payout), "score up", blit=False)

	def setup_response_collector(self, trial_factors):
		self.rc.display_args = [trial_factors[1], trial_factors[3]]
		self.rc.uses([RC_AUDIO, RC_KEYPRESS])
		self.rc.before_flip_callback = self.display_refresh
		self.rc.display_callback = self.display_refresh
		self.rc.keypress_listener.interrupts = True
		self.rc.keypress_listener.min_response_count = 1
		self.rc.audio_listener.min_response_count = 1
		self.rc.response_window = self.response_window
		self.rc.keypress_listener.key_map = KeyMap('bandit_response', ['/','z'], ['/','z'], [sdl2.SDLK_SLASH, sdl2.SDLK_z])
		self.rc.after_flip_callback = self.post_flip_events
		self.rc.after_flip_args = [trial_factors[1], trial_factors[3]]
		if self.collecting_response_for == PROBE:
			self.rc.audio_listener.interrupts = False
			if trial_factors[1] == PROBE:
				self.rc.audio_listener.interrupts = True
			self.rc.post_flip_tk_label = "cpoa"
			self.rc.audio_listener.interrupts = True
			self.rc.response_window = self.pbra
			self.rc.disable(RC_KEYPRESS)
			self.rc.enable(RC_AUDIO)
			self.rc.before_flip_args = [trial_factors[1], trial_factors[3], False]
		elif self.collecting_response_for == BANDIT:
			self.rc.post_flip_sample_key = None
			self.rc.display_args = [trial_factors[1], False]
			self.rc.enable(RC_KEYPRESS)
			self.rc.disable(RC_AUDIO)
			self.rc.before_flip_args = [trial_factors[1], False, False]


	def block(self, block_num):
		if Params.practicing:
			if self.high_value_color in [PURPLE, None]:
				self.high_value_color = GREEN
				self.low_value_color = PURPLE
			elif self.high_value_color is GREEN:
				self.high_value_color = PURPLE
				self.low_value_color = GREEN
		else:
			if self.high_value_color in [PURPLE, GREEN]:
				self.high_value_color = None
				self.low_value_color = None
			if self.high_value_color in [RED, None]:
				self.high_value_color = BLUE
				self.low_value_color = RED
			elif self.high_value_color is BLUE:
				self.high_value_color = RED
				self.low_value_color = BLUE

	def trial_prep(self, trial_factors):
		self.clear()
		self.collecting_response_for = None
		# If probed trial, establish location of probe (default: left box)
		if trial_factors[0] == PROBE or BOTH:
			self.prepare_bandits(trial_factors[2])
			if trial_factors[2] == RIGHT:
				self.probe_loc = self.right_box_loc
		if trial_factors[0] == BANDIT:
			self.prepare_bandits(trial_factors[2])
		self.eyelink.drift_correct()
		self.probe_loc = trial_factors[3]
		self.high_value_loc = trial_factors[2]

	def trial(self, trial_factors):
		# Trial Factors: 1) trial_type, 2) high_value_loc, 3) probe_loc, 4) cue_loc, 5) winning_bandit
		self.eyelink.start(Params.trial_number)
		self.present_neutral_boxes()
		Params.tk.start('cue_onset')
		self.present_cues(trial_factors[4])
		self.prepare_bandits(trial_factors[2])

		# CUEING PERIOD cotoa = cue offset, taget onset asynchrony
		cotoa = random.choice(range(self.cotoa_min, self.cotoa_max, 1))
		if trial_factors[1] == PROBE:
			cotoa += self.bpoa
		cotoa = Params.tk.countdown(cotoa, TK_MS)
		while cotoa.counting():
			self.present_neutral_boxes()

		#  BANDIT PRIMING PERIOD
		bandit_priming_period = Params.tk.countdown(self.bpoa, TK_MS)
		if trial_factors[1] in [BANDIT, BOTH]:
			while bandit_priming_period.counting():
				self.log_cboa = True  # one time only per trial, display_refresh() needs to record a time post-flip
				self.display_refresh(trial_factors[1])
		#  PROBE RESPONSE PERIOD
		if trial_factors[1] in [PROBE, BOTH]:
			self.collecting_response_for = PROBE
			self.setup_response_collector(trial_factors)
			print Params.tk.elapsed('cue_onset')
			self.rc.collect()
			if self.rc.audio_listener.responses[0][1] != TIMEOUT:
				self.evi.send("DetectProbe")
			if self.rc.audio_listener.responses[0][0] == self.rc.audio_listener.null_response:
				acknowledged = False
				while not acknowledged:
					self.fill()
					self.blit(self.probe_timeout_msg, location=Params.screen_c, registration=5)
					self.flip()
					acknowledged = self.any_key()
				raise TrialException("No vocal response.")
			
		else:
			bandit_response_delay = Params.tk.countdown(self.pbra, TK_MS)
			while bandit_response_delay.counting():
				self.display_refresh(trial_factors[1])

		#  BANDIT RESPONSE PERIOD
		if trial_factors [1] in [BANDIT, BOTH]:
			self.collecting_response_for = BANDIT
			self.setup_response_collector(trial_factors)
			self.rc.collect()
			choice = self.rc.keypress_listener.responses[0][0]
			self.evi.send("SelectHighBand" if self.high_value_loc == choice else "SelectLowBand")

		# get the stimuli off screen quickly whilst text renders
		self.fill()
		self.flip()

		#  FEEDBACK PERIOD
		reward = "N/A"
		if trial_factors[1] != PROBE:
			reward = self.feedback(self.rc.keypress_listener.responses[0][0], trial_factors[1], trial_factors[2], trial_factors[5])
		try:
			audio_rt = self.rc.audio_listener.responses[0][1]
			audio_timeout = self.rc.audio_listener.responses[0][1] == TIMEOUT
		except IndexError:
			audio_rt = "N/A"
			audio_timeout = "N/A"
		try:
			keypress_rt = self.rc.keypress_listener.responses[0][1]
			keypress_timeout = self.rc.keypress_listener.responses[0][1] == TIMEOUT
			keypress_response = LEFT if self.rc.keypress_listener.responses[0][0] == "z" else RIGHT
		except IndexError:
			keypress_rt = "N/A"
			keypress_timeout = "N/A"
			keypress_response = "N/A"

		return {
		"block_num": Params.block_number,
		"trial_num": Params.trial_number,
		"audio_response_time": audio_rt,
		"audio_timed_out": audio_timeout,
		"keypress_response_time": keypress_rt,
		"keypress_timed_out": keypress_timeout,
		"keypress_response": keypress_response,
		"trial_type": trial_factors[1],
		"high_value_loc": trial_factors[2],
		"winning_bandit": trial_factors[5],
		"reward": reward if reward else "N/A",
		"probe_loc": trial_factors[3],
		"cue_loc": trial_factors[4],
		"cpoa": Params.tk.period('cpoa') if trial_factors[1] in [PROBE, BOTH] else "N/A",
		"cboa": Params.tk.period('cboa') if trial_factors[1] in [BANDIT, BOTH] else "N/A"
		}

	def trial_clean_up(self, trial_id,  trial_factors):
		pass

	def clean_up(self):
		pass

	def feedback(self, response_key, trial_type, high_value_loc, winning_bandit):
		if trial_type == PROBE:
			return
		if response_key == "z":
			response = LEFT
		elif response_key == "/":
			response = RIGHT
		else:
			response = False

		if winning_bandit == HIGH:
			winning_bandit_loc = high_value_loc
		else:
			winning_bandit_loc = LEFT if high_value_loc == RIGHT else RIGHT

		won = response == winning_bandit_loc
		timeout = not response
		high_win = random.choice(self.high_bandit_messages)
		low_win = random.choice(self.low_bandit_messages)
		event = "Win" if won else "Loss"
		event += "High" if high_value_loc == response else "Low"
		if trial_type == BOTH:
			event += "ProbeHigh" if self.probe_loc == high_value_loc else "ProbeLow"
		if not timeout:
			if won:
				feedback = high_win if high_value_loc == response else low_win
			else:
				feedback = [self.penalty, self.low_penalty_msg]
		else:
			feedback = [None, self.bandit_timeout_msg]
		if feedback[0]:
			post_selection_wait = Params.tk.countdown(self.post_selection_wait, TK_MS)
			while post_selection_wait.counting():
				self.ui_request()
				self.fill()
				self.blit(self.star, 5, Params.screen_c)
				self.flip()

		self.evi.send(event)
		self.blit(feedback[1], location=Params.screen_c, registration=5)
		feedback_exposure = Params.tk.countdown(self.feedback_exposure_period, TK_MS)
		self.flip()
		while feedback_exposure.counting():
			self.ui_request()
			self.fill()
			self.blit(feedback[1], location=Params.screen_c, registration=5)
			self.flip()
		return feedback[0]

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
		cue_presentation = Params.tk.countdown(self.cue_presentation_duration, TK_MS)
		event = "LeftCue"
		if cue_condition == RIGHT:
			event = "RightCue"
		elif cue_condition == DOUBLE:
			event = "DouCue"

		while cue_presentation.counting():
			self.fill()
			self.blit(left_box, 5, self.left_box_loc)
			self.blit(right_box, 5, self.right_box_loc)
			self.blit(self.star, 5, Params.screen_c)
			if not Params.eye_tracker_available:
				self.blit(cursor())
			self.flip()
			self.evi.send(event)
			Params.tk.start("cpoa")
			Params.tk.start("cboa", Params.tk.read("cpoa")[0])
			self.confirm_fixation()

	def present_neutral_boxes(self, pre_trial_blit=False):
		cue_onset = Params.tk.countdown(self.cue_onset_duration, TK_MS)
		while cue_onset.counting():
			self.ui_request()
			self.fill()
			self.blit(self.star, 5, Params.screen_c)
			self.blit(self.neutral_box, 5, self.left_box_loc)
			self.blit(self.neutral_box, 5, self.right_box_loc)
			if not Params.eye_tracker_available:
				self.blit(cursor())
			self.flip()
			self.confirm_fixation()

	def confirm_fixation(self):
		if not self.eyelink.within_boundary('fixation'):
			self.evi.send("DepartFix")
			acknowledged = False
			while not acknowledged:
				self.fill()
				self.blit(self.fixation_fail_msg, location=Params.screen_c, registration=5)
				self.flip()
				acknowledged = self.any_key()
			raise TrialException("Eyes must remain at fixation")

	def display_refresh(self, trial_type, probe_loc=None, flip=True):
		self.fill()
		if probe_loc == RIGHT:
			probe_loc = self.right_box_loc
		else:
			probe_loc = self.left_box_loc
		if trial_type in (BANDIT, BOTH):
			self.blit(self.left_bandit, 5, self.left_box_loc)
			self.blit(self.right_bandit, 5, self.right_box_loc)
		else:
			self.blit(self.neutral_box, 5, self.left_box_loc)
			self.blit(self.neutral_box, 5, self.right_box_loc)

		if self.collecting_response_for == PROBE:
			self.blit(self.probe, 5, probe_loc)

		if self.collecting_response_for == BANDIT:
			self.blit(self.star_muted, 5, Params.screen_c)
		else:
			self.blit(self.star, 5, Params.screen_c)

		if flip:
			self.flip()
			if self.collecting_response_for == BANDIT:
				self.evi.send("FixMute")
			if self.log_cboa:
				Params.tk.stop("cboa")
				self.log_cboa = False
		self.confirm_fixation()

	def post_flip_events(self, trial_type, probe_loc):
		if trial_type in (PROBE, BOTH):
			if self.collecting_response_for == BOTH:
				self.evi.send("ProbeHigh" if self.high_value_loc == probe_loc else "ProbeLow")
			else:
				self.evi.send("ProbeRight" if probe_loc == RIGHT else "ProbeLeft")

		if trial_type in (BANDIT, BOTH):
			self.evi.send("HighBandLeft" if self.high_value_loc == LEFT else "HighBandRight")



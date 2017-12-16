__author__ = "Brett Feltmate"

import klibs
from klibs.KLConstants import *
from klibs import P
from klibs.KLExceptions import *
from klibs.KLGraphics import flip, blit, fill, clear
from klibs.KLGraphics.KLDraw import Rectangle, Asterisk, Ellipse
from klibs.KLUtilities import deg_to_px
from klibs.KLUserInterface import ui_request, any_key
from klibs.KLCommunication import message
from klibs import env
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

	def setup(self):
		
		self.square_size_px = deg_to_px(self.square_size)
		self.star_size_px = deg_to_px(self.star_size)
		self.thick_rect = Rectangle(self.square_size_px, stroke=[self.thick_rect_border, self.square_border_colour, STROKE_OUTER])
		self.thin_rect = Rectangle(self.square_size_px, stroke=[self.thin_rect_border, self.square_border_colour, STROKE_OUTER])
		self.neutral_box = self.thin_rect.render()
		self.star = Asterisk(self.star_size_px, self.star_color)
		self.star_muted = Asterisk(self.star_size_px, self.muted_star_color)
		self.star_loc = self.probe_loc
		self.left_box_loc, self.right_box_loc = [ [P.screen_x // 4 * a, P.screen_c[1] ] for a in [1,3]]
		self.probe = Ellipse(int(0.75 * self.square_size_px), fill=self.square_border_colour).render()
		
		fix_x_1 = (P.screen_c[0] - self.star_size_px //2) - 60
		fix_y_1 = (P.screen_c[1] - self.star_size_px //2) - 60
		fix_x_2 = (P.screen_c[0] + self.star_size_px //2) + 60
		fix_y_2 = (P.screen_c[1] + self.star_size_px //2) + 60
		self.el.add_boundary('fixation', [(fix_x_1, fix_y_1), (fix_x_2, fix_y_2)], RECT_BOUNDARY)
		self.txtm.add_style("score up", 48, [75,210,100,255], anti_alias=True)
		self.txtm.add_style("score down", 48, [210,75,75,255], anti_alias=True)
		self.txtm.add_style("timeout", 48, [255,255,255,255])
		probe_timeout_text = "No response detected; trial recycled. \nPlease answer louder or faster. \nPress space to continue."
		bandit_text = "You {0} {1} points!\n Press any key to continue."
		self.probe_timeout_msg = message(probe_timeout_text, 'timeout', blit_txt=False)
		self.bandit_timeout_msg = message("Timed out; trial recycled.\n Press any key to continue.","timeout", blit_txt=False)
		self.fixation_fail_msg = message("Eyes moved. Please keep your eyes on the asterisk.", 'timeout', location=P.screen_c, registration=5, blit_txt=False)
		self.low_penalty_msg = message(bandit_text.format("lost", self.low_payout), "score down", blit_txt=False)
		for i in range(self.low_bandit_payout_baseline - self.bandit_payout_variance, self.low_bandit_payout_baseline + self.bandit_payout_variance):
			self.low_bandit_messages.append([i, message(bandit_text.format("won", i), "score up", blit_txt=False)])
		for i in range(self.high_bandit_payout_baseline - self.bandit_payout_variance, self.high_bandit_payout_baseline + self.bandit_payout_variance):
			self.high_bandit_messages.append([i,message(bandit_text.format("won", i), "score up", blit_txt=False)])
		self.low_reward_msg = message(bandit_text.format("won", self.low_payout), "score up", blit_txt=False)
		self.high_reward_msg = message(bandit_text.format("won", self.high_payout), "score up", blit_txt=False)

	def setup_response_collector(self):
		self.rc.display_args = [self.trial_type, self.probe_loc]
		self.rc.uses([RC_AUDIO, RC_KEYPRESS])
		self.rc.before_flip_callback = self.display_refresh
		self.rc.display_callback = self.display_refresh
		self.rc.keypress_listener.interrupts = True
		self.rc.keypress_listener.min_response_count = 1
		self.rc.audio_listener.min_response_count = 1
		self.rc.response_window = self.response_window
		self.rc.keypress_listener.key_map = KeyMap('bandit_response', ['/','z'], ['/','z'], [sdl2.SDLK_SLASH, sdl2.SDLK_z])
		self.rc.after_flip_callback = self.post_flip_events
		self.rc.after_flip_args = [self.trial_type, self.probe_loc]
		if self.collecting_response_for == PROBE:
			self.rc.audio_listener.interrupts = False
			if self.trial_type == PROBE:
				self.rc.audio_listener.interrupts = True
			self.rc.post_flip_tk_label = "cpoa"
			self.rc.audio_listener.interrupts = True
			self.rc.response_window = self.pbra
			self.rc.disable(RC_KEYPRESS)
			self.rc.enable(RC_AUDIO)
			self.rc.before_flip_args = [self.trial_type, self.probe_loc, False]
		elif self.collecting_response_for == BANDIT:
			self.rc.post_flip_sample_key = None
			self.rc.display_args = [self.trial_type, False]
			self.rc.enable(RC_KEYPRESS)
			self.rc.disable(RC_AUDIO)
			self.rc.before_flip_args = [self.trial_type, False, False]


	def block(self):
		if P.practicing:
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

	def trial_prep(self):
		if P.block_number == 1 and P.trial_number == 1:
			self.rc.audio_listener.calibrate()
		
		clear()
		self.collecting_response_for = None
		# If probed trial, establish location of probe (default: left box)
		if self.trial_type in [PROBE, BOTH]:
			self.prepare_bandits(self.high_value_location)
			if self.high_value_location == RIGHT:
				self.probe_loc = self.right_box_loc
		if self.trial_type == BANDIT:
			self.prepare_bandits(self.high_value_location)
		self.el.drift_correct()

	def trial(self):
		# Trial Factors: 1) trial_type, 2) high_value_loc, 3) probe_loc, 4) cue_loc, 5) winning_bandit
		self.el.start(P.trial_number)
		self.present_neutral_boxes()
		env.tk.start('cue_onset')
		self.present_cues(self.cue_location)
		self.prepare_bandits(self.high_value_location)

		# CUEING PERIOD cotoa = cue offset, taget onset asynchrony
		cotoa = random.choice(range(self.cotoa_min, self.cotoa_max, 1))
		if self.trial_type == PROBE:
			cotoa += self.bpoa
		cotoa = env.tk.countdown(cotoa, TK_MS)
		while cotoa.counting():
			self.present_neutral_boxes()

		#  BANDIT PRIMING PERIOD
		bandit_priming_period = env.tk.countdown(self.bpoa, TK_MS)
		if self.trial_type in [BANDIT, BOTH]:
			while bandit_priming_period.counting():
				self.log_cboa = True  # one time only per trial, display_refresh() needs to record a time post-flip
				self.display_refresh(self.trial_type)
		#  PROBE RESPONSE PERIOD
		if self.trial_type in [PROBE, BOTH]:
			self.collecting_response_for = PROBE
			self.setup_response_collector(trial_factors)
			print env.tk.elapsed('cue_onset')
			self.rc.collect()
			#if self.rc.audio_listener.responses[0][1] != TIMEOUT:
				#self.evm.send("DetectProbe")
			if self.rc.audio_listener.responses[0][0] == self.rc.audio_listener.null_response:
				acknowledged = False
				while not acknowledged:
					fill()
					blit(self.probe_timeout_msg, location=P.screen_c, registration=5)
					flip()
					acknowledged = any_key()
					#self.evm.send('TrialRecycled')
				raise TrialException("No vocal response.")
			
		else:
			bandit_response_delay = env.tk.countdown(self.pbra, TK_MS)
			while bandit_response_delay.counting():
				self.display_refresh(self.trial_type)

		#  BANDIT RESPONSE PERIOD
		if self.trial_type in [BANDIT, BOTH]:
			self.collecting_response_for = BANDIT
			self.setup_response_collector(trial_factors)
			self.rc.collect()
			choice = LEFT if self.rc.keypress_listener.responses[0][0] == 'z' else RIGHT
			#self.evm.send("SelectHighBand" if self.high_value_location == choice else "SelectLowBand")

		# get the stimuli off screen quickly whilst text renders
		fill()
		flip()

		#  FEEDBACK PERIOD
		reward = "N/A"
		if self.trial_type != PROBE:
			reward = self.feedback(self.rc.keypress_listener.responses[0][0], self.trial_type, self.high_value_location, trial_factors[5])
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
		"block_num": P.block_number,
		"trial_num": P.trial_number,
		"audio_response_time": audio_rt,
		"audio_timed_out": audio_timeout,
		"keypress_response_time": keypress_rt,
		"keypress_timed_out": keypress_timeout,
		"keypress_response": keypress_response,
		"trial_type": self.trial_type,
		"high_value_loc": self.high_value_location,
		"winning_bandit": self.winning_bandit,
		"reward": reward if reward else "N/A",
		"probe_loc": self.probe_loc,
		"cue_loc": self.cue_location,
		"cpoa": env.tk.period('cpoa') if self.trial_type in [PROBE, BOTH] else "N/A",
		"cboa": env.tk.period('cboa') if self.trial_type in [BANDIT, BOTH] else "N/A"
		}

	def trial_clean_up(self):
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
			post_selection_wait = env.tk.countdown(self.post_selection_wait, TK_MS)
			while post_selection_wait.counting():
				ui_request()
				fill()
				blit(self.star, 5, P.screen_c)
				flip()

		#self.evm.send(event)
		blit(feedback[1], location=P.screen_c, registration=5)
		feedback_exposure = env.tk.countdown(self.feedback_exposure_period, TK_MS)
		flip()
		while feedback_exposure.counting():
			ui_request()
			fill()
			blit(feedback[1], location=P.screen_c, registration=5)
			flip()
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
		self.thin_rect.fill = P.default_fill_color

	def present_cues(self, cue_condition):
		# assign graphics to cued location
		left_box = self.thick_rect if cue_condition in [LEFT, DOUBLE] else self.thin_rect
		right_box = self.thick_rect if cue_condition in [RIGHT, DOUBLE] else self.thin_rect

		# present cue
		cue_presentation = env.tk.countdown(self.cue_presentation_duration, TK_MS)
		event = "LeftCue"
		if cue_condition == RIGHT:
			event = "RightCue"
		elif cue_condition == DOUBLE:
			event = "DouCue"

		while cue_presentation.counting():
			fill()
			blit(left_box, 5, self.left_box_loc)
			blit(right_box, 5, self.right_box_loc)
			blit(self.star, 5, P.screen_c)
			flip()
			#self.evm.send(event)
			env.tk.start("cpoa")
			env.tk.start("cboa", env.tk.read("cpoa")[0])
			self.confirm_fixation()

	def present_neutral_boxes(self, pre_trial_blit=False):
		cue_onset = env.tk.countdown(self.cue_onset_duration, TK_MS)
		while cue_onset.counting():
			ui_request()
			fill()
			blit(self.star, 5, P.screen_c)
			blit(self.neutral_box, 5, self.left_box_loc)
			blit(self.neutral_box, 5, self.right_box_loc)
			flip()
			self.confirm_fixation()

	def confirm_fixation(self):
		if not self.el.within_boundary('fixation', EL_GAZE_POS):
			#self.evm.send("DepartFix")
			acknowledged = False
			while not acknowledged:
				fill()
				blit(self.fixation_fail_msg, location=P.screen_c, registration=5)
				flip()
				acknowledged = any_key()
			raise TrialException("Eyes must remain at fixation")

	def display_refresh(self, trial_type, probe_loc=None, flip=True):
		fill()
		if probe_loc == RIGHT:
			probe_loc = self.right_box_loc
		else:
			probe_loc = self.left_box_loc
		if trial_type in (BANDIT, BOTH):
			blit(self.left_bandit, 5, self.left_box_loc)
			blit(self.right_bandit, 5, self.right_box_loc)
		else:
			blit(self.neutral_box, 5, self.left_box_loc)
			blit(self.neutral_box, 5, self.right_box_loc)

		if self.collecting_response_for == PROBE:
			blit(self.probe, 5, probe_loc)

		if self.collecting_response_for == BANDIT:
			blit(self.star_muted, 5, P.screen_c)
		else:
			blit(self.star, 5, P.screen_c)

		if flip:
			flip()
			#if self.collecting_response_for == BANDIT:
				#self.evm.send("FixMute")
			if self.log_cboa:
				env.tk.stop("cboa")
				self.log_cboa = False
		self.confirm_fixation()

	def post_flip_events(self, trial_type, probe_loc):
		pass
		#if trial_type in (PROBE, BOTH):
			#if self.collecting_response_for == BOTH:
				#self.evm.send("ProbeHigh" if self.high_value_location == probe_loc else "ProbeLow")
			#else:
				#self.evm.send("ProbeRight" if probe_loc == RIGHT else "ProbeLeft")

		#if trial_type in (BANDIT, BOTH):
			#self.evm.send("HighBandLeft" if self.high_value_location == LEFT else "HighBandRight")



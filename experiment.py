__author__ = "Brett Feltmate"


# Import required KLibs classes and functions

import klibs
from klibs.KLConstants import *
from klibs.KLExceptions import TrialException
from klibs import P
from klibs.KLGraphics import flip, blit, fill, clear
from klibs.KLGraphics.KLDraw import Rectangle, Asterisk, Ellipse
from klibs.KLUtilities import deg_to_px
from klibs.KLKeyMap import KeyMap
from klibs.KLUserInterface import ui_request, any_key
from klibs.KLCommunication import message
from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLEventInterface import TrialEventTicket as ET
from klibs import env

# Import additional required libraries

import random

# Define some useful constants (?)

LEFT = "left"
RIGHT = "right"
DOUBLE = "double"
PROBE = "probe"
BOTH = "both"
BANDIT = "bandit"
HIGH = "high"
LOW = "low"

# Define colours for the experiment

WHITE = [255, 255, 255, 255]
GREY = [100, 100, 100, 255]
BLUE = [0, 0, 255, 255]
RED = [255, 0, 0, 255]
GREEN = [0, 255, 0, 255]
PURPLE = [95, 25, 130, 255]
PASTEL_GREEN = [75, 210, 100, 255]
PASTEL_RED = [210, 75, 75, 255]



class IOR_Reward(klibs.Experiment):
	
	high_bandit_payout_baseline = 12
	low_bandit_payout_baseline = 5
	penalty = -5

	# Runtime vars (ie. defined on a per-trial or per-block basis)
	high_value_color = None  				# block-level var
	low_value_color = None	 				# block-level var
	low_payout = 5
	high_payout = 10
	prob_loc = None
	high_value_loc = None


	def __init__(self, *args, **kwargs):
		super(IOR_Reward, self).__init__(*args, **kwargs)

	def setup(self):
		
		# Stimulus Sizes
		
		thick_rect_border = deg_to_px(0.35)
		thin_rect_border = deg_to_px(0.05)
		star_size = deg_to_px(0.75)
		star_thickness = deg_to_px(0.1)
		square_size = deg_to_px(4)
		
		# Stimulus Drawbjects
		
		self.thick_rect = Rectangle(square_size, stroke=[thick_rect_border, WHITE, STROKE_CENTER])
		self.thin_rect = Rectangle(square_size, stroke=[thin_rect_border, WHITE, STROKE_CENTER])
		self.left_bandit = Rectangle(square_size, stroke=[thin_rect_border, WHITE, STROKE_CENTER])
		self.right_bandit = Rectangle(square_size, stroke=[thin_rect_border, WHITE, STROKE_CENTER])
		self.neutral_box = self.thin_rect.render()
		self.star = Asterisk(star_size, WHITE, stroke=star_thickness)
		self.star_muted = Asterisk(star_size, GREY, stroke=star_thickness)
		self.probe = Ellipse(int(0.75 * square_size), fill=WHITE).render()
		
		# Layout
		
		self.left_box_loc = (P.screen_x // 4, P.screen_c[1])
		self.right_box_loc = (3 * P.screen_x // 4, P.screen_c[1])
		
		# Timing
		
		self.cue_onset = 1000
		self.cue_duration = 350
		self.cotoa_min = 700
		self.cotoa_max = 1000
		self.response_window = 2000
		self.pbra = 1000								# probe-bandit response asynchrony
		self.bpoa = 1000								# bandit-probe onset asynchrony
		self.post_selection_wait = 1000				#
		self.feedback_exposure_period = 1000
		
		# EyeLink Boundaries
		bounds_offset = star_size//2 + 60
		fix_bounds = [
			(P.screen_c[0] - bounds_offset, P.screen_c[1] - bounds_offset),
			(P.screen_c[0] + bounds_offset, P.screen_c[1] + bounds_offset)
		]
		self.el.add_boundary('fixation', fix_bounds, RECT_BOUNDARY)
		
		# Experiment Messages
		
		self.txtm.add_style("score up", 34, PASTEL_GREEN)
		self.txtm.add_style("score down", 34, PASTEL_RED)
		self.txtm.add_style("timeout", 34, WHITE)
		
		probe_timeout_text = (
			"No response detected; trial recycled.\n"
			"Please answer louder or faster.\n"
			"Press space to continue."
		)
		bandit_text = "You {0} {1} points!"#"\nPress any key to continue."
		
		self.fixation_fail_msg = message("Eyes moved. Please keep your eyes on the asterisk.", 
			'timeout', blit_txt=False)
		self.probe_timeout_msg = message(probe_timeout_text, 'timeout', align='center', blit_txt=False)
		self.bandit_timeout_msg = message("Timed out; trial recycled.\nPress any key to continue.",
			'timeout', align='center', blit_txt=False)
			
		self.low_penalty_msg = message(bandit_text.format("lost", self.low_payout), "score down",
			align='center', blit_txt=False)
		self.low_reward_msg = message(bandit_text.format("won", self.low_payout), "score up", 
			align='center', blit_txt=False)
		self.high_reward_msg = message(bandit_text.format("won", self.high_payout), "score up", 
			align='center', blit_txt=False)
			
		low_bandit_messages = []
		for i in range(self.low_bandit_payout_baseline - 1, self.low_bandit_payout_baseline + 1):
			self.low_bandit_messages.append(
				[i, message(bandit_text.format("won", i), "score up", align='center', blit_txt=False)]
			)
		high_bandit_messages = []
		for i in range(self.high_bandit_payout_baseline - 1, self.high_bandit_payout_baseline + 1):
			self.high_bandit_messages.append(
				[i, message(bandit_text.format("won", i), "score up", align='center', blit_txt=False)]
			)
		
		# Initialize separate ResponseCollectors for probe and bandit responses
		
		self.probe_rc = ResponseCollector(uses=RC_AUDIO)
		self.bandit_rc = ResponseCollector(uses=RC_KEYPRESS)
		
		# Initialize ResponseCollector keymap
		
		self.keymap = KeyMap(
			'bandit_response', # Name
			['z', '/'], # UI labels
			['left', 'right'], # Data labels
			[sdl2.SDLK_z, sdl2.SDLK_SLASH] # SDL2 Keysyms
		)
		
		# If first block, calibrate audio response threshold for probe responses
		self.probe_rc.audio_listener.calibrate()


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
		

	def setup_response_collector(self):
		
		# Configure probe response collector
		self.probe_rc.terminate_after = [2000, TK_MS]
		self.probe_rc.display_callback = self.probe_callback
		self.probe_rc.display_args = [self.trial_type == BOTH]
		#self.probe_rc.display_kwargs = {'mixed': self.trial_type == BOTH}
		self.probe_rc.flip = True
		self.probe_rc.audio_listener.interrupts = True
		
		# Configure bandit response collector
		self.bandit_rc.terminate_after = [2000, TK_MS]
		self.bandit_rc.display_callback = self.bandit_callback
		self.bandit_rc.flip = True
		self.bandit_rc.keypress_listener.key_map = self.keymap
		self.bandit_rc.keypress_listener.interrupts = True


	def trial_prep(self):

		# If probed trial, establish location of probe (default: left box)
		self.probe_loc = self.right_box_loc if self.probe_location == RIGHT else self.left_box_loc
			
		if self.high_value_loc == LEFT:
			self.left_bandit.fill = self.high_value_color
			self.right_bandit.fill = self.low_value_color
		else:
			self.left_bandit.fill = self.low_value_color
			self.right_bandit.fill = self.high_value_color
		self.left_bandit.render()
		self.right_bandit.render()
		
		self.cotoa = random.choice(range(self.cotoa_min, self.cotoa_max, 1))
		
		# Add timecourse of events to EventManager
		events = [[1000, 'cue_on']]
		events.append([events[-1][0] + 350, 'cue_off'])
		events.append([events[-1][0] + self.cotoa, 'target_on']) # either probe or bandits
		if self.trial_type in [BANDIT, BOTH]:
			events.append([events[-1][0] + 1000, 'nogo_end'])
		for e in events:
			self.evm.register_ticket(ET(e[1], e[0]))
			
		self.el.drift_correct()


	def trial(self):
		
		if P.development_mode:
			trial_info = "trial_type: {0} high_val_loc: {1} probe_loc: {2} cue_loc: {3} winning_bandit: {4}"
			print(trial_info.format(self.trial_type, self.high_value_location, self.probe_location, self.cue_location, self.winning_bandit))
		
		while self.evm.before('target_on', True):
			
			self.confirm_fixation()
			self.present_neutral_boxes()
			
			if self.evm.between('cue_on', 'cue_off'):
				if self.cue_location in [LEFT, DOUBLE]:
					blit(self.thick_rect, 5, self.left_box_loc)
				if self.cue_location in [RIGHT, DOUBLE]:
					blit(self.thick_rect, 5, self.right_box_loc)
					
			flip()

		if self.trial_type in [BANDIT, BOTH]:
			while self.evm.before('nogo_end', True):
				self.confirm_fixation()
				self.bandit_callback(before_go=True)
				flip()

		#  PROBE RESPONSE PERIOD
		if self.trial_type in [PROBE, BOTH]:
			self.probe_rc.collect()
			if self.probe_rc.audio_listener.responses[0][0] == self.probe_rc.audio_listener.null_response:
				fill()
				blit(self.probe_timeout_msg, location=P.screen_c, registration=5)
				flip()
				any_key()
				raise TrialException("No vocal response.")

		#  BANDIT RESPONSE PERIOD
		if self.trial_type in [BANDIT, BOTH]:
			self.bandit_rc.collect()
			choice = self.bandit_rc.keypress_listener.responses[0][0]

		#  FEEDBACK PERIOD
		reward = "NA"
		if self.trial_type != PROBE:
			reward = self.feedback(self.bandit_rc.keypress_listener.responses[0][0])
		try:
			audio_rt = self.probe_rc.audio_listener.responses[0][1]
			audio_timeout = self.probe_rc.audio_listener.responses[0][1] == TIMEOUT
		except IndexError:
			audio_rt = "NA"
			audio_timeout = "NA"
		try:
			keypress_rt = self.bandit_rc.keypress_listener.responses[0][1]
			keypress_timeout = self.bandit_rc.keypress_listener.responses[0][1] == TIMEOUT
			keypress_response = self.bandit_rc.keypress_listener.responses[0][0]
		except IndexError:
			keypress_rt = "NA"
			keypress_timeout = "NA"
			keypress_response = "NA"

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
			"reward": reward if reward else "NA",
			"probe_loc": self.probe_location,
			"cue_loc": self.cue_location,
			"cpoa": "NA",
			"cboa": "NA"
		}

	def trial_clean_up(self):
		self.probe_rc.audio_listener.reset()
		self.bandit_rc.keypress_listener.reset()

	def clean_up(self):
		pass

	def feedback(self, response):

		if self.winning_bandit == HIGH:
			winning_bandit_loc = self.high_value_loc
		else:
			winning_bandit_loc = LEFT if self.high_value_loc == RIGHT else RIGHT

		won = response == winning_bandit_loc
		timeout = not response
		high_win = random.choice(self.high_bandit_messages)
		low_win = random.choice(self.low_bandit_messages)

		if timeout:
			feedback = [None, self.bandit_timeout_msg]
		else:
			if won:
				feedback = high_win if self.high_value_loc == response else low_win
			else:
				feedback = [self.penalty, self.low_penalty_msg]
			post_selection_wait = env.tk.countdown(self.post_selection_wait, unit=TK_MS)
			while post_selection_wait.counting():
				ui_request()
				fill()
				blit(self.star, 5, P.screen_c)
				flip()

		feedback_exposure = env.tk.countdown(self.feedback_exposure_period, unit=TK_MS)
		while feedback_exposure.counting():
			ui_request()
			fill()
			blit(feedback[1], location=P.screen_c, registration=5)
			flip()
			
		return feedback[0]


	def confirm_fixation(self):
		if not self.el.within_boundary('fixation', EL_GAZE_POS):
			fill()
			blit(self.fixation_fail_msg, location=P.screen_c, registration=5)
			flip()
			any_key()
			raise TrialException("Eyes must remain at fixation")


	def present_neutral_boxes(self):
		fill()
		blit(self.star, 5, P.screen_c)
		blit(self.neutral_box, 5, self.left_box_loc)
		blit(self.neutral_box, 5, self.right_box_loc)
			
	def bandit_callback(self, before_go=False):
		fill()
		blit(self.star if before_go else self.star_muted, 5, P.screen_c)
		blit(self.left_bandit, 5, self.left_box_loc)
		blit(self.right_bandit, 5, self.right_box_loc)
		
	def probe_callback(self, mixed=False):
		self.confirm_fixation()
		if mixed:
			self.bandit_callback(True)
		else:
			self.present_neutral_boxes()
			
		probe_loc = self.right_box_loc if self.probe_location == RIGHT else self.left_box_loc
		blit(self.probe, 5, probe_loc)


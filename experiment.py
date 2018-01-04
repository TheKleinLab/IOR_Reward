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
import sdl2

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
	
	
	def __init__(self, *args, **kwargs):
		super(IOR_Reward, self).__init__(*args, **kwargs)


	def setup(self):
		
		# Bandit Variables
		
		self.high_payout_baseline = 12
		self.low_payout_baseline = 8
		self.penalty = -5
		# default high/low value bandit colors (changed every block)
		self.high_value_color = BLUE
		self.low_value_color = RED
		self.total_score = None
		
		# Stimulus Sizes
		
		thick_rect_border = deg_to_px(0.5)
		thin_rect_border = deg_to_px(0.1)
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
		
		self.cotoa_min = 700
		self.cotoa_max = 1000
		self.post_selection_wait = 1000
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
		
		self.fixation_fail_msg = message("Eyes moved. Please keep your eyes on the asterisk.", 
			'timeout', blit_txt=False)
		self.probe_timeout_msg = message(probe_timeout_text, 'timeout', align='center', blit_txt=False)
		self.bandit_timeout_msg = message("Timed out!\nPress any key to continue.",
			'timeout', align='center', blit_txt=False)
		
		# Initialize separate ResponseCollectors for probe and bandit responses
		
		self.probe_rc = ResponseCollector(uses=RC_AUDIO)
		self.bandit_rc = ResponseCollector(uses=RC_KEYPRESS)
		
		# Initialize ResponseCollector keymap
		
		self.keymap = KeyMap(
			'bandit_response', # Name
			['z', '/'], # UI labels
			["left", "right"], # Data labels
			[sdl2.SDLK_z, sdl2.SDLK_SLASH] # SDL2 Keysyms
		)
		
		# Add practice block of 20 trials to start of experiment
		if P.run_practice_blocks:
			self.insert_practice_block(1, trial_counts=20)
		
		# If first block, calibrate audio response threshold for probe responses
		self.probe_rc.audio_listener.calibrate()


	def block(self):
		
		#if self.total_score:
		#	fill()
		#	msg = message("Total block score: {0} points!".format(self.total_score), 'timeout', blit_txt=False)
		#	blit(msg, 5, P.screen_c)
		#	flip()
		#	any_key()
		if self.total_score:
			print("Total score for block: {0} points!\n".format(self.total_score))
		self.total_score = 0 # reset total bandit score each block 
		
		# If practicing, use different colours than during experimental blocks
		if P.practicing:
			practice_colors = random.sample([PURPLE, GREEN], 2)
			self.high_value_color = practice_colors[0]
			self.low_value_color = practice_colors[1]
		else:
			# Alternate high value colour between blocks
			if self.high_value_color is BLUE:
				self.high_value_color = RED
				self.low_value_color = BLUE
			else:
				self.high_value_color = BLUE
				self.low_value_color = RED
		

	def setup_response_collector(self):
		
		# Configure probe response collector
		self.probe_rc.terminate_after = [2000, TK_MS]
		self.probe_rc.display_callback = self.probe_callback
		self.probe_rc.display_args = [self.trial_type == BOTH]
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
			
		if self.high_value_location == LEFT:
			self.left_bandit.fill = self.high_value_color
			self.right_bandit.fill = self.low_value_color
			self.low_value_location = RIGHT
		else:
			self.left_bandit.fill = self.low_value_color
			self.right_bandit.fill = self.high_value_color
			self.low_value_location = LEFT
		self.left_bandit.render()
		self.right_bandit.render()
		
		# Randomly choose cue off-target on asynchrony (cotoa) on each trial
		self.cotoa = self.random_interval(self.cotoa_min, self.cotoa_max)
		
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
			trial_info = "trial_type: '{0}', high_val_loc: '{1}', probe_loc: '{2}', cue_loc: '{3}', winning_bandit: '{4}'\n"
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
		
		# Retreive responses from RepsponseCollector(s) and record data
		if self.trial_type in [BANDIT, BOTH]:
			bandit_choice = self.bandit_rc.keypress_listener.responses[0][0]
			bandit_rt = self.bandit_rc.keypress_listener.responses[0][1]
			bandit_timeout = bandit_rt == TIMEOUT
			# determine bandit payout (reward) and display feedback to participant
			reward = self.feedback(bandit_choice)
		else:
			bandit_choice, bandit_rt, bandit_timeout, reward = ['NA', 'NA', 'NA', 'NA']
			
		if self.trial_type in [PROBE, BOTH]:
			probe_rt = self.probe_rc.audio_listener.responses[0][1]
			probe_timeout = probe_rt == TIMEOUT
		else:
			probe_rt, probe_timeout = ['NA', 'NA']

		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"trial_type": self.trial_type,
			"cue_loc": self.cue_location,
			"cotoa": self.cotoa,
			"high_value_loc": self.high_value_location if self.trial_type != PROBE else "NA",
			"winning_bandit": self.winning_bandit if self.trial_type != PROBE else "NA",
			"bandit_choice": bandit_choice,
			"bandit_rt": bandit_rt,
			"reward": reward,
			"probe_loc": self.probe_location if self.trial_type != BANDIT else "NA",
			"probe_rt": probe_rt
		}


	def trial_clean_up(self):
		self.probe_rc.audio_listener.reset()
		self.bandit_rc.keypress_listener.reset()
		
		
	def clean_up(self):
		pass


	def feedback(self, response):

		if self.winning_bandit == HIGH:
			winning_bandit_loc = self.high_value_location
		else:
			winning_bandit_loc = self.low_value_location

		if response == "NO_RESPONSE":
			feedback = ["NA", self.bandit_timeout_msg]
		else:
			if response == winning_bandit_loc:
				points = self.bandit_payout(value=self.winning_bandit)
				msg = message("You won {0} points!".format(points), "score up", blit_txt=False)
			else:
				points = self.penalty # -5
				msg = message("You lost 5 points!", "score down", blit_txt=False)
			self.total_score += points
			feedback = [points, msg]
				
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
	
	def bandit_payout(self, value):
		mean = self.high_payout_baseline if value == HIGH else self.low_payout_baseline
		# sample from normal distribution with sd of 1 and round to nearest int
		return int(random.gauss(mean, 1) + 0.5)

	def confirm_fixation(self):
		if not self.el.within_boundary('fixation', EL_GAZE_POS):
			fill()
			blit(self.fixation_fail_msg, location=P.screen_c, registration=5)
			flip()
			any_key()
			raise TrialException("Eyes must remain at fixation")
			
	def random_interval(self, lower, upper):
		# utility function to generate random time intervals with a given range
		# that are multiples of the current refresh rate (e.g. 16.7ms for a 60Hz monitor)
		min_flips = int(round(lower/P.refresh_time))
		max_flips = int(round(upper/P.refresh_time))
		return random.choice(range(min_flips, max_flips+1, 1)) * P.refresh_time


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


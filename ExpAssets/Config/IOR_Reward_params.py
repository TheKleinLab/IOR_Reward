### IOR_Reward Parameter overrides ###

#########################################
# Available Hardware
#########################################
eye_tracker_available = True
eye_tracking = True
labjack_available = False
labjacking = False

#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (45, 45, 45, 255)
default_color = (255, 255, 255, 255)
default_font_size = 28
default_font_name = 'Frutiger'

#########################################
# EyeLink Sensitivities
#########################################
saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

#########################################
# Experiment Structure
#########################################
view_distance = 57
multi_user = False
collect_demographics = True
run_practice_blocks = True

trials_per_block = 96
blocks_per_experiment = 3

#########################################
# Development Mode Settings
#########################################
dm_auto_threshold = False
dm_trial_show_mouse = True
dm_ignore_local_overrides = False
dm_show_gaze_dot = True

#########################################
# Data Export Settings
#########################################
primary_table = "trials"
unique_identifier = "userhash"
default_participant_fields = [[unique_identifier, "participant"], "gender", "age", "handedness"]
default_participant_fields_sf = [[unique_identifier, "participant"], "random_seed", "gender", "age", "handedness"]

#########################################
# Project-specific params
#########################################
ignore_vocal_for_bandits = True # with more sensitive mics, key presses pass audio threshold
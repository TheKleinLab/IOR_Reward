from klibs.KLIndependentVariable import IndependentVariableSet
from klibs import P

IOR_Reward_ind_vars = IndependentVariableSet()

IOR_Reward_ind_vars.add_variable("trial_type", str)
IOR_Reward_ind_vars["trial_type"].add_values(("bandit", 2), "probe", "both")
IOR_Reward_ind_vars.add_variable("high_value_location", str)
IOR_Reward_ind_vars["high_value_location"].add_values("left", "right")

IOR_Reward_ind_vars.add_variable("probe_location", str)
IOR_Reward_ind_vars["probe_location"].add_values("left", "right")

IOR_Reward_ind_vars.add_variable("cue_location", str)
IOR_Reward_ind_vars["cue_location"].add_values("left", "right", "double")

IOR_Reward_ind_vars.add_variable("winning_bandit", str)
IOR_Reward_ind_vars["winning_bandit"].add_values("high", "low")

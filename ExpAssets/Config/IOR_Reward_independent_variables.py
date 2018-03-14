from klibs.KLIndependentVariable import IndependentVariableSet
from klibs import P

IOR_Reward_ind_vars = IndependentVariableSet()

IOR_Reward_ind_vars.add_variable("trial_type", str, [("bandit", 2), "probe", "both"])
IOR_Reward_ind_vars.add_variable("cue_location", str, ["left", "right"])
IOR_Reward_ind_vars.add_variable("probe_location", str, ["left", "right"])
IOR_Reward_ind_vars.add_variable("high_value_location", str, ["left", "right"])
IOR_Reward_ind_vars.add_variable("winning_bandit", str, ["high", "low"])

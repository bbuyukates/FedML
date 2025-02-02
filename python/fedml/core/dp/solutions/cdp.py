from fedml.core.dp.mechanisms.dp_mechanism import DPMechanism
from fedml.core.dp.solutions.base_dp_solution import BaseDPSolution


class GlobalDP(BaseDPSolution):
    def __init__(self, args):
        super().__init__(args)
        self.set_cdp(
            DPMechanism(args.mechanism_type, args.epsilon, args.delta, args.sensitivity)
        )

    def add_global_noise(self, global_model: dict):
        return super().add_global_noise(global_model=global_model)

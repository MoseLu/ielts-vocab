from __future__ import annotations


class AdminProjectionUnavailable(RuntimeError):
    def __init__(self, action: str, projection_name: str):
        super().__init__(f'{projection_name} projection is not bootstrapped for {action}')
        self.action = action
        self.projection_name = projection_name

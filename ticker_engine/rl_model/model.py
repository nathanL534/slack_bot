

from dataclasses import dataclass
from typing import Literal, Optional, Union
import torch
from torch import nn
import numpy as np
import os



ModelType = Literal["linear", "mlp"]




@dataclass 
class ModelConfig:
    # number of factors
    input_size: int = 9
    # number of neurons in hidden layer for mlp
    hidden_units: int = 32
    #options linear and mlp
    model_type: ModelType  = "linear"
    device: Optional[str] = None 
    
    
    

class LinearScorer(nn.Module):
    def __init__(self, input_size: int):
        super().__init__()

        self.lin = nn.Linear(input_size, 1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.lin(x).squeeze(-1)
    
    
class MLPScorer(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)
    
    
    
    
    
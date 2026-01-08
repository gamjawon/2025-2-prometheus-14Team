"""
Safety Check Model - RiskClassifier for binary classification
"""
import torch
import torch.nn as nn
from typing import List, Optional


class RiskClassifier(nn.Module):
    """위험성 이진 분류를 위한 MLP 모델"""

    def __init__(
        self,
        input_dim: int = 36,
        hidden_dims: List[int] = [256, 128, 64, 32],
        dropout_rate: float = 0,
    ):
        """
        Parameters
        ----------
        input_dim : int
            입력 차원 (임베딩 벡터 크기)
        hidden_dims : List[int]
            은닉층 차원 리스트
        dropout_rate : float
            Dropout 비율
        """
        super(RiskClassifier, self).__init__()

        self.input_dim = input_dim

        layers = []
        prev_dim = self.input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.SiLU())
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim

        # 출력층 (이진 분류)
        layers.append(nn.Linear(prev_dim, 2))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : torch.Tensor
            임베딩 벡터 (batch_size, embedding_dim)

        Returns
        -------
        outputs : torch.Tensor
            분류 로짓 (batch_size, 2)
        """
        return self.network(x)


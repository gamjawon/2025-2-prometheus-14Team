import os
import sys
import tempfile
from typing import Iterable, List, Optional

import pandas as pd
import torch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from CrabNet.kingcrab import CrabNet  # noqa: E402
from CrabNet.model import Model  # noqa: E402


DEFAULT_PROPERTIES: List[str] = [
    'OQMD_Formation_Enthalpy',
    'aflow__energy_atom',
    'OQMD_Energy_per_atom',
    'CritExam__Ef',
    'aflow__Egap',
    'aflow__ael_debye_temperature',
    'mp_bulk_modulus',
    'dielectric1',
    'dielectric2',
    'mp_e_form1',
    'mp_e_form2',
    'mp_e_form3'
]


def _prepare_loader(model: Model, formula: str) -> None:
    """Create a temporary single-entry CSV and attach it to the model."""
    df = pd.DataFrame({'formula': [formula], 'target': [0.0]})
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        df.to_csv(tmp.name, index=False)
        csv_path = tmp.name
    try:
        model.load_data(csv_path, batch_size=1, train=False)
    finally:
        os.remove(csv_path)


def get_property_embedding(
    formula: str,
    property_name: str,
    compute_device: Optional[str] = None,
    verbose: bool = False,
) -> torch.Tensor:
    """
    Extract a (3,) embedding vector for a single property using a pretrained CrabNet model.

    Parameters
    ----------
    formula : str
        Chemical formula string (e.g. 'Al2O3').
    property_name : str
        Name of the property. Must match the pretrained checkpoint filename.
    compute_device : str, optional
        Torch device string. Defaults to CrabNet's automatic selection.
    verbose : bool, optional
        Whether to print CrabNet initialization logs.

    Returns
    -------
    torch.Tensor
        1D tensor of length 3 containing `[value, uncertainty, gate_prob]`.
    """
    crabnet = CrabNet(compute_device=compute_device)
    wrapper = Model(crabnet, model_name=property_name, drop_unary=False, verbose=verbose)
    wrapper.load_network(f'{property_name}.pth')
    
    # CrabNet 모델 freeze (학습 시 업데이트 방지)
    wrapper.model.eval()
    for param in wrapper.model.parameters():
        param.requires_grad = False
    
    # 디바이스로 명시적으로 이동 (compute_device가 지정된 경우)
    if compute_device is not None:
        device = torch.device(compute_device)
        wrapper.model = wrapper.model.to(device)
        # wrapper의 compute_device도 업데이트 (collect_embeddings에서 사용)
        wrapper.compute_device = device
    
    _prepare_loader(wrapper, formula)

    captures = wrapper.collect_embeddings(
        loader=wrapper.data_loader,
        capture_head=True,
        capture_encoder=False,
        apply_pooling=True,
        apply_gating=True,
    )

    head = captures['head'].view(-1)  # value components (after gating)
    logits = captures.get('head_logits')

    # 디버깅: 각 단계의 차원 출력
    if verbose:
        print(f"captures['head'] shape: {captures['head'].shape}")
        if logits is not None:
            print(f"captures['head_logits'] shape: {logits.shape}")
        print(f"head (after view(-1)) shape: {head.shape}")

    if logits is not None:
        gate_prob = torch.sigmoid(logits.view(-1))
        if verbose:
            print(f"gate_prob (after sigmoid) shape: {gate_prob.shape}")
        embedding = torch.cat([head, gate_prob], dim=0)
    else:
        embedding = head

    if verbose:
        print(f"Final embedding shape: {embedding.shape}")

    return embedding


def get_combined_embedding(
    formula: str,
    properties: Iterable[str] = DEFAULT_PROPERTIES,
    compute_device: Optional[str] = None,
    verbose: bool = False,
) -> torch.Tensor:
    """
    Concatenate per-property embeddings into a single feature vector.

    Returns
    -------
    torch.Tensor
        1D tensor of shape `(len(properties) * 3,)` containing the concatenated
        embeddings `[value, uncertainty, gate_prob]` for each property.
    """
    vectors = []
    for prop in properties:
        vec = get_property_embedding(
            formula=formula,
            property_name=prop,
            compute_device=compute_device,
            verbose=verbose,
        )
        vectors.append(vec)
    return torch.cat(vectors, dim=0)


if __name__ == '__main__':
    test_formula = 'Al2O3'
    embedding = get_combined_embedding(test_formula)
    print(f'Embedding length: {embedding.numel()}')
    print(embedding)


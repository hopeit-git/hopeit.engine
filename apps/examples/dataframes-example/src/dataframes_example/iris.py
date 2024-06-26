"""Iris datasets schemas
"""

from datetime import datetime
from typing import List, Optional

from hopeit.dataframes import Dataset, dataframe
from hopeit.dataobjects import dataclass, dataobject, field


@dataframe
@dataclass
class Iris:
    sepal_length: float = field(serialization_alias="sepal length (cm)")
    sepal_width: float = field(serialization_alias="sepal width (cm)")
    petal_length: float = field(serialization_alias="petal length (cm)")
    petal_width: float = field(serialization_alias="petal width (cm)")
    variety: int = field(serialization_alias="target")


@dataframe
@dataclass
class IrisFeatures:
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float


@dataframe
@dataclass
class IrisLabels:
    variety: int


@dataobject
@dataclass
class EvalMetrics:
    accuracy_score: float


@dataobject
@dataclass
class InputData:
    iris: Dataset[Iris]


@dataobject
@dataclass
class Experiment:
    """Experiment parameters, data and model"""
    experiment_id: str
    experiment_dt: datetime
    input_data: Dataset[Iris]
    train_features: Optional[Dataset[IrisFeatures]] = None
    train_labels: Optional[Dataset[IrisLabels]] = None
    test_features: Optional[Dataset[IrisFeatures]] = None
    test_labels: Optional[Dataset[IrisLabels]] = None
    eval_metrics: Optional[EvalMetrics] = None
    trained_model_location: Optional[str] = None
    experiment_partition_key: Optional[str] = None


@dataobject
@dataclass
class IrisPredictionRequest:
    prediction_id: str
    features: IrisFeatures.DataObject  # type: ignore[name-defined]


@dataobject(unsafe=True)
@dataclass
class IrisBatchPredictionRequest:
    items: List[IrisPredictionRequest]


@dataobject
@dataclass
class IrisPredictionResponse:
    prediction_id: str
    prediction: IrisLabels.DataObject  # type: ignore[name-defined]


@dataobject
@dataclass
class IrisBatchPredictionResponse:
    items: List[IrisPredictionResponse]

"""Iris datasets schemas
"""

from hopeit.dataobjects import dataclass, field
from datetime import datetime
from typing import List, Optional

from hopeit.dataframes import dataframe, dataframeobject
from hopeit.dataobjects import dataobject


@dataframe
@dataclass
class Iris:
    sepal_length: float = field(metadata={"source_field_name": "sepal length (cm)"})
    sepal_width: float = field(metadata={"source_field_name": "sepal width (cm)"})
    petal_length: float = field(metadata={"source_field_name": "petal length (cm)"})
    petal_width: float = field(metadata={"source_field_name": "petal width (cm)"})
    variety: int = field(metadata={"source_field_name": "target"})


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


@dataframeobject
@dataclass
class InputData:
    iris: Iris


@dataframeobject
@dataclass
class Experiment:
    experiment_id: str
    experiment_dt: datetime
    input_data: Iris
    train_features: Optional[IrisFeatures] = None
    train_labels: Optional[IrisLabels] = None
    test_features: Optional[IrisFeatures] = None
    test_labels: Optional[IrisLabels] = None
    model_location: Optional[str] = None
    eval_metrics: Optional[EvalMetrics] = None


@dataobject(unsafe=True)
@dataclass
class IrisPredictionRequest:
    prediction_id: str
    features: IrisFeatures


@dataobject(unsafe=True)
@dataclass
class IrisBatchPredictionRequest:
    items: List[IrisPredictionRequest]


@dataobject(unsafe=True)
@dataclass
class IrisPredictionResponse:
    prediction_id: str
    prediction: IrisLabels


@dataobject(unsafe=True)
@dataclass
class IrisBatchPredictionResponse:
    items: List[IrisPredictionResponse]

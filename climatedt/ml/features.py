import logging

import pandas as pd

from pipeline.features import engineer_features

logger = logging.getLogger(__name__)


class FeatureEngine:
    def __init__(self) -> None:
        self._fitted = False

    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        result = engineer_features(df)
        self._fitted = True
        return result

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.engineer(df)

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional

def read_datasets(dir: str = "./data/", ext: str = ".csv.gz") -> list[pd.DataFrame]:
    """Read all time series files with the given extension from ``dir``."""
    if ext not in (".csv", ".csv.gz"):
        raise ValueError(f"Extension not supported: {ext}")

    data_dir = Path(dir)
    files = sorted(data_dir.glob(f"*{ext}"))
    if not files:
        raise FileNotFoundError(f"No '{ext}' files found in {data_dir.resolve()}")

    datasets: list[pd.DataFrame] = []
    for file in files:
        df = pd.read_csv(file, header=None, names=["timestamp", "value"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        df.attrs["name"] = file.name.removesuffix(ext)
        datasets.append(df)
    return datasets
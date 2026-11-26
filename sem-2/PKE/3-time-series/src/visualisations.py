import colorsys
from pathlib import Path
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional

DEFAULT_CMAP = plt.get_cmap("tab10")
def get_sizes(n: int):
    """Return the size of the grid."""
    ncols = int(np.ceil(np.sqrt(n)))
    nrows = int(np.ceil(n / ncols))
    return nrows, ncols


def visualise_datasets(datasets: list[pd.DataFrame]) -> None:
    """Plot each dataset in a clean multi-panel subplot grid."""
    if not datasets:
        raise ValueError("No datasets to visualise")

    nrows, ncols = get_sizes(len(datasets))

    fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 4 * nrows), squeeze=False)
    cmap = plt.get_cmap("tab10")

    for idx, (ax, df) in enumerate(zip(axes.flat, datasets)):
        if idx < len(datasets):
            name = df.attrs.get("name", f"Dataset {idx + 1}")
            series = df["value"] if "value" in df.columns else df.iloc[:, 0]
            ax.plot(df.index, series, color=cmap(idx % 10), linewidth=0.5, alpha=0.85)
            ax.set_title(name, fontsize=12, fontweight="bold")
            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis="x", rotation=25)
        else:
            ax.set_visible(False)

    fig.suptitle("Time Series Datasets Overview", fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.show()



############################ SERIES DISTRIBUTION ########################################### 
def _outlier_stats(df, outlier_stats):
    """Helper function for `series_distribution` that calculates outlier statistics."""
    s = df["value"]
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    upper_fence, lower_fence = q3 + 1.5 * iqr, q1 - 1.5 * iqr
    n_outliers = int(((s > upper_fence) | (s < lower_fence)).sum())
    
    outlier_stats.append({
                "dataset": df.attrs['name'],
                "iqr": round(iqr, 3),
                "lower_fence": round(lower_fence, 3),
                "upper_fence": round(upper_fence, 3),
                "iqr_outliers": n_outliers,
                "outlier_pct": round(100 * n_outliers / len(s), 2),
                "zero_pct": round(100 * (s == 0).mean(), 2),
            })

def _series_distribution_subplot(df: pd.DataFrame, ax: plt.Axes, idx:int, cmap=DEFAULT_CMAP, outlier_stats:Optional[list[dict]]=None):
    """Plot the distribution of values for a single time series. This is a helper function for `series_distribution`."""
    s = df["value"]
    color = cmap(idx % 10)

    ax.hist(s, bins=60, color=color, alpha=0.75, edgecolor="white", linewidth=0.4)
    ax.axvline(s.mean(), color="black", linestyle="--", linewidth=1.5, label=f"Mean: {s.mean():.2f}")
    ax.axvline(s.median(), color="darkred", linestyle=":", linewidth=1.8, label=f"Median: {s.median():.2f}")
    ax.set_title(f"{df.attrs['name']}", fontsize=12, fontweight="bold")
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, alpha=0.3)
    if outlier_stats is not None:
        _outlier_stats(df, outlier_stats)

def series_distributions(datasets: list[pd.DataFrame], plot_outliers:bool=False , cmap=DEFAULT_CMAP):
    """ Plots `ncols` rows by `nrows` columns series in from the `datasets` list. Uses `_series_distribution_subplot`.
        Args: 
            datasets: a list of pandas DataFrames with series to be analysed
            plot_outliers: whether to plot the outliers boxplots
        Returns: 
            a pandas DataFrame with outlier statistics
    """
    nrows, ncols = get_sizes(len(datasets))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 9))

    outlier_stats = []
    for idx, (ax, df) in enumerate(zip(axes.flat, datasets)):
        _series_distribution_subplot(df, ax, idx, cmap, outlier_stats)

    fig.suptitle("Value Distributions Across Datasets", fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.show()

    if plot_outliers:
        fig, ax = plt.subplots(figsize=(12, 4.5))
        bp = ax.boxplot(
            [df["value"].values for df in datasets],
            vert=False,
            patch_artist=True,
            flierprops={"marker": ".", "markersize": 2, "alpha": 0.35},
        )
        ax.set_yticklabels([df.attrs["name"] for df in datasets])
        for idx, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(cmap(idx % 10))
            patch.set_alpha(0.7)
        ax.set_title("Value Spread & Outliers (Boxplots)", fontsize=13, fontweight="bold")
        ax.set_xlabel("Value")
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        plt.show()

    return pd.DataFrame(outlier_stats)


################### DIURNAL PROFILE ###########################################
def _diurnal_profile_subplot(df: pd.DataFrame, ax: plt.Axes, idx:int, cmap=DEFAULT_CMAP):
    """Helper function for `diurnal_profile` that plots the diurnal profile of a single time series."""
    name = df.attrs["name"]
    color = cmap(idx % 10)
    hour_of_day = df.index.hour + df.index.minute / 60.0
    is_weekend = df.index.dayofweek >= 5

    weekday_profile = df.loc[~is_weekend, "value"].groupby(hour_of_day[~is_weekend]).mean()
    weekend_profile = df.loc[is_weekend, "value"].groupby(hour_of_day[is_weekend]).mean()

    ax.plot(weekday_profile.index, weekday_profile.values, color=color, linewidth=2, label="Weekday Mean")
    ax.plot(weekend_profile.index, weekend_profile.values, color="dimgray", linestyle="--", linewidth=2, label="Weekend Mean")
    ax.set_title(f"{name}", fontsize=12, fontweight="bold")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Mean Value")
    ax.set_xticks(range(0, 25, 3))
    ax.legend()
    ax.grid(True, alpha=0.3)    
    
def diurnal_profiles(datasets: list[pd.DataFrame], 
                    title: str="Weekday vs. Weekend Average Diurnal Profiles (15-min Averages)",figsize: tuple[int, int]=(14, 9), cmap=DEFAULT_CMAP) -> None:
    """Plots the diurnal profile of each dataset in a multi-panel subplot grid.
    """
    nrows, ncols = get_sizes(len(datasets))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    for idx, (ax, df) in enumerate(zip(axes.flat, datasets)):
        _diurnal_profile_subplot(df, ax, idx, cmap)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.show()


########################################## zoomed-in profiles #####################
def _closest_weekday(date: pd.Timestamp, target_dayofweek: int = 0) -> pd.Timestamp:
    """Return the date closest to ``date`` (within +-3 days) with ``dayofweek == target_dayofweek``."""
    diff = (target_dayofweek - date.dayofweek) % 7
    if diff > 3:
        diff -= 7
    return date + pd.Timedelta(days=diff)


def _resolve_zoom_period(datasets, zoom_period:Optional[tuple[str,str]]=None) -> tuple[pd.Timestamp,pd.Timestamp]:
    """Helper function for `zoom_datasets` that resolves the zoom period.
    If zoom_period is None, a random Monday-to-Monday week will be selected from the overlapping range of all datasets.
    Returns:
        tuple[pd.Timestamp, pd.Timestamp]: The start and end timestamps of the zoom period.
    """
    if zoom_period is not None:
        zoom_start, zoom_end = pd.Timestamp(zoom_period[0]), pd.Timestamp(zoom_period[1])
    else:
        earliest = max(df.index.min() for df in datasets).ceil("D")
        latest   = min(df.index.max() for df in datasets).floor("D")
        max_start = latest - pd.Timedelta(days=7)
        first_monday = earliest + pd.Timedelta(days=(-earliest.dayofweek) % 7)
        last_monday = max_start - pd.Timedelta(days=max_start.dayofweek)
        if last_monday < first_monday:
            raise ValueError(f"Overlapping range ({earliest.date()} to {latest.date()}) does not contain a full Mon-Mon week.")
        offset_days = int(np.random.default_rng().integers(0, (max_start - earliest).days + 1))
        candidate   = earliest + pd.Timedelta(days=offset_days)
        zoom_start  = min(max(_closest_weekday(candidate, target_dayofweek=0), first_monday), last_monday)
        zoom_end    = zoom_start + pd.Timedelta(days=7)
    return zoom_start, zoom_end

def _shade_color(color, lightness_shift: float) -> tuple[float, float, float]:
    """Return a lighter (>0) or darker (<0) RGB shade of ``color``."""
    h, l, s = colorsys.rgb_to_hls(*mcolors.to_rgb(color))
    if lightness_shift >= 0:
        l_new = l + (1.0 - l) * min(lightness_shift, 0.85)
    else:
        l_new = l * max(1.0 + lightness_shift, 0.15)
    return colorsys.hls_to_rgb(h, l_new, s)


def _closest_dow_start(zoom_start: pd.Timestamp, target_year: int) -> pd.Timestamp:
    """Return the date in ``target_year`` closest to ``zoom_start``'s calendar date with the same day of week."""
    nominal = zoom_start + pd.DateOffset(years=target_year - zoom_start.year)
    return _closest_weekday(nominal, zoom_start.dayofweek)


def _zoom_yearly_subplot(df: pd.DataFrame, ax: plt.Axes, zoom_start: pd.Timestamp, zoom_end: pd.Timestamp, base_color) -> None:
    """Plot weekday-aligned slices across all available years on ``ax``."""
    name = df.attrs["name"]
    window_span = zoom_end - zoom_start # e.g. one week
    year_slices = []
    for year in range(df.index.year.min(), df.index.year.max() + 1):
        y_start = _closest_dow_start(zoom_start, year)
        y_end = y_start + window_span
        year_window = df.loc[(df.index >= y_start) & (df.index <= y_end), "value"]
        if not year_window.empty:
            year_slices.append((year, y_start, year_window))

    other_years = [y for y, _, _ in year_slices if y != zoom_start.year]
    color_shifts = ([0.35] if len(other_years) == 1 else np.linspace(-0.35, 0.45, len(other_years)))
    year_to_shade = dict(zip(other_years, color_shifts))

    for year, y_start, year_window in year_slices:
        aligned_x = zoom_start + (year_window.index - y_start)
        is_ref = year == zoom_start.year # reference year
        line_color = base_color if is_ref else _shade_color(base_color, float(year_to_shade[year]))
        ax.plot(aligned_x, year_window.values,
                color=line_color, linestyle="-" if is_ref else "--", linewidth=1.5 if is_ref else 1.0,
                                alpha=0.95 if is_ref else 0.85,    zorder=3 if is_ref else 2,
                label=f"{year} ({y_start:%m-%d})")
    ax.legend(title="Year (Start)", fontsize=8, ncol=2, loc="upper right")
    # Use day of week as x-axis labels if multiple years series are plotted:
    day_step = max(1, window_span.days // 10)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=day_step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a"))
    ax.set_title(f"{name}", fontsize=12, fontweight="bold")


def zoom_datasets(datasets, zoom_period:Optional[tuple[str,str]]=None, yearly:bool=False, 
                    title: str="Zoomed-In High-Resolution Sample (15-min Intervals)", figsize=(14, 9), cmap=DEFAULT_CMAP):
    """Plot series zoomed in.
    Args:
        datasets: a list of pandas DataFrames with series to be analysed
        zoom_period: a tuple of strings with the start and end dates of the zoom period in the format YYYY-MM-DD. 
                     If None, a random week will be selected.
        yearly: if True, overlay the closest same-weekday window across all available years on a common x-axis.
        cmap: a colormap to use for the plots
    """
    nrows, ncols = get_sizes(len(datasets))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)
    zoom_start, zoom_end = _resolve_zoom_period(datasets, zoom_period)

    for idx, ax in enumerate(axes.flat):
        if idx >= len(datasets):
            ax.set_visible(False)
            continue

        df = datasets[idx]
        name = df.attrs["name"]
        base_color = cmap(idx % 10)

        if yearly:
            _zoom_yearly_subplot(df, ax, zoom_start, zoom_end, base_color)
            ax.set_xlabel(f"Day of Week")
        else:
            window = df.loc[(df.index >= zoom_start) & (df.index <= zoom_end), "value"]
            ax.plot(window.index, window.values, color=base_color, linewidth=1.1)
            ax.set_title(f"{name} ({zoom_start:%Y-%m-%d} to {zoom_end:%Y-%m-%d})", fontsize=12, fontweight="bold")
        
        ax.set_ylabel("Value")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=25)

    fig.suptitle(f"{title} (ref: {zoom_start:%Y-%m-%d})", fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.show()
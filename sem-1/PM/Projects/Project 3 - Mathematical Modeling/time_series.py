import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("solution.csv")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

df[["demand", "pv_prod", "bought", "sold", "charge", "discharge"]].plot(ax=ax1, grid=True)
ax1.set_ylabel("Energy [kWh]")

df["soc"].plot(ax=ax2, color="blue", label="SoC", grid=True)
ax2.axhline(15.67, color="r", linestyle="--", label="Max SoC")
ax2.axhline(2.65, color="r", linestyle=":", label="Min SoC")
ax2.axhline(8.31, color="purple", linestyle="-.", label="Final SoC Target")
ax2.set_ylabel("SoC [kWh]")
ax2.set_xlabel("Period")
ax2.legend()

plt.tight_layout()
plt.savefig("timeseries.png", dpi=300)
plt.show()

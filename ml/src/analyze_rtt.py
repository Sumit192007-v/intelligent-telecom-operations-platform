import pandas as pd

df = pd.read_csv("ml/data/features/telecom_features.csv")

df["elevated_latency"] = (df["rtt_ms"] >= 75).astype(int)

print("Overall latency classes:")
print(
    df["elevated_latency"]
    .value_counts()
    .sort_index()
    .rename(index={0: "Normal (<75 ms)", 1: "Elevated (>=75 ms)"})
    .to_string()
)

print("\nLatency classes by drive:")

drive_table = pd.crosstab(
    df["source_drive"],
    df["elevated_latency"],
    normalize="index"
) * 100

drive_table = drive_table.rename(
    columns={
        0: "Normal (<75 ms)",
        1: "Elevated (>=75 ms)"
    }
)

print(drive_table.round(2).to_string())

print("\nLatency classes by operator:")

operator_table = pd.crosstab(
    df["operator"],
    df["elevated_latency"],
    normalize="index"
) * 100

operator_table = operator_table.rename(
    columns={
        0: "Normal (<75 ms)",
        1: "Elevated (>=75 ms)"
    }
)

print(operator_table.round(2).to_string())
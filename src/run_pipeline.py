from preprocess import preprocess_all
from make_split import make_split
from evaluate import evaluate_baseline
import json

if __name__ == "__main__":
    print("step 1: preprocessing raw scans")
    preprocess_all("data/raw_scans", "data/preprocessed")

    print("\nstep 2: creating train/test split")
    make_split("data/preprocessed")

    print("\nstep 3: running baseline evaluation")
    with open("data/split.json") as f:
        split_info = json.load(f)
    evaluate_baseline(split_info["test"], "data/preprocessed", "data/ground_truth")

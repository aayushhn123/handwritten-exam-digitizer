import os
import random
import json


def make_split(preprocessed_folder, test_ratio=0.2):
    filenames = sorted([f for f in os.listdir(preprocessed_folder) if f.endswith((".jpg", ".png"))])
    random.seed(42)
    random.shuffle(filenames)

    split_point = int(len(filenames) * (1 - test_ratio))
    train_files = filenames[:split_point]
    test_files = filenames[split_point:]

    split_info = {"train": train_files, "test": test_files}
    os.makedirs("data", exist_ok=True)
    with open("data/split.json", "w") as f:
        json.dump(split_info, f, indent=2)

    print("train pages:", len(train_files))
    print("test pages:", len(test_files))
    return train_files, test_files


if __name__ == "__main__":
    make_split("data/preprocessed")

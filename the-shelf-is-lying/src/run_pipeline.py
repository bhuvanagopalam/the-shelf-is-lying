"""Run the full local analysis in order."""

from availability import train_and_score
from clearance import build_clearance_fingerprints
from generate_data import main as generate_data
from prepare_data import prepare_and_save
from recommendations import build_recommendations


def main() -> None:
    print("\n1. Generating the fictional retail operation")
    generate_data()

    print("\n2. Preparing observable analysis features")
    prepare_and_save()

    print("\n3. Estimating practical availability")
    train_and_score()

    print("\n4. Describing store clearance patterns")
    build_clearance_fingerprints()

    print("\n5. Ranking weekly store actions")
    build_recommendations()


if __name__ == "__main__":
    main()

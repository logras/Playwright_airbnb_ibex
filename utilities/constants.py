from pathlib import Path


class Constants:
    AUTOMATION_USER_AGENT: str = "automation"
    DATA_PATH: Path = Path(Path(__file__).absolute().parent.parent, "data")
    CHROME_DOWNLOAD_DIRECTORY: Path = DATA_PATH / "downloads"
    DIFF_TOLERANCE_PERCENT: float = 0.01
    BASE_URL: str = "https://www.airbnb.com/"

    #test helpers
    ADULTS_COUNT = 2
    TOTAL_GUESTS_COUNT = 2

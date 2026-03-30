from src.siigo.infraestructure.base import BaseSiigoClient


class ReportClient(BaseSiigoClient):
    URL = "https://services.siigo.com/ACReportApi/api/v1/Report/post"

    def __init__(self) -> None:
        super().__init__()

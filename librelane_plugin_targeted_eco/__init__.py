from pathlib import Path
from librelane.steps import Step
from librelane.steps.odb import InsertECODiodes

__version__ = "0.1.0"


@Step.factory.register()
class InsertECODiodesOnly(InsertECODiodes):
    id = "Odb.InsertECODiodesOnly"
    name = "Insert ECO Diodes Only"

    def get_script_path(self):
        return str(
            Path(__file__).with_name("insert_eco_diodes_only.py")
        )
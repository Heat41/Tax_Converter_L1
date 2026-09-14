from ui.pages.worksheet_pph_stage3 import WorksheetPage as Stage3WorksheetPage
from ui.pages.worksheet_pph_stage5 import WorksheetPage as Stage5WorksheetPage


def test_stage5_uses_inherited_bupot_action_refresh():
    assert "_refresh_bupot_actions" not in Stage5WorksheetPage.__dict__
    assert (
        Stage5WorksheetPage._refresh_bupot_actions
        is Stage3WorksheetPage._refresh_bupot_actions
    )

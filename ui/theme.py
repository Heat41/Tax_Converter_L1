from PySide6.QtGui import QFont

APP_FONT = QFont("Segoe UI", 10)

STYLESHEET = """
QMainWindow, QWidget {
    background: #F6F8FB;
    color: #172033;
    font-family: "Segoe UI";
}
QWidget#mainContent {
    background: #F6F8FB;
}
QFrame#sidebar {
    background: #102A43;
    border: none;
}
QLabel#brandLogo {
    background: transparent;
    border: none;
}
QLabel#brand,
QLabel#brandMain {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 800;
}
QLabel#brandAccent {
    color: #2CC55E;
    font-size: 18px;
    font-weight: 800;
}
QLabel#brandSub {
    color: #B9C7D6;
    font-size: 12px;
    font-weight: 600;
}
QLabel#sidebarCaption {
    color: #93AFC8;
    font-size: 11px;
    font-weight: 600;
}
QPushButton {
    background: #FFFFFF;
    color: #1976D2;
    border: 1px solid #90CAF9;
    border-radius: 8px;
    padding: 9px 17px;
    font-weight: 600;
}
QPushButton:hover {
    background: #EAF4FD;
    border-color: #1976D2;
}
QPushButton:pressed {
    background: #DCEEFF;
    border-color: #1565C0;
    color: #1565C0;
}
QPushButton:disabled {
    background: #F5F7FA;
    color: #9AA5B1;
    border-color: #D9E2EC;
}
QPushButton#navButton {
    color: #D9E2EC;
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 13px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 700;
}
QPushButton#navButton:hover {
    background: #1F486A;
    color: white;
}
QPushButton#navButton[active="true"] {
    background: #2563EB;
    color: white;
}
QLabel#pageTitle {
    color: #102A43;
    font-size: 29px;
    font-weight: 800;
}
QLabel#pageSubTitle {
    color: #526D82;
    font-size: 14px;
    font-weight: 500;
}
QFrame#card {
    background: #FFFFFF;
    border: 1px solid #E1E8EF;
    border-radius: 12px;
}
QLabel#cardTitle {
    color: #526D82;
    font-size: 13px;
    font-weight: 600;
}
QLabel#cardValue {
    color: #102A43;
    font-size: 24px;
    font-weight: 700;
}
QPushButton#primaryButton {
    background: #1976D2;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#primaryButton:hover { background: #1565C0; }
QPushButton#primaryButton:pressed { background: #0D47A1; }
QPushButton#primaryButton:disabled {
    background: #CBD2D9;
    color: #9AA5B1;
}
QPushButton#secondaryButton {
    background: #FFFFFF;
    color: #1976D2;
    border: 1px solid #90CAF9;
    border-radius: 8px;
    padding: 9px 17px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#secondaryButton:hover {
    background: #EAF4FD;
    border-color: #1976D2;
}
QPushButton#secondaryButton:pressed {
    background: #DCEEFF;
    border-color: #1565C0;
    color: #1565C0;
}
QPushButton#secondaryButton:disabled {
    background: #F5F7FA;
    color: #9AA5B1;
    border-color: #D9E2EC;
}
QPushButton#themeButton {
    background: #FFFFFF;
    color: #334E68;
    border: 1px solid #CBD2D9;
    border-radius: 10px;
    padding: 13px 18px;
    font-size: 14px;
    font-weight: 700;
    text-align: left;
}
QPushButton#themeButton:hover {
    background: #F0F6FF;
    border-color: #90CAF9;
}
QPushButton#themeButton:checked {
    background: #EAF2FF;
    color: #1D4ED8;
    border: 2px solid #2563EB;
}
QLabel#mutedLabel {
    color: #526D82;
    font-size: 13px;
    font-weight: 700;
}
QLabel#sectionTitle {
    color: #102A43;
    font-size: 18px;
    font-weight: 700;
}
QLineEdit,
QComboBox {
    background: #FFFFFF;
    color: #102A43;
    border: 1px solid #CBD2D9;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    selection-background-color: #BFDBFE;
    selection-color: #102A43;
}
QLineEdit:focus,
QComboBox:focus {
    border-color: #1976D2;
}
QLineEdit:read-only {
    background: #F6F8FB;
    color: #334E68;
}
QProgressBar {
    background-color: #E2E8F0;
    border-radius: 4px;
    text-align: center;
    color: #102A43;
    font-size: 11px;
    font-weight: 600;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #1976D2;
    border-radius: 4px;
}
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E1E8EF;
    border-radius: 8px;
    gridline-color: #F0F4F8;
    color: #102A43;
    font-size: 13px;
    selection-background-color: #DBEAFE;
    selection-color: #102A43;
}
QHeaderView::section {
    background-color: #F0F4F8;
    color: #334E68;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #D9E2EC;
    border-right: 1px solid #E2E8F0;
}
QTabWidget#worksheetTabs::pane {
    background: #FFFFFF;
    border: 1px solid #D9E2EC;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: #EAF0F6;
    color: #486581;
    border: 1px solid #D9E2EC;
    border-bottom: none;
    padding: 11px 18px;
    margin-right: 4px;
    min-width: 150px;
    font-size: 14px;
    font-weight: 700;
}
QTabBar::tab:first {
    border-top-left-radius: 8px;
}
QTabBar::tab:last {
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #1976D2;
    border-color: #90CAF9;
}
QTabBar::tab:hover:!selected {
    background: #DDEAF5;
    color: #334E68;
}
QScrollBar:vertical {
    background: #EEF3F8;
    width: 12px;
    margin: 2px;
    border: none;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #90AFC8;
    min-height: 32px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #5E8DB3;
}
QScrollBar::handle:vertical:pressed {
    background: #1976D2;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #EEF3F8;
    height: 12px;
    margin: 2px;
    border: none;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #90AFC8;
    min-width: 32px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #5E8DB3;
}
QScrollBar::handle:horizontal:pressed {
    background: #1976D2;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""

DARK_OVERRIDES = """
QMainWindow, QWidget {
    background: #0F172A;
    color: #E5EDF7;
}
QWidget#mainContent {
    background: #0F172A;
}
QFrame#sidebar {
    background: #081426;
}
QLabel#brandMain,
QLabel#brand {
    color: #F8FAFC;
}
QLabel#brandAccent {
    color: #4ADE80;
}
QLabel#brandSub {
    color: #A8B8CC;
}
QLabel#sidebarCaption {
    color: #8399B3;
}
QPushButton {
    background: #17243A;
    color: #93C5FD;
    border-color: #355070;
}
QPushButton:hover {
    background: #1E3350;
    border-color: #60A5FA;
}
QPushButton:pressed {
    background: #203A5C;
    border-color: #3B82F6;
    color: #DBEAFE;
}
QPushButton:disabled {
    background: #162033;
    color: #66758A;
    border-color: #2B3A4F;
}
QPushButton#navButton {
    color: #C7D2E0;
    background: transparent;
    border: none;
}
QPushButton#navButton:hover {
    background: #142C47;
    color: #FFFFFF;
}
QPushButton#navButton[active="true"] {
    background: #2563EB;
    color: #FFFFFF;
}
QLabel#pageTitle,
QLabel#sectionTitle,
QLabel#cardValue {
    color: #F1F5F9;
}
QLabel#pageSubTitle,
QLabel#cardTitle,
QLabel#mutedLabel {
    color: #A9B8CB;
}
QFrame#card {
    background: #111C2E;
    border-color: #263750;
}
QPushButton#primaryButton {
    background: #2563EB;
    color: #FFFFFF;
    border: none;
}
QPushButton#primaryButton:hover {
    background: #1D4ED8;
}
QPushButton#primaryButton:pressed {
    background: #1E40AF;
}
QPushButton#secondaryButton {
    background: #111C2E;
    color: #93C5FD;
    border-color: #365B85;
}
QPushButton#secondaryButton:hover {
    background: #172A43;
    border-color: #60A5FA;
}
QPushButton#secondaryButton:pressed {
    background: #1D3656;
    color: #DBEAFE;
}
QPushButton#themeButton {
    background: #111C2E;
    color: #D7E2EF;
    border-color: #34465F;
}
QPushButton#themeButton:hover {
    background: #172A43;
    border-color: #4F7EAD;
}
QPushButton#themeButton:checked {
    background: #18335D;
    color: #DBEAFE;
    border: 2px solid #3B82F6;
}
QLineEdit,
QComboBox {
    background: #0D1727;
    color: #E5EDF7;
    border-color: #34465F;
    selection-background-color: #1D4ED8;
    selection-color: #FFFFFF;
}
QLineEdit:focus,
QComboBox:focus {
    border-color: #60A5FA;
}
QLineEdit:read-only {
    background: #141F31;
    color: #C7D2E0;
}
QComboBox QAbstractItemView {
    background: #111C2E;
    color: #E5EDF7;
    selection-background-color: #1D4ED8;
    selection-color: #FFFFFF;
}
QProgressBar {
    background-color: #243147;
    color: #E5EDF7;
}
QProgressBar::chunk {
    background-color: #3B82F6;
}
QTableWidget {
    background-color: #111C2E;
    alternate-background-color: #142136;
    border-color: #2A3B53;
    gridline-color: #25364D;
    color: #E5EDF7;
    selection-background-color: #1E3A5F;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #17243A;
    color: #D7E2EF;
    border-bottom-color: #34465F;
    border-right-color: #2A3B53;
}
QTableCornerButton::section {
    background: #17243A;
    border: none;
}
QTabWidget#worksheetTabs::pane {
    background: #111C2E;
    border-color: #2A3B53;
}
QTabBar::tab {
    background: #17243A;
    color: #A9B8CB;
    border-color: #2A3B53;
}
QTabBar::tab:selected {
    background: #111C2E;
    color: #93C5FD;
    border-color: #3B82F6;
}
QTabBar::tab:hover:!selected {
    background: #1B2D47;
    color: #D7E2EF;
}
QScrollArea,
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical,
QScrollBar:horizontal {
    background: #18253A;
}
QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #526A86;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: #6F8AA7;
}
QScrollBar::handle:vertical:pressed,
QScrollBar::handle:horizontal:pressed {
    background: #3B82F6;
}
"""


def stylesheet_for(theme: str = "light") -> str:
    return STYLESHEET + DARK_OVERRIDES if str(theme).lower() == "dark" else STYLESHEET

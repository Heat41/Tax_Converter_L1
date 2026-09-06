from PySide6.QtGui import QFont

APP_FONT = QFont("Segoe UI", 10)

STYLESHEET = """
QMainWindow, QWidget {
    background: #F6F8FB;
    color: #172033;
    font-family: "Segoe UI";
}
QFrame#sidebar {
    background: #102A43;
    border: none;
}
QLabel#brand {
    color: white;
    font-size: 20px;
    font-weight: 700;
}
QLabel#brandSub {
    color: #B9C7D6;
    font-size: 11px;
}
QPushButton#navButton {
    color: #D9E2EC;
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 11px 14px;
    text-align: left;
}
QPushButton#navButton:hover, QPushButton#navButton[active="true"] {
    background: #1F486A;
    color: white;
}
QLabel#pageTitle {
    font-size: 26px;
    font-weight: 700;
}
QLabel#pageSubTitle {
    color: #627D98;
}
QFrame#card {
    background: white;
    border: 1px solid #E1E8EF;
    border-radius: 12px;
}
QLabel#cardTitle {
    color: #627D98;
    font-size: 12px;
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
    font-weight: 600;
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
    font-weight: 600;
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
QLabel#mutedLabel {
    color: #627D98;
    font-size: 13px;
}
QLabel#sectionTitle {
    color: #102A43;
    font-size: 16px;
    font-weight: 600;
}
QComboBox {
    background: white;
    color: #102A43;
    border: 1px solid #CBD2D9;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}
QComboBox:focus {
    border-color: #1976D2;
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
    background-color: white;
    border: 1px solid #E1E8EF;
    border-radius: 8px;
    gridline-color: #F0F4F8;
    color: #102A43;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #F0F4F8;
    color: #334E68;
    font-weight: 600;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #D9E2EC;
    border-right: 1px solid #E2E8F0;
}

/* Scrollbar utama halaman dan tabel */
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

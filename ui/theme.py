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
"""

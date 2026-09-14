from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPainter, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.performance import optimize_scroll_area


class LegacyPdfPreviewDialog(QDialog):
    """Stage 8D.4N - viewer PDF Form 1770 sementara."""

    MIN_ZOOM = 0.5
    MAX_ZOOM = 2.0
    ZOOM_STEP = 0.15
    BASE_RENDER_WIDTH = 850

    def __init__(self, pdf_path: str | Path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.current_page = 0
        self.zoom_factor = 1.0

        self.setWindowTitle("Preview Format Lama 1770")
        self.resize(1050, 760)
        self.setMinimumSize(760, 560)

        self.document = QPdfDocument(self)
        self._build_ui()
        self._load_document()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QFrame(objectName="card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(8)

        self.previous_button = QPushButton("Sebelumnya")
        self.previous_button.setObjectName("secondaryButton")
        self.next_button = QPushButton("Berikutnya")
        self.next_button.setObjectName("secondaryButton")

        self.page_label = QLabel("Halaman - / -")
        self.page_label.setObjectName("mutedLabel")
        self.page_label.setAlignment(Qt.AlignCenter)

        self.zoom_out_button = QPushButton("Zoom -")
        self.zoom_out_button.setObjectName("secondaryButton")
        self.zoom_reset_button = QPushButton("100%")
        self.zoom_reset_button.setObjectName("secondaryButton")
        self.zoom_in_button = QPushButton("Zoom +")
        self.zoom_in_button.setObjectName("secondaryButton")

        self.previous_button.clicked.connect(self._previous_page)
        self.next_button.clicked.connect(self._next_page)
        self.zoom_out_button.clicked.connect(self._zoom_out)
        self.zoom_reset_button.clicked.connect(self._zoom_reset)
        self.zoom_in_button.clicked.connect(self._zoom_in)

        header_layout.addWidget(self.previous_button)
        header_layout.addWidget(self.next_button)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.page_label)
        header_layout.addStretch()
        header_layout.addWidget(self.zoom_out_button)
        header_layout.addWidget(self.zoom_reset_button)
        header_layout.addWidget(self.zoom_in_button)
        root.addWidget(header)

        self.page_container = QWidget()
        page_layout = QVBoxLayout(self.page_container)
        page_layout.setContentsMargins(20, 20, 20, 20)
        page_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.page_image = QLabel()
        self.page_image.setAlignment(Qt.AlignCenter)
        self.page_image.setObjectName("pdfPreviewPage")
        page_layout.addWidget(self.page_image, alignment=Qt.AlignHCenter)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("legacyPdfPreviewScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setWidget(self.page_container)
        optimize_scroll_area(self.scroll, vertical_step=30)
        root.addWidget(self.scroll, 1)

        footer = QHBoxLayout()
        self.file_label = QLabel(
            f"Preview sementara • {self.pdf_path.name}"
        )
        self.file_label.setObjectName("mutedLabel")
        self.file_label.setToolTip(str(self.pdf_path))
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        footer.addWidget(self.file_label, 1)

        close_button = QPushButton("Tutup")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def _load_document(self):
        error = self.document.load(str(self.pdf_path))
        if error != QPdfDocument.Error.None_:
            self.page_image.setText(
                f"PDF preview tidak dapat dibuka. Error: {error}"
            )
            self._update_controls()
            return
        self.current_page = 0
        self._render_current_page()

    @property
    def page_count(self) -> int:
        return max(0, int(self.document.pageCount()))

    def _render_current_page(self):
        if self.page_count <= 0:
            self.page_image.setText("PDF tidak memiliki halaman.")
            self._update_controls()
            return

        self.current_page = min(
            max(0, self.current_page),
            self.page_count - 1,
        )

        point_size = self.document.pagePointSize(self.current_page)
        if point_size.width() <= 0 or point_size.height() <= 0:
            self.page_image.setText("Ukuran halaman PDF tidak valid.")
            self._update_controls()
            return

        width = max(
            320,
            int(self.BASE_RENDER_WIDTH * self.zoom_factor),
        )
        height = max(
            320,
            int(width * point_size.height() / point_size.width()),
        )
        image = self.document.render(
            self.current_page,
            QSize(width, height),
        )

        # QPdfDocument dapat menghasilkan area transparan. Pada Dark Mode,
        # transparansi tersebut membuat warna background aplikasi menembus
        # halaman dan kertas PDF terlihat gelap. Komposisikan hasil render ke
        # canvas putih agar preview selalu menyerupai dokumen/kertas aslinya.
        white_canvas = QImage(
            image.size(),
            QImage.Format.Format_ARGB32,
        )
        white_canvas.fill(Qt.GlobalColor.white)
        painter = QPainter(white_canvas)
        painter.drawImage(0, 0, image)
        painter.end()

        self.page_image.setPixmap(QPixmap.fromImage(white_canvas))
        self.page_image.adjustSize()
        self._update_controls()

    def _update_controls(self):
        count = self.page_count
        if count:
            self.page_label.setText(
                f"Halaman {self.current_page + 1} / {count}"
            )
        else:
            self.page_label.setText("Halaman - / -")

        self.previous_button.setEnabled(
            count > 0 and self.current_page > 0
        )
        self.next_button.setEnabled(
            count > 0 and self.current_page < count - 1
        )
        self.zoom_out_button.setEnabled(
            self.zoom_factor > self.MIN_ZOOM
        )
        self.zoom_in_button.setEnabled(
            self.zoom_factor < self.MAX_ZOOM
        )
        self.zoom_reset_button.setText(
            f"{round(self.zoom_factor * 100):.0f}%"
        )

    def _previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.page_count - 1:
            self.current_page += 1
            self._render_current_page()

    def _zoom_out(self):
        self.zoom_factor = max(
            self.MIN_ZOOM,
            self.zoom_factor - self.ZOOM_STEP,
        )
        self._render_current_page()

    def _zoom_in(self):
        self.zoom_factor = min(
            self.MAX_ZOOM,
            self.zoom_factor + self.ZOOM_STEP,
        )
        self._render_current_page()

    def _zoom_reset(self):
        self.zoom_factor = 1.0
        self._render_current_page()


    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self._previous_page()
            event.accept()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._next_page()
            event.accept()
            return
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._zoom_in()
            event.accept()
            return
        if key == Qt.Key.Key_Minus:
            self._zoom_out()
            event.accept()
            return
        if key == Qt.Key.Key_0:
            self._zoom_reset()
            event.accept()
            return
        super().keyPressEvent(event)

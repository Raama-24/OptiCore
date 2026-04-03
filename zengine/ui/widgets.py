"""
Reusable UI widgets for Z-Engine
"""

import datetime
import os

from PySide6.QtWidgets import (
    QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QCheckBox, QProgressBar, QPlainTextEdit,
    QGroupBox, QScrollArea, QToolBox, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen

from zengine.models import OptimizationTask, OptimizationCategory, StrategyOption
from zengine.safety import CommandSafety, RiskLevel
from zengine.script import ScriptGenerator, ScriptRunner, LiveRiskCalculator


THEME = {
    # Tuned to the reference screenshot (dark, subtle borders, neon accents).
    "bg": "#05070c",
    "panel": "#0a0d13",
    "panel2": "#070a10",
    "border": "rgba(78, 130, 160, 0.18)",
    "border2": "rgba(78, 130, 160, 0.28)",
    "text": "rgba(240, 248, 255, 0.90)",
    "muted": "rgba(240, 248, 255, 0.52)",
    "cyan": "#2bf2ff",
    "green": "#38ff8f",
    "magenta": "#b15bff",
    "yellow": "#ffd06a",
    "red": "#ff4b6e",
}


class TaskChecklistWidget(QFrame):
    """Left-side optimization task checklist like the reference screenshot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("taskChecklist")
        self.setStyleSheet(f"""
            QFrame#taskChecklist {{
                background: transparent;
                border: none;
            }}
            QCheckBox {{
                spacing: 10px;
                color: {THEME["text"]};
                font-weight: 700;
                font-size: 10px;
            }}
            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
                border: 1px solid {THEME["border2"]};
                background: rgba(7,10,16,0.8);
            }}
            QCheckBox::indicator:checked {{
                background: rgba(43,242,255,0.18);
                border: 1px solid rgba(43,242,255,0.55);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.rows = []
        for label, status, pts in [
            ("Clear temp + prefetch cache", "SAFE", "+4"),
            ("Disable startup bloatware", "SAFE", "+2"),
            ("Optimize virtual memory", "CAUTION", "+5"),
            ("Rebuild WMI repository", "SAFE", "+1"),
            ("Flush DNS / reset Winsock", "SAFE", "+3"),
            ("Disable redundant services", "CAUTION", "+6"),
            ("Defrag pagefile", "SAFE", "+2"),
            ("Clear event log backlog", "SAFE", "+1"),
        ]:
            row = QWidget()
            r = QHBoxLayout(row)
            r.setContentsMargins(0, 0, 0, 0)
            r.setSpacing(8)

            cb = QCheckBox(label)
            r.addWidget(cb, 1)

            pill = QLabel(f"{status} {pts}")
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pill.setMinimumWidth(88)
            pill.setStyleSheet(self._pill_style(status))
            r.addWidget(pill, 0, Qt.AlignmentFlag.AlignRight)

            layout.addWidget(row)
            self.rows.append((cb, pill))

        layout.addStretch()

    def _pill_style(self, status: str) -> str:
        status = status.upper()
        if status == "SAFE":
            bg = "rgba(56,255,143,0.12)"
            fg = THEME["green"]
            br = "rgba(56,255,143,0.35)"
        else:
            bg = "rgba(255,208,106,0.12)"
            fg = THEME["yellow"]
            br = "rgba(255,208,106,0.35)"
        return f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border: 1px solid {br};
                padding: 3px 6px;
                border-radius: 0px;
                font-weight: 900;
                letter-spacing: 1px;
                font-size: 9px;
            }}
        """


class LiveAnalysisWidget(QFrame):
    """Screenshot: CPU, MEMORY, DISK I/O, NET LOAD, STABILITY + histogram."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("liveAnalysis")
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Order and colors match reference: lime, cyan, orange, magenta, pale
        self.bars = {}
        for name, color in [
            ("CPU LOAD", "#9aff3a"),
            ("MEMORY", THEME["cyan"]),
            ("DISK I/O", THEME["yellow"]),
            ("NET LOAD", THEME["magenta"]),
            ("STABILITY", "rgba(200, 230, 255, 0.95)"),
        ]:
            row = QWidget()
            r = QHBoxLayout(row)
            r.setContentsMargins(0, 0, 0, 0)
            r.setSpacing(8)

            lbl = QLabel(name)
            lbl.setFixedWidth(78)
            lbl.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px; font-size: 9px;")
            r.addWidget(lbl)

            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(0)
            pb.setTextVisible(False)
            pb.setFixedHeight(8)
            pb.setStyleSheet(f"""
                QProgressBar {{
                    background: rgba(12,16,26,0.75);
                    border: 1px solid {THEME["border"]};
                    border-radius: 0px;
                }}
                QProgressBar::chunk {{
                    background: {color};
                }}
            """)
            r.addWidget(pb, 1)

            pct = QLabel("0%")
            pct.setFixedWidth(34)
            pct.setAlignment(Qt.AlignmentFlag.AlignRight)
            pct.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; font-size: 9px;")
            r.addWidget(pct)

            layout.addWidget(row)
            self.bars[name] = (pb, pct)

        # Histogram
        hist = QWidget()
        h = QHBoxLayout(hist)
        h.setContentsMargins(0, 4, 0, 0)
        h.setSpacing(3)
        self.hist_bars = []
        for i in range(24):
            b = QFrame()
            b.setFixedWidth(8)
            height = 22 + (i % 7) * 3
            b.setFixedHeight(height)
            b.setStyleSheet(f"background: rgba(120,180,200,0.22); border: 1px solid {THEME['border']};")
            h.addWidget(b)
            self.hist_bars.append(b)
        h.addStretch()
        layout.addWidget(hist)

    def set_metrics(self, cpu: int, mem: int, disk_io: int, net: int, stability: int):
        mapping = [
            ("CPU LOAD", cpu),
            ("MEMORY", mem),
            ("DISK I/O", disk_io),
            ("NET LOAD", net),
            ("STABILITY", stability),
        ]
        for name, v in mapping:
            pb, pct = self.bars[name]
            v = max(0, min(100, int(v)))
            pb.setValue(v)
            pct.setText(f"{v}%")


class SystemLogWidget(QFrame):
    """Right-side system log list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemLog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(500)
        self.view.setStyleSheet(f"""
            QPlainTextEdit {{
                background: rgba(7,10,16,0.65);
                border: 1px solid {THEME["border"]};
                border-radius: 0px;
                padding: 8px;
                color: rgba(240,248,255,0.55);
                font-family: "Consolas", "Courier New", monospace;
                font-size: 10px;
            }}
        """)
        layout.addWidget(self.view, 1)

    def append(self, line: str):
        self.view.appendPlainText(line)


class ResultsCardWidget(QFrame):
    """Bottom-right results card like screenshot 'BEFORE vs AFTER'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resultsCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("BEFORE VS AFTER")
        title.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; letter-spacing: 2px; font-size: 9px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.before = QLabel("--")
        self.after = QLabel("--")
        self.delta = QLabel("--")
        for w, c in [(self.before, THEME["yellow"]), (self.after, THEME["cyan"]), (self.delta, THEME["green"])]:
            w.setStyleSheet(f"color: {c}; font-weight: 900; font-size: 16px;")

        grid.addWidget(QLabel("BEFORE"), 0, 0)
        grid.addWidget(self.before, 0, 1)
        grid.addWidget(QLabel("AFTER"), 0, 2)
        grid.addWidget(self.after, 0, 3)
        grid.addWidget(QLabel("GAIN"), 0, 4)
        grid.addWidget(self.delta, 0, 5)
        layout.addLayout(grid)

        self.bar_layout = QVBoxLayout()
        for label_text, color, val in [("BEFORE", THEME["yellow"], 70), ("AT PLAN", THEME["cyan"], 90), ("REFINED", THEME["green"], 98)]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; font-size: 9px;")
            lbl.setFixedWidth(60)
            
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(val)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background: rgba(12,16,26,0.75);
                    border: 1px solid {THEME["border"]};
                    border-radius: 0px;
                }}
                QProgressBar::chunk {{
                    background: {color};
                }}
            """)
            row.addWidget(lbl)
            row.addWidget(bar)
            self.bar_layout.addLayout(row)
        
        layout.addLayout(self.bar_layout)
        layout.addSpacing(10)

        self.export = QPushButton("EXPORT SCRIPT")
        self.export.setStyleSheet(f"""
            QPushButton {{
                background: rgba(177,91,255,0.12);
                border: 1px solid rgba(177,91,255,0.45);
                color: {THEME["magenta"]};
                padding: 8px 10px;
                font-weight: 900;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background: rgba(177,91,255,0.18);
                border: 1px solid rgba(177,91,255,0.65);
            }}
        """)
        layout.addWidget(self.export)


class NeonPanel(QFrame):
    """A reusable cyberpunk-styled panel container."""

    def __init__(self, title: str = "", accent: str = "#00ff88", parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)

        self.setObjectName("neonPanel")
        self.setFrameStyle(QFrame.Shape.Box)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # Screenshot-like rectangular heading tag
        self._title_row = QWidget()
        tr = QHBoxLayout(self._title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(8)

        self._title_dot = QFrame()
        self._title_dot.setFixedSize(6, 6)
        self._title_dot.setStyleSheet(f"background: {accent};")
        tr.addWidget(self._title_dot)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("neonPanelTitle")
        self.title_label.setStyleSheet(f"""
            color: {THEME["muted"]};
            letter-spacing: 2px;
            font-weight: 900;
            font-size: 9px;
        """)
        tr.addWidget(self.title_label)
        tr.addStretch()

        self._title_tag = QFrame()
        self._title_tag.setObjectName("neonPanelTitleTag")
        self._title_tag_layout = QHBoxLayout(self._title_tag)
        self._title_tag_layout.setContentsMargins(10, 6, 10, 6)
        self._title_tag_layout.setSpacing(0)
        self._title_tag_layout.addWidget(self._title_row)
        outer.addWidget(self._title_tag)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)
        outer.addWidget(self.body, 1)

        self.setStyleSheet(f"""
            QFrame#neonPanel {{
                background-color: {THEME["panel"]};
                border: 1px solid {THEME["border2"]};
                border-radius: 0px;
            }}
            QFrame#neonPanelTitleTag {{
                background-color: rgba(12, 16, 26, 0.72);
                border: 1px solid {THEME["border"]};
                border-radius: 0px;
            }}
            QLabel#neonPanelTitle {{
                padding: 0px;
            }}
        """)

    def set_accent(self, accent: str):
        self._accent = QColor(accent)
        self._title_dot.setStyleSheet(f"background: {accent};")
        self.setStyleSheet(f"""
            QFrame#neonPanel {{
                background-color: {THEME["panel"]};
                border: 1px solid {THEME["border2"]};
                border-radius: 0px;
            }}
            QFrame#neonPanelTitleTag {{
                background-color: rgba(12, 16, 26, 0.72);
                border: 1px solid {THEME["border"]};
                border-radius: 0px;
            }}
            QLabel#neonPanelTitle {{
                padding: 0px;
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Add "panel chrome" like the reference: double stroke + corner cuts.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        r = self.rect().adjusted(0, 0, -1, -1)
        cut = 10

        def draw_path(pen: QPen, inset: int):
            rr = r.adjusted(inset, inset, -inset, -inset)
            points = [
                (rr.left() + cut, rr.top()),
                (rr.right() - cut, rr.top()),
                (rr.right(), rr.top() + cut),
                (rr.right(), rr.bottom() - cut),
                (rr.right() - cut, rr.bottom()),
                (rr.left() + cut, rr.bottom()),
                (rr.left(), rr.bottom() - cut),
                (rr.left(), rr.top() + cut),
                (rr.left() + cut, rr.top()),
            ]
            p.setPen(pen)
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                p.drawLine(int(x1), int(y1), int(x2), int(y2))

        outer = QPen(QColor(120, 255, 255, 70))
        outer.setWidth(1)
        draw_path(outer, 0)

        inner = QPen(QColor(120, 255, 255, 35))
        inner.setWidth(1)
        draw_path(inner, 2)

        accent = QPen(QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 170))
        accent.setWidth(1)
        # Small accent segments (top-left and bottom-right)
        p.setPen(accent)
        p.drawLine(r.left() + cut, r.top(), r.left() + cut + 60, r.top())
        p.drawLine(r.right() - cut - 60, r.bottom(), r.right() - cut, r.bottom())


class MetricCard(QFrame):
    """Compact metric card used in right-side dashboard."""

    def __init__(self, label: str, value: str = "--", accent: str = "#00ff88", parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("metricCard")
        self.setFrameStyle(QFrame.Shape.Box)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.label = QLabel(label.upper())
        self.label.setStyleSheet(f"color: {THEME['muted']}; font-size: 9px; letter-spacing: 1px;")
        layout.addWidget(self.label)

        self.value = QLabel(value)
        self.value.setStyleSheet(f"color: {accent}; font-size: 16px; font-weight: 800;")
        layout.addWidget(self.value)

        self.sub = QLabel("")
        self.sub.setStyleSheet(f"color: {THEME['muted']}; font-size: 10px;")
        self.sub.hide()
        layout.addWidget(self.sub)

        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {THEME["panel2"]};
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
            }}
        """)

    def set_value(self, value: str, sub: str | None = None):
        self.value.setText(value)
        if sub:
            self.sub.setText(sub)
            self.sub.show()
        else:
            self.sub.hide()


class DonutGauge(QFrame):
    """A simple donut gauge rendered with QPainter."""

    def __init__(self, label: str = "RISK RATING", value: int = 0, accent: str = "#00ff88", parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, int(value)))
        self._accent = QColor(accent)
        self._label = label

        self.setObjectName("donutGauge")
        self.setMinimumHeight(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.title = QLabel(label.upper())
        self.title.setStyleSheet(f"color: {THEME['muted']}; font-size: 9px; letter-spacing: 1px;")
        layout.addWidget(self.title)

        self.center_value = QLabel(f"{self._value}%")
        self.center_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_value.setStyleSheet(f"color: {THEME['text']}; font-size: 20px; font-weight: 800;")
        layout.addWidget(self.center_value, 1)

        self.legend = QLabel("")
        self.legend.setStyleSheet(f"color: {THEME['muted']}; font-size: 10px;")
        layout.addWidget(self.legend)

        self.setStyleSheet("""
            QFrame#donutGauge {
                background-color: rgba(10, 14, 20, 0.95);
                border: 1px solid rgba(120, 255, 255, 0.14);
                border-radius: 10px;
            }
        """)

    def set_value(self, value: int, legend: str = ""):
        self._value = max(0, min(100, int(value)))
        self.center_value.setText(f"{self._value}%")
        self.legend.setText(legend)
        self.update()

    def set_accent(self, accent: str):
        self._accent = QColor(accent)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Draw gauge behind the value label; keep clear of the title/legend.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(14, 34, -14, -44)
        size = min(rect.width(), rect.height())
        g = QRectF(
            rect.center().x() - size / 2,
            rect.center().y() - size / 2,
            size,
            size,
        )

        bg_pen = QPen(QColor(40, 50, 60, 220))
        bg_pen.setWidth(10)
        painter.setPen(bg_pen)
        painter.drawArc(g, 90 * 16, -360 * 16)

        pen = QPen(self._accent)
        pen.setWidth(10)
        painter.setPen(pen)
        span = int(-360 * 16 * (self._value / 100.0))
        painter.drawArc(g, 90 * 16, span)


class ClickableTaskCard(QFrame):
    toggled = Signal(str, bool)
    
    def __init__(self, task: OptimizationTask, plan_type: str = "original"):
        super().__init__()
        self.task = task
        self.selected = False
        self.plan_type = plan_type
        self.setup_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def setup_ui(self):
        border_color = THEME["cyan"] if self.plan_type == "refined" else "rgba(120,255,255,0.14)"
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{ 
                border: 1px solid {border_color};
                border-radius: 10px;
                margin: 0px;
                background: {THEME["panel2"]};
            }}
            QFrame:hover {{ 
                border: 1px solid rgba(46, 243, 255, 0.45);
                background: {THEME["panel"]};
            }}
            QFrame[selected="true"] {{ 
                border: 1px solid rgba(180, 77, 255, 0.65);
                background: rgba(180, 77, 255, 0.08);
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.indicator = QLabel("")
        self.indicator.setFixedWidth(14)
        layout.addWidget(self.indicator)
        
        details = QVBoxLayout()
        details.setSpacing(3)
        
        desc_text = f"{self.task.description}"
        desc = QLabel(desc_text)
        desc.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        desc.setStyleSheet(f"color: {THEME['text']};")
        desc.setWordWrap(True)
        desc.setMinimumWidth(200)
        details.addWidget(desc)
        
        meta = QHBoxLayout()
        meta.setSpacing(10)
        
        if self.task.impact_on_stability > 0:
            gain = QLabel(f"+{self.task.impact_on_stability}")
            gain.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            gain.setStyleSheet(f"color: {THEME['green']};")
            meta.addWidget(gain)
            lbl = QLabel("stability")
            lbl.setStyleSheet(f"color: {THEME['muted']};")
            meta.addWidget(lbl)
        
        if self.task.risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            warning = QLabel("UNSAFE")
            warning.setStyleSheet(f"background: rgba(255, 77, 109, 0.20); color: {THEME['red']}; font-weight: 800; padding: 2px 6px; border-radius: 8px;")
            meta.addWidget(warning)
        else:
            safe_badge = QLabel("SAFE")
            safe_badge.setStyleSheet(f"background: rgba(66, 255, 158, 0.14); color: {THEME['green']}; font-weight: 800; padding: 2px 6px; border-radius: 8px;")
            meta.addWidget(safe_badge)
            
        risk_color = self.task.get_risk_color()
        risk = QLabel(f"{self.task.get_risk_badge().strip()}")
        risk.setStyleSheet(f"background: rgba(46, 243, 255, 0.10); color: {THEME['cyan']}; font-weight: 800; padding: 2px 6px; border-radius: 8px;")
        meta.addWidget(risk)
        
        if self.task.requires_reboot:
            reboot = QLabel("REBOOT")
            reboot.setStyleSheet(f"background: rgba(255, 213, 106, 0.14); color: {THEME['yellow']}; font-weight: 800; padding: 2px 6px; border-radius: 8px;")
            meta.addWidget(reboot)
        
        if self.plan_type == "refined":
            refined_badge = QLabel("REFINED")
            refined_badge.setStyleSheet(f"background: rgba(46, 243, 255, 0.12); color: {THEME['cyan']}; font-weight: 800; padding: 2px 6px; border-radius: 8px;")
            meta.addWidget(refined_badge)
        
        meta.addStretch()
        details.addLayout(meta)
        layout.addLayout(details)
        layout.addStretch()
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        self.selected = not self.selected
        self.setProperty("selected", self.selected)
        self.style().polish(self)
        self.indicator.setText("▣" if self.selected else "□")
        self.indicator.setStyleSheet(f"color: {THEME['magenta']}; font-weight: 800;")
        self.toggled.emit(self.task.id, self.selected)


class CategoryWidget(QGroupBox):
    changed = Signal()
    
    def __init__(self, category: OptimizationCategory, is_priority: bool = False, plan_type: str = "original"):
        super().__init__(category.name)
        self.category = category
        self.cards = {}
        self.plan_type = plan_type
        self.setup_ui(is_priority)
    
    def setup_ui(self, is_priority: bool):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        if is_priority:
            priority_badge = QLabel("FOCUS AREA")
            priority_badge.setStyleSheet("""
                background: rgba(66, 255, 158, 0.12);
                color: #42ff9e;
                font-weight: 900;
                padding: 4px 10px;
                border-radius: 10px;
                max-width: 140px;
            """)
            layout.addWidget(priority_badge)
        
        if self.plan_type == "refined":
            refined_badge = QLabel("IMPROVED")
            refined_badge.setStyleSheet("""
                background: rgba(46, 243, 255, 0.12);
                color: #2ef3ff;
                font-weight: 900;
                padding: 4px 10px;
                border-radius: 10px;
                max-width: 140px;
            """)
            layout.addWidget(refined_badge)
        
        if self.category.reasoning:
            reasoning = QLabel(f" {self.category.reasoning}")
            reasoning.setWordWrap(True)
            reasoning.setMinimumWidth(200)
            reasoning.setStyleSheet(f"color: {THEME['muted']}; padding: 4px;")
            layout.addWidget(reasoning)
        
        safe_tasks = self.category.get_safe_tasks()
        advanced_tasks = self.category.get_unsafe_tasks()
        
        if safe_tasks:
            safe_header = QLabel("SAFE OPTIMIZATIONS")
            safe_header.setStyleSheet(f"color: {THEME['green']}; font-weight: 900; margin-top: 8px; letter-spacing: 1px;")
            layout.addWidget(safe_header)
            
            for task in safe_tasks:
                card = ClickableTaskCard(task, self.plan_type)
                card.toggled.connect(self._on_task_toggled)
                layout.addWidget(card)
                self.cards[task.id] = card
        
        if advanced_tasks:
            if safe_tasks:
                layout.addSpacing(10)
            
            advanced_header = QLabel("ADVANCED / CAUTION")
            advanced_header.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900; margin-top: 8px; letter-spacing: 1px;")
            layout.addWidget(advanced_header)
            
            for task in advanced_tasks:
                card = ClickableTaskCard(task, self.plan_type)
                card.toggled.connect(self._on_task_toggled)
                layout.addWidget(card)
                self.cards[task.id] = card
        
        self.setLayout(layout)
    
    def _on_task_toggled(self, task_id: str, checked: bool):
        self.changed.emit()
    
    def get_selected(self) -> list:
        return [t for t in self.category.tasks if t.id in self.cards and self.cards[t.id].selected]


class LiveRiskWidget(QFrame):
    """Widget showing real-time risk calculations"""
    
    def __init__(self):
        super().__init__()
        self.current_tasks = []
        self.base_score = 70
        self.setup_ui()
        self.hide()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QLabel {{
                color: {THEME["muted"]};
                font-weight: 700;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        self.header = QLabel("LIVE RISK ANALYSIS")
        self.header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.header.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 1px;")
        layout.addWidget(self.header)
        
        meter_layout = QHBoxLayout()
        
        self.risk_meter = QProgressBar()
        self.risk_meter.setRange(0, 100)
        self.risk_meter.setFormat("%v% Risk")
        self.risk_meter.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                text-align: center;
                color: {THEME["muted"]};
                background: {THEME["panel"]};
                font-weight: 900;
            }}
            QProgressBar::chunk {{
                background-color: rgba(46, 243, 255, 0.35);
                border-radius: 10px;
            }}
        """)
        meter_layout.addWidget(self.risk_meter)
        
        self.risk_level = QLabel("LOW")
        self.risk_level.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px;")
        meter_layout.addWidget(self.risk_level)
        
        layout.addLayout(meter_layout)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)
        
        grid.addWidget(QLabel("HIGH RISK"), 0, 0)
        self.high_risk_label = QLabel("0")
        self.high_risk_label.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900;")
        grid.addWidget(self.high_risk_label, 0, 1)
        
        grid.addWidget(QLabel("UNSAFE"), 1, 0)
        self.unsafe_label = QLabel("0")
        self.unsafe_label.setStyleSheet(f"color: {THEME['red']}; font-weight: 900;")
        grid.addWidget(self.unsafe_label, 1, 1)
        
        grid.addWidget(QLabel("REBOOT"), 2, 0)
        self.reboot_label = QLabel("No")
        self.reboot_label.setStyleSheet(f"color: {THEME['muted']};")
        grid.addWidget(self.reboot_label, 2, 1)
        
        grid.addWidget(QLabel("GAIN"), 3, 0)
        self.gain_label = QLabel("+0")
        self.gain_label.setStyleSheet(f"color: {THEME['green']}; font-weight: 900;")
        grid.addWidget(self.gain_label, 3, 1)
        
        grid.addWidget(QLabel("CONFIDENCE"), 4, 0)
        self.confidence_label = QLabel("100%")
        self.confidence_label.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900;")
        grid.addWidget(self.confidence_label, 4, 1)
        
        layout.addLayout(grid)
        self.setLayout(layout)
    
    def set_color(self, color: str, bg: str):
        """Change the widget's color scheme"""
        # Keep for compatibility; map to the new theme (we use chunk color as accent).
        self.header.setStyleSheet(f"color: {color}; letter-spacing: 1px;")
        self.risk_meter.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                text-align: center;
                color: {THEME["muted"]};
                background: {THEME["panel"]};
                font-weight: 900;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 10px;
            }}
        """)
    
    def update_risk(self, tasks: list, base_score: int):
        self.current_tasks = tasks
        self.base_score = base_score
        
        if not tasks:
            self.hide()
            return
        
        risk_data = LiveRiskCalculator.calculate_risk(tasks, base_score)
        
        self.risk_meter.setValue(int(risk_data["total_risk"]))
        
        level = risk_data["risk_level"]
        if level in ["High", "Critical"]:
            accent = THEME["red"]
        elif level == "Medium":
            accent = THEME["yellow"]
        else:
            accent = THEME["green"]

        self.risk_meter.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                text-align: center;
                color: {THEME["muted"]};
                background: {THEME["panel"]};
                font-weight: 900;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 10px;
            }}
        """)
        self.risk_level.setStyleSheet(f"color: {accent}; font-weight: 900; letter-spacing: 1px;")
        
        self.risk_level.setText(level.upper())
        self.high_risk_label.setText(str(risk_data["high_risk_tasks"]))
        self.unsafe_label.setText(str(risk_data["unsafe_commands"]))
        self.reboot_label.setText("YES" if risk_data["reboot_required"] else "NO")
        self.reboot_label.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900;" if risk_data["reboot_required"] else f"color: {THEME['muted']}; font-weight: 900;")
        self.gain_label.setText(f"+{risk_data['stability_impact']}")
        self.confidence_label.setText(f"{risk_data['confidence']}%")
        
        self.show()


class RiskDeltaWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.hide()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QLabel {{
                color: {THEME["muted"]};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QLabel("BEFORE / AFTER")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 1px;")
        layout.addWidget(header)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)
        
        grid.addWidget(QLabel("Original:"), 0, 0)
        self.original_label = QLabel("--")
        self.original_label.setStyleSheet(f"color: {THEME['yellow']}; font-size: 14pt; font-weight: 900;")
        grid.addWidget(self.original_label, 0, 1)
        
        grid.addWidget(QLabel("Refined:"), 1, 0)
        self.refined_label = QLabel("--")
        self.refined_label.setStyleSheet(f"color: {THEME['cyan']}; font-size: 14pt; font-weight: 900;")
        grid.addWidget(self.refined_label, 1, 1)
        
        grid.addWidget(QLabel("Risk ↓:"), 2, 0)
        self.risk_label = QLabel("--")
        self.risk_label.setStyleSheet(f"color: {THEME['green']}; font-size: 14pt; font-weight: 900;")
        grid.addWidget(self.risk_label, 2, 1)
        
        grid.addWidget(QLabel("Confidence:"), 3, 0)
        self.confidence_label = QLabel("--")
        self.confidence_label.setStyleSheet(f"color: {THEME['yellow']}; font-size: 14pt; font-weight: 900;")
        grid.addWidget(self.confidence_label, 3, 1)
        
        layout.addLayout(grid)
        
        self.improvements = QLabel()
        self.improvements.setWordWrap(True)
        self.improvements.setMinimumWidth(150)
        self.improvements.setStyleSheet(f"color: {THEME['muted']}; padding: 10px; border-top: 1px solid {THEME['border']};")
        layout.addWidget(self.improvements)
        
        self.setLayout(layout)
    
    def update_delta(self, original: int, refined: int, risk_reduction: float,
                    confidence: float, improvements: list):
        self.original_label.setText(f"{original}")
        self.refined_label.setText(f"{refined}")
        self.risk_label.setText(f"{risk_reduction:.1f}%")
        self.confidence_label.setText(f"{confidence:.1f}%")
        
        if improvements:
            self.improvements.setText("✓ " + "\n✓ ".join(improvements[:3]))
        
        self.show()


class ScriptPreviewWidget(QFrame):
    """Widget to preview, export and run PowerShell scripts"""
    
    def __init__(self):
        super().__init__()
        self.current_script = ""
        self.current_tasks = []
        self.current_script_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QPlainTextEdit {{
                background-color: {THEME["panel"]};
                color: {THEME["green"]};
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
            }}
            QCheckBox {{
                color: {THEME["muted"]};
                font-weight: 700;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QHBoxLayout()
        
        title = QLabel("SCRIPT PREVIEW")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 1px;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.safe_mode_cb = QCheckBox("SAFE MODE")
        self.safe_mode_cb.setChecked(True)
        self.safe_mode_cb.stateChanged.connect(self._update_preview)
        header.addWidget(self.safe_mode_cb)
        
        self.save_btn = QPushButton("EXPORT")
        self.save_btn.clicked.connect(self._save_script)
        self.save_btn.setEnabled(False)
        header.addWidget(self.save_btn)
        
        self.run_btn = QPushButton("RUN")
        self.run_btn.clicked.connect(self._run_script)
        self.run_btn.setEnabled(False)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(46, 243, 255, 0.12);
                color: {THEME["cyan"]};
                border: 1px solid rgba(46, 243, 255, 0.45);
                font-weight: 900;
            }}
            QPushButton:hover {{
                background-color: rgba(46, 243, 255, 0.22);
                border: 1px solid rgba(46, 243, 255, 0.70);
            }}
            QPushButton:disabled {{
                background-color: rgba(10, 14, 20, 0.6);
                color: rgba(240,245,255,0.35);
                border: 1px solid {THEME["border"]};
            }}
        """)
        header.addWidget(self.run_btn)
        
        layout.addLayout(header)
        
        self.stats_bar = QFrame()
        self.stats_bar.setFrameStyle(QFrame.Shape.Box)
        self.stats_bar.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: rgba(20, 26, 36, 0.65);
                margin: 0px;
            }}
            QLabel {{
                color: {THEME["muted"]};
                font-weight: 700;
            }}
        """)
        stats_layout = QHBoxLayout(self.stats_bar)
        stats_layout.setContentsMargins(10, 5, 10, 5)
        
        self.tasks_count = QLabel("TASKS: 0")
        self.tasks_count.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900;")
        stats_layout.addWidget(self.tasks_count)
        
        stats_layout.addWidget(QLabel("|"))
        
        self.mode_label = QLabel("SAFE MODE: ON")
        self.mode_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(self.mode_label)
        
        stats_layout.addWidget(QLabel("|"))
        
        self.risk_label = QLabel("RISK: LOW")
        self.risk_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(self.risk_label)
        
        stats_layout.addStretch()
        layout.addWidget(self.stats_bar)
        
        self.safety_warning = QLabel()
        self.safety_warning.setWordWrap(True)
        self.safety_warning.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900; padding: 8px; background: rgba(255, 213, 106, 0.10); border: 1px solid rgba(255, 213, 106, 0.25); border-radius: 10px;")
        self.safety_warning.hide()
        layout.addWidget(self.safety_warning)
        
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(200)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.preview)
        
        self.status_label = QLabel("Select tasks to generate script")
        self.status_label.setStyleSheet(f"color: {THEME['muted']};")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def _update_preview(self):
        if self.current_tasks:
            self.update_script(self.current_tasks)
    
    def update_script(self, tasks: list):
        self.current_tasks = tasks
        
        if not tasks:
            self.preview.clear()
            self.save_btn.setEnabled(False)
            self.run_btn.setEnabled(False)
            self.status_label.setText("No tasks selected")
            self.safety_warning.hide()
            self.tasks_count.setText("TASKS: 0")
            self.current_script_path = None
            return
        
        safe_mode = self.safe_mode_cb.isChecked()
        self.current_script = ScriptGenerator.generate_script(tasks, safe_mode)
        self.preview.setPlainText(self.current_script)
        self.save_btn.setEnabled(True)
        
        self.current_script_path = ScriptRunner.create_temp_script(self.current_script)
        self.run_btn.setEnabled(self.current_script_path is not None)
        
        self.tasks_count.setText(f"TASKS: {len(tasks)}")
        self.mode_label.setText(f"SAFE MODE: {'ON' if safe_mode else 'OFF'}")
        
        high_risk = sum(1 for t in tasks if t.risk == RiskLevel.HIGH or t.risk == RiskLevel.CRITICAL)
        if high_risk > 0:
            risk_text = "High"
            self.risk_label.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900;")
        elif sum(1 for t in tasks if t.risk == RiskLevel.MEDIUM) > 0:
            risk_text = "Medium"
            self.risk_label.setStyleSheet(f"color: {THEME['cyan']}; font-weight: 900;")
        else:
            risk_text = "Low"
            self.risk_label.setStyleSheet(f"color: {THEME['green']}; font-weight: 900;")
        self.risk_label.setText(f"RISK: {risk_text.upper()}")
        
        unsafe_commands = []
        for task in tasks:
            is_safe, risk, reason = CommandSafety.is_command_safe(task.original_command)
            if not is_safe:
                unsafe_commands.append((task.description, risk, reason))
        
        if unsafe_commands and not safe_mode:
            warning_text = "UNSAFE COMMANDS DETECTED\n" + "\n".join([f"- {desc} ({risk})" for desc, risk, _ in unsafe_commands])
            self.safety_warning.setText(warning_text)
            self.safety_warning.show()
            self.status_label.setText(f"{len(tasks)} tasks selected ({len(unsafe_commands)} unsafe) - Enable Safe Mode")
            self.status_label.setStyleSheet(f"color: {THEME['red']}; font-weight: 900;")
        elif unsafe_commands and safe_mode:
            self.safety_warning.setText(f"{len(unsafe_commands)} unsafe commands will be modified for safety")
            self.safety_warning.show()
            self.status_label.setText(f"{len(tasks)} tasks selected (safe mode active)")
            self.status_label.setStyleSheet(f"color: {THEME['muted']};")
        else:
            self.safety_warning.hide()
            self.status_label.setText(f"{len(tasks)} safe tasks selected - Ready to export or run")
            self.status_label.setStyleSheet(f"color: {THEME['muted']};")
    
    def _save_script(self):
        if not self.current_script:
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Z-Engine_{timestamp}.ps1"
        
        file_path = ScriptGenerator.save_script(self.current_script, default_name)
        if file_path:
            self.current_script_path = file_path
            QMessageBox.information(self, "Success", f"Script saved to:\n{file_path}")
    
    def _run_script(self):
        if not self.current_script_path or not os.path.exists(self.current_script_path):
            QMessageBox.critical(self, "Error", "No script available to run. Please generate a script first.")
            return
        
        ScriptRunner.run_script(self.current_script_path, self)


class CleanGraphWidget(QFrame):
    """Simple graph for clean default view"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {THEME["panel"]}, stop:1 #060810);
                margin: 0px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("OPTICORE")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("SYSTEM OPTIMIZATION DASHBOARD")
        subtitle.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        subtitle.setStyleSheet(f"color: {THEME['muted']}; letter-spacing: 1px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        self.score_label = QLabel("--")
        self.score_label.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        self.score_label.setStyleSheet(f"color: {THEME['green']}; padding: 2px;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score_label)
        
        self.setLayout(layout)
    
    def set_score(self, score: int):
        self.score_label.setText(str(score))


class FlowIndicator(QFrame):
    """Shows current stage of the optimization flow"""
    
    def __init__(self):
        super().__init__()
        self.current_stage = 0
        self.stages = ["Scan", "Analyze", "Strategize", "Review", "Refine"]
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 8)
        
        self.indicators = []
        for i, stage in enumerate(self.stages):
            num_label = QLabel(f"{i+1}")
            num_label.setFixedSize(24, 24)
            num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(20, 26, 36, 0.95);
                    color: {THEME["muted"]};
                    border: 1px solid {THEME["border"]};
                    border-radius: 8px;
                    font-weight: 800;
                }}
            """)
            
            name_label = QLabel(stage)
            name_label.setStyleSheet(f"color: {THEME['muted']}; font-weight: 800; letter-spacing: 1px; font-size: 10px;")
            
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(num_label)
            container_layout.addWidget(name_label)
            
            self.indicators.append({"num": num_label, "name": name_label, "container": container})
            
            layout.addWidget(container)
            
            if i < len(self.stages) - 1:
                dot = QLabel("•")
                dot.setStyleSheet(f"color: rgba(240,245,255,0.22); font-size: 12px; font-weight: 900;")
                layout.addWidget(dot)
        
        layout.addStretch()
        self.setLayout(layout)
        self.set_stage(0)
    
    def set_stage(self, stage: int):
        self.current_stage = stage
        for i, ind in enumerate(self.indicators):
            if i < stage:
                ind["num"].setStyleSheet(f"""
                    QLabel {{
                        background: rgba(66, 255, 158, 0.18);
                        color: {THEME["green"]};
                        border: 1px solid rgba(66, 255, 158, 0.55);
                        border-radius: 8px;
                        font-weight: 900;
                    }}
                """)
                ind["name"].setStyleSheet(f"color: {THEME['green']}; font-weight: 900; letter-spacing: 1px; font-size: 10px;")
            elif i == stage:
                ind["num"].setStyleSheet(f"""
                    QLabel {{
                        background: rgba(46, 243, 255, 0.16);
                        color: {THEME["cyan"]};
                        border: 1px solid rgba(46, 243, 255, 0.65);
                        border-radius: 8px;
                        font-weight: 900;
                    }}
                """)
                ind["name"].setStyleSheet(f"color: {THEME['cyan']}; font-weight: 900; letter-spacing: 1px; font-size: 10px;")
            else:
                ind["num"].setStyleSheet(f"""
                    QLabel {{
                        background: rgba(20, 26, 36, 0.95);
                        color: rgba(240,245,255,0.35);
                        border: 1px solid {THEME["border"]};
                        border-radius: 8px;
                        font-weight: 900;
                    }}
                """)
                ind["name"].setStyleSheet("color: rgba(240,245,255,0.28); font-weight: 900; letter-spacing: 1px; font-size: 10px;")


class StrategyComparisonWidget(QFrame):
    """Widget to display and compare different optimization strategies"""
    
    def __init__(self):
        super().__init__()
        self.strategies = []
        self.selected_index = -1
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QFrame#strategy_card {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: rgba(12, 16, 26, 0.92);
                margin: 0px;
                padding: 10px;
            }}
            QFrame#strategy_card:hover {{
                border: 1px solid rgba(46, 243, 255, 0.45);
                background: {THEME["panel"]};
            }}
            QFrame#strategy_card[selected="true"] {{
                border: 1px solid rgba(180, 77, 255, 0.65);
                background: rgba(180, 77, 255, 0.08);
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QLabel("STRATEGY COMPARISON")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 1px;")
        layout.addWidget(header)
        
        subtitle = QLabel("AI evaluated multiple approaches and selected optimal balance")
        subtitle.setStyleSheet(f"color: {THEME['muted']}; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(8)
        layout.addLayout(self.cards_layout)
        
        self.reasoning_label = QLabel()
        self.reasoning_label.setWordWrap(True)
        self.reasoning_label.setMinimumWidth(200)
        self.reasoning_label.setStyleSheet(f"color: {THEME['muted']}; padding: 10px; border-top: 1px solid {THEME['border']}; margin-top: 10px;")
        layout.addWidget(self.reasoning_label)
        
        self.setLayout(layout)
    
    def update_strategies(self, strategies: list, selected_index: int, reasoning: str):
        self.strategies = strategies
        self.selected_index = selected_index
        
        self._clear_layout(self.cards_layout)
        
        for i, strategy in enumerate(strategies):
            card = self._create_strategy_card(strategy, i == selected_index)
            self.cards_layout.addWidget(card)
        
        self.reasoning_label.setText(f"AI REASONING: {reasoning}")
        self.show()
    
    def _create_strategy_card(self, strategy, is_selected):
        card = QFrame()
        card.setObjectName("strategy_card")
        card.setProperty("selected", is_selected)
        card.setFrameStyle(QFrame.Shape.Box)
        
        if is_selected:
            card.setStyleSheet("""
                QFrame {
                    border: 1px solid rgba(180, 77, 255, 0.65);
                    border-radius: 10px;
                    background: rgba(180, 77, 255, 0.08);
                    margin: 0px;
                    padding: 10px;
                }
            """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        name = QLabel(strategy.name)
        name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {THEME['text']};")
        header_layout.addWidget(name)
        
        if is_selected:
            selected_badge = QLabel("SELECTED")
            selected_badge.setStyleSheet("""
                background: rgba(180, 77, 255, 0.18);
                color: #b44dff;
                font-weight: 900;
                padding: 3px 10px;
                border-radius: 10px;
            """)
            header_layout.addWidget(selected_badge)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        stats_layout = QGridLayout()
        stats_layout.setHorizontalSpacing(15)
        
        gain_label = QLabel("Gain:")
        gain_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(gain_label, 0, 0)
        
        gain_value = QLabel(f"+{strategy.gain}")
        gain_value.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        gain_value.setStyleSheet(f"color: {THEME['green']};")
        stats_layout.addWidget(gain_value, 0, 1)
        
        risk_label = QLabel("Risk:")
        risk_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(risk_label, 0, 2)
        
        risk_color = {
            "Very Low": THEME["green"], "Low": THEME["green"], "Medium": THEME["yellow"],
            "High": THEME["red"], "Critical": THEME["red"]
        }.get(strategy.risk_level, THEME["text"])
        
        risk_value = QLabel(strategy.risk_level)
        risk_value.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        risk_value.setStyleSheet(f"color: {risk_color};")
        stats_layout.addWidget(risk_value, 0, 3)
        
        confidence_label = QLabel("Confidence:")
        confidence_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(confidence_label, 1, 0)
        
        confidence_value = QLabel(f"{strategy.confidence}%")
        confidence_value.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        confidence_value.setStyleSheet(f"color: {THEME['cyan']};")
        stats_layout.addWidget(confidence_value, 1, 1)
        
        ratio_label = QLabel("Gain/Risk:")
        ratio_label.setStyleSheet(f"color: {THEME['muted']};")
        stats_layout.addWidget(ratio_label, 1, 2)
        
        ratio_value = QLabel(f"{strategy.stability_risk_ratio:.2f}")
        ratio_value.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        ratio_value.setStyleSheet(f"color: {THEME['magenta']};")
        stats_layout.addWidget(ratio_value, 1, 3)
        
        stats_layout.setColumnStretch(4, 1)
        layout.addLayout(stats_layout)
        
        if strategy.description:
            desc = QLabel(strategy.description)
            desc.setWordWrap(True)
            desc.setMinimumWidth(200)
            desc.setStyleSheet(f"color: {THEME['muted']}; padding: 5px;")
            layout.addWidget(desc)
        
        card.setLayout(layout)
        return card
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ScriptDiffWidget(QFrame):
    """Widget to show differences between original and refined plans"""
    
    def __init__(self):
        super().__init__()
        self.diff_data = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QLabel("PLAN COMPARISON")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {THEME['cyan']}; letter-spacing: 1px;")
        layout.addWidget(header)
        
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        self.stats_label.setMinimumWidth(200)
        self.stats_label.setStyleSheet(f"color: {THEME['muted']}; padding: 8px; background: rgba(20, 26, 36, 0.65); border: 1px solid {THEME['border']}; border-radius: 10px;")
        layout.addWidget(self.stats_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(150)
        scroll.setStyleSheet(f"border: 1px solid {THEME['border']}; border-radius: 10px;")
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(8)
        scroll.setWidget(self.content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
    
    def update_diff(self, original_tasks: list, refined_tasks: list):
        self.stats_label.setText(f"ORIGINAL: {len(original_tasks)} tasks   |   REFINED: {len(refined_tasks)} tasks")
        self.show()


class ThreeBarChartWidget(QFrame):
    """Widget showing before vs after comparison with 3 bars"""
    
    def __init__(self):
        super().__init__()
        self.current_score = None
        self.original_projected = None
        self.refined_projected = None
        self.live_projected = None
        self._refresh_attempts = 0
        self._max_refresh_attempts = 10
        self.setup_ui()
        self.hide()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME["border"]};
                border-radius: 10px;
                background: {THEME["panel2"]};
                margin: 0px;
            }}
            QLabel {{
                color: {THEME["muted"]};
                font-weight: 700;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QLabel("STABILITY IMPROVEMENT")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {THEME['green']}; letter-spacing: 1px;")
        layout.addWidget(header)
        
        self.subtitle = QLabel("AI reasoning improves system stability")
        self.subtitle.setStyleSheet(f"color: {THEME['muted']}; margin-bottom: 10px;")
        layout.addWidget(self.subtitle)
        
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setSpacing(15)
        
        # Bar 1 - Current Score
        bar1_layout = QHBoxLayout()
        bar1_layout.addWidget(QLabel("Current"), 1)
        self.bar1_container = QWidget()
        self.bar1_container.setMinimumHeight(25)
        self.bar1_container.setStyleSheet(f"background: rgba(20, 26, 36, 0.75); border: 1px solid {THEME['border']}; border-radius: 10px;")
        bar1_container_layout = QHBoxLayout(self.bar1_container)
        bar1_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bar1 = QFrame()
        self.bar1.setFixedHeight(25)
        self.bar1.setStyleSheet(f"background: rgba(66, 255, 158, 0.65); border-radius: 10px;")
        bar1_container_layout.addWidget(self.bar1)
        bar1_container_layout.addStretch()
        self.bar1_label = QLabel("0")
        self.bar1_label.setFixedWidth(40)
        self.bar1_label.setStyleSheet(f"color: {THEME['text']}; font-weight: 900;")
        bar1_layout.addWidget(self.bar1_container, 8)
        bar1_layout.addWidget(self.bar1_label, 1)
        chart_layout.addLayout(bar1_layout)
        
        # Bar 2 - Original Plan
        bar2_layout = QHBoxLayout()
        bar2_layout.addWidget(QLabel("AI Plan"), 1)
        self.bar2_container = QWidget()
        self.bar2_container.setMinimumHeight(25)
        self.bar2_container.setStyleSheet(f"background: rgba(20, 26, 36, 0.75); border: 1px solid {THEME['border']}; border-radius: 10px;")
        bar2_container_layout = QHBoxLayout(self.bar2_container)
        bar2_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bar2 = QFrame()
        self.bar2.setFixedHeight(25)
        self.bar2.setStyleSheet(f"background: rgba(255, 213, 106, 0.60); border-radius: 10px;")
        bar2_container_layout.addWidget(self.bar2)
        bar2_container_layout.addStretch()
        self.bar2_label = QLabel("0")
        self.bar2_label.setFixedWidth(40)
        self.bar2_label.setStyleSheet(f"color: {THEME['text']}; font-weight: 900;")
        bar2_layout.addWidget(self.bar2_container, 8)
        bar2_layout.addWidget(self.bar2_label, 1)
        chart_layout.addLayout(bar2_layout)
        
        # Bar 3 - Refined Plan
        bar3_layout = QHBoxLayout()
        bar3_layout.addWidget(QLabel("Refined"), 1)
        self.bar3_container = QWidget()
        self.bar3_container.setMinimumHeight(25)
        self.bar3_container.setStyleSheet(f"background: rgba(20, 26, 36, 0.75); border: 1px solid {THEME['border']}; border-radius: 10px;")
        bar3_container_layout = QHBoxLayout(self.bar3_container)
        bar3_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bar3 = QFrame()
        self.bar3.setFixedHeight(25)
        self.bar3.setStyleSheet(f"background: rgba(46, 243, 255, 0.55); border-radius: 10px;")
        bar3_container_layout.addWidget(self.bar3)
        bar3_container_layout.addStretch()
        self.bar3_label = QLabel("0")
        self.bar3_label.setFixedWidth(40)
        self.bar3_label.setStyleSheet(f"color: {THEME['text']}; font-weight: 900;")
        bar3_layout.addWidget(self.bar3_container, 8)
        bar3_layout.addWidget(self.bar3_label, 1)
        chart_layout.addLayout(bar3_layout)
        
        # Bar 4 - Live Selection
        bar4_layout = QHBoxLayout()
        bar4_layout.addWidget(QLabel("Selection"), 1)
        self.bar4_container = QWidget()
        self.bar4_container.setMinimumHeight(25)
        self.bar4_container.setStyleSheet(f"background: rgba(20, 26, 36, 0.75); border: 1px solid {THEME['border']}; border-radius: 10px;")
        bar4_container_layout = QHBoxLayout(self.bar4_container)
        bar4_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bar4 = QFrame()
        self.bar4.setFixedHeight(25)
        self.bar4.setStyleSheet(f"background: rgba(180, 77, 255, 0.55); border-radius: 10px;")
        bar4_container_layout.addWidget(self.bar4)
        bar4_container_layout.addStretch()
        self.bar4_label = QLabel("0")
        self.bar4_label.setFixedWidth(40)
        self.bar4_label.setStyleSheet(f"color: {THEME['text']}; font-weight: 900;")
        bar4_layout.addWidget(self.bar4_container, 8)
        bar4_layout.addWidget(self.bar4_label, 1)
        chart_layout.addLayout(bar4_layout)
        self.bar4_container.hide()
        
        self.gain_label = QLabel()
        self.gain_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gain_label.setStyleSheet(f"color: {THEME['green']}; font-weight: 900; padding: 2px; letter-spacing: 1px;")
        chart_layout.addWidget(self.gain_label)
        
        chart_layout.addStretch()
        layout.addWidget(chart_widget)
        self.setLayout(layout)
    
    def update_scores(self, current: int, original_projected: int = None,
                     refined_projected: int = None, live_projected: int = None):
        self.current_score = current
        self.original_projected = original_projected
        self.refined_projected = refined_projected
        self.live_projected = live_projected
        self._refresh_attempts = 0
        
        if current:
            self.bar1_label.setText(str(current))
        if original_projected:
            self.bar2_label.setText(str(original_projected))
        if refined_projected:
            self.bar3_label.setText(str(refined_projected))
        
        if live_projected and live_projected not in [current, original_projected, refined_projected]:
            self.bar4_container.show()
            self.bar4_label.setText(str(live_projected))
        else:
            self.bar4_container.hide()
        
        if current and refined_projected:
            gain = refined_projected - current
            if gain > 0:
                self.gain_label.setText(f"+{gain} points")
                self.gain_label.setStyleSheet(f"color: {THEME['green']}; font-weight: 900; padding: 2px; letter-spacing: 1px;")
            else:
                self.gain_label.setText("")
        
        self.show()
        self._refresh_bars()
    
    def _refresh_bars(self):
        w = self.bar1_container.width()
        if w <= 0:
            self._refresh_attempts += 1
            if self._refresh_attempts < self._max_refresh_attempts:
                QTimer.singleShot(100, self._refresh_bars)
            return
        
        self._refresh_attempts = 0
        
        if self.current_score:
            self.bar1.setFixedWidth(int(w * self.current_score / 100))
        
        w = self.bar2_container.width()
        if w > 0 and self.original_projected:
            self.bar2.setFixedWidth(int(w * self.original_projected / 100))
        
        w = self.bar3_container.width()
        if w > 0 and self.refined_projected:
            self.bar3.setFixedWidth(int(w * self.refined_projected / 100))
        
        if self.bar4_container.isVisible():
            w = self.bar4_container.width()
            if w > 0 and self.live_projected:
                self.bar4.setFixedWidth(int(w * self.live_projected / 100))
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_bars()
    
    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_bars()

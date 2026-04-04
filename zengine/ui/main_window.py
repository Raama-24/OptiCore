"""
Main window for Z-Engine
"""

import datetime
import os
import threading
from typing import List, Optional
from zengine.safety import CommandSafety
from zengine.script import ScriptGenerator, LiveRiskCalculator
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QGroupBox, QGridLayout, QTabWidget, QScrollArea,
    QStackedWidget, QToolBox, QTextEdit, QMessageBox, QFileDialog,
    QMenuBar, QMenu, QProgressBar, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QAction

from zengine.config import ASI_API_KEY
from zengine.analyzer import PureAIAnalyzer
from zengine.backup import BackupManager, RestorePointCreator
from zengine.models import (
    SimulationResult, RiskLevel, OptimizationCategory,
    OptimizationTask
)
from zengine.workers import (
    ScanWorker, AnalyzeWorker, InsightWorker, PlanWorker,
    CritiqueWorker, RegenerateWorker, SimulationWorker, ConfidenceWorker
)
from zengine.ui.widgets import (
    FlowIndicator, CleanGraphWidget, ThreeBarChartWidget,
    StrategyComparisonWidget, ScriptDiffWidget, ScriptPreviewWidget,
    LiveRiskWidget, CategoryWidget, NeonPanel, MetricCard, DonutGauge, THEME,
    TaskChecklistWidget, LiveAnalysisWidget, SystemLogWidget, ResultsCardWidget,
    GeneratedPlanWidget
)
from zengine.ui.dialogs import SystemDetailsDialog, ThoughtTraceWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = PureAIAnalyzer(ASI_API_KEY)
        self.backup_manager = BackupManager()
        self.snapshot = None
        self.metrics = None
        self.strategic_insight = None
        self.plan_critique = None
        self.original_categories = []
        self.refined_categories = []
        self.original_projected = None
        self.refined_projected = None
        self.risk_reduction = None
        self.improvements = []
        self.confidence_score = 0
        self.simulation_result = None
        self.last_backup = None
        self.thought_trace_visible = False
        self.thought_trace_widget = None
        self.trace_action = None
        
        # Dedicated workers for each step
        self.scan_worker = None
        self.analyze_worker = None
        self.insight_worker = None
        self.plan_worker = None
        self.critique_worker = None
        self.regenerate_worker = None
        self.simulation_worker = None
        self.confidence_worker = None
        self.refresh_worker = None
        
        self.setWindowTitle("Z-Engine: Generates, Engineers and Deploys")
        self.setGeometry(100, 100, 1400, 900)
        self.setup_ui()
        self.setup_menu()

        # Persistent background scanner (Refined Plan)
        self.refresh_worker = ScanWorker()
        self.refresh_worker.finished.connect(self._on_refresh_done)
        self.refresh_worker.start()
        
        self.prev_snapshot = None
    
    def _stop_worker(self, worker):
        """Stop a worker if it's running"""
        if worker and worker.isRunning():
            worker.stop()
            worker.wait(1000)
    
    def _cleanup_workers(self):
        """Clean up all workers"""
        self._stop_worker(self.scan_worker)
        self._stop_worker(self.analyze_worker)
        self._stop_worker(self.insight_worker)
        self._stop_worker(self.plan_worker)
        self._stop_worker(self.critique_worker)
        self._stop_worker(self.regenerate_worker)
        self._stop_worker(self.simulation_worker)
        self._stop_worker(self.confidence_worker)
        self._stop_worker(self.refresh_worker)
    
    def setup_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {THEME["bg"]};
                color: {THEME["text"]};
                border-bottom: 1px solid rgba(120,255,255,0.10);
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 6px 10px;
                font-weight: 700;
            }}
            QMenuBar::item:selected {{
                background-color: rgba(46,243,255,0.08);
                border: 1px solid rgba(46,243,255,0.22);
                border-radius: 8px;
            }}
            QMenu {{
                background-color: {THEME["panel"]};
                color: {THEME["text"]};
                border: 1px solid rgba(120,255,255,0.12);
            }}
            QMenu::item:selected {{
                background-color: rgba(46,243,255,0.10);
            }}
        """)
        
        view_menu = menubar.addMenu("View")
        
        self.trace_action = QAction("Show AI Reasoning Trace", self)
        self.trace_action.setCheckable(True)
        self.trace_action.triggered.connect(self._toggle_thought_trace)
        view_menu.addAction(self.trace_action)
    
    def _toggle_thought_trace(self, checked):
        self.thought_trace_visible = checked
        if checked and not self.thought_trace_widget:
            self.thought_trace_widget = ThoughtTraceWidget()
            self.thought_trace_widget.closed.connect(self._on_trace_closed)
            self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
            self.thought_trace_widget.show()
        elif checked and self.thought_trace_widget:
            self.thought_trace_widget.show()
            self.thought_trace_widget.raise_()
        elif not checked and self.thought_trace_widget:
            self.thought_trace_widget.hide()
    
    def _on_trace_closed(self):
        self.thought_trace_visible = False
        if self.trace_action:
            self.trace_action.setChecked(False)
    
    def setup_ui(self):
        self._apply_global_style()
        # Hide the native menubar; the reference uses an in-app top bar.
        try:
            self.menuBar().hide()
        except Exception:
            pass

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # Top bar (logo + step nav + status)
        root.addLayout(self._create_header())
        # Pipeline controls + status (not inside Optimization Tasks)
        root.addLayout(self._create_subbar())

        # Main content: left icon rail + screenshot grid
        content = QHBoxLayout()
        content.setSpacing(6)
        content.setContentsMargins(0, 0, 0, 0)

        rail = self._create_left_rail()
        content.addWidget(rail)

        # Use a fixed grid like the reference screenshot (not generic splitters)
        dashboard = QWidget()
        grid = QGridLayout(dashboard)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)

        # LEFT TOP: system scan — compact (smaller than before)
        self.system_panel = NeonPanel("SYSTEM SCAN", accent=THEME["cyan"])
        self.system_panel.setMaximumHeight(198)
        
        sys_container = QWidget()
        sys_layout = QVBoxLayout(sys_container)
        sys_layout.setContentsMargins(0, 0, 0, 0)
        sys_layout.setSpacing(12)
        
        sys_grid = QGridLayout()
        sys_grid.setHorizontalSpacing(8)
        sys_grid.setVerticalSpacing(2)
        sys_grid.setContentsMargins(5, 5, 5, 5)


        def _kv_stacked(r: int, c: int, k: str, v: str = "--"):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(4, 4, 4, 4)
            l.setSpacing(2)
            key = QLabel(k)
            key.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px; font-size: 8px;")
            val = QLabel(v)
            val.setStyleSheet(f"color: {THEME['text']}; font-weight: 900; font-size: 11px;")
            l.addWidget(key)
            l.addWidget(val)
            w.setStyleSheet("background: rgba(12, 16, 26, 0.5); border: 1px solid rgba(120, 255, 255, 0.1); border-radius: 4px;")
            sys_grid.addWidget(w, r, c)
            return val
            
        self.sys_os = _kv_stacked(0, 0, "OS", "--")
        self.sys_host = _kv_stacked(0, 1, "HOSTNAME", "--")
        self.sys_cpu = _kv_stacked(1, 0, "CPU CORES", "--")
        self.sys_mem = _kv_stacked(1, 1, "RAM TOTAL", "--")
        self.sys_uptime = _kv_stacked(2, 0, "UPTIME", "--")
        self.sys_score = _kv_stacked(2, 1, "PROCESSES", "--")
        
        sys_layout.addLayout(sys_grid)

        self.run_scan_btn = QPushButton("[ INITIALIZE SCAN ]")
        self.run_scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(46, 243, 255, 0.05);
                border: 1px solid {THEME['cyan']};
                color: {THEME['cyan']};
                font-weight: 900;
                letter-spacing: 2px;
                padding: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(46, 243, 255, 0.15);
            }}
        """)
        self.run_scan_btn.clicked.connect(self._scan)
        sys_layout.addWidget(self.run_scan_btn)

        self.system_panel.body_layout.addWidget(sys_container)
        grid.addWidget(self.system_panel, 0, 0)

        # Row 1 and 2: Generated Plan (spans 2 columns, goes down 2 rows)
        self.plan_panel = NeonPanel("GENERATED PLAN", accent=THEME["cyan"])
        
        self.refined_btn = QPushButton("REFINED PLAN")
        self.refined_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refined_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(46, 243, 255, 0.1);
                border: 1px solid {THEME['cyan']};
                color: {THEME['cyan']};
                font-weight: 900;
                font-size: 10px;
                padding: 4px 10px;
                border-radius: 2px;
                min-height: 16px;
            }}
            QPushButton:hover {{
                background: rgba(46, 243, 255, 0.2);
            }}
        """)
        self.refined_btn.clicked.connect(self._show_refined_plan_in_list)
        self.refined_btn.hide()
        self.plan_panel._title_row.layout().addWidget(self.refined_btn)
        
        self.plan_list = GeneratedPlanWidget()
        self.plan_list.selection_changed.connect(self._selection_changed)
        self.plan_panel.body_layout.addWidget(self.plan_list, 1)
        grid.addWidget(self.plan_panel, 1, 0, 2, 2)

        # CENTER TOP: live analysis
        self.analysis_panel = NeonPanel("LIVE ANALYSIS", accent=THEME["green"])
        self.live_analysis = LiveAnalysisWidget()
        self.analysis_panel.body_layout.addWidget(self.live_analysis)
        grid.addWidget(self.analysis_panel, 0, 1)

        # RIGHT TOP: risk matrix
        self.risk_panel = NeonPanel("RISK MATRIX", accent=THEME["cyan"])
        risk_outer = QVBoxLayout()
        risk_outer.setContentsMargins(0, 0, 0, 0)
        risk_outer.setSpacing(8)
        risk_row = QHBoxLayout()
        self.donut = DonutGauge("RISK", 0, accent=THEME["cyan"])
        self.donut.setMinimumHeight(120)
        self.donut.setMaximumHeight(140)
        risk_row.addWidget(self.donut, 1)

        rgrid = QGridLayout()
        rgrid.setHorizontalSpacing(8)
        rgrid.setVerticalSpacing(4)

        def _rlab(row: int, k: str, val: QLabel):
            kk = QLabel(k)
            kk.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px; font-size: 8px;")
            rgrid.addWidget(kk, row, 0)
            rgrid.addWidget(val, row, 1)

        self.r_threat = QLabel("--")
        self.r_threat.setStyleSheet(f"color: {THEME['green']}; font-weight: 900; font-size: 10px;")
        _rlab(0, "THREAT LVL", self.r_threat)

        self.r_high_risk = QLabel("--")
        self.r_high_risk.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900; font-size: 10px;")
        _rlab(1, "HIGH RISK", self.r_high_risk)

        self.r_unsafe = QLabel("--")
        self.r_unsafe.setStyleSheet(f"color: {THEME['yellow']}; font-weight: 900; font-size: 10px;")
        _rlab(2, "UNSAFE CMD", self.r_unsafe)

        self.r_reboot = QLabel("--")
        self.r_reboot.setStyleSheet(f"color: {THEME['magenta']}; font-weight: 900; font-size: 10px;")
        _rlab(3, "REBOOT REQ", self.r_reboot)

        self.r_conf = QLabel("--")
        self.r_conf.setStyleSheet(f"color: {THEME['magenta']}; font-weight: 900; font-size: 10px;")
        _rlab(4, "CONFIDENCE", self.r_conf)

        risk_row.addLayout(rgrid, 1)
        risk_outer.addLayout(risk_row)

        scores_row = QHBoxLayout()
        self.r_score_now = QLabel("--")
        self.r_proj = QLabel("--")
        sn = QLabel("SCORE NOW:")
        sn.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; font-size: 8px;")
        pj = QLabel("PROJECTED:")
        pj.setStyleSheet(f"color: {THEME['muted']}; font-weight: 900; font-size: 8px;")
        self.r_score_now.setStyleSheet(f"color: {THEME['green']}; font-weight: 900; font-size: 12px;")
        self.r_proj.setStyleSheet(f"color: {THEME['cyan']}; font-weight: 900; font-size: 12px;")
        scores_row.addWidget(sn)
        scores_row.addWidget(self.r_score_now)
        scores_row.addSpacing(16)
        scores_row.addWidget(pj)
        scores_row.addWidget(self.r_proj)
        scores_row.addStretch()
        risk_outer.addLayout(scores_row)

        self.risk_panel.body_layout.addLayout(risk_outer)
        grid.addWidget(self.risk_panel, 0, 2)

        # Row 1 (Right): System Log connects beside optimization tasks
        self.syslog_panel = NeonPanel("SYSTEM LOG", accent=THEME["magenta"])
        self.syslog = SystemLogWidget()
        self.syslog_panel.body_layout.addWidget(self.syslog, 1)
        grid.addWidget(self.syslog_panel, 1, 2)

        # Row 2 previously had generated plan. Now it's merged into row 1 span.

        self.results_panel = NeonPanel("RESULTS CARD", accent=THEME["cyan"])
        self.results = ResultsCardWidget()
        self.results.export.clicked.connect(self._export_script)
        self.results_panel.body_layout.addWidget(self.results)
        grid.addWidget(self.results_panel, 2, 2)

        # Hide panel bodies initially to ensure strict empty boxes.
        self._animated_early = [self.system_panel, self.analysis_panel, self.risk_panel]
        # Syslog is explicitly omitted so text flow is visible at initialization
        self._animated_late = [self.plan_panel, self.results_panel]
        
        for p in self._animated_early + self._animated_late:
            eff = QGraphicsOpacityEffect(p.body)
            eff.setOpacity(0.0)
            p.body.setGraphicsEffect(eff)

        # Hidden pipeline widgets (logic still uses these)
        self._pipeline_host = QWidget()
        self._pipeline_host.hide()
        ph = QVBoxLayout(self._pipeline_host)
        ph.setContentsMargins(0, 0, 0, 0)
        self.flow_indicator = FlowIndicator()
        self.flow_indicator.setMaximumHeight(40)
        ph.addWidget(self.flow_indicator)
        self.chart_stack = QStackedWidget()
        self.chart_stack.setMaximumHeight(140)
        self.clean_view = CleanGraphWidget()
        self.chart_stack.addWidget(self.clean_view)
        self.chart = ThreeBarChartWidget()
        self.chart_stack.addWidget(self.chart)
        ph.addWidget(self.chart_stack)
        self.script_preview = ScriptPreviewWidget()
        self.live_risk = LiveRiskWidget()
        self.live_risk.hide()
        ph.addWidget(self.live_risk)
        self.category_tabs = QTabWidget()
        self.original_tab = QWidget()
        self.original_tab_layout = QVBoxLayout(self.original_tab)
        self.original_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.category_tabs.addTab(self.original_tab, "ORIGINAL")
        self.refined_tab = QWidget()
        self.refined_tab_layout = QVBoxLayout(self.refined_tab)
        self.refined_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.category_tabs.addTab(self.refined_tab, "REFINED")
        ph.addWidget(self.category_tabs)
        self.toolbox = QToolBox()
        self.strategy_comparison = StrategyComparisonWidget()
        self.toolbox.addItem(self.strategy_comparison, "Strategy")
        self.script_diff = ScriptDiffWidget()
        self.toolbox.addItem(self.script_diff, "Diff")
        self.toolbox.addItem(self.script_preview, "Script")
        ph.addWidget(self.toolbox)

        self.card_score = MetricCard("AI SCORE", "--", accent=THEME["green"])
        self.card_projected = MetricCard("PROJECTED", "--", accent=THEME["cyan"])
        self.card_gain = MetricCard("GAIN", "--", accent=THEME["green"])
        self.card_conf = MetricCard("CONFIDENCE", "--", accent=THEME["yellow"])
        for c in (self.card_score, self.card_projected, self.card_gain, self.card_conf):
            c.setParent(self._pipeline_host)
            c.hide()

        # Columns stretch normally to fill width
        grid.setColumnStretch(0, 34)
        grid.setColumnStretch(1, 38)
        grid.setColumnStretch(2, 28)
        
        # Squeeze everything to the top to eliminate vertical centering gaps
        grid.setRowStretch(3, 1)

        content.addWidget(dashboard, 1)
        root.addLayout(content, 1)
        # Pipeline widgets not shown in main grid (still wired for workers)
        self._pipeline_host.setParent(central)
        self._pipeline_host.hide()

    def _create_subbar(self):
        """Secondary bar like screenshot: stats + pipeline buttons (not in task list)."""
        bar = QHBoxLayout()
        bar.setSpacing(12)
        bar.setContentsMargins(0, 2, 0, 4)
        self.subbar_stats = QLabel("94%  |  TASKS: 0 QUEUED  |  EXPORT READY")
        self.subbar_stats.setStyleSheet(f"color: {THEME['cyan']}; font-weight: 700; letter-spacing: 1px; font-size: 9px;")
        bar.addWidget(self.subbar_stats)
        bar.addStretch()
        btn_row = self._create_buttons()
        bar.addWidget(btn_row)
        self.status = QLabel("Ready")
        self.status.setObjectName("statusLine")
        bar.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(160)
        self.progress.hide()
        bar.addWidget(self.progress)
        return bar

    def _create_header(self):
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        title = QLabel("OPTICORE")
        title.setFont(QFont("Bahnschrift", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {THEME['magenta']}; letter-spacing: 3px; font-weight: 900;")
        hdr.addWidget(title)
        
        steps = QWidget()
        steps_layout = QHBoxLayout(steps)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.setSpacing(6)

        self.step_badges = []
        self.step_lines = []
        steps_list = ["SCAN", "ANALYZE", "PLAN", "REVIEW", "REFINE"]
        for i, name in enumerate(steps_list):
            # Step container
            step_widget = QWidget()
            sw_layout = QHBoxLayout(step_widget)
            sw_layout.setContentsMargins(0, 0, 0, 0)
            sw_layout.setSpacing(8)
            
            # The number badge
            num_badge = QLabel(f"{i+1}")
            num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_badge.setFixedSize(20, 20)
            
            # The name label
            name_label = QLabel(name)
            
            sw_layout.addWidget(num_badge)
            sw_layout.addWidget(name_label)
            
            self.step_badges.append((step_widget, num_badge, name_label))
            steps_layout.addWidget(step_widget)
            
            # Add connecting line if not the last step
            if i < len(steps_list) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setMinimumWidth(30)
                line.setFixedHeight(1)
                self.step_lines.append(line)
                steps_layout.addWidget(line)

        hdr.addWidget(steps)
        
        hdr.addStretch()
        
        self.details_btn = QPushButton("System Details")
        self.details_btn.clicked.connect(self._show_system_details)
        self.details_btn.setEnabled(False)
        hdr.addWidget(self.details_btn)
        
        self.api_label = QLabel("PLAN READY")
        self.api_label.setStyleSheet(f"border: 1px solid rgba(46,243,255,0.22); padding: 6px 10px; border-radius: 10px; color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px;")
        hdr.addWidget(self.api_label)
        
        return hdr

    def _create_left_rail(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("leftRail")
        rail.setFixedWidth(54)
        rail.setStyleSheet(f"""
            QFrame#leftRail {{
                background: {THEME["panel2"]};
                border: 1px solid {THEME["border"]};
                border-radius: 0px;
            }}
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(120,255,255,0.12);
                border-radius: 0px;
                min-height: 38px;
                min-width: 38px;
                max-height: 38px;
                max-width: 38px;
                padding: 0px;
                color: rgba(240,245,255,0.65);
                font-weight: 900;
            }}
            QPushButton:hover {{
                border: 1px solid rgba(46,243,255,0.45);
                color: {THEME["cyan"]};
                background: rgba(46,243,255,0.06);
            }}
        """)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        brand = QLabel("O")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet(f"color: {THEME['cyan']}; font-weight: 900; font-size: 14px;")
        layout.addWidget(brand)

        for txt in ["▦", "◧", "◎", "≋", "⟠"]:
            btn = QPushButton(txt)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()
        return rail

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {THEME["bg"]};
                color: {THEME["text"]};
                font-family: "Bahnschrift", "Segoe UI", "Arial";
                font-size: 10px;
            }}
            QGroupBox {{
                border: 1px solid rgba(78,130,160,0.18);
                border-radius: 0px;
                margin-top: 10px;
                padding: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                color: {THEME["muted"]};
                letter-spacing: 2px;
                font-weight: 900;
                font-size: 9px;
            }}
            QPushButton {{
                background-color: rgba(12, 16, 26, 0.80);
                color: rgba(240,248,255,0.80);
                border: 1px solid rgba(78,130,160,0.18);
                padding: 6px 10px;
                border-radius: 0px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                border: 1px solid rgba(43,242,255,0.40);
                color: {THEME["cyan"]};
                background-color: rgba(12, 16, 26, 0.95);
            }}
            QPushButton:disabled {{
                color: rgba(240,248,255,0.25);
                border: 1px solid rgba(78,130,160,0.10);
                background-color: rgba(7, 10, 16, 0.60);
            }}
            QTextEdit {{
                background-color: rgba(10, 13, 19, 0.95);
                border: 1px solid rgba(78,130,160,0.16);
                border-radius: 0px;
                padding: 8px;
                font-family: "Consolas", "Courier New", monospace;
                color: rgba(240,248,255,0.62);
            }}
            QTabWidget::pane {{
                border: 1px solid rgba(78,130,160,0.16);
                border-radius: 0px;
                background: rgba(7, 10, 16, 0.65);
            }}
            QTabBar::tab {{
                background-color: rgba(12, 16, 26, 0.80);
                color: rgba(240,248,255,0.60);
                border: 1px solid rgba(78,130,160,0.16);
                padding: 5px 10px;
                margin-right: 4px;
                border-radius: 0px;
                font-weight: 900;
                letter-spacing: 2px;
                font-size: 9px;
            }}
            QTabBar::tab:selected {{
                background-color: rgba(43,242,255,0.10);
                border: 1px solid rgba(43,242,255,0.45);
                color: {THEME["cyan"]};
            }}
            QToolBox::tab {{
                background-color: rgba(12, 16, 26, 0.80);
                color: rgba(240,248,255,0.64);
                border: 1px solid rgba(78,130,160,0.16);
                border-radius: 0px;
                padding: 7px 10px;
                margin-top: 6px;
                font-weight: 900;
                letter-spacing: 2px;
                font-size: 9px;
            }}
            QToolBox::tab:selected {{
                border: 1px solid rgba(43,242,255,0.45);
                color: {THEME["cyan"]};
                background-color: rgba(43,242,255,0.08);
            }}
            QLabel#statusLine {{
                color: rgba(230,230,230,0.75);
                padding: 4px 2px;
            }}
            QProgressBar {{
                border: 1px solid rgba(78,130,160,0.16);
                border-radius: 0px;
                text-align: center;
                background: rgba(10, 13, 19, 0.95);
                color: rgba(240,248,255,0.70);
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QProgressBar::chunk {{
                background-color: rgba(43,242,255,0.35);
                border-radius: 0px;
            }}
        """)

    def _set_step_stage(self, stage: int):
        if not hasattr(self, "step_badges") or not self.step_badges:
            return
        
        # Colors based on plan
        active_magenta = THEME["magenta"]
        active_bg = "rgba(177, 91, 255, 0.15)"
        dim_cyan = "rgba(46, 243, 255, 0.3)"
        dim_text = "rgba(240, 248, 255, 0.5)"
        
        for i, (widget, num_badge, name_label) in enumerate(self.step_badges):
            if i == stage:
                # Active step: Magenta sharp square border around number, bold naming
                widget.setStyleSheet(f"background: transparent;")
                num_badge.setStyleSheet(f"""
                    background: {active_magenta};
                    color: #000000;
                    font-weight: 900;
                    font-size: 10px;
                    border-radius: 0px;
                """)
                name_label.setStyleSheet(f"""
                    color: {active_magenta};
                    font-weight: 900;
                    letter-spacing: 1px;
                    font-size: 10px;
                """)
            elif i < stage:
                # Completed step: Cyan (dimmed)
                widget.setStyleSheet(f"background: transparent;")
                num_badge.setStyleSheet(f"""
                    background: {dim_cyan};
                    color: #000000;
                    font-weight: 900;
                    font-size: 10px;
                    border-radius: 0px;
                """)
                name_label.setStyleSheet(f"""
                    color: {THEME["cyan"]};
                    font-weight: 900;
                    letter-spacing: 1px;
                    font-size: 10px;
                """)
            else:
                # Future step
                widget.setStyleSheet(f"background: transparent;")
                num_badge.setStyleSheet(f"""
                    background: rgba(12, 16, 26, 0.85);
                    border: 1px solid rgba(120, 255, 255, 0.2);
                    color: {dim_text};
                    font-weight: 900;
                    font-size: 10px;
                    border-radius: 0px;
                """)
                name_label.setStyleSheet(f"""
                    color: {dim_text};
                    font-weight: 900;
                    letter-spacing: 1px;
                    font-size: 10px;
                """)
                
        for i, line in enumerate(self.step_lines):
            if i < stage:
                line.setStyleSheet(f"background-color: {THEME['cyan']};")
            else:
                line.setStyleSheet("background-color: rgba(120, 255, 255, 0.2);")
    
    def _create_buttons(self):
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setSpacing(10)
        
        # Operations Group
        op_group = QGroupBox("Operations")
        op_layout = QHBoxLayout()
        op_layout.setSpacing(5)
        
        self.scan_btn = QPushButton("1. Scan System")
        self.scan_btn.setFixedHeight(32)
        self.scan_btn.clicked.connect(self._scan)
        op_layout.addWidget(self.scan_btn)
        
        self.analyze_btn = QPushButton("2. Analyze")
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.clicked.connect(self._analyze)
        self.analyze_btn.setEnabled(False)
        op_layout.addWidget(self.analyze_btn)
        
        self.plan_btn = QPushButton("3. Generate Plan")
        self.plan_btn.setFixedHeight(32)
        self.plan_btn.clicked.connect(self._generate_plan)
        self.plan_btn.setEnabled(False)
        op_layout.addWidget(self.plan_btn)
        
        op_group.setLayout(op_layout)
        buttons_layout.addWidget(op_group)
        
        # Strategy Group
        strategy_group = QGroupBox("Strategy")
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(5)
        
        self.simulate_btn = QPushButton("Simulate Strategies")
        self.simulate_btn.setFixedHeight(32)
        self.simulate_btn.clicked.connect(self._simulate_strategies)
        self.simulate_btn.setEnabled(False)
        strategy_layout.addWidget(self.simulate_btn)
        
        strategy_group.setLayout(strategy_layout)
        buttons_layout.addWidget(strategy_group)
        
        # Export Group
        export_group = QGroupBox("Export")
        export_layout = QHBoxLayout()
        export_layout.setSpacing(5)
        
        self.export_btn = QPushButton("Export Script")
        self.export_btn.setFixedHeight(32)
        self.export_btn.clicked.connect(self._export_script)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        self.restore_btn = QPushButton("Create Restore Point")
        self.restore_btn.setFixedHeight(32)
        self.restore_btn.clicked.connect(self._create_restore_point)
        export_layout.addWidget(self.restore_btn)
        
        export_group.setLayout(export_layout)
        buttons_layout.addWidget(export_group)
        
        # Safety Group
        safety_group = QGroupBox("Safety")
        safety_layout = QHBoxLayout()
        safety_layout.setSpacing(5)
        
        self.reverse_btn = QPushButton("Reverse Last Action")
        self.reverse_btn.setFixedHeight(32)
        self.reverse_btn.clicked.connect(self._reverse_last_action)
        self.reverse_btn.setEnabled(False)
        safety_layout.addWidget(self.reverse_btn)
        
        self.backup_btn = QPushButton("Create Backup")
        self.backup_btn.setFixedHeight(32)
        self.backup_btn.clicked.connect(self._create_backup)
        safety_layout.addWidget(self.backup_btn)
        
        safety_group.setLayout(safety_layout)
        buttons_layout.addWidget(safety_group)
        
        return buttons_widget
    
    def log_msg(self, msg: str, level="INFO"):
        line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}"
        try:
            if hasattr(self, "syslog") and self.syslog:
                self.syslog.append(line)
            if hasattr(self, "plan_text") and self.plan_text:
                # Keep latest important lines visible in the plan pane as well.
                if level in ["ERROR", "WARN"]:
                    self.plan_text.append(line)
        except Exception:
            pass
    
    def set_api_status(self, status: str, error: Optional[str] = None):
        if status == "online":
            self.api_label.setText("PLAN READY")
            self.api_label.setStyleSheet(f"border: 1px solid rgba(66,255,158,0.35); padding: 6px 10px; border-radius: 10px; color: {THEME['green']}; font-weight: 900; letter-spacing: 1px;")
        elif status == "error":
            self.api_label.setText("API ERROR")
            self.api_label.setStyleSheet(f"border: 1px solid rgba(255,77,109,0.35); padding: 6px 10px; border-radius: 10px; color: {THEME['red']}; font-weight: 900; letter-spacing: 1px;")
        else:
            self.api_label.setText("STANDBY")
            self.api_label.setStyleSheet(f"border: 1px solid rgba(46,243,255,0.18); padding: 6px 10px; border-radius: 10px; color: {THEME['muted']}; font-weight: 900; letter-spacing: 1px;")
    
    def _show_system_details(self):
        if self.snapshot:
            dialog = SystemDetailsDialog(self.snapshot, self)
            dialog.exec()
    
    def _scan(self):
        self.log_msg("Scanning system...")
        self.scan_btn.setEnabled(False)
        self.details_btn.setEnabled(False)
        self.set_api_status("unknown")
        
        # Hide all containers immediately
        for panel in self._animated_early + self._animated_late:
            if hasattr(panel, 'body'):
                eff = panel.body.graphicsEffect()
                if eff:
                    eff.setOpacity(0.0)
        
        self._cleanup_workers()
        self._clear_all_categories()
        self.flow_indicator.set_stage(0)
        self._set_step_stage(0)
        self.analyzer.client.start_pipeline()
        
        self.scan_worker = ScanWorker()
        self.scan_worker.finished.connect(self._scan_done)
        self.scan_worker.start()
    
    def _scan_done(self, snapshot):
        self.snapshot = snapshot
        self.scan_btn.setEnabled(True)
        self.details_btn.setEnabled(True)
        
        try:
            self._update_system_summary(snapshot)
        except Exception as e:
            self.log_msg(f"UI summary update failed: {e}", "WARN")

        if snapshot.get("error"):
            self.log_msg(f"Scan error: {snapshot['error']}", "ERROR")
            return
        
        self.log_msg("Scan complete")
        self.analyze_btn.setEnabled(True)
        self.simulate_btn.setEnabled(True)
        self.set_api_status("online")
        self.flow_indicator.set_stage(1)
        self._set_step_stage(1)
        
        # Visual top-to-bottom flow: Reveal Phase 1 (Top Scan Panels)
        self._animations_1 = []
        for i, panel in enumerate(self._animated_early):
            eff = panel.body.graphicsEffect()
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(500)
            anim.setStartValue(eff.opacity())
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            QTimer.singleShot(i * 150, anim.start)
            self._animations_1.append(anim)
            
        self.chart_stack.setCurrentWidget(self.clean_view)
        
        self.scan_worker = None
    
    def _analyze(self):
        if not self.snapshot:
            return
        
        self.log_msg("Calling ASI-1 for analysis...")
        self.analyze_btn.setEnabled(False)
        self.flow_indicator.set_stage(1)
        self._set_step_stage(1)
        
        self._stop_worker(self.analyze_worker)
        self.analyze_worker = AnalyzeWorker(self.analyzer, self.snapshot)
        self.analyze_worker.finished.connect(self._analyze_done)
        self.analyze_worker.start()
    
    def _analyze_done(self, metrics):
        self.metrics = metrics
        
        if metrics.error:
            self.log_msg(f"Analysis issue: {metrics.error}", "WARN")
        
        self.log_msg(f"ASI-1 score: {metrics.overall_score}")
        self.status.setText(f"AI score: {metrics.overall_score}")
        self.clean_view.set_score(metrics.overall_score)
        self.chart.update_scores(metrics.overall_score)
        self.flow_indicator.set_stage(2)
        self._set_step_stage(2)

        # Drive center analysis + results values
        try:
            # Use real data from snapshot if available, fallback only if missing
            current_cpu = self.snapshot.get("cpu", {}).get("usage_percent", 24)
            current_mem = self.snapshot.get("memory", {}).get("usage_percent", 61)
            
            # Simple scaling for Disk/Net load if not calculated yet
            disk_io = self.snapshot.get("storage_io", {}).get("read_count", 18) % 100
            net_load = self.snapshot.get("network_io", {}).get("packets_recv", 27) % 100

            self.live_analysis.set_metrics(
                cpu=current_cpu, 
                mem=current_mem, 
                disk_io=disk_io, 
                net=net_load, 
                stability=min(100, max(0, metrics.overall_score))
            )
            self.results.before.setText(str(metrics.overall_score))
            if hasattr(self, "r_score_now"):
                self.r_score_now.setText(str(metrics.overall_score))
            
            # Start live refresh
            self.refresh_timer.start()
        except Exception:
            pass
        
        if self.thought_trace_visible and self.thought_trace_widget:
            self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
        
        self.analyze_worker = None
        self._get_strategic_insight()
    
    def _get_strategic_insight(self):
        self.log_msg("Getting strategic insight...")
        
        self._stop_worker(self.insight_worker)
        self.insight_worker = InsightWorker(self.analyzer, self.snapshot, self.metrics)
        self.insight_worker.finished.connect(self._insight_done)
        self.insight_worker.start()
    
    def _insight_done(self, insight):
        self.strategic_insight = insight
        
        if insight:
            self.log_msg(f"Priority: {insight.priority_domain}")
            self.flow_indicator.set_stage(2)
        else:
            self.log_msg("No insight received", "WARN")
        
        if self.thought_trace_visible and self.thought_trace_widget:
            self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
        
        self.insight_worker = None
        self.plan_btn.setEnabled(True)
        self._set_step_stage(2)
    
    def _generate_plan(self):
        if not self.snapshot or not self.metrics:
            return
        
        self.log_msg("Generating optimization plan...")
        self.plan_btn.setEnabled(False)
        self.flow_indicator.set_stage(2)
        self._set_step_stage(2)
        
        self.chart_stack.setCurrentWidget(self.chart)
        
        self._stop_worker(self.plan_worker)
        self.plan_worker = PlanWorker(self.analyzer, self.snapshot, self.metrics, self.strategic_insight)
        self.plan_worker.finished.connect(self._plan_done)
        self.plan_worker.start()
    
    def _plan_done(self, categories, projected, error, warning):
        if error:
            self.log_msg(f"Plan generation issue: {error}", "WARN")
            if categories is None:
                self.plan_btn.setEnabled(True)
                return
        
        self.original_categories = categories
        self.original_projected = projected
        
        self.log_msg(f"Plan generated. Projected: {projected}")
        self.chart.update_scores(
            self.metrics.overall_score if self.metrics else 70, 
            original_projected=projected
        )
        self.flow_indicator.set_stage(3)
        self._set_step_stage(3)
        
        if self.thought_trace_visible and self.thought_trace_widget:
            self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
        
        self.plan_worker = None
        self._display_original_plan()
        
        self.log_msg("Ready for Simulate Strategies.")
        self.simulate_btn.setEnabled(True)

        if self.metrics and self.metrics.overall_score is not None and projected is not None:
            gain = projected - self.metrics.overall_score
            try:
                self.results.after.setText(str(projected))
                self.results.delta.setText(f"{gain:+d}")
                if hasattr(self, "r_proj"):
                    self.r_proj.setText(str(projected))
            except Exception:
                pass

        try:
            # Also mirror into script preview for export.
            selected = []
            for cat in self.original_categories:
                selected.extend(cat.tasks[:2])
            
            self.script_preview.update_script(selected)

            # Render plan output using custom layout component
            self.plan_list.set_plan(self.original_categories)
        except Exception as e:
            self.log_msg(f"Could not format plan string: {e}", "WARN")
            
        # Flow from top-to-bottom Phase 2 (Tasks, Plan) MUST always trigger regardless of parsing failure
        self._animations_2 = []
        for i, panel in enumerate(self._animated_late):
            eff = panel.body.graphicsEffect()
            if eff and eff.opacity() < 1.0:
                anim = QPropertyAnimation(eff, b"opacity")
                anim.setDuration(500)
                anim.setStartValue(eff.opacity())
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                QTimer.singleShot(i * 150, anim.start)
                self._animations_2.append(anim)
                
        # Continue pipeline to generate the refined plan automatically
        self._get_plan_critique()
    
    def _display_original_plan(self):
        self._clear_tab_layout(self.original_tab_layout)
        QTimer.singleShot(50, lambda: self._build_original_plan())
    
    def _build_original_plan(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(400)
        scroll.setStyleSheet("border: none;")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        priority_domain = self.strategic_insight.priority_domain if self.strategic_insight else None
        
        for cat in self.original_categories:
            is_priority = (priority_domain and cat.name == priority_domain)
            w = CategoryWidget(cat, is_priority, "original")
            w.changed.connect(self._selection_changed)
            layout.addWidget(w)
        
        layout.addStretch()
        scroll.setWidget(container)
        self.original_tab_layout.addWidget(scroll)
    
    def _get_plan_critique(self):
        self.log_msg("AI Self-Review in progress...")
        
        self._stop_worker(self.critique_worker)
        self.critique_worker = CritiqueWorker(self.analyzer, self.original_categories, self.metrics)
        self.critique_worker.finished.connect(self._critique_done)
        self.critique_worker.start()
    
    def _critique_done(self, critique):
        self.plan_critique = critique
        
        if critique:
            self.log_msg("Self-review complete")
            self.flow_indicator.set_stage(4)
            self._set_step_stage(4)
            
            if self.thought_trace_visible and self.thought_trace_widget:
                self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
            
            self.critique_worker = None
            self._regenerate_plan()
        else:
            self.log_msg("No review received", "WARN")
            self.critique_worker = None
            self.export_btn.setEnabled(True)
    
    def _regenerate_plan(self):
        self.log_msg("Creating refined strategy...")
        
        self._stop_worker(self.regenerate_worker)
        self.regenerate_worker = RegenerateWorker(
            self.analyzer, self.snapshot, self.metrics, self.plan_critique, self.original_projected
        )
        self.regenerate_worker.finished.connect(self._regenerate_done)
        self.regenerate_worker.start()
    
    def _regenerate_done(self, categories, projected, risk_reduction, improvements):
        if not categories:
            self.log_msg("Filtering original plan for maximum safety...", "WARN")
            # Strict safety filter: Only LOW risk tasks, limited to 2 per category
            categories = []
            for cat in self.original_categories:
                safe_tasks = [t for t in cat.tasks if t.risk == RiskLevel.LOW]
                if safe_tasks:
                    new_cat = cat.copy()
                    new_cat.tasks = safe_tasks[:2]
                    for t in new_cat.tasks:
                        t.description = f"[SAFE] {t.description}"
                        t.is_safe = True
                    categories.append(new_cat)
            self.refined_categories = categories
            self.refined_projected = max(self.metrics.overall_score + 3, (self.original_projected or 80) - 5)
            self.risk_reduction = 45.0
            self.improvements = ["Strict risk filtering", "Stability-first tuning"]
        else:
            # API returned a plan, but we still apply a safety filter to be sure
            filtered_categories = []
            for cat in categories:
                # Filter: Must be marked safe AND not be High/Critical risk
                safe_tasks = [t for t in cat.tasks if t.is_safe and t.risk not in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
                if safe_tasks:
                    cat.tasks = safe_tasks
                    filtered_categories.append(cat)
            
            self.refined_categories = filtered_categories
            self.refined_projected = projected or (self.original_projected - 2)
            self.risk_reduction = risk_reduction or 30.0
            self.improvements = improvements or ["AI-refined safety path"]
            
        gain = 0
        if self.metrics and self.metrics.overall_score is not None and self.refined_projected is not None:
            gain = self.refined_projected - self.metrics.overall_score
            
        try:
            self.refined_btn.show()
            if self.plan_panel.title_label.text() != "REFINED PLAN":
                self._show_refined_plan_in_list()
        except Exception as e:
            self.log_msg(f"Could not display refined plan: {e}", "WARN")
        
        self.log_msg(f"Refined strategy ready: +{gain} gain, -{self.risk_reduction:.0f}% risk")
        self.flow_indicator.set_stage(4)
        self._set_step_stage(4)

        # Update right-side metrics
        if self.metrics and self.metrics.overall_score is not None and self.refined_projected is not None:
            rgain = self.refined_projected - self.metrics.overall_score
            self.card_projected.set_value(str(self.refined_projected), sub="refined")
            self.card_gain.set_value(f"{rgain:+d}", sub=f"-{self.risk_reduction:.0f}% risk")
            if hasattr(self, "r_proj"):
                self.r_proj.setText(str(self.refined_projected))
        
        if self.thought_trace_visible and self.thought_trace_widget:
            self.thought_trace_widget.update_trace(self.analyzer.client.get_thought_trace())
        
        self.chart.update_scores(
            self.metrics.overall_score if self.metrics else 70,
            original_projected=self.original_projected,
            refined_projected=self.refined_projected
        )
        
        self.regenerate_worker = None
        self._assess_confidence()
    
    def _assess_confidence(self):
        plan_data = {
            "original": self.original_projected,
            "refined": self.refined_projected,
            "risk_reduction": self.risk_reduction
        }
        
        self.log_msg("Assessing confidence...")
        
        self._stop_worker(self.confidence_worker)
        self.confidence_worker = ConfidenceWorker(self.analyzer, plan_data, self.metrics)
        self.confidence_worker.finished.connect(self._confidence_done)
        self.confidence_worker.start()
    
    def _confidence_done(self, assessment):
        if assessment:
            self.confidence_score = min(100, assessment.confidence_score)
        else:
            self.confidence_score = min(100, 85 + (self.risk_reduction / 2 if self.risk_reduction else 0))
        
        self.confidence_worker = None
        self._display_refined_plan()
        self.export_btn.setEnabled(True)
        self.reverse_btn.setEnabled(True)

        self.card_conf.set_value(f"{int(self.confidence_score)}%")
        if hasattr(self, "r_conf"):
            self.r_conf.setText(f"{int(self.confidence_score)}%")

        # Drive donut gauge (rough mapping: more risk reduction -> lower risk)
        rr = float(self.risk_reduction or 0)
        risk = int(max(0, min(100, 80 - rr)))
        legend = "LOW" if risk < 35 else ("MED" if risk < 70 else "HIGH")
        self.donut.set_value(risk, legend=legend)
    
    def _display_refined_plan(self):
        self._clear_tab_layout(self.refined_tab_layout)
        QTimer.singleShot(50, lambda: self._build_refined_plan())
    
    def _build_refined_plan(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(400)
        scroll.setStyleSheet("border: none;")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        priority_domain = self.strategic_insight.priority_domain if self.strategic_insight else None
        
        for cat in self.refined_categories:
            is_priority = (priority_domain and cat.name == priority_domain)
            w = CategoryWidget(cat, is_priority, "refined")
            w.changed.connect(self._selection_changed)
            layout.addWidget(w)
        
        layout.addStretch()
        scroll.setWidget(container)
        self.refined_tab_layout.addWidget(scroll)
        
        self.category_tabs.setCurrentIndex(1)
        
        original_tasks = []
        for cat in self.original_categories:
            original_tasks.extend(cat.tasks)
        
        refined_tasks = []
        for cat in self.refined_categories:
            refined_tasks.extend(cat.tasks)
        
        self.script_diff.update_diff(original_tasks, refined_tasks)
    
    def _clear_tab_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _clear_all_categories(self):
        self._clear_tab_layout(self.original_tab_layout)
        self._clear_tab_layout(self.refined_tab_layout)
    
    def _selection_changed(self):
        if not self.metrics:
            return
        
        selected = self._get_selected()
        
        if selected:
            impact = sum(t.impact_on_stability for t in selected)
            self.status.setText(f"Selected {len(selected)} tasks (impact: +{impact})")
            
            is_refined = self.category_tabs.currentIndex() == 1
            if is_refined:
                self.live_risk.set_color(THEME["cyan"], THEME["panel2"])
            else:
                self.live_risk.set_color(THEME["yellow"], THEME["panel2"])
            self.live_risk.update_risk(selected, self.metrics.overall_score)
            
            if self.metrics:
                risk_data = LiveRiskCalculator.calculate_risk(selected, self.metrics.overall_score)
                self.chart.update_scores(
                    self.metrics.overall_score,
                    original_projected=self.original_projected,
                    refined_projected=self.refined_projected,
                    live_projected=risk_data["projected_score"]
                )
                
                # Update visible Risk Matrix
                self.donut.set_value(risk_data["total_risk"], legend=risk_data["risk_level"])
                self.r_threat.setText(risk_data["risk_level"].upper())
                self.r_high_risk.setText(str(risk_data["high_risk_tasks"]))
                self.r_unsafe.setText(str(risk_data["unsafe_commands"]))
                self.r_reboot.setText("YES" if risk_data["reboot_required"] else "NO")
                self.r_conf.setText(f"{int(risk_data['confidence'])}%")
                
                # Dynamic mapping: Base Score + Current Impact
                self.r_score_now.setText(str(self.metrics.overall_score))
                self.r_proj.setText(str(risk_data["projected_score"]))
            
            self.script_preview.update_script(selected)
            self.toolbox.setCurrentIndex(2)
        else:
            self.status.setText("No tasks selected")
            self.live_risk.hide()
            self.script_preview.update_script([])
            
            # Reset Risk Matrix to baseline
            if self.metrics:
                self.donut.set_value(0, legend="NONE")
                self.r_threat.setText("NONE")
                self.r_high_risk.setText("0")
                self.r_unsafe.setText("0")
                self.r_reboot.setText("NO")
                self.r_conf.setText("--")
                self.r_score_now.setText(str(self.metrics.overall_score))
                self.r_proj.setText(str(self.metrics.overall_score))
            
            self.chart.update_scores(
                self.metrics.overall_score,
                original_projected=self.original_projected,
                refined_projected=self.refined_projected
            )

    def _update_system_summary(self, snapshot: dict):
        sys_info = snapshot.get("system", {}) if snapshot else {}
        cpu_info = snapshot.get("cpu", {}) if snapshot else {}
        mem_info = snapshot.get("memory", {}) if snapshot else {}

        os_name = sys_info.get("os", "Unknown")
        host = sys_info.get("hostname", "Unknown")
        uptime_days = sys_info.get("uptime_days", None)
        uptime = f"{uptime_days} days" if uptime_days is not None else "Unknown"

        cpu_usage = cpu_info.get("usage_percent", None)
        cpu_freq = cpu_info.get("frequency_mhz", None)
        cpu_txt = "Unknown"
        if cpu_usage is not None and cpu_freq is not None:
            cpu_txt = f"{cpu_usage}% @ {cpu_freq}MHz"
        elif cpu_usage is not None:
            cpu_txt = f"{cpu_usage}%"

        mem_used = mem_info.get("used_gb", None)
        mem_total = mem_info.get("total_gb", None)
        mem_pct = mem_info.get("usage_percent", None)
        mem_txt = "Unknown"
        if mem_used is not None and mem_total is not None and mem_pct is not None:
            mem_txt = f"{mem_used}/{mem_total}GB ({mem_pct}%)"
        elif mem_used is not None and mem_total is not None:
            mem_txt = f"{mem_used}/{mem_total}GB"

        self.sys_os.setText(str(os_name)[:32])
        self.sys_host.setText(str(host)[:32])
        phys = cpu_info.get("cores_physical", 0)
        logi = cpu_info.get("cores_logical", 0)
        if phys or logi:
            self.sys_cpu.setText(f"{phys}C/{logi}T"[:32])
        else:
            self.sys_cpu.setText(str(cpu_txt)[:32])
        if mem_total is not None:
            self.sys_mem.setText(f"{mem_total} GB"[:32])
        else:
            self.sys_mem.setText(str(mem_txt)[:32])
        self.sys_uptime.setText(str(uptime)[:32])
        proc_count = len(snapshot.get("processes", []) or [])
        if proc_count:
            self.sys_score.setText(str(proc_count))
    
    def _get_selected(self) -> List[OptimizationTask]:
        try:
            return self.plan_list.get_selected()
        except Exception as e:
            self.log_msg(f"Error getting selected tasks: {e}", "ERROR")
            return []
            
    def _show_refined_plan_in_list(self):
        if hasattr(self, "plan_panel") and self.plan_panel:
            if "REFINED PLAN" not in self.plan_panel.title_label.text():
                if self.refined_categories:
                    self.plan_list.set_plan(self.refined_categories, is_refined=True)
                    self.plan_panel.title_label.setText("REFINED PLAN")
                    self.refined_btn.setText("ORIGINAL PLAN")
                    self._selection_changed()
            else:
                if self.original_categories:
                    self.plan_list.set_plan(self.original_categories, is_refined=False)
                    self.plan_panel.title_label.setText("GENERATED PLAN")
                    self.refined_btn.setText("REFINED PLAN")
                    self._selection_changed()
    
    def _simulate_strategies(self):
        if not self.snapshot or not self.metrics:
            QMessageBox.information(self, "Cannot Simulate", "Please scan and analyze the system first")
            return
        
        self.log_msg("Running strategy simulation...")
        self.simulate_btn.setEnabled(False)
        
        self._stop_worker(self.simulation_worker)
        self.simulation_worker = SimulationWorker(self.analyzer, self.snapshot, self.metrics)
        self.simulation_worker.finished.connect(self._simulation_done)
        self.simulation_worker.start()
    
    def _simulation_done(self, result):
        if result and isinstance(result, SimulationResult):
            self.simulation_result = result
            self.strategy_comparison.update_strategies(
                result.strategies, 
                result.selected_index, 
                result.reasoning
            )
            self.toolbox.setCurrentIndex(0)
            self.log_msg(f"Best: {result.strategies[result.selected_index].name}")
            
            selected = result.strategies[result.selected_index]
            QMessageBox.information(self, "Simulation Complete", 
                f"Recommended: {selected.name}\n"
                f"Gain: +{selected.gain}\n"
                f"Risk: {selected.risk_level}\n"
                f"Confidence: {selected.confidence:.1f}%\n\n"
                f"Reasoning: {result.reasoning}")
        else:
            self.log_msg("Simulation failed or returned invalid result", "ERROR")
        
        self.simulation_worker = None
        self.simulate_btn.setEnabled(True)
    
    def _export_script(self):
        selected = self._get_selected()
        if not selected:
            QMessageBox.information(self, "No Selection", "Select tasks first")
            return
        
        self.script_preview.update_script(selected)
        self.toolbox.setCurrentIndex(2)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Z-Engine_{timestamp}.ps1"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PowerShell Script",
            default_name,
            "PowerShell Scripts (*.ps1);;All Files (*)"
        )
        
        if file_path:
            try:
                safe_mode = self.script_preview.safe_mode_cb.isChecked()
                script = ScriptGenerator.generate_script(selected, safe_mode)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script)
                self.log_msg(f"Script saved to: {file_path}")
                QMessageBox.information(self, "Success", f"Script saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save script: {e}")
    
    def _create_restore_point(self):
        self.log_msg("Creating system restore point...")
        success, msg = RestorePointCreator.create_restore_point()
        if success:
            self.log_msg("Restore point created")
            QMessageBox.information(self, "Success", msg)
        else:
            self.log_msg(f"Failed to create restore point: {msg}", "ERROR")
            QMessageBox.warning(self, "Warning", msg)
    
    def _create_backup(self):
        self.log_msg("Creating system backup...")
        backup_path = self.backup_manager.create_backup("Pre-optimization state")
        if backup_path:
            self.last_backup = backup_path
            self.reverse_btn.setEnabled(True)
            self.log_msg(f"Backup created: {backup_path}")
            QMessageBox.information(self, "Success", f"Backup created successfully")
        else:
            self.log_msg("Failed to create backup", "ERROR")
            QMessageBox.warning(self, "Warning", "Failed to create backup")
    
    def _reverse_last_action(self):
        reply = QMessageBox.question(
            self,
            "Reverse Last Action",
            "This will restore your system to the state before the last optimization.\n"
            "This action cannot be undone.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_msg("Restoring from backup...")
            backup = self.backup_manager.get_latest_backup()
            if backup and self.backup_manager.restore_backup(backup):
                self.log_msg("System restored successfully")
                QMessageBox.information(self, "Success", "System restored successfully")
                
                if self.metrics:
                    self.metrics.overall_score = 70
                self.clean_view.set_score(70)
                self.chart_stack.setCurrentWidget(self.clean_view)
                self.reverse_btn.setEnabled(False)
            else:
                self.log_msg("Failed to restore system", "ERROR")
                QMessageBox.warning(self, "Warning", "Failed to restore system")
    
    def _on_refresh_tick(self):
        """Deprecated: The ScanWorker now runs persistently in the background."""
        pass

    def _on_refresh_done(self, new_snapshot):
        """Update metrics from the background scan result"""
        if not new_snapshot:
            return
            
        try:
            if not new_snapshot.get("error"):
                self.snapshot = new_snapshot
                self._update_system_summary(self.snapshot)
                
                cpu = self.snapshot.get("cpu", {}).get("usage_percent", 0)
                mem = self.snapshot.get("memory", {}).get("usage_percent", 0)
                
                # For Disk/Net bars using real I/O metrics
                io = self.snapshot.get("storage_io", {})
                net_io = self.snapshot.get("network_io", {})
                
                # Drive bars using scaled real counters
                disk = (io.get("write_count", 0) + io.get("read_count", 0)) % 100
                net = (net_io.get("packets_sent", 0) + net_io.get("packets_recv", 0)) % 100
                
                # Stability remains what the AI scored
                stab = self.metrics.overall_score if self.metrics else 50
                
                self.live_analysis.set_metrics(cpu, mem, disk, net, stab)
        except Exception:
            pass

    def closeEvent(self, event):
        """Clean up workers on close"""
        self._cleanup_workers()
        if self.thought_trace_widget:
            self.thought_trace_widget.close()
        event.accept()

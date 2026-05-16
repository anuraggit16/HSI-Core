# =============================================================================
# HSI-Core GUI — Professional Acquisition Control Interface
# =============================================================================
# Features:
# - Real-time parameter control
# - 3D data cube visualization
# - Spectral analysis plots
# - Live camera preview
# - Acquisition state management
# - Wavelength range selector
# =============================================================================

import sys
import json
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime
import threading
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QProgressBar,
    QGridLayout, QSplitter, QFrame, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QRect, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QImage, QPixmap
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtCore import QPointF

import cv2
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# =============================================================================
# WORKER THREAD FOR ACQUISITION
# =============================================================================

class AcquisitionWorker(QThread):
    """Background thread for handling scan acquisition"""
    
    progress_updated = pyqtSignal(dict)  # Emit scan progress data
    error_occurred = pyqtSignal(str)    # Emit error messages
    finished = pyqtSignal()              # Emit when scan completes
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__()
        self.params = params
        self.is_running = False
        self.is_paused = False
        
    def run(self):
        """Execute scan acquisition"""
        try:
            self.is_running = True
            from pylablib.devices import Thorlabs
            from pypylon import pylon
            
            # Connect hardware
            stage = Thorlabs.KinesisMotor(
                self.params['controller_serial'],
                is_rack_system=True,
                default_channel=1
            )
            
            stage.setup_velocity(
                min_velocity=self.params['min_velocity'],
                max_velocity=self.params['max_velocity'],
                acceleration=self.params['acceleration']
            )
            
            camera = pylon.InstantCamera(
                pylon.TlFactory.GetInstance().CreateFirstDevice()
            )
            camera.Open()
            camera.ExposureTime.SetValue(self.params['exposure_us'])
            
            # Move to start position
            stage.move_to(self.params['start_position'])
            stage.wait_move()
            time.sleep(1)
            
            # Main scan loop
            for i in range(self.params['num_images']):
                if not self.is_running:
                    break
                    
                while self.is_paused:
                    time.sleep(0.1)
                
                # Calculate position
                current_pos = self.params['start_position'] + (i * self.params['step_size'])
                current_mm = current_pos / self.params['units_per_mm']
                
                # Move stage
                stage.move_to(current_pos)
                stage.wait_move()
                time.sleep(self.params['settling_time'])
                
                # Capture image
                grab = camera.GrabOne(5000)
                
                if grab.GrabSucceeded():
                    image = grab.Array
                    
                    # Emit progress
                    self.progress_updated.emit({
                        'image_num': i + 1,
                        'total_images': self.params['num_images'],
                        'position_mm': current_mm,
                        'image_data': image,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    self.error_occurred.emit(f"Image capture failed at position {current_mm:.3f}mm")
            
            # Cleanup
            camera.Close()
            stage.close()
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Acquisition error: {str(e)}")
        finally:
            self.is_running = False
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def stop(self):
        self.is_running = False


# =============================================================================
# 3D DATA CUBE VISUALIZATION
# =============================================================================

class DataCubeVisualizer(FigureCanvas):
    """3D visualization of hyperspectral data cube"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        
        for spine in self.ax.spines.values():
            spine.set_color('white')
        
        super().__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #2b2b2b;")
    
    def update_cube(self, data: np.ndarray):
        """Update 3D cube visualization"""
        self.ax.clear()
        
        # Create sample 3D data from intensity map
        if data is not None and data.size > 0:
            # Normalize data
            data_norm = (data - data.min()) / (data.max() - data.min() + 1e-6)
            
            # Create coordinate arrays
            ny, nx = data_norm.shape
            x = np.linspace(0, nx, 20)
            y = np.linspace(0, ny, 20)
            X, Y = np.meshgrid(x, y)
            
            # Interpolate Z values
            from scipy.interpolate import griddata
            xy = np.column_stack([np.tile(x, len(y)), np.repeat(y, len(x))])
            Z = griddata((np.arange(nx), np.arange(ny)), 
                        data_norm.flatten()[:len(xy)], xy, method='cubic')
            Z = Z.reshape(len(y), len(x))
            
            # Plot surface
            self.ax.plot_surface(X, Y, Z, cmap='hot', alpha=0.8)
            
            self.ax.set_xlabel('X [mm]', color='white')
            self.ax.set_ylabel('Y [mm]', color='white')
            self.ax.set_zlabel('Intensity', color='white')
        
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.draw()


# =============================================================================
# SPECTRAL PLOT VISUALIZATION
# =============================================================================

class SpectralPlotter(FigureCanvas):
    """Spectral plot visualization"""
    
    def __init__(self, parent=None, width=5, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        
        super().__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #2b2b2b;")
    
    def update_spectrum(self, intensity: np.ndarray, wavelengths: np.ndarray = None):
        """Update spectral plot"""
        self.ax.clear()
        
        if intensity is not None and len(intensity) > 0:
            if wavelengths is None:
                wavelengths = np.linspace(400, 1000, len(intensity))
            
            self.ax.plot(wavelengths, intensity, color='#00ff00', linewidth=2)
            self.ax.fill_between(wavelengths, intensity, alpha=0.3, color='#00ff00')
            self.ax.set_xlabel('Wavelength [nm]', color='white')
            self.ax.set_ylabel('Intensity [e⁻]', color='white')
        
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('white')
        self.draw()


# =============================================================================
# MAIN GUI WINDOW
# =============================================================================

class HSICoreGUI(QMainWindow):
    """Main GUI application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HSI-Core Acquisition v3.0")
        self.setGeometry(100, 100, 1600, 1000)
        self.setStyleSheet(self._get_stylesheet())
        
        self.acquisition_worker = None
        self.current_image = None
        self.intensity_map = np.zeros((100, 100))
        
        # Initialize UI
        self.init_ui()
        
        # Timer for updating displays
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(500)
    
    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        left_panel = self._create_control_panel()
        
        # Right panel - Visualizations
        right_panel = self._create_visualization_panel()
        
        # Splitter for resizing
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1200])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
    
    def _create_control_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Acquisition Control Section
        acq_group = QGroupBox("Acquisition Control")
        acq_layout = QVBoxLayout()
        
        # Start/Pause/Stop buttons
        button_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_start.clicked.connect(self.start_acquisition)
        
        self.btn_pause = QPushButton("⏸ PAUSE")
        self.btn_pause.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 10px;")
        self.btn_pause.clicked.connect(self.pause_acquisition)
        self.btn_pause.setEnabled(False)
        
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 10px;")
        self.btn_stop.clicked.connect(self.stop_acquisition)
        self.btn_stop.setEnabled(False)
        
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_stop)
        acq_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid white; border-radius: 5px; background-color: #1e1e1e; } QProgressBar::chunk { background-color: #28a745; }")
        acq_layout.addWidget(QLabel("Scan Progress:"))
        acq_layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setStyleSheet("background-color: #1e1e1e; color: #00ff00; border: 1px solid white;")
        acq_layout.addWidget(QLabel("Status:"))
        acq_layout.addWidget(self.status_text)
        
        acq_group.setLayout(acq_layout)
        layout.addWidget(acq_group)
        
        # Scan Settings Section
        scan_group = QGroupBox("Scan Settings")
        scan_layout = QGridLayout()
        
        # Start position
        scan_layout.addWidget(QLabel("Start Position [mm]:"), 0, 0)
        self.spin_start_pos = QDoubleSpinBox()
        self.spin_start_pos.setRange(0, 200)
        self.spin_start_pos.setValue(80)
        self.spin_start_pos.setDecimals(2)
        self.spin_start_pos.setSingleStep(0.1)
        scan_layout.addWidget(self.spin_start_pos, 0, 1)
        
        # Step size
        scan_layout.addWidget(QLabel("Step Size [mm]:"), 1, 0)
        self.spin_step_size = QDoubleSpinBox()
        self.spin_step_size.setRange(0.001, 10)
        self.spin_step_size.setValue(1)
        self.spin_step_size.setDecimals(3)
        self.spin_step_size.setSingleStep(0.1)
        scan_layout.addWidget(self.spin_step_size, 1, 1)
        
        # Number of images
        scan_layout.addWidget(QLabel("Number of Images:"), 2, 0)
        self.spin_num_images = QSpinBox()
        self.spin_num_images.setRange(1, 10000)
        self.spin_num_images.setValue(100)
        scan_layout.addWidget(self.spin_num_images, 2, 1)
        
        # Exposure time
        scan_layout.addWidget(QLabel("Exposure [ms]:"), 3, 0)
        self.spin_exposure = QDoubleSpinBox()
        self.spin_exposure.setRange(1, 10000)
        self.spin_exposure.setValue(100)
        self.spin_exposure.setDecimals(1)
        scan_layout.addWidget(self.spin_exposure, 3, 1)
        
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)
        
        # Stage Settings Section
        stage_group = QGroupBox("Stage Settings")
        stage_layout = QGridLayout()
        
        # Min velocity
        stage_layout.addWidget(QLabel("Min Velocity:"), 0, 0)
        self.spin_min_vel = QSpinBox()
        self.spin_min_vel.setRange(1000, 1000000)
        self.spin_min_vel.setValue(20000)
        self.spin_min_vel.setSingleStep(10000)
        stage_layout.addWidget(self.spin_min_vel, 0, 1)
        
        # Max velocity
        stage_layout.addWidget(QLabel("Max Velocity:"), 1, 0)
        self.spin_max_vel = QSpinBox()
        self.spin_max_vel.setRange(1000, 1000000)
        self.spin_max_vel.setValue(300000)
        self.spin_max_vel.setSingleStep(10000)
        stage_layout.addWidget(self.spin_max_vel, 1, 1)
        
        # Acceleration
        stage_layout.addWidget(QLabel("Acceleration:"), 2, 0)
        self.spin_accel = QSpinBox()
        self.spin_accel.setRange(1000, 10000000)
        self.spin_accel.setValue(500000)
        self.spin_accel.setSingleStep(10000)
        stage_layout.addWidget(self.spin_accel, 2, 1)
        
        # Settling time
        stage_layout.addWidget(QLabel("Settling Time [s]:"), 3, 0)
        self.spin_settling = QDoubleSpinBox()
        self.spin_settling.setRange(0, 10)
        self.spin_settling.setValue(0.1)
        self.spin_settling.setDecimals(3)
        stage_layout.addWidget(self.spin_settling, 3, 1)
        
        stage_group.setLayout(stage_layout)
        layout.addWidget(stage_group)
        
        # Wavelength Section
        wave_group = QGroupBox("Wavelength Range Selector")
        wave_layout = QVBoxLayout()
        
        wavelength_slider_layout = QHBoxLayout()
        wavelength_slider_layout.addWidget(QLabel("Min [nm]:"))
        self.wave_min_label = QLabel("400")
        wavelength_slider_layout.addWidget(self.wave_min_label)
        wavelength_slider_layout.addWidget(QLabel("Max [nm]:"))
        self.wave_max_label = QLabel("1000")
        wavelength_slider_layout.addWidget(self.wave_max_label)
        wave_layout.addLayout(wavelength_slider_layout)
        
        self.wavelength_slider = QSlider(Qt.Horizontal)
        self.wavelength_slider.setRange(400, 1000)
        self.wavelength_slider.setValue(700)
        self.wavelength_slider.setTickPosition(QSlider.TicksBelow)
        self.wavelength_slider.setTickInterval(100)
        wave_layout.addWidget(self.wavelength_slider)
        
        wave_group.setLayout(wave_layout)
        layout.addWidget(wave_group)
        
        # Hardware Info Section
        hw_group = QGroupBox("Hardware Info")
        hw_layout = QGridLayout()
        
        hw_layout.addWidget(QLabel("Controller Serial:"), 0, 0)
        self.label_serial = QLineEdit("103425854")
        hw_layout.addWidget(self.label_serial, 0, 1)
        
        hw_layout.addWidget(QLabel("Units/mm:"), 1, 0)
        self.label_units_per_mm = QSpinBox()
        self.label_units_per_mm.setValue(20000)
        hw_layout.addWidget(self.label_units_per_mm, 1, 1)
        
        hw_layout.addWidget(QLabel("Camera Model:"), 2, 0)
        self.label_camera = QLabel("Basler - Not connected")
        hw_layout.addWidget(self.label_camera, 2, 1)
        
        hw_layout.addWidget(QLabel("Stage Status:"), 3, 0)
        self.label_stage = QLabel("Not connected")
        hw_layout.addWidget(self.label_stage, 3, 1)
        
        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def _create_visualization_panel(self) -> QWidget:
        """Create right visualization panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Tabs for different views
        tabs = QTabWidget()
        
        # 3D Cube tab
        cube_widget = QWidget()
        cube_layout = QVBoxLayout()
        self.cube_viz = DataCubeVisualizer()
        cube_layout.addWidget(self.cube_viz)
        cube_widget.setLayout(cube_layout)
        tabs.addTab(cube_widget, "3D Data Cube")
        
        # Spectral tab
        spectral_widget = QWidget()
        spectral_layout = QVBoxLayout()
        self.spectral_plot = SpectralPlotter()
        spectral_layout.addWidget(self.spectral_plot)
        spectral_widget.setLayout(spectral_layout)
        tabs.addTab(spectral_widget, "Spectral Plot")
        
        # Camera preview tab
        camera_widget = QWidget()
        camera_layout = QVBoxLayout()
        self.camera_label = QLabel("Camera Preview")
        self.camera_label.setMinimumHeight(400)
        self.camera_label.setStyleSheet("background-color: #000; border: 1px solid white;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.camera_label)
        camera_widget.setLayout(camera_layout)
        tabs.addTab(camera_widget, "Camera Preview")
        
        # Intensity map tab
        intensity_widget = QWidget()
        intensity_layout = QVBoxLayout()
        self.intensity_canvas = FigureCanvas(Figure(figsize=(5, 5), dpi=100, facecolor='#2b2b2b'))
        self.intensity_ax = self.intensity_canvas.figure.add_subplot(111)
        self.intensity_ax.set_facecolor('#1e1e1e')
        intensity_layout.addWidget(self.intensity_canvas)
        intensity_widget.setLayout(intensity_layout)
        tabs.addTab(intensity_widget, "Intensity Map")
        
        # Histogram tab
        histogram_widget = QWidget()
        histogram_layout = QVBoxLayout()
        self.histogram_canvas = FigureCanvas(Figure(figsize=(5, 5), dpi=100, facecolor='#2b2b2b'))
        self.histogram_ax = self.histogram_canvas.figure.add_subplot(111)
        self.histogram_ax.set_facecolor('#1e1e1e')
        histogram_layout.addWidget(self.histogram_canvas)
        histogram_widget.setLayout(histogram_layout)
        tabs.addTab(histogram_widget, "Histogram")
        
        layout.addWidget(tabs)
        
        # Info box at bottom
        info_group = QGroupBox("Scan Info")
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel("Current Position:"), 0, 0)
        self.label_position = QLabel("-- mm")
        info_layout.addWidget(self.label_position, 0, 1)
        
        info_layout.addWidget(QLabel("Images Acquired:"), 0, 2)
        self.label_images = QLabel("0")
        info_layout.addWidget(self.label_images, 0, 3)
        
        info_layout.addWidget(QLabel("Timestamp:"), 1, 0)
        self.label_timestamp = QLabel("--:--:--")
        info_layout.addWidget(self.label_timestamp, 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        panel.setLayout(layout)
        return panel
    
    def start_acquisition(self):
        """Start scan acquisition"""
        try:
            params = {
                'controller_serial': self.label_serial.text(),
                'units_per_mm': self.label_units_per_mm.value(),
                'start_mm': self.spin_start_pos.value(),
                'start_position': int(self.spin_start_pos.value() * self.label_units_per_mm.value()),
                'step_size_mm': self.spin_step_size.value(),
                'step_size': int(self.spin_step_size.value() * self.label_units_per_mm.value()),
                'num_images': self.spin_num_images.value(),
                'exposure_ms': self.spin_exposure.value(),
                'exposure_us': int(self.spin_exposure.value() * 1000),
                'min_velocity': self.spin_min_vel.value(),
                'max_velocity': self.spin_max_vel.value(),
                'acceleration': self.spin_accel.value(),
                'settling_time': self.spin_settling.value(),
            }
            
            self.acquisition_worker = AcquisitionWorker(params)
            self.acquisition_worker.progress_updated.connect(self.on_progress_update)
            self.acquisition_worker.error_occurred.connect(self.on_error)
            self.acquisition_worker.finished.connect(self.on_acquisition_finished)
            self.acquisition_worker.start()
            
            # Update UI state
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Acquisition started")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start acquisition: {str(e)}")
    
    def pause_acquisition(self):
        """Pause acquisition"""
        if self.acquisition_worker:
            self.acquisition_worker.pause()
            self.btn_pause.setText("▶ RESUME")
            self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Acquisition paused")
    
    def stop_acquisition(self):
        """Stop acquisition"""
        if self.acquisition_worker:
            self.acquisition_worker.stop()
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_pause.setText("⏸ PAUSE")
            self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Acquisition stopped")
    
    def on_progress_update(self, data: Dict):
        """Handle progress update from acquisition worker"""
        image_num = data['image_num']
        total = data['total_images']
        position = data['position_mm']
        image = data['image_data']
        
        # Update progress bar
        progress = int((image_num / total) * 100)
        self.progress_bar.setValue(progress)
        
        # Update labels
        self.label_images.setText(str(image_num))
        self.label_position.setText(f"{position:.3f} mm")
        self.label_timestamp.setText(datetime.now().strftime('%H:%M:%S'))
        
        # Update status
        self.status_text.append(f"[{image_num:04d}/{total:04d}] Position: {position:.3f}mm")
        
        # Store and display image
        if image is not None:
            self.current_image = image
            self._update_camera_preview(image)
            self._update_intensity_map(image)
            self._update_histogram(image)
    
    def on_error(self, error_msg: str):
        """Handle error from acquisition worker"""
        self.status_text.append(f"[ERROR] {error_msg}")
        QMessageBox.warning(self, "Acquisition Error", error_msg)
    
    def on_acquisition_finished(self):
        """Handle acquisition completion"""
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setText("⏸ PAUSE")
        self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] Acquisition completed!")
        self.progress_bar.setValue(100)
    
    def _update_camera_preview(self, image: np.ndarray):
        """Update camera preview display"""
        if image is None or image.size == 0:
            return
        
        # Resize for display
        h, w = image.shape[:2]
        if h > 400 or w > 400:
            scale = min(400/h, 400/w)
            image = cv2.resize(image, (int(w*scale), int(h*scale)))
        
        # Convert to RGB
        if len(image.shape) == 2:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to QPixmap
        h, w, ch = image_rgb.shape
        bytes_per_line = 3 * w
        qt_image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        self.camera_label.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
    
    def _update_intensity_map(self, image: np.ndarray):
        """Update intensity map visualization"""
        if image is None or image.size == 0:
            return
        
        # Use grayscale or intensity
        if len(image.shape) == 3:
            intensity = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            intensity = image
        
        # Accumulate to intensity map
        if self.intensity_map.shape != intensity.shape:
            self.intensity_map = np.zeros_like(intensity, dtype=np.float32)
        
        self.intensity_map = (self.intensity_map * 0.9 + intensity.astype(np.float32) * 0.1)
        
        # Plot
        self.intensity_ax.clear()
        im = self.intensity_ax.imshow(self.intensity_map, cmap='hot')
        self.intensity_ax.set_title('Accumulated Intensity Map', color='white')
        self.intensity_canvas.figure.colorbar(im, ax=self.intensity_ax)
        self.intensity_canvas.draw()
    
    def _update_histogram(self, image: np.ndarray):
        """Update histogram visualization"""
        if image is None or image.size == 0:
            return
        
        self.histogram_ax.clear()
        
        if len(image.shape) == 3:
            for i, color in enumerate(['r', 'g', 'b']):
                self.histogram_ax.hist(image[:,:,i].ravel(), bins=256, alpha=0.5, color=color)
        else:
            self.histogram_ax.hist(image.ravel(), bins=256, color='white', alpha=0.7)
        
        self.histogram_ax.set_xlabel('Pixel Intensity', color='white')
        self.histogram_ax.set_ylabel('Frequency', color='white')
        self.histogram_ax.set_title('Intensity Distribution', color='white')
        self.histogram_ax.tick_params(colors='white')
        for spine in self.histogram_ax.spines.values():
            spine.set_color('white')
        
        self.histogram_canvas.draw()
    
    def update_displays(self):
        """Periodic update of visualizations"""
        if self.current_image is not None:
            # Update 3D cube occasionally
            if self.intensity_map.size > 0:
                self.cube_viz.update_cube(self.intensity_map)
            
            # Update spectral mock
            if len(self.current_image.shape) == 2:
                spectrum = np.mean(self.current_image, axis=0)
            else:
                spectrum = np.mean(self.current_image, axis=(0, 1))
            
            self.spectral_plot.update_spectrum(spectrum[:100])
    
    def _get_stylesheet(self) -> str:
        """Get dark mode stylesheet"""
        return """
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0c3aa7;
            }
            QProgressBar {
                border: 1px solid white;
                border-radius: 5px;
                background-color: #1e1e1e;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: white;
                padding: 5px 15px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #0d47a1;
                border-bottom: 2px solid #0d47a1;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #555;
                font-family: Courier;
            }
        """


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = HSICoreGUI()
    gui.show()
    sys.exit(app.exec_())

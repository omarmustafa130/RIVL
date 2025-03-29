import sys
import os
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"
from PyQt6.QtCore import Qt, QTimer, QRect, QPointF, QUrl, QSize, QSizeF
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QFileDialog, QSlider,
    QComboBox, QStackedLayout, QSpinBox, QGridLayout, 
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
    QGraphicsColorizeEffect, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QVideoFrame
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

class AnimatedOverlayItem(QGraphicsPixmapItem):
    def __init__(self, pixmap):
        super().__init__()
        self.original_pixmap = pixmap
        self.mask_pixmap = None
        self.setOpacity(1.0)
        self.scale_min = 0.8
        self.scale_max = 1.0

    def set_mask_pixmap(self, background_pixmap):
        bg = background_pixmap.scaled(
            self.original_pixmap.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        masked = QPixmap(self.original_pixmap.size())
        masked.fill(Qt.GlobalColor.transparent)

        painter = QPainter(masked)
        painter.drawPixmap(0, 0, bg)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, self.original_pixmap)
        painter.end()

        self.mask_pixmap = masked
        self.update_blend_to_white(0.0)

    def update_blend_to_white(self, fraction):
        blended = QPixmap(self.original_pixmap.size())
        blended.fill(Qt.GlobalColor.transparent)

        painter = QPainter(blended)

        # Blend masked background first
        painter.setOpacity(1.0 - fraction)
        painter.drawPixmap(0, 0, self.mask_pixmap)

        # White version of logo on top
        painter.setOpacity(fraction)
        painter.drawPixmap(0, 0, self._white_version())
        painter.end()

        self.setPixmap(blended)

    def _white_version(self):
        white_pixmap = QPixmap(self.original_pixmap.size())
        white_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(white_pixmap)
        painter.drawPixmap(0, 0, self.original_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(self.original_pixmap.rect(), Qt.GlobalColor.white)
        painter.end()

        return white_pixmap

    def set_scale_progress(self, progress):
        eased = progress * progress * (3 - 2 * progress)  # Ease-in-out
        scale = self.scale_min + (self.scale_max - self.scale_min) * eased
        self.setScale(scale)




class AudiTVCApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audi TVC Application (PyQt6)")
        self.setAcceptDrops(True)
        self.setMinimumSize(1366, 768)
        self.setStyleSheet("""
            background-color: #1E1E1E; 
            color: white;
            QFrame {
                background-color: #2C2C2C;
            }
        """)

        # Qt Multimedia setup
        self.media_player = QMediaPlayer()
        self.video_item = QGraphicsVideoItem()
        self.media_player.setVideoOutput(self.video_item)
        
        # Create graphics scene
        self.scene = QGraphicsScene(self)
        self.scene.addItem(self.video_item)
        
        # Error handling
        self.media_player.errorOccurred.connect(self.handle_player_error)
        
        self.timer = QTimer()
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update_ui)

        # Video state
        self.video_loaded = False
        self.overlay_item = None
        self.video_duration_s = 0

        # UI setup
        self.stack = QStackedLayout(self)
        self.drop_screen = self.build_drop_screen()
        self.main_screen = self.build_main_screen()
        self.stack.addWidget(self.drop_screen)
        self.stack.addWidget(self.main_screen)

        # Media player signals
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.playbackStateChanged.connect(self.update_play_button)

    def handle_player_error(self, error, error_string):
        QMessageBox.warning(self, "Error", 
                          f"Cannot play video: {error_string}\n\n"
                          "Please ensure you have proper codecs installed.\n"
                          "Recommended: Install ffmpeg")



    # Style Helpers
    def button_style(self):
        return """
        QPushButton {
            background: transparent;
            border: 1px solid #aaa;
            color: white;
            padding: 4px;
            min-width: 80px;
        }
        QPushButton:hover {
            background: #555;
        }
        QPushButton:pressed {
            background: #777;
        }
        """

    def combo_style(self):
        return """
        QComboBox {
            background-color: #3E3E3E;
            border: 1px solid #777;
            padding: 4px;
            color: white;
            min-width: 120px;
        }
        QComboBox QAbstractItemView {
            background-color: #2C2C2C;
            color: white;
            selection-background-color: #555;
        }
        """

    def spin_style(self):
        return """
        QSpinBox {
            background-color: #3E3E3E;
            border: 1px solid #777;
            padding: 2px;
            color: white;
            min-width: 60px;
        }
        """

    def slider_style(self):
        return """
        QSlider::groove:horizontal {
            height: 3px;
            background: #777;
            border-radius: 1px;
        }
        QSlider::sub-page:horizontal {
            background: #00AEEF;
            border-radius: 1px;
        }
        QSlider::handle:horizontal {
            background: white;
            border: none;
            width: 10px;
            margin: -4px 0;
            border-radius: 5px;
        }
        """

    # Drop Screen
    def build_drop_screen(self):
        screen = QWidget()
        layout = QHBoxLayout(screen)

        # Left panel
        left_panel = QFrame()
        left_panel.setFixedWidth(230)
        left_panel.setStyleSheet("background-color: #2C2C2C;")
        left_layout = QVBoxLayout(left_panel)

        logo = QLabel()
        if os.path.exists("logo.png"):
            logo.setPixmap(QPixmap("logo.png").scaledToWidth(100, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Audi Motion Branding")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 12px; font-weight: bold;")

        load_button = QPushButton("Load content")
        load_button.setStyleSheet(self.button_style())
        load_button.clicked.connect(self.open_video_dialog)

        left_layout.addWidget(logo)
        left_layout.addWidget(title)
        left_layout.addSpacing(20)
        left_layout.addWidget(load_button)
        left_layout.addStretch()

        help_button = QPushButton("Help")
        help_button.setStyleSheet(self.button_style())
        left_layout.addWidget(help_button)

        layout.addWidget(left_panel)

        # Right panel
        drop_label = QLabel("Drop content here")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("""
            color: #aaa; 
            font-size: 11px; 
            border: 2px dashed #555;
            padding: 40px;
        """)
        layout.addWidget(drop_label)

        return screen

    # Main Screen
    def build_main_screen(self):
        screen = QWidget()
        layout = QHBoxLayout(screen)

        # Left panel
        self.left_panel = self.build_left_panel_full()
        layout.addWidget(self.left_panel)

        # Right side wrapper
        right_wrapper = QVBoxLayout()

        # Video container
        self.video_container = QFrame()
        self.video_container.setStyleSheet("background-color: black;")
        self.video_container.setMinimumSize(800, 600)
        self.video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Graphics View for video and overlays
        self.video_view = QGraphicsView(self.scene)
        self.video_view.setStyleSheet("background: black; border: none;")
        self.video_view.setRenderHints(
            QPainter.RenderHint.Antialiasing | 
            QPainter.RenderHint.SmoothPixmapTransform
        )
        
        right_wrapper.addWidget(self.video_container)
        self.video_container.setLayout(QVBoxLayout())
        self.video_container.layout().addWidget(self.video_view)
        self.build_media_controls(right_wrapper)
        layout.addLayout(right_wrapper)
        return screen

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.video_loaded:
            self.fit_video_view()

    def fit_video_view(self):
        """Resize video view to fit container while maintaining aspect ratio"""
        if not self.video_item.nativeSize().isEmpty():
            video_size = self.video_item.nativeSize()
            view_size = self.video_view.size()
            
            # Calculate aspect ratio
            video_ratio = video_size.width() / video_size.height()
            view_ratio = view_size.width() / view_size.height()
            
            if view_ratio > video_ratio:
                # View is wider than video
                new_height = view_size.height()
                new_width = new_height * video_ratio
            else:
                # View is taller than video
                new_width = view_size.width()
                new_height = new_width / video_ratio
                
            # Center the video - using QSize properly now
            self.video_item.setSize(QSizeF(new_width, new_height))

            self.video_item.setPos(
                (view_size.width() - new_width) / 2,
                (view_size.height() - new_height) / 2
            )
            
            # Update overlay position if exists
            if self.overlay_item:
                self.center_overlay_item()


    def resize_video_and_overlay(self, event):
        """Handle window resize events"""
        if self.video_loaded:
            self.fit_video_view()


    # Left panel with controls
    def build_left_panel_full(self):
        panel = QFrame()
        panel.setFixedWidth(230)
        panel.setStyleSheet("background-color: #2C2C2C;")
        layout = QVBoxLayout(panel)

        # Logo and title
        logo = QLabel()
        if os.path.exists("logo.png"):
            logo.setPixmap(QPixmap("logo.png").scaledToWidth(100, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Audi Motion Branding")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addSpacing(10)

        # File info
        self.file_info = QLabel("File not loaded")
        self.file_info.setStyleSheet("font-size: 10px; color: #ccc;")
        layout.addWidget(self.file_info)
        layout.addSpacing(10)

        # Animation controls
        anim_layout = QHBoxLayout()
        anim_label = QLabel("Animation")
        anim_label.setStyleSheet("font-size: 11px;")
        self.anim_combo = QComboBox()
        self.anim_combo.addItems(["Opener", "Ending", "Short Version", "Dealership"])
        self.anim_combo.setStyleSheet(self.combo_style())
        anim_layout.addWidget(anim_label)
        anim_layout.addStretch()
        anim_layout.addWidget(self.anim_combo)
        layout.addLayout(anim_layout)
        layout.addSpacing(10)

        # Ring Size controls
        ring_size_layout = QVBoxLayout()
        ring_label = QLabel("Ring Size")
        ring_label.setStyleSheet("font-size: 11px;")
        ring_size_layout.addWidget(ring_label)
        
        ring_size_row = QHBoxLayout()
        self.ring_size_spin = QSpinBox()
        self.ring_size_spin.setRange(0, 100)
        self.ring_size_spin.setValue(50)
        self.ring_size_spin.setStyleSheet(self.spin_style())
        ring_size_row.addWidget(self.ring_size_spin)
        
        self.ring_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.ring_size_slider.setRange(0, 100)
        self.ring_size_slider.setValue(50)
        self.ring_size_slider.setStyleSheet(self.slider_style())
        ring_size_row.addWidget(self.ring_size_slider)
        
        ring_size_layout.addLayout(ring_size_row)
        layout.addLayout(ring_size_layout)
        layout.addSpacing(10)

        # Ring Position controls
        ring_pos_layout = QVBoxLayout()
        ring_pos_label = QLabel("Ring Position")
        ring_pos_label.setStyleSheet("font-size: 11px;")
        ring_pos_layout.addWidget(ring_pos_label)
        
        ring_pos_row = QHBoxLayout()
        self.ring_pos_combo = QComboBox()
        self.ring_pos_combo.addItems(["Top", "Center", "Bottom"])
        self.ring_pos_combo.setStyleSheet(self.combo_style())
        ring_pos_row.addWidget(self.ring_pos_combo)
        
        self.ring_pos_spin = QSpinBox()
        self.ring_pos_spin.setRange(0, 100)
        self.ring_pos_spin.setValue(50)
        self.ring_pos_spin.setStyleSheet(self.spin_style())
        ring_pos_row.addWidget(self.ring_pos_spin)
        
        ring_pos_layout.addLayout(ring_pos_row)
        layout.addLayout(ring_pos_layout)
        layout.addSpacing(10)

        # Background Scale controls
        bg_scale_layout = QVBoxLayout()
        bg_scale_label = QLabel("Background Scale")
        bg_scale_label.setStyleSheet("font-size: 11px;")
        bg_scale_layout.addWidget(bg_scale_label)
        
        bg_scale_row = QHBoxLayout()
        self.bg_scale_spin = QSpinBox()
        self.bg_scale_spin.setRange(0, 100)
        self.bg_scale_spin.setValue(20)
        self.bg_scale_spin.setStyleSheet(self.spin_style())
        bg_scale_row.addWidget(self.bg_scale_spin)
        
        self.bg_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_scale_slider.setRange(0, 100)
        self.bg_scale_slider.setValue(20)
        self.bg_scale_slider.setStyleSheet(self.slider_style())
        bg_scale_row.addWidget(self.bg_scale_slider)
        
        bg_scale_layout.addLayout(bg_scale_row)
        layout.addLayout(bg_scale_layout)
        layout.addSpacing(10)

        # Ring Color controls
        ring_color_layout = QHBoxLayout()
        ring_color_label = QLabel("Ring Color")
        ring_color_label.setStyleSheet("font-size: 11px;")
        ring_color_layout.addWidget(ring_color_label)
        
        self.ring_color_combo = QComboBox()
        self.ring_color_combo.addItems(["White rings", "Black rings"])
        self.ring_color_combo.setStyleSheet(self.combo_style())
        ring_color_layout.addWidget(self.ring_color_combo)
        
        layout.addLayout(ring_color_layout)
        layout.addSpacing(20)

        # Timing controls
        timing_layout = QVBoxLayout()
        timing_label = QLabel("Timing")
        timing_label.setStyleSheet("font-size: 11px;")
        timing_layout.addWidget(timing_label)
        
        timing_desc = QLabel("Snap logo animation\nto current video position.")
        timing_desc.setStyleSheet("font-size: 10px; color: #aaa;")
        timing_layout.addWidget(timing_desc)
        
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setStyleSheet(self.button_style())
        timing_layout.addWidget(confirm_btn)
        
        layout.addLayout(timing_layout)
        layout.addSpacing(20)

        # Render button
        render_button = QPushButton("Render")
        render_button.setStyleSheet(self.button_style())
        layout.addWidget(render_button)
        layout.addStretch()

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        audio_btn = QPushButton("Audio Setup")
        audio_btn.setStyleSheet(self.button_style())
        help_btn = QPushButton("Help")
        help_btn.setStyleSheet(self.button_style())
        
        bottom_layout.addWidget(audio_btn)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(help_btn)
        
        layout.addLayout(bottom_layout)

        # Load PNG Overlay button
        self.load_overlay_btn = QPushButton("Load PNG Overlay")
        self.load_overlay_btn.setStyleSheet(self.button_style())
        self.load_overlay_btn.setEnabled(False)
        self.load_overlay_btn.clicked.connect(self.load_png_overlay)
        layout.addWidget(self.load_overlay_btn)

        return panel

    # Media Controls
    def build_media_controls(self, outer_layout):
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(5, 5, 5, 5)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setStyleSheet(self.slider_style())
        self.slider.sliderMoved.connect(self.set_position)

        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: #aaa; font-size: 10px; margin-left: 6px;")

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setStyleSheet(self.button_style())
        self.prev_btn.clicked.connect(self.seek_backward)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setStyleSheet(self.button_style())
        self.play_btn.clicked.connect(self.toggle_play)

        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setStyleSheet(self.button_style())
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setStyleSheet(self.slider_style())
        self.volume_slider.valueChanged.connect(self.set_volume)

        controls_layout.addWidget(self.slider, 4)
        controls_layout.addWidget(self.time_label, 1)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.mute_btn)
        controls_layout.addWidget(self.volume_slider)

        outer_layout.addLayout(controls_layout)

    # Video Loading
    def open_video_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        if file_path:
            self.load_video(file_path)

    def load_video(self, file_path):
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.stack.setCurrentIndex(1)
        self.video_loaded = True
        
        # Enable overlay button
        if hasattr(self, 'load_overlay_btn'):
            self.load_overlay_btn.setEnabled(True)
            
        self.timer.start()
        
        # Update file info
        if hasattr(self, 'file_info'):
            self.file_info.setText(os.path.basename(file_path))
        
        # Fit video immediately and after short delay when metadata is loaded
        self.fit_video_view()
        QTimer.singleShot(100, self.fit_video_view)
        
        # Start playback after ensuring video is fitted
        QTimer.singleShot(200, lambda: self.media_player.play())


    # Player Controls
    def toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def toggle_mute(self):
        self.media_player.setMuted(not self.media_player.isMuted())
        self.mute_btn.setText("🔇" if self.media_player.isMuted() else "🔊")

    def set_volume(self, volume):
        self.media_player.setVolume(volume)

    def seek_backward(self):
        self.media_player.setPosition(self.media_player.position() - 5000)

    # Position/Duration Handling
    def update_duration(self, duration):
        self.video_duration_s = duration // 1000

    def update_position(self, position):
        if self.media_player.duration() > 0:
            fraction = position / self.media_player.duration()
            self.slider.blockSignals(True)
            self.slider.setValue(int(fraction * 1000))
            self.slider.blockSignals(False)

            pos_s = position // 1000
            hh = pos_s // 3600
            mm = (pos_s % 3600) // 60
            ss = pos_s % 60
            self.time_label.setText(f"{hh:02}:{mm:02}:{ss:02}")

    def set_position(self, val):
        if self.media_player.duration() > 0:
            new_time = int((val / 1000) * self.media_player.duration())
            self.media_player.setPosition(new_time)

    # Overlay Functions
    def load_png_overlay(self):
        if not self.video_loaded:
            QMessageBox.warning(self, "Error", "Please load a video first")
            return

        # Ask user to pick an overlay image
        png_path, _ = QFileDialog.getOpenFileName(
            self, "Load PNG Overlay", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )

        if not png_path:
            return

        print(f"Loading overlay: {png_path}")

        # Load the image
        pixmap = QPixmap(png_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Error", "Failed to load overlay image")
            return

        # Resize it to 50% of the video size if needed
        max_width = self.video_item.size().width() * 0.5
        max_height = self.video_item.size().height() * 0.5

        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(
                int(max_width), int(max_height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Remove previous overlay
        if self.overlay_item:
            self.scene.removeItem(self.overlay_item)

        # Create overlay item and add to scene
        self.overlay_item = AnimatedOverlayItem(pixmap)
        self.scene.addItem(self.overlay_item)
        self.overlay_item.setVisible(True)

        # Center the overlay on the video
        self.center_overlay_item()

        # Render the video scene as background for masking
        scene_img = QImage(self.video_view.viewport().size(), QImage.Format.Format_ARGB32)
        painter = QPainter(scene_img)
        self.video_view.render(painter)
        painter.end()

        # Set blended mask from background
        scene_pixmap = QPixmap.fromImage(scene_img)
        self.overlay_item.set_mask_pixmap(scene_pixmap)

        print("Overlay loaded, centered, and masked with video frame")


    def center_overlay_item(self):
        if not self.overlay_item:
            return

        video_size = self.video_item.size()
        video_pos = self.video_item.pos()

        # Store the center point of the video only once
        self.overlay_center = QPointF(
            video_pos.x() + video_size.width() / 2,
            video_pos.y() + video_size.height() / 2
        )

        # Initial overlay centering
        self.update_overlay_position()

    def update_overlay_position(self):
        """Keeps the overlay centered during scaling."""
        if not self.overlay_item or not hasattr(self, "overlay_center"):
            return

        overlay_size = self.overlay_item.pixmap().size() * self.overlay_item.scale()
        x = self.overlay_center.x() - overlay_size.width() / 2
        y = self.overlay_center.y() - overlay_size.height() / 2
        self.overlay_item.setPos(x, y)

    # Drag & Drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                self.load_video(file_path)
            break

    # UI Update
    def update_ui(self):
        if not self.video_loaded:
            return

        self.fit_video_view()

        current_pos_s = self.media_player.position() / 1000

        if self.overlay_item:
            self.overlay_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

            if current_pos_s <= 2:
                # Scale + fade in white
                t = current_pos_s / 2.0
                eased = 2*t*t if t < 0.5 else 1 - pow(-2*t + 2, 2)/2
                self.overlay_item.set_scale_progress(eased)
                self.overlay_item.update_blend_to_white(eased)
                self.overlay_item.setOpacity(1.0)
                self.overlay_item.setVisible(True)
                self.update_overlay_position()

            elif 2 < current_pos_s <= 4:
                # Hold full size/white
                self.overlay_item.set_scale_progress(1.0)
                self.overlay_item.update_blend_to_white(1.0)
                self.overlay_item.setOpacity(1.0)
                self.overlay_item.setVisible(True)
                self.update_overlay_position()

            elif 4 < current_pos_s <= 5:
                # Smooth fade out
                t = (current_pos_s - 4) / 1.0
                eased = 1 - pow(1 - t, 3)  # cubic ease-out
                self.overlay_item.setOpacity(1.0 - eased)
                self.overlay_item.setVisible(True)

            else:
                self.overlay_item.setVisible(False)





    def get_background_color_at_overlay(self):
        """Get the average color of the video at the overlay position"""
        if not self.overlay_item or not self.video_item.nativeSize().isValid():
            return QColor(0, 0, 0)  # Default black
        
        # Get overlay position and size
        overlay_pos = self.overlay_item.pos()
        overlay_size = self.overlay_item.boundingRect().size() * self.overlay_item.scale()
        
        # Get center point of overlay
        center_x = overlay_pos.x() + overlay_size.width() / 2
        center_y = overlay_pos.y() + overlay_size.height() / 2
        
        # Get video frame (if available)
        frame = self.video_item.videoFrame()
        if frame.isValid():
            image = frame.toImage()
            if not image.isNull():
                # Get color at center point
                return image.pixelColor(int(center_x), int(center_y))
        
        return QColor(0, 0, 0)  # Default black if can't get frame
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check multimedia support
    if not QMediaPlayer().isAvailable():
        QMessageBox.critical(None, "Error", "Multimedia services not available")
        sys.exit(1)
    
    window = AudiTVCApp()
    window.show()
    sys.exit(app.exec())
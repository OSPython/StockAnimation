import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox,
                            QFileDialog, QSlider)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.dates import DateFormatter, AutoDateLocator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import timedelta

class StockVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Price Visualizer")
        # Adjusted window dimensions for portrait layout
        self.setGeometry(100, 100, 800, 1200)
        
        # Rest of the initialization code remains the same until the matplotlib figure creation
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create input controls
        controls_layout = QHBoxLayout()
        
        # Tickers input
        ticker_layout = QVBoxLayout()
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Enter tickers (comma-separated)")
        self.ticker_input.setText("TSLA,NVDA,AAPL")
        self.ticker_input.setMinimumWidth(200)
        ticker_layout.addWidget(QLabel("Tickers:"))
        ticker_layout.addWidget(self.ticker_input)
        controls_layout.addLayout(ticker_layout)
        
        # Start date input
        start_date_layout = QVBoxLayout()
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("YYYY-MM-DD")
        self.start_date_input.setText("2014-01-01")
        self.start_date_input.setMinimumWidth(100)
        start_date_layout.addWidget(QLabel("Start Date:"))
        start_date_layout.addWidget(self.start_date_input)
        controls_layout.addLayout(start_date_layout)
        
        # End date input
        end_date_layout = QVBoxLayout()
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("YYYY-MM-DD")
        self.end_date_input.setText("2024-11-11")
        self.end_date_input.setMinimumWidth(100)
        end_date_layout.addWidget(QLabel("End Date:"))
        end_date_layout.addWidget(self.end_date_input)
        controls_layout.addLayout(end_date_layout)
        
        # Speed control
        speed_layout = QVBoxLayout()
        speed_label = QLabel("Animation Speed:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['Slow', 'Normal', 'Fast', 'Very Fast', 'Ultra Fast'])
        self.speed_combo.setCurrentText('Normal')
        self.speed_combo.currentTextChanged.connect(self.update_speed)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_combo)
        controls_layout.addLayout(speed_layout)
        
        # Button layout
        button_layout = QVBoxLayout()
        
        # Run button
        self.run_button = QPushButton("Run Animation")
        self.run_button.setMinimumWidth(100)
        self.run_button.clicked.connect(self.run_animation)
        button_layout.addWidget(self.run_button)
        
        # Play/Pause button
        self.play_pause_button = QPushButton("Pause")
        self.play_pause_button.setMinimumWidth(100)
        self.play_pause_button.clicked.connect(self.toggle_animation)
        self.play_pause_button.setEnabled(False)
        button_layout.addWidget(self.play_pause_button)
        
        # Save button
        self.save_button = QPushButton("Save as MP4")
        self.save_button.setMinimumWidth(100)
        self.save_button.clicked.connect(self.save_animation)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        controls_layout.addLayout(button_layout)
        layout.addLayout(controls_layout)
        
        # Create matplotlib figure with portrait orientation
        self.fig, self.ax = plt.subplots(figsize=(8, 12))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        # Add timeline slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.update_frame)
        layout.addWidget(self.slider)
        
        # Initialize variables
        self.anim = None
        self.is_playing = True
        self.combined_df = None
        self.normalized_df = None
        self.current_frame = 0
        self.lines = []
        self.annotations = []
    
    def normalize_data(self, df):
        return df.div(df.iloc[0]) * 100
    
    def get_speed_factor(self):
        speed_text = self.speed_combo.currentText()
        speed_map = {
            'Slow': 100,
            'Normal': 50,
            'Fast': 20,
            'Very Fast': 10,
            'Ultra Fast': 1
        }
        return speed_map.get(speed_text, 50)
    
    def update_speed(self):
        if self.anim:
            interval = self.get_speed_factor()
            self.anim.event_source.interval = interval
    
    def update_frame(self):
        if self.combined_df is not None and not self.is_playing:
            frame = int((self.slider.value() / 100) * len(self.combined_df))
            self.current_frame = frame
            self.animate(frame)
            self.canvas.draw()
    
    def toggle_animation(self):
        if self.anim:
            if self.is_playing:
                self.anim.event_source.stop()
                self.play_pause_button.setText("Play")
            else:
                self.anim.event_source.start()
                self.play_pause_button.setText("Pause")
            self.is_playing = not self.is_playing
    
    def animate(self, frame):
        if self.combined_df is None or frame >= len(self.combined_df):
            # When animation reaches the end, update button state
            if frame >= len(self.combined_df) - 1:
                self.play_pause_button.setText("Play")
                self.is_playing = False
            return self.lines + self.annotations
            
        data = self.combined_df.iloc[:frame+1]
        normalized_data = self.normalized_df.iloc[:frame+1]
        
        # Update lines and annotations
        for i, (ticker, line) in enumerate(zip(self.combined_df.columns, self.lines)):
            # Update line data
            line.set_data(normalized_data.index, normalized_data[ticker])
            
            # Update annotation position and text
            if len(normalized_data) > 0:
                current_price = data[ticker].iloc[-1]
                last_x = normalized_data.index[-1]
                last_y = normalized_data[ticker].iloc[-1]
                
                # Calculate vertical offset for staggered labels
                vertical_offset = last_y + (i - len(self.combined_df.columns)/2) * (self.max_y * 0.03)  # Reduced spacing
                
                self.annotations[i].set_x(last_x)
                self.annotations[i].set_y(vertical_offset)
                self.annotations[i].set_text(f'{ticker}')  # Only show ticker
        
        # Update y-axis limits
        if not normalized_data.empty:
            current_max = normalized_data.max().max()
            self.max_y = max(self.max_y, current_max)
            y_padding = self.max_y * 0.15  # Reduced padding for more compact layout
            self.ax.set_ylim(0, self.max_y + y_padding)
        
        # Update slider position if not being dragged
        if not self.slider.isSliderDown():
            self.slider.setValue(int((frame / len(self.combined_df)) * 100))
        
        return self.lines + self.annotations
    
    def save_animation(self):
        if self.anim:
            try:
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Animation",
                    "stock_price_animation.mp4",
                    "MP4 files (*.mp4);;All Files (*)"
                )
                
                if file_name:
                    if not file_name.endswith('.mp4'):
                        file_name += '.mp4'
                    
                    self.setWindowTitle(f"{self.windowTitle()} - Saving animation...")
                    self.run_button.setEnabled(False)
                    self.save_button.setEnabled(False)
                    self.play_pause_button.setEnabled(False)

                    # Create a new figure for saving
                    save_fig, save_ax = plt.subplots(figsize=(8, 12))
                    
                    # Copy the current figure's properties
                    save_ax.set_title('Normalized Stock Price Evolution', fontsize=16, pad=15)
                    save_ax.set_xlabel('Date', fontsize=14)
                    save_ax.set_ylabel('Price (% of Initial Value)', fontsize=14)
                    save_ax.grid(True, alpha=0.3)
                    
                    # Configure date formatting
                    locator = AutoDateLocator()
                    save_ax.xaxis.set_major_locator(locator)
                    save_ax.xaxis.set_major_formatter(DateFormatter('%b %Y'))
                    save_ax.tick_params(axis='both', labelsize=12)
                    plt.setp(save_ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                    
                    # Set x-axis limits
                    last_date = self.combined_df.index[-1]
                    date_range = (last_date - self.combined_df.index[0]).days
                    extra_days = int(date_range * 0.1)
                    save_ax.set_xlim(self.combined_df.index[0], 
                                   last_date + pd.Timedelta(days=extra_days))
                    
                    # Create new lines and annotations for saving
                    save_lines = []
                    save_annotations = []
                    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                    
                    for i, ticker in enumerate(self.combined_df.columns):
                        line, = save_ax.plot([], [], color=colors[i], linewidth=2)
                        save_lines.append(line)
                        
                        annotation = save_ax.text(
                            0, 0,
                            f'{ticker}',
                            color=colors[i],
                            fontweight='bold',
                            fontsize=12,
                            bbox=dict(
                                facecolor='white',
                                edgecolor='none',
                                alpha=0.8,
                                pad=2
                            ),
                            horizontalalignment='left',
                            verticalalignment='center'
                        )
                        save_annotations.append(annotation)
                    
                    # Create animation function for saving
                    max_y = 0
                    
                    def save_animate(frame):
                        nonlocal max_y
                        data = self.combined_df.iloc[:frame+1]
                        normalized_data = self.normalized_df.iloc[:frame+1]
                        
                        for i, (ticker, line) in enumerate(zip(self.combined_df.columns, save_lines)):
                            line.set_data(normalized_data.index, normalized_data[ticker])
                            
                            if len(normalized_data) > 0:
                                last_x = normalized_data.index[-1]
                                last_y = normalized_data[ticker].iloc[-1]
                                
                                # Calculate vertical offset for staggered labels
                                if normalized_data.max().max() > max_y:
                                    max_y = normalized_data.max().max()
                                
                                vertical_offset = last_y + (i - len(self.combined_df.columns)/2) * (max_y * 0.03)
                                
                                save_annotations[i].set_x(last_x)
                                save_annotations[i].set_y(vertical_offset)
                        
                        # Update y-axis limits
                        if not normalized_data.empty:
                            current_max = normalized_data.max().max()
                            max_y = max(max_y, current_max)
                            y_padding = max_y * 0.15
                            save_ax.set_ylim(0, max_y + y_padding)
                        
                        return save_lines + save_annotations
                    
                    # Create and save the animation
                    save_anim = FuncAnimation(
                        save_fig,
                        save_animate,
                        frames=len(self.combined_df),
                        interval=self.get_speed_factor(),
                        blit=True,
                        repeat=False
                    )
                    
                    plt.tight_layout()
                    save_anim.save(file_name, writer='ffmpeg', fps=30)
                    plt.close(save_fig)
                    
                    self.run_button.setEnabled(True)
                    self.save_button.setEnabled(True)
                    self.play_pause_button.setEnabled(True)
                    self.setWindowTitle("Stock Price Visualizer")
            except Exception as e:
                print(f"Error saving animation: {str(e)}")

    def run_animation(self):
        if self.anim is not None:
            self.anim.event_source.stop()
        
        self.ax.clear()
        self.max_y = 0
        self.is_playing = True
        self.play_pause_button.setText("Pause")
        
        # Get input values and process data
        tickers = [t.strip().upper() for t in self.ticker_input.text().split(',') if t.strip()]
        start_date = self.start_date_input.text()
        end_date = self.end_date_input.text()
        
        # Limit to 10 tickers (changed from 5)
        tickers = list(dict.fromkeys(tickers[:10]))
        
        # Fetch and process data
        stock_data = {}
        for ticker in tickers:
            try:
                data = yf.Ticker(ticker).history(start=start_date, end=end_date)
                if not data.empty:
                    stock_data[ticker] = data['Close']
                else:
                    print(f"No data available for {ticker}")
            except Exception as e:
                print(f"Error fetching data for {ticker}: {str(e)}")
        
        if not stock_data:
            print("No valid data retrieved for any ticker")
            return
        
        # Combine data and normalize
        self.combined_df = pd.DataFrame(stock_data)
        self.normalized_df = self.normalize_data(self.combined_df)
        
        # Setup plot
        # Extended color palette for 10 stocks
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        self.lines = []
        self.annotations = []
        
        # Add extra space on the right for labels
        last_date = self.combined_df.index[-1]
        date_range = (self.combined_df.index[-1] - self.combined_df.index[0]).days
        extra_days = int(date_range * 0.1)
        
        for i, ticker in enumerate(self.combined_df.columns):
            # Create line
            line, = self.ax.plot([], [], color=colors[i], linewidth=2)
            self.lines.append(line)
            
            # Create text annotation with only ticker symbol
            annotation = self.ax.text(
                0, 0,  # Initial position
                f'{ticker}',  # Removed price information
                color=colors[i],
                fontweight='bold',
                fontsize=12,  # Slightly reduced font size for more tickers
                bbox=dict(
                    facecolor='white',
                    edgecolor='none',
                    alpha=0.8,
                    pad=2
                ),
                horizontalalignment='left',
                verticalalignment='center'
            )
            self.annotations.append(annotation)
        
        # Configure axes
        self.ax.set_xlim(self.combined_df.index[0], 
                        last_date + pd.Timedelta(days=extra_days))
        self.ax.set_title('Normalized Stock Price Evolution', fontsize=16, pad=15)
        self.ax.set_xlabel('Date', fontsize=14)
        self.ax.set_ylabel('Price (% of Initial Value)', fontsize=14)
        self.ax.grid(True, alpha=0.3)
        
        # Configure date formatting
        locator = AutoDateLocator()
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(DateFormatter('%b %Y'))
        self.ax.tick_params(axis='both', labelsize=12)
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Enable controls
        self.slider.setEnabled(True)
        self.slider.setValue(0)
        
        # Create animation
        interval = self.get_speed_factor()
        self.anim = FuncAnimation(
            self.fig,
            self.animate,
            frames=len(self.combined_df),
            interval=interval,
            blit=True,
            repeat=False
        )
        
        # Enable buttons
        self.play_pause_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
        plt.tight_layout()
        self.canvas.draw()

def main():
    app = QApplication(sys.argv)
    window = StockVisualizerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
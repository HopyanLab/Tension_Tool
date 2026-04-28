#!/usr/bin/env python3

import sys
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib import pyplot as plt
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_qt5agg import (
							FigureCanvasQTAgg as FigureCanvas,
							NavigationToolbar2QT as NavigationToolbar
							)
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib import colors, ticker, colormaps
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import Delaunay, Voronoi, KDTree
from scipy.interpolate import RectBivariateSpline
from skimage.feature import peak_local_max
from skimage.segmentation import find_boundaries
from scipy.interpolate import make_interp_spline
from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QIntValidator, QMouseEvent
from PyQt5.QtWidgets import (
							QApplication, QLabel, QWidget,
							QPushButton, QHBoxLayout, QVBoxLayout,
							QComboBox, QCheckBox, QSlider, QProgressBar,
							QFormLayout, QLineEdit, QTabWidget,
							QSizePolicy, QFileDialog, QMessageBox,
							QFrame
							)
from pathlib import Path
#import h5py
#from dw2d import geometry_reconstruction_2d
#from foambryo2d import infer_tension,plot_tension_inference

################################################################################
# helper functions for GUI elements #
#####################################

def display_error (error_text = 'Something went wrong!'):
	msg = QMessageBox()
	msg.setIcon(QMessageBox.Critical)
	msg.setText("Error")
	msg.setInformativeText(error_text)
	msg.setWindowTitle("Error")
	msg.exec_()

def setup_textbox (function, layout, label_text,
				   initial_value = 0):
	textbox = QLineEdit()
	need_inner = not isinstance(layout, QHBoxLayout)
	if need_inner:
		inner_layout = QHBoxLayout()
	label = QLabel(label_text)
	label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
	if need_inner:
		inner_layout.addWidget(label)
	else:
		layout.addWidget(label)
	textbox.setMaxLength(4)
	textbox.setFixedWidth(50)
	textbox.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
	textbox.setValidator(QIntValidator())
	textbox.setText(str(initial_value))
	textbox.editingFinished.connect(function)
	if need_inner:
		inner_layout.addWidget(textbox)
		layout.addLayout(inner_layout)
	else:
		layout.addWidget(textbox)
	return textbox

def get_textbox (textbox,
				 minimum_value = None,
				 maximum_value = None,
				 is_int = False):
	if is_int:
		value = int(np.floor(float(textbox.text())))
	else:
		value = float(textbox.text())
	if maximum_value is not None:
		if value > maximum_value:
			value = maximum_value
	if minimum_value is not None:
		if value < minimum_value:
			value = minimum_value
	textbox.setText(str(value))
	return value

def setup_button (function, layout, label_text, toggle = False):
	button = QPushButton()
	if toggle:
		button.setCheckable(True)
	button.setText(label_text)
	button.clicked.connect(function)
	layout.addWidget(button)
	return button

def setup_checkbox (function, layout, label_text,
					is_checked = False):
		checkbox = QCheckBox()
		checkbox.setText(label_text)
		checkbox.setChecked(is_checked)
		checkbox.stateChanged.connect(function)
		layout.addWidget(checkbox)
		return checkbox

def setup_tab (tabs, tab_layout, label):
	tab = QWidget()
	tab.layout = QVBoxLayout()
	tab.setLayout(tab.layout)
	tab.layout.addLayout(tab_layout)
	tabs.addTab(tab, label)

def horizontal_separator (layout, palette):
	separator = QFrame()
	separator.setFrameShape(QFrame.HLine)
	#separator.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
	separator.setLineWidth(1)
	palette.setColor(QPalette.WindowText, QColor('lightgrey'))
	separator.setPalette(palette)
	layout.addWidget(separator)

def setup_progress_bar (layout):
	progress_bar = QProgressBar()
	clear_progress_bar(progress_bar)
	layout.addWidget(progress_bar)
	return progress_bar

def clear_progress_bar (progress_bar):
	progress_bar.setMinimum(0)
	progress_bar.setFormat('')
	progress_bar.setMaximum(1)
	progress_bar.setValue(0)

def update_progress_bar (progress_bar, value = None,
						 minimum_value = None,
						 maximum_value = None,
						 text = None):
	if minimum_value is not None:
		progress_bar.setMinimum(minimum_value)
	if maximum_value is not None:
		progress_bar.setMaximum(maximum_value)
	if value is not None:
		progress_bar.setValue(value)
	if text is not None:
		progress_bar.setFormat(text)

def setup_slider (layout, function, maximum_value = 1,
				  direction = Qt.Horizontal):
		slider = QSlider(direction)
		slider.setMinimum(0)
		slider.setMaximum(maximum_value)
		slider.setSingleStep(1)
		slider.setValue(0)
		slider.valueChanged.connect(function)
		return slider

def update_slider (slider, value = None,
				   maximum_value = None):
	if value is not None:
		slider.setValue(value)
	if maximum_value is not None:
		slider.setMaximum(maximum_value)

def setup_combobox (function, layout, label_text):
	combobox = QComboBox()
	need_inner = not isinstance(layout, QHBoxLayout)
	if need_inner:
		inner_layout = QHBoxLayout()
	label = QLabel(label_text)
	label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
	if need_inner:
		inner_layout.addWidget(label)
	else:
		layout.addWidget(label)
	combobox.currentIndexChanged.connect(function)
	if need_inner:
		inner_layout.addWidget(combobox)
		layout.addLayout(inner_layout)
	else:
		layout.addWidget(combobox)
	return combobox

def setup_labelbox (label_text, initial_text):
	text_box = QFrame()
	layout = QHBoxLayout()
	text_box.setFrameShape(QFrame.StyledPanel)
#	self.instruction_box.setSizePolicy(QSizePolicy.Expanding)
	label = QLabel(label_text)
	label.setAlignment(Qt.AlignLeft)
	text = QLabel(initial_text)
	text.setAlignment(Qt.AlignLeft)
#	self.instruction_text.setWordWrap(True)
	layout.addWidget(label)
	layout.addWidget(text)
	layout.addStretch()
	text_box.setLayout(layout)
	return text_box, text

def clear_layout (layout):
	for i in reversed(range(layout.count())): 
		widgetToRemove = layout.takeAt(i).widget()
		layout.removeWidget(widgetToRemove)
		widgetToRemove.deleteLater()

################################################################################
# read multichannel tiff #
##########################

def read_tiff (path):
	img = Image.open(path)
	images = []
	for i in range(img.n_frames):
		img.seek(i)
		images.append(np.array(img))
	return np.array(images)

################################################################################
# randomise and consolodate segment numbers #
#############################################

def randomise_segments (segments = None):
	if segments is None:
		return None
	segments = segments.astype(int)
	# consolodate and shuffle segment labels
	shuffled = np.unique(segments)
	index = 0
	segments -= np.amin(shuffled)
	shuffled -= np.amin(shuffled)
	while index < len(shuffled)-1:
		if index+1 in shuffled:
			index+=1
		else:
			segments[segments>index] -= 1
			shuffled[shuffled>index] -= 1
	np.random.shuffle(shuffled)
	segments = shuffled[segments]
	# make the zero segment at the corner
	corner = segments[0,0]
	corner_mask = (segments == corner)
	zero_mask = (segments == 0)
	segments[corner_mask] = 0
	segments[zero_mask] = corner
	return segments

################################################################################
# helper functions for fixing fourfold vertices #
#################################################

def _recover_ignore_index(input, orig, ignore_index):
	if ignore_index is not None:
		mask = orig == ignore_index
		input[mask] = ignore_index
	return input

class StandardLabelToBoundary:
	def __init__(self, ignore_index=None, append_label=False,
				 mode='thick', foreground=False,
				 **kwargs):
		self.ignore_index = ignore_index
		self.append_label = append_label
		self.mode = mode
		self.foreground = foreground
	def __call__(self, m):
		assert m.ndim == 3
		boundaries = find_boundaries(m, connectivity=2, mode=self.mode)
		boundaries = boundaries.astype('int32')
		results = []
		if self.foreground:
			foreground = (m > 0).astype('uint32')
			results.append(_recover_ignore_index(foreground, m,
													self.ignore_index))
		results.append(_recover_ignore_index(boundaries, m, self.ignore_index))
		if self.append_label:
			# append original input data
			results.append(m)
		return np.stack(results, axis=0)

def pad_mask(mask,pad_size = 1): 
	padded_mask = mask.copy()[pad_size:-pad_size,pad_size:-pad_size]
	padded_mask = np.pad(padded_mask, ((pad_size, pad_size),
										(pad_size, pad_size)),
							'constant',constant_values = 1)
	return(padded_mask)

def give_corners(img):
	Points=np.zeros((4,2))
	index=0
	a,b = img.shape
	for i in [0,a-1]: 
		for j in [0,b-1]: 
			Points[index]=np.array([i,j])
			index+=1
	return(Points)

def find_points (labels, min_distance = 2):
	b = StandardLabelToBoundary(mode='thick')(labels.reshape(1,
									labels.shape[0],labels.shape[1]))[0,0]
	# mask_2 is 1 on cell boundaries and 0 elsewhere
	mask_2 = b
	# distance to cell interior (thickness of boundaries?)
	EDT_2 = ndi.distance_transform_edt(mask_2)
	b = pad_mask(b) # boundary of image defined as not boundary of cells!
	# mask_1 is 0 on cell boundaries and 1 elsewhere
	mask_1 = 1-b
	# distance to boundaries
	EDT_1 = ndi.distance_transform_edt(mask_1)
	
	inv = np.amax(EDT_2)-EDT_2
	Total_EDT = (EDT_1+np.amax(EDT_2))*mask_1 + inv*mask_2
	seeds_coords = []
	values_lbls = np.unique(labels) 
	for i in values_lbls:
		seed = np.argmax(Total_EDT*((labels==i).astype(float)))
		seeds_coords.append([seed//labels.shape[1],seed%labels.shape[1]])
	# seed_coords are cell centres
	seeds_coords = np.array(seeds_coords) 
	# positions of max distances to boundaries
	seeds_indices = values_lbls # renumbered 0 -> n
	# points are boundaries
	points = peak_local_max(-Total_EDT,min_distance=min_distance,
								exclude_border=False)
	local_maxes = peak_local_max(Total_EDT,min_distance=min_distance,
								exclude_border=False)
	corners = give_corners(Total_EDT)
	all_points = np.vstack((points,corners,local_maxes))
	tesselation=Delaunay(all_points)
	x = np.linspace(0,Total_EDT.shape[0]-1,Total_EDT.shape[0])
	y = np.linspace(0,Total_EDT.shape[1]-1,Total_EDT.shape[1])
	# label_func = interpolate.interp2d(x, y, labels.transpose(), kind='linear')
	spline_object = RectBivariateSpline(x,y,labels)
	label_func = lambda xnew, ynew: spline_object(xnew, ynew).T
	possible = np.argwhere(np.bincount(
							tesselation.simplices.flatten())==4).flatten()
	possible = possible[possible<len(points)]
	return points, possible

def remove_outer (labels):
	x_max, y_max = labels.shape
	x_max-=1; y_max-=1
	should_remove = False
	for label in np.unique(labels):
		coords = np.argwhere(labels == label)
		if 0 in coords[:,0] or x_max in coords[:,0] or \
		   0 in coords[:,1] or y_max in coords[:,1]:
			labels[labels==label] = 0
	index = 0
	unique_labels = np.unique(labels)
	labels -= np.amin(unique_labels)
	unique_labels -= np.amin(unique_labels)
	while index < len(unique_labels)-1:
		if index+1 in unique_labels:
			index+=1
		else:
			labels[labels>index] -= 1
			unique_labels[unique_labels>index] -= 1
	return labels

################################################################################
# matplotlib canvas widget #
############################

class MPLCanvas(FigureCanvas):
	def __init__ (self, parent=None, width=8, height=8, dpi=100):
		self.fig = Figure(figsize=(width, height), dpi=dpi)
		self.ax = self.fig.add_subplot(111)
		self.ax.set_facecolor('black')
		FigureCanvas.__init__(self, self.fig)
		self.setParent(parent)
		FigureCanvas.setSizePolicy(self,
				QSizePolicy.Expanding,
				QSizePolicy.Expanding)
		FigureCanvas.updateGeometry(self)
		self.fig.tight_layout()
		self.image = None
		self.points = None
		self.edges = None
		self.areas = None
		self.image_plot = None
		self.points_plot = None
		self.areas_plot = None
		self.edges_plot = None
		self.show_image = True
		self.show_points = True
		self.show_edges = True
		self.show_areas = True
		self.image_changed = False
		self.points_changed = False
		self.edges_changed = False
		self.areas_changed = False
	
	def remove_plot_element (self, plot_element):
		if plot_element is not None:
			if isinstance(plot_element,list):
				for thingy in plot_element:
					try:
						self.remove_plot_element(thingy)
					except:
						print('problem')
			else:
				try:
					plot_element.remove()
				except:
					print('problem')
	
	def clear_canvas (self):
		self.remove_plot_element(self.image_plot)
		self.image_plot = None
		self.remove_plot_element(self.points_plot)
		self.points_plot = None
		self.remove_plot_element(self.edges_plot)
		self.edges_plot = None
		self.remove_plot_element(self.areas_plot)
		self.areas_plot = None
		xmin, xmax = self.ax.get_xlim()
		ymin, ymax = self.ax.get_ylim()
		self.ax.clear()
		self.ax.set_xlim([xmin,xmax])
		self.ax.set_ylim([ymin,ymax])
		self.ax.set_facecolor('black')
		self.draw()
	
	def reset_zoom (self):
		if self.image is None:
			return False
		self.ax.set_ylim([self.image.shape[0]-1,0])
		self.ax.set_xlim([0,self.image.shape[1]-1])
		self.draw()
	
	def reset (self):
		self.clear_canvas()
		self.image = None
		self.points = None
		self.edges = None
		self.areas = None
		self.image_plot = None
		self.points_plot = None
		self.areas_plot = None
		self.edges_plot = None
		self.show_image = True
		self.show_points = True
		self.show_edges = True
		self.show_areas = True
		self.image_changed = False
		self.points_changed = False
		self.edges_changed = False
		self.areas_changed = False
	
	def refresh (self):
	#	self.clear_canvas()
		self.plot_image()
		self.plot_points()
		self.plot_edges()
		self.plot_areas()
		self.draw()
	
	def update_image (self, image = None):
		self.image = image
		self.image_changed = True
		self.refresh()
	
	def update_points (self, points = None):
		self.points = points
		self.points_changed = True
		self.refresh()
	
	def update_edges (self, edges = None):
		self.edges = edges
		self.edges_changed = True
		self.refresh()
	
	def update_areas (self, areas = None):
		self.areas = areas
		self.areas_changed = True
		self.refresh()
	
	def update_switches (self, show_image = True, show_points = True,
							show_edges = True, show_areas = True):
		if show_image != self.show_image:
			self.image_changed = True
			self.show_image = show_image
		if show_points != self.show_points:
			self.points_changed = True
			self.show_points = show_points
		if show_edges != self.show_edges:
			self.edges_changed = True
			self.show_edges = show_edges
		if show_areas != self.show_areas:
			self.areas_changed = True
			self.show_areas = show_areas
		self.refresh()
	
	def plot_image (self):
		if self.image is None:
			return False
		if not self.image_changed:
			return False
		self.image_changed = False
		self.remove_plot_element(self.image_plot)
		self.image_plot = None
		if self.show_image:
			self.image_plot = self.ax.imshow(self.image,
											 cmap = 'Grays_r',
											 zorder = 5)
	
	def plot_areas (self):
		if self.areas is None:
			return False
		if not self.areas_changed:
			return False
		self.areas_changed = False
		self.remove_plot_element(self.areas_plot)
		self.areas_plot = None
		if self.show_areas:
			cmap = colormaps.get_cmap('hsv')
			norm = Normalize(vmin = np.amin(self.areas),
										vmax = np.amax(self.areas))
			self.areas_plot = self.ax.imshow(self.areas,
											 cmap = cmap,
											 norm = norm,
											 alpha = 0.2,
											 zorder = 6)
	
	def plot_edges (self):
		if self.edges is None:
			return False
		if not self.edges_changed:
			return False
		self.edges_changed = False
		self.remove_plot_element(self.edges_plot)
		self.edges_plot = None
		if self.show_edges:
			self.edges_plot = self.ax.imshow(self.edges,
											cmap = 'Grays_r',
											alpha = self.edges.astype(float),
											zorder = 7)
	
	def plot_points (self):
		pass
	

################################################################################
# main window #
###############

class Window(QWidget):
	def __init__ (self):
		super().__init__()
		self.title = "Tension Tool"
		self.canvas = MPLCanvas()
		self.toolbar = NavigationToolbar(self.canvas, self)
		self.setWindowTitle(self.title)
		#
		self.image_file_path = None
		self.segment_file_path = None
		self.image = None
		self.points = None
		self.edges = None
		self.areas = None
		self.frame = 0
		self.channel = 0
		#
		self.setup_GUI()
	
	def setup_GUI (self):
		# layout for full window
		main_layout = QVBoxLayout()
		main_layout.addWidget(self.canvas)
		#
		toolbar_layout = QHBoxLayout()
		toolbar_layout.addWidget(self.toolbar)
		self.checkbox_image = setup_checkbox(self.checkboxes,
											toolbar_layout,
											'image',
											True)
		self.checkbox_points = setup_checkbox(self.checkboxes,
											toolbar_layout,
											'points',
											True)
		self.checkbox_edges = setup_checkbox(self.checkboxes,
											toolbar_layout,
											'edges',
											True)
		self.checkbox_areas = setup_checkbox(self.checkboxes,
											toolbar_layout,
											'segments',
											True)
		self.button_zoom = setup_button(self.reset_zoom,
										toolbar_layout,
										'Reset Zoom')
		main_layout.addLayout(toolbar_layout)
		#
		upper_layout = QHBoxLayout()
		self.frame_box = setup_combobox(
							self.select_frame,
							upper_layout, 'Frame:')
		self.channel_box = setup_combobox(
							self.select_channel,
							upper_layout, 'Channel:')
		self.button_find_bounds = setup_button(self.remove_outer,
											upper_layout,
											'Remove Outer')
		self.button_find_bounds = setup_button(self.find_bounds,
											upper_layout,
											'Find Bounds')
		self.button_save_bounds = setup_button(self.save_bounds,
											upper_layout,
											'Save Bounds')
		main_layout.addLayout(upper_layout)
		#
		image_file_layout = QHBoxLayout()
		self.button_open_image = setup_button(self.open_image_file,
										image_file_layout,
										'Open Image')
		image_file_box, self.image_file_text = setup_labelbox(
						'<font color="red">Image File Name: </font>',
						'No file opened.')
		image_file_layout.addWidget(image_file_box)
		main_layout.addLayout(image_file_layout)
		#
		segment_file_layout = QHBoxLayout()
		self.button_open_segment = setup_button(self.open_segment_file,
										segment_file_layout,
										'Open Segments')
		segment_file_box, self.segment_file_text = setup_labelbox(
						'<font color="red">Segments File Name: </font>',
						'No file opened.')
		segment_file_layout.addWidget(segment_file_box)
		main_layout.addLayout(segment_file_layout)
		#
		self.setLayout(main_layout)
	
	def reset_zoom (self):
		self.canvas.reset_zoom()
	
	def checkboxes (self):
		self.canvas.update_switches(
						show_image = self.checkbox_image.isChecked(),
						show_points = self.checkbox_points.isChecked(),
						show_areas = self.checkbox_areas.isChecked())
	
	def update_image (self):
		if self.image is None:
			return False
		if self.channel < self.image.shape[-1]:
			self.canvas.update_image(self.image[self.frame,:,:,self.channel])
		else:
			self.canvas.update_image(np.sum(self.image[self.frame,:,:,:],
												axis=-1))
		self.canvas.reset_zoom()
	
	def update_areas (self):
		if self.areas is None:
			return False
		self.canvas.update_areas(self.areas)
		self.canvas.reset_zoom()
	
	def update_edges (self):
		if self.edges is None:
			return False
		self.canvas.update_edges(self.edges)
		self.canvas.reset_zoom()
	
	def select_frame (self):
		self.frame = self.frame_box.currentIndex()
		self.update_image()
	
	def select_channel (self):
		self.channel = self.channel_box.currentIndex()
		self.update_image()
	
	def file_dialog (self):
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		file_name, _ = QFileDialog.getOpenFileName(self,
								'Open TIF File', '',
								'TIF Files (*.tif);;' + \
								'H5 Files (*.h5);;' + \
								'All Files (*)',
								options=options)
		if file_name == '':
			return None
		else:
			file_path = Path(file_name)
			if file_path.suffix.lower() == '.tif' or \
			   file_path.suffix.lower() == '.tiff' or \
			   file_path.suffix.lower() == '.h5':
				return file_path
			else:
				return None
	
	def open_image_file (self):
		self.image_file_path = None
		self.image = None
		self.image_file_text.setText('No file opened.')
		self.image_file_path = self.file_dialog()
		if self.image_file_path is not None:
			self.image_file_text.setText(str(self.image_file_path))
			if self.image_file_path.suffix.lower() == '.tif' or \
					self.image_file_path.suffix.lower() == '.tiff':
				self.image = read_tiff(self.image_file_path)
				if len(self.image.shape) == 3:
					self.image = self.image[:,:,:,np.newaxis]
					self.channel_box.addItem('0')
					current_index = 0
				else:
					for index in range(self.image.shape[3]):
						self.channel_box.addItem(f'{index:d}')
					self.channel_box.addItem('all')
					current_index = self.image.shape[3]
				self.channel_box.setCurrentIndex(current_index)
				for index in range(self.image.shape[0]):
					self.frame_box.addItem(f'{index:d}')
				self.frame_box.setCurrentIndex = 0
		self.update_image()
	
	def open_segment_file (self):
		self.segment_file_path = None
		self.areas = None
		self.segment_file_text.setText('No file opened.')
		self.segment_file_path = self.file_dialog()
		if self.segment_file_path is not None:
			segments = None
			self.segment_file_text.setText(str(self.segment_file_path))
			if self.segment_file_path.suffix.lower() == '.tif' or \
					self.segment_file_path.suffix.lower() == '.tiff':
				segments = read_tiff(self.segment_file_path)[0,:,:]
#			elif self.segment_file_path.suffix.lower() == '.h5':
#				h5file = h5py.File(self.segment_file_path, 'r')
#				data = h5file['exported_data']
#				segments = data[:,:,0]
			if segments is not None:
				self.areas = randomise_segments(segments)
		self.update_areas()
	
	def remove_outer (self):
		self.areas = remove_outer(self.areas)
		self.update_areas()
	
	def find_bounds (self):
		if self.areas is None:
			return False
#		points, possible = find_points(self.areas, min_distance = 2)
#		self.edges = np.zeros_like(self.areas)
#		self.edges[points[:,0], points[:,1]] = 1
		self.edges = StandardLabelToBoundary(mode='thick')(
							self.areas.reshape(1,
											self.areas.shape[0],
											self.areas.shape[1]))[0,0]
		self.update_edges()
	
	def save_bounds (self):
		if self.edges is None:
			return False
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		file_name, _ = QFileDialog.getSaveFileName(self,
								'Save TIF File', '',
								'TIF Files (*.tif);;' + \
								'All Files (*)',
								options=options)
		if file_name == '':
			return False
		file_path = Path(file_name)
		if file_path.suffix.lower() != '.tif':
			file_path = file_path.with_suffix('.tif')
		output_array = np.zeros_like(self.edges.astype(int))
		output_array[self.edges != 0] = 255
		im = Image.fromarray(output_array.astype(np.uint8))
		im.save(file_path)

################################################################################

if __name__ == "__main__":
	QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
	QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec_())

################################################################################
# EOF

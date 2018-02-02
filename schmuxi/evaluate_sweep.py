'''Interactive tool to evaluate spectral sweeps.
To use it type the following command:
    
bokeh serve --show evaluate_map.py

Make sure, you have a config_file with the right name in the same folder.'''
import numpy as np
import matplotlib.pyplot as plt
import yaml
from bokeh.plotting import curdoc, gridplot, figure, show, output_file
from bokeh.layouts import column, widgetbox, layout
from bokeh.models.widgets import CheckboxButtonGroup, Select, MultiSelect, TextInput
from bokeh.models import Button, TapTool, Slider
from bokeh.events import Tap
import scipy.io as sio
import pandas as pd
from spec_evaluation import Experiment
from math import e


# --- Configration ---

with open("spec_config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

source_dir = cfg["general"]["source_path"]
working_dir = cfg["general"]["working_dir"]
working_file = cfg["sweep_paras"]["file"]
calibration_wavelength = cfg["sweep_paras"]["calibration_wavelength"]
calibration_parameters = cfg["sweep_paras"]["calibration_parameter"]
background_file = cfg["sweep_paras"]["background_file"]

# --- Function Declarations ---



def display_spectrum(event):
    '''Display the spectrum for the clicked/tapped point on the map'''
    new_data = dict()
    new_data["x"] = x2
    new_data["y"] = sweep[int(np.round(event.y)),:]
    
    if background_check.active[0] == 0:
        new_data["y"] = (new_data["y"]-background_list)/(new_data["y"] + background_list + 0.02)
    ds.data = new_data



class SweepImage:
    

    def __init__(self, working_file, seperator="\t"):
        
        self.sweep, self.calibration, self.sweep_parameter = self.load_file(working_file, seperator)
        self.background, self.background_tiled = load_background(np.shape(self.sweep)[0])
        self.x = self.calibration
        self.y = self.sweep_parameter
        


    def load_file(self, working_file, seperator="\t"):
        '''loads a .tsv-file and initializes the sweep-data'''
        data = pd.read_csv(source_dir + working_file, seperator)
        data_matrix = data.as_matrix()
        calibration_wave = pd.read_csv(source_dir + calibration_wavelength, '\t', header=None)
        calibration_wave_list = np.array(list(calibration_wave[0]))
        calibration_param = pd.read_csv(source_dir + calibration_parameters, '\t', header=None)
        calibration_param_list = np.array(list(calibration_param[0]))
        print(np.shape(data_matrix))
        print(np.shape(calibration_wave_list))
        return(data_matrix,
               calibration_wave_list,
               calibration_param_list)


    def load_background(self, number_of_lines):
        '''loads the background spectrum. Be careful. It has to fit.'''
        background_data = pd.read_csv(source_dir + background_file)
        background_list = background_data.as_matrix()[:,1]
        print(background_list)
        print(background_list.shape)
        print(number_of_lines)
        background = np.tile(background_list, (number_of_lines, 1))
        print("Kooowazy")
        return (background_list, background)


    def switch_calibration(scale, conversion_factor=1239.8):
        '''switch between energy [eV] and wavelength [nm]'''
        self.x = 1239.8/self.x
        Session.convert_to_energy = not Session.convert_to_energy
        return conversion_factor/scale
    
    
    def adjust_contrast(self):
        '''adjusts contrast by mapping the values on a power-law and clipping high
        values'''
        z = self.sweep
        
        if background_check.active[0] == 0:
            print(z + self.background_tiled)
            z = (z - self.background_tiled)/(z + self.background_tiled + 0.1)
        
        #Prototype --
        
        min_egy = 1.501
        max_egy = 1.800
        
        
        z = np.clip(z, 0, np.median(z)*threshold_slider.value)
        z = z/(np.max(z) + 0.02)
        z = np.power(z, contrast_slider.value)
         
        return z


    def make_image(self):
        '''renders an image of the sweep.'''
        z = self.adjust_contrast()

        stripe_image = sweep_figure.image(image=[z], 
                                          x=0, y=0,
                                          dw=np.shape(z)[1],
                                          dh=np.shape(z)[0],
                                          palette="Inferno256")


    def adjust_marker(attr, old, new):
        '''adjust the position of the marker'''
        new_data = dict()
        new_data["x"] = [min(x2)+marker_slider.value*(max(x2)-min(x2)), min(x2)+marker_slider.value*(max(x2)-min(x2))]
        new_data["y"] = [0,max(ds.data["y"])]
        ds2.data = new_data


    def publish():
        '''publishes the currently displayed spectrum, using spec_evaluation.py'''
        # Bad things can happen here. Find out and fix!
        publish_x = ds.data["x"]
        publish_y = ds.data["y"]
        publish_data = pd.DataFrame({'index': publish_x, 'values': publish_y})
        erase_cosmics = True
        y_scale = None
        if sweep_type.value == 'Reflection':
            erase_cosmics = False
            if background_check.active[0] == True:
                y_scale = "DR/R"
        spectrum = Session.adjust_spectrum(publish_data, 
                                           background=False, 
                                           overwrite_exposure=True,
                                           overwrite_rescaling=True,
                                           erase_cosmics = erase_cosmics)
        plot = Session.plot_spectrum(spectrum)
        Session.plot_to_png(plot, export_name.value + '.png')
        Session.save_as_csv(publish_data, export_name.value + '.csv')


    def fix_intervall():
        '''changes the intervall in Energy that contributes to the sweep image.'''

    
    def widgets(self):
        
        self.marker_slider = Slider(start=0,
                                    end=1,
                                    value=0.5,
                                    step=0.002,
                                    title="Marker")
        self.marker_slider.on_change('value', adjust_marker)

        self.energy_wavelength = Button(label="Fuck this up")
        self.energy_wavelength.on_click(self.switch_calibration)

        self.publish_button = Button(label="Fool Referees")
        self.publish_button.on_click(publish)

        self.threshold_slider = Slider(start=0,
                                       end=10,
                                       value=3,
                                       step=0.02,
                                       title="Upper Threshold / times median")
                
        self.contrast_slider = Slider(start=0,
                                      end=10,
                                      value=3,
                                      step=0.02,
                                      title="Contrast")
        #contrast_slider.on_change('value', adjust_contrast)

        self.contrast_button = Button(label="Fuck up Contrast")
        self.contrast_button.on_click(adjust_contrast)

        self.background_check = CheckboxButtonGroup(labels=["Use Background"], active=[1])

        self.export_name = TextInput(value="FAAAKE", title="File Name")

        self.sweep_type = Select(title="Sweep Type",
                                 value="Photoluminescence",
                                 options=["Photoluminescence",
                                          "Reflection"]) 

        self.sweep_figure = figure(width=500,
                                   height=500,
                                   x_range=(-1,len(x)),
                                   y_range=(-1,len(y)),
                                   tools=TOOLS)

        self.spec = figure(width=500, height = 500, tools=TOOLS)

        stripe_image = sweep_figure.image(image=[z], 
                                          x=0, y=0,
                                          dw=np.shape(z)[1],
                                          dh=np.shape(z)[0],
                                          palette="Inferno256")
        z_datasource = stripe_image.data_source

        self.sweep_figure.on_event(Tap, display_spectrum)
# --- Display ---

panel = gridplot([[sweep_figure, spec]])

curdoc().add_root(column(marker_slider, energy_wavelength, panel,
    publish_button, contrast_slider, contrast_button, threshold_slider,
    background_check, export_name, sweep_type))
# --- Skript starts ---


sweep, calibration_wave, calibration_param = load_file(working_file)



Session = Experiment()
Session.convert_to_energy = False

x2=1239.8/calibration_wave

background_list, background = load_background(np.shape(z)[0])
# --- Data Visualization ---

TOOLS="hover,crosshair,pan,wheel_zoom,box_zoom,reset,tap,previewsave"


print(z_datasource)

# --- Interfaces ---

marker_start_x = np.median(x2)
r = spec.line(x=[],y=[], line_color="red")
marker = spec.line(x=[marker_start_x,marker_start_x],y=[0,10], line_color="green")
ds = r.data_source
ds2 = marker.data_source



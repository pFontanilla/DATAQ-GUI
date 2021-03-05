import tkinter as tk
from tkinter.ttk import Combobox
from tkinter import messagebox, StringVar
import tkinter.font as tkFont
import matplotlib
from mcculw import ul
from mcculw.enums import (BoardInfo, InfoType, ErrorCode, EventType, InterfaceType, ExpansionInfo, TempScale,
                         DigitalPortType, AiChanType, TcType, TempScale, AnalogInputMode)
from mcculw.ul import ULError
from PIL import Image, ImageTk
from cust_widgets.TerminalButton import TerminalButton
from cust_widgets.Terminal import MyTerminal, ChTypes64, ADCSubtypes2, DIOSubtypes, ADCSubtypes
from functools import partial
import os, threading, re
matplotlib.use("TkAgg")

class UIExample(tk.Frame, object):
    """Provides a base class for all UI-based examples in this package."""

    # Intended for module USB-2416 and AI-EXP32

    def __init__(self, master=None):
        super(UIExample, self).__init__(master)

        self.board_num = 0

        example_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(example_dir, 'MCC.ico')

        # Initialize tkinter properties
        master.iconbitmap(icon_path)
        master.wm_title(type(self).__name__)
        master.minsize(width=400, height=75)
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        self.master = master
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.grid(sticky=tk.NSEW)

    def on_closing(self):
        if tk.messagebox.askokcancel("Quit", "Warning:\nAny unsaved work will be lost.\nDo you want to quit?"):
            self.master.destroy()

    def create_unsupported_widgets(self, error=False):
        incompatible_label = tk.Label(self, fg="red")
        incompatible_label["text"] = "Board " + str(self.board_num) + " "
        if error:
            incompatible_label["text"] += "was not found."
        else:
            incompatible_label["text"] += "is not compatible with this example."
        incompatible_label.pack(fill=tk.X, side=tk.LEFT, anchor=tk.NW)

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

    def configure_first_detected_device(self):
        ul.ignore_instacal()
        devices = ul.get_daq_device_inventory(InterfaceType.ANY)
        if not devices:
            print("No device detected")
            # raise ULError(ErrorCode.BADBOARD)
            return None

        # Add the first DAQ device to the UL with the specified board number
        ul.create_daq_device(self.board_num, devices[0])


def show_ul_error(ul_error):
    message = 'A UL Error occurred.\n\n' + str(ul_error)
    messagebox.showerror("Error", message)

class NewWindow(tk.Toplevel):

    def __init__(self, master, board_num):
        super().__init__(master=master)
        self.master = master
        self.board_num = board_num
        self.master.withdraw()
        windowWidth = 694
        windowHeight = 640
        self.title("New Window")
        self.geometry("{}x{}".format(windowWidth, windowHeight))
        self.resizable(False, False)
        font_style = tkFont.Font(family="Helvetica", size=-7, weight="bold")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.deiconify()
            self.destroy()

    @staticmethod
    def set_ch_as_tc(channel_num=0):
        # Set channel to thermocouple mode, with input_mode as differential
        ul.a_chan_input_mode(0, channel_num, AnalogInputMode.DIFFERENTIAL)
        ul.set_config(InfoType.BOARDINFO, 0, channel_num, BoardInfo.ADCHANTYPE, AiChanType.TC)

    @staticmethod
    def set_ch_as_volt_se(channel_num=0):
        # Set channel to single-ended voltage mode
        ul.a_chan_input_mode(0, channel_num, AnalogInputMode.Single_Ended)
        ul.set_config(InfoType.BOARDINFO, 0, channel_num, BoardInfo.ADCHANTYPE, AiChanType.VOLTAGE)

    @staticmethod
    def set_ch_as_volt_diff(channel_num=0):
        # Set channel to differential voltage mode
        ul.a_chan_input_mode(0, channel_num, AnalogInputMode.DIFFERENTIAL)
        ul.set_config(InfoType.BOARDINFO, 0, channel_num, BoardInfo.ADCHANTYPE, AiChanType.VOLTAGE)

    @staticmethod
    def set_ch_tc_type(channel_num=0, tc_type=TcType.K):
        # Set the thermocouple type of a channel
        # Function must be utilized for every TC channel, as there are no default TC channels
        ul.set_config(InfoType.BOARDINFO, 0, channel_num, BoardInfo.CHANTCTYPE, tc_type)

    @staticmethod
    def set_ch_data_rate(channel_num=0, data_rate=100):
        # Set datarate of A/D channel
        # data_rate: 2 (2.5), 5, 10, 25, 50, 60, 100, 500, 1000, 2000, 3750. The data rate is specified as S/s.
        ul.set_config(InfoType.BOARDINFO, 0, channel_num, BoardInfo.ADDATARATE, data_rate)

class DaqDevDiscovery01(UIExample):
    def __init__(self, master):
        super(DaqDevDiscovery01, self).__init__(master)

        self.board_num = 0

        self.device_created = False

        # Tell the UL to ignore any boards configured in InstaCal
        ul.ignore_instacal()

        self.create_widgets(master)

    def discover_devices(self):
        self.inventory = ul.get_daq_device_inventory(InterfaceType.ANY)

        if len(self.inventory) > 0:
            combobox_values = []
            for device in self.inventory:
                combobox_values.append(str(device))

            self.devices_combobox["values"] = combobox_values
            self.devices_combobox.current(0)
            self.status_label["text"] = (str(len(self.inventory))
                                         + " DAQ Device(s) Discovered")
            self.devices_combobox["state"] = "readonly"
            self.flash_led_button["state"] = "normal"
        else:
            self.devices_combobox["values"] = [""]
            self.devices_combobox.current(0)
            self.status_label["text"] = "No Devices Discovered"
            self.devices_combobox["state"] = "disabled"
            self.flash_led_button["state"] = "disabled"

    def flash_led(self):
        try:
            # Flash the device LED
            ul.flash_led(self.board_num)
        except ULError as e:
            show_ul_error(e)

    def selected_device_changed(self, *args):  # @UnusedVariable
        selected_index = self.devices_combobox.current()
        inventory_count = len(self.inventory)

        if self.device_created:
            # Release any previously configured DAQ device from the UL.
            ul.release_daq_device(self.board_num)
            self.device_created = False

        if inventory_count > 0 and selected_index < inventory_count:
            descriptor = self.inventory[selected_index]
            # Update the device ID label
            self.device_id_label["text"] = descriptor.unique_id

            # Create the DAQ device from the descriptor
            # For performance reasons, it is not recommended to create
            # and release the device every time hardware communication is
            # required. Instead, create the device once and do not release
            # it until no additional library calls will be made for this
            # device
            ul.create_daq_device(self.board_num, descriptor)
            self.device_created = True

    def create_widgets(self, master):
        '''Create the tkinter UI'''
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.X, anchor=tk.NW)

        discover_button = tk.Button(main_frame)
        discover_button["text"] = "Discover DAQ Devices"
        discover_button["command"] = self.discover_devices
        discover_button.pack(padx=3, pady=3)

        self.status_label = tk.Label(main_frame)
        self.status_label["text"] = "Status"
        self.status_label.pack(anchor=tk.NW, padx=3, pady=3)

        results_group = tk.LabelFrame(self, text="Discovered Devices")
        results_group.pack(fill=tk.X, anchor=tk.NW, padx=3, pady=3)

        self.selected_device_textvar = StringVar()
        self.selected_device_textvar.trace('w', self.selected_device_changed)
        self.devices_combobox = Combobox(
            results_group, textvariable=self.selected_device_textvar)
        self.devices_combobox["state"] = "disabled"
        self.devices_combobox.pack(fill=tk.X, padx=3, pady=3)

        device_id_frame = tk.Frame(results_group)
        device_id_frame.pack(anchor=tk.NW)

        device_id_left_label = tk.Label(device_id_frame)
        device_id_left_label["text"] = "Device Identifier:"
        device_id_left_label.grid(row=0, column=0, sticky=tk.W, padx=3, pady=3)

        self.device_id_label = tk.Label(device_id_frame)
        self.device_id_label.grid(row=0, column=1, sticky=tk.W, padx=3, pady=3)

        self.flash_led_button = tk.Button(results_group)
        self.flash_led_button["text"] = "Flash LED"
        self.flash_led_button.bind("<Button>", lambda e: NewWindow(master, self.board_num))
        self.flash_led_button["command"] = self.flash_led
        self.flash_led_button["state"] = "disabled"
        self.flash_led_button.pack(padx=3, pady=3)

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

        quit_button = tk.Button(button_frame)
        quit_button["text"] = "Quit"
        quit_button["command"] = self.master.destroy
        quit_button.grid(row=0, column=1, padx=3, pady=3)


# Start the example if this module is being run
if __name__ == "__main__":
    # Start the example
    DaqDevDiscovery01(master=tk.Tk()).mainloop()

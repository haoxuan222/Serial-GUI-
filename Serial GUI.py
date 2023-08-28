import tkinter as tk
from tkinter import ttk
import serial
from tkinter import messagebox
import threading
import queue
import serial.tools.list_ports
import configparser

class SerialConfigurationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.config_window = tk.Toplevel(self.parent)
        self.config_window.title("Serial Configuration")

        self.selected_baud_rate = tk.StringVar(value="19200")
        self.selected_data_bits = tk.StringVar(value="8")
        self.selected_stop_bits = tk.StringVar(value="1")
        self.selected_parity = tk.StringVar(value="None")

        self.create_configuration_widgets()
        self.load_settings()  # Load saved settings

    def create_configuration_widgets(self):
        self.baud_rate_label = ttk.Label(self.config_window, text="Baud Rate:")
        self.baud_rate_label.pack(padx=10, pady=5)

        baud_rate_options = ["9600", "19200", "38400", "57600", "115200"]
        self.baud_rate_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_baud_rate, values=baud_rate_options)
        self.baud_rate_combobox.pack(padx=10, pady=5)

        # Add other configuration widgets here
        self.data_bits_label = ttk.Label(self.config_window, text="Data Bits:")
        self.data_bits_label.pack(padx=10, pady=5)

        data_bits_options = ["5", "6", "7", "8"]
        self.data_bits_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_data_bits, values=data_bits_options)
        self.data_bits_combobox.pack(padx=10, pady=5)

        self.stop_bits_label = ttk.Label(self.config_window, text="Stop Bits:")
        self.stop_bits_label.pack(padx=10, pady=5)

        stop_bits_options = ["1", "1.5", "2"]
        self.stop_bits_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_stop_bits, values=stop_bits_options)
        self.stop_bits_combobox.pack(padx=10, pady=5)

        self.parity_label = ttk.Label(self.config_window, text="Parity:")
        self.parity_label.pack(padx=10, pady=5)

        parity_options = ["None", "Even", "Odd", "Mark", "Space"]
        self.parity_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_parity, values=parity_options)
        self.parity_combobox.pack(padx=10, pady=5)

        self.save_button = ttk.Button(self.config_window, text="Save", command=self.save_settings)
        self.save_button.pack(padx=10, pady=10)

        self.set_default_button = ttk.Button(self.config_window, text="Set to Default", command=self.set_default_settings)
        self.set_default_button.pack(padx=10, pady=10)
        
    def save_settings(self):
        config = configparser.ConfigParser()
        config["Serial"] = {
            "baud_rate": self.selected_baud_rate.get(),
            "data_bits": self.selected_data_bits.get(),
            "stop_bits": self.selected_stop_bits.get(),
            "parity": self.selected_parity.get()
        }
        with open("settings.ini", "w") as config_file:
            config.write(config_file)

        tk.messagebox.showinfo("Success", "Settings saved successfully!")

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read("settings.ini")

        if "Serial" in config:
            serial_config = config["Serial"]
            self.selected_baud_rate.set(serial_config.get("baud_rate", "19200"))
            self.selected_data_bits.set(serial_config.get("data_bits", "8"))
            self.selected_stop_bits.set(serial_config.get("stop_bits", "1"))
            self.selected_parity.set(serial_config.get("parity", "None"))

    def set_default_settings(self):
        self.selected_baud_rate.set("19200")
        self.selected_data_bits.set("8")
        self.selected_stop_bits.set("1")
        self.selected_parity.set("None")

class SerialCommunicationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Communication App")
        self.serial_port = ""
        self.after_id = None
        self.configuration_window = None
        self.sending_data = True  # Set the flag to True while sending data
        self.receive_thread_running = False
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.data_queue = queue.Queue()  # Initialize data_queue here
        self.load_serial_settings()
        self.frontend_frame = ttk.LabelFrame(self.root, text="Frontend Window")
        self.frontend_frame.grid(row=0, column=0, sticky = "nsew")
        
        self.target_baud_rate = 19200
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.clear_log_button = ttk.Button(self.frontend_frame, text="Clear Log", command=self.clear_log_frontend)
        self.clear_log_button.grid(row=4, columnspan=2, padx=5, pady=5)

        self.create_frontend_widgets()
        self.backend_frame = None
        

    def create_frontend_widgets(self):
        self.port_label = ttk.Label(self.frontend_frame, text="Select COM Port:")
        self.port_label.grid(row=2, column=0, padx=5, pady=5)

        self.available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.selected_port = tk.StringVar(value=self.available_ports[0] if self.available_ports else "")
        self.port_combobox = ttk.Combobox(self.frontend_frame, textvariable=self.selected_port, values=self.available_ports)
        self.port_combobox.grid(row=2, column=1, padx=5, pady=5)

        self.port_status = tk.StringVar()
        self.port_status.set("Port Closed")
        self.port_status_label = ttk.Label(self.frontend_frame, textvariable=self.port_status)
        self.port_status_label.grid(row=3, columnspan=2, padx=5, pady=5)

        self.port_open_button = ttk.Button(self.frontend_frame, text="Open Port", command=self.open_port)
        self.port_open_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.port_close_button = ttk.Button(self.frontend_frame, text="Close Port", command=self.closed_port)
        self.port_close_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.data_receive_monitor = tk.Text(self.frontend_frame, height=10, width=40)
        self.data_receive_monitor.grid(row=1, columnspan=2, padx=5, pady=5)
        
        self.password_label = ttk.Label(root, text="Password:")
        self.password_label.grid(row=3, column=0, padx=2, pady=2)
        
        self.password_entry = ttk.Entry(root, show="*")
        self.password_entry.grid(row=4, column=0, padx=5, pady=5)
        
        self.backend_frame = None
        self.receive_thread = None

    def open_command_panel(self):
        command_panel_window = tk.Toplevel(self.root)
        command_panel_window.title("Command Panel")

        command_buttons = [
            ("Product Info", b"3:PRD?\r\n"),
            ("Firmware Version", b"3:FWV?\r\n"),
            ("Set IR Library", b"3:irdev-B079010FE20FE20FE20F000100103600240ED80100000000100010001000320100000200051E0900001003C900860041090800100536008600410910001005360086004100240011DA2700C50000D711DA27004200005411DA270000392000A0000006600000C18000C5151E051501D4D80F051502D4D800081E003840004048D7081E013840104048E70B1003C8CC0A03C8CC0303C8CC0503C8CC071616045F004806043F003606083F04123704153F091E37040C0803CCD00F03CCD00000D4070104000216080605040111232302030217020A1A03B0B40303B0B40403B0B40006B0B406B8C03206B0B402B8C0C0170A1E05010300051E010100147F04090A081205036108064807801603F016010A078089C008890B06200100021B1C4149C13C007800B400F0002C016801A401E0011C0258029402D002010505036109063607801603F016010D078089C009890B061A0100021C1D414991C6038607460B060FC6128616461A061EC6210105060001A11E0001060001B1210084\r\n"),
            ]
        for label, data in command_buttons:
            button = ttk.Button(command_panel_window, text=label, command=lambda d=data: self.send_command_data(d))
            button.pack(padx=10, pady=5)
    
    def send_command_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write(data)
            self.data_send_monitor.insert(tk.END, f">> Sent: {data}\n")
            self.data_send_monitor.see(tk.END)
            self.sending_data = True

    def update_port_status(self):
        selected_port = self.selected_port.get()
        if self.serial_port and self.serial_port.is_open:
            self.port_status.set(f"Port {selected_port} is Open")
            self.port_status_label.configure(foreground="green")

        else:
            self.port_status.set(f"Port is Closed")
            self.port_status.set(f"Port {selected_port} is Closed")
            self.port_status_label.configure(foreground="red")

    def start_receive_thread(self):
        if self.receive_thread_running:
            return #to verify the thread is running

        def receive_data():
            self.receive_thread_running = True
            while self.serial_port and self.serial_port.is_open:
                    try:
                        self.serial_port = self.serial_port
                        if self.serial_port.baudrate == self.target_baud_rate:
                            data = self.serial_port.readline().decode()
                            if data:
                                self.data_queue.put(data)
                        else:
                            tk.messagebox.showerror("Error", "Incorrect baud used. Please use 19200 for baud.")
                            break
                    except serial.SerialException:
                        break                        
            self.receive_thread_running = False

        self.receive_thread = threading.Thread(target=receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        self.root.after(1, self.update_received_data)

    def stop_receive_thread(self):
        if not self.receive_thread_running:
            return  # Verify the thread is running

        def stop_receive_data():
            self.receive_thread_running = False
            print(self.serial_port)
            if self.serial_port and not self.serial_port.is_open:
                self.serial_port.close()
                print("Serial port closed.")

        # Rename the thread object to avoid naming conflict
        stop_thread = threading.Thread(target=stop_receive_data)
        stop_thread.daemon = True
        stop_thread.start()

        self.root.after(1, self.update_received_data)

    def update_received_data(self):
        while not self.data_queue.empty():
            received_data = self.data_queue.get()
            self.data_receive_monitor.insert(tk.END, received_data + '\n')
            self.data_receive_monitor_backend.insert(tk.END, received_data + '\n')
            self.data_receive_monitor_backend.see(tk.END)   
            if self.serial_port and self.serial_port.is_open:
                    if received_data.strip() == ".":
                        self.process_incoming_data(received_data)

        self.root.after(1, self.update_received_data)

    def start_monitoring_data(self):
        self.update_data_monitors()
    
    #data receive
    def process_received_data(self):
        while not self.data_queue.empty():
            received_data = self.data_queue.get()
            self.data_receive_monitor.insert(tk.END, received_data)
            self.data_receive_monitor_backend.insert(tk.END, received_data)
            self.data_receive_monitor_backend.see(tk.END)
            self.root.update()  # Explicitly update the GUI
        self.root.after(1, self.process_received_data)
        
    def update_data_monitors(self):
        while not self.data_queue.empty():
            received_data = self.data_queue.get()
            self.data_receive_monitor.insert(tk.END, received_data)
            self.data_receive_monitor_backend.insert(tk.END, received_data)
            self.data_receive_monitor_backend.see(tk.END)

        if not self.sending_data and self.serial_port and self.serial_port.is_open:
            sent_data = self.send_data_entry.get()
            if sent_data:
                self.data_send_monitor.insert(tk.END, sent_data + '\n')
                self.data_send_monitor_backend.insert(tk.END, sent_data + '\n')
                self.data_send_monitor.see(tk.END)
                self.data_send_monitor_backend.see(tk.END)
                self.twoe_byte_detected = False

        self.update_data_job = self.root.after(1, self.update_data_monitors)

    def clear_log_frontend(self):
        self.data_receive_monitor.delete('1.0', tk.END)

    def open_port(self):
        port_name = self.selected_port.get()
        if not self.serial_port or not self.serial_port.is_open:
            baud_rate = int(self.serial_config["baud_rate"].get())  # Use the loaded value
            self.serial_port = serial.Serial(port_name, baud_rate, timeout=0.5)
            self.update_port_status()
            self.start_receive_thread()
            print(self.serial_port)

    def closed_port(self):
        if self.serial_port and self.serial_port.is_open:
            self.stop_receive_thread()
            self.serial_port = self.serial_port
            self.serial_port.close()
            self.update_port_status()
    
    def open_backend_window(self):
        entered_password = self.password_entry.get()
        
        while True:
            if entered_password == "123":
                        if hasattr(self, "backend_frame") and self.backend_frame is not None and self.backend_frame.winfo_exists():
                            tk.messagebox.showinfo("Info", "Backend window is already open.")
                                
                        elif self.backend_frame is None:
                            self.backend_frame = tk.Toplevel(self.root)
                            self.backend_frame.title("Communication Window")

                            self.send_data_label = ttk.Label(self.backend_frame, text="Send Data:")
                            self.send_data_label.grid(row=0, column=0, padx=5, pady=5)

                            self.send_data_entry = ttk.Entry(self.backend_frame)
                            self.send_data_entry.grid(row=0, column=1, padx=5, pady=5)

                            self.data_format_var = tk.StringVar(value="String")
                            self.data_format_label = ttk.Label(self.backend_frame, text="Data Format:")
                            self.data_format_label.grid(row=1, column=0, padx=5, pady=5)
                            self.after_id = self.root.after(1, self.update_data_monitors)  # Store the after_id

                            config_button = ttk.Button(self.backend_frame, text="Configuration Window", command=app.open_configuration_window)
                            config_button.grid(row=2, column=1, pady=10)

                            command_panel_button = ttk.Button(self.backend_frame, text="Open Command Panel", command=self.open_command_panel)
                            command_panel_button.grid(row=2, column=2, pady=5)

                            data_format_options = ["Hex", "Binary", "Octal", "String"]
                            for idx, data_format in enumerate(data_format_options):
                                rb = ttk.Radiobutton(self.backend_frame, text=data_format, variable=self.data_format_var, value=data_format)
                                rb.grid(row=1, column=idx + 1, padx=5, pady=5)

                            self.add_crlf_var = tk.BooleanVar(value=True)
                            self.add_crlf_checkbox = ttk.Checkbutton(self.backend_frame, text="Add Carriage Return and Line Feed", variable=self.add_crlf_var)
                            self.add_crlf_checkbox.grid(row=3, columnspan=4, padx=5, pady=5)

                            self.send_button = ttk.Button(self.backend_frame, text="Send", command=self.send_data)
                            self.send_button.grid(row=0, column=2, padx=5, pady=5)
                        
                            # Data Sending Monitor Section
                            self.data_send_label = ttk.Label(self.backend_frame, text="Data Sending Monitor:")
                            self.data_send_label.grid(row=4, column=0, padx=5, pady=5, columnspan=3)
                            
                            self.data_send_monitor = tk.Text(self.backend_frame, height=5, width=40)
                            self.data_send_monitor.grid(row=5, column=0, padx=5, pady=5, columnspan=3)
                            
                            # Data Receiving Monitor Section
                            self.data_receive_label = ttk.Label(self.backend_frame, text="Data Receiving Monitor:")
                            self.data_receive_label.grid(row=6, column=0, padx=5, pady=5, columnspan=3)
                            
                            self.data_receive_monitor_backend = tk.Text(self.backend_frame, height=10, width=40)
                            self.data_receive_monitor_backend.grid(row=7, column=0, padx=5, pady=5, columnspan=3)

                            self.clear_log_button_backend = ttk.Button(self.backend_frame, text="Clear Log", command=self.clear_log_backend)
                            self.clear_log_button_backend.grid(row=8, column=0, columnspan=3, padx=5, pady=5)

                            self.backend_frame.protocol("WM_DELETE_WINDOW", self.close_backend_window)
                            self.start_monitoring_data()
            else:
                tk.messagebox.showerror("Error", "Invalid password, Please Insert Again")
            break
        
    def close_backend_window(self):
        self.backend_frame.destroy()  # Destroy the window
        self.backend_frame = None 

    def clear_log_backend(self):
        self.data_receive_monitor_backend.delete('1.0', tk.END)
        self.data_send_monitor_backend.delete('1.0', tk.END)

    def send_data(self):
        if self.serial_port and self.serial_port.is_open:
            data = self.send_data_entry.get()
            if data:
                if self.add_crlf_var.get():
                    data += "\r\n"
                data_format = self.data_format_var.get()

                # Convert data to the selected format
                if data_format == "Hex":
                    data = bytes.fromhex(data)
                elif data_format == "Binary":
                    data = int(data, 2).to_bytes((len(data) + 7) // 8, byteorder="big")
                elif data_format == "Octal":
                    data = int(data, 8).to_bytes((len(data) + 2) // 3, byteorder="big")
                elif data_format == "String":
                    data = data.encode()

                self.serial_port.write(data)
                self.data_send_monitor.insert(tk.END, f">> Sent: {data}\n")
                self.data_send_monitor.see(tk.END)
                self.sending_data = True  # Set the flag to True while sending data

    def create_backend_widgets(self):
        # Data Sending Monitor
        self.data_send_frame = ttk.LabelFrame(self.backend_frame, text="Data Sending Monitor")
        self.data_send_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.send_data_label = ttk.Label(self.data_send_frame, text="Send Data:")
        self.send_data_label.grid(row=0, column=0, padx=5, pady=5)

        self.send_data_entry = ttk.Entry(self.data_send_frame)
        self.send_data_entry.grid(row=0, column=1, padx=5, pady=5)

        self.send_button = ttk.Button(self.data_send_frame, text="Send", command=self.send_data)
        self.send_button.grid(row=0, column=2, padx=5, pady=5)

        self.data_send_monitor_backend = tk.Text(self.data_send_frame, height=5, width=40)
        self.data_send_monitor_backend.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        
        # Data Receiving Monitor
        self.data_receive_frame = ttk.LabelFrame(self.backend_frame, text="Data Receiving Monitor")
        self.data_receive_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.data_receive_monitor_backend = tk.Text(self.data_receive_frame, height=10, width=40)
        self.data_receive_monitor_backend.grid(row=1, column=0, padx=5, pady=5)

#data send
    def process_incoming_data(self, incoming_data):
        # Add logic to process incoming_data and generate response_data
            response_data = b'\x1B\x1B\x1B\x1B\x1B'
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(response_data)
                self.data_send_monitor.insert(tk.END, f">> Sent: {response_data}\n")
                self.data_send_monitor.see(tk.END)
                self.sending_data = True  # Set the data sending flag
                tk.messagebox.showinfo("Success", "MCU in listening mode!")

    def open_configuration_window(self):
        if self.configuration_window is None:
            self.configuration_window = SerialConfigurationWindow(self.root)
            self.configuration_window.config_window.protocol("WM_DELETE_WINDOW", self.close_configuration_window)
        else:
            tk.messagebox.showinfo("Info", "Configuration window is already open.")

    def close_configuration_window(self):
        self.configuration_window.config_window.destroy()
        self.configuration_window = None

    def load_serial_settings(self):
        config = configparser.ConfigParser()
        config.read("settings.ini")
        self.serial_config = {
            "baud_rate": tk.StringVar(value=config.get("Serial", "baud_rate")),
            "data_bits": tk.StringVar(value=config.get("Serial", "data_bits")),
            "stop_bits": tk.StringVar(value=config.get("Serial", "stop_bits")),
            "parity": tk.StringVar(value=config.get("Serial", "parity"))
        }
        
    def confirm_exit(self):
        result = tk.messagebox.askyesno("Confirm Exit", "Are you sure you want to exit?")
        if result:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialCommunicationApp(root)
    
    backend_button = ttk.Button(root, text="Open Communication Window", command=app.open_backend_window)
    backend_button.grid(row=5, column=0,pady=10)
    
    root.mainloop()

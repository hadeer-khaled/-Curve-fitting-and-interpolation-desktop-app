from tkinter import *
from tkinter import ttk
import tkinter as tk
import pandas as pd
import numpy as np
from tkinter.filedialog import askopenfilename
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import *
from tkinter import ttk
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter.filedialog import askopenfilename
import time
from tkinter.messagebox import showinfo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import threading
import sys
import trace
from tkinter import messagebox
import warnings
from statistics import mean, median
from pandas.tseries.offsets import Tick
import math

warnings.simplefilter('ignore', np.RankWarning)
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', RuntimeWarning)

df = None
back_thread = None

x = []
y = []

x_after_interpolation_at_1_chunks = []
y_after_interpolation_at_1_chunks = []
x_list_of_chunks = []
y_list_of_chunks = []

Y_error = []
x_after_interpolation_at_multiple_chunks = []  # x_after_interpolation_at_multiple_chunks
y_after_interpolation_at_multiple_chunks = []  # y_after_interpolation_at_multiple_chunks

current_chunk_number = 0
chunks_names = []

coefficients = []
coefficients_each_chunk = []
coefficients_extrapolation = []


class thread_with_trace(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


def import_csv_data():
    global df, x, y, latex_ax
    csv_file_path = askopenfilename()
    df = pd.read_csv(csv_file_path)
    x = df.iloc[:, 0].to_numpy()
    y = df.iloc[:, 1].to_numpy()
    draw_data(x, y, [], [], [], 0)
    looping()


def percentage_error(y_percentage, y_interpolated, residuals):  # Done
    y_use = y_percentage
    y_error_use = y_interpolated
    while 1:
        if (len(y_use) - len(y_error_use)) > 0:
            y_use = y_use[0:-1]
        elif (len(y_use) - len(y_error_use)) < 0:
            y_error_use = y_error_use[0:-1]
        else:
            break

    std = np.std(y)
    deviation = (std**2)*len(y)
    rSquare = (deviation - residuals)/deviation
    error = 1 - rSquare
    return error


def polynomial_interpolation(x, y, order): 
    global coefficients 
    residual = 0
    coefficients, residuals, _,_,_ = np.polyfit(x, y, order, full = True)
    y_interpolated = np.polyval(coefficients, x)  # y of the curve for x //y_interpolated
    #error_percent =  math.sqrt((residuals**2)/len(x))
    for each_y,each_y_interpolated in zip(y,y_interpolated):
        residual += (each_y - each_y_interpolated)**2
    error_percent = percentage_error(y, y_interpolated, residual) 
    x_after_interpolation_at_1_chunks = np.linspace(min(x), max(x))
    y_after_interpolation_at_1_chunks = np.polyval(coefficients,
                                                   x_after_interpolation_at_1_chunks)  # polynomial value in the points contained in xx
    return x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, y_interpolated, error_percent, coefficients


def polynomial_extrapolation(x, y, order, extra_percent):  
    global x_after_interpolation_at_1_chunks, coefficients_extrapolation
    x_firstpart, x_secondpart = np.split(x, [int(extra_percent * len(x))])
    y_firstpart, y_secondpart = np.split(y, [int(extra_percent * len(x))])
    coefficients_extrapolation = np.polyfit(x_firstpart, y_firstpart, order)
    y_extrapolated = np.polyval(coefficients_extrapolation, x)
    return y_extrapolated


def peicewise_polynomial_interpolation(x, y, numofChunks, order, overlapping_percentage):  
    global x_after_interpolation_at_multiple_chunks, y_after_interpolation_at_multiple_chunks, Y_error, coefficients_each_chunk, x_list_of_chunks, y_list_of_chunks
    Y_error, x_after_interpolation_at_multiple_chunks, y_after_interpolation_at_multiple_chunks, coefficients_each_chunk = [], [], [], []
    error_list = []
    x_list_of_chunks = chunks_divider(x, numofChunks, overlapping_percentage)
    y_list_of_chunks = chunks_divider(y, numofChunks, overlapping_percentage)

    for x_chunk, y_chunk in zip(x_list_of_chunks, y_list_of_chunks):
        newx, newy, y_interpolated, error_each_chunck, coefficients_of_current_chunk = polynomial_interpolation(x_chunk, y_chunk, order)
        coefficients_each_chunk.append(coefficients_of_current_chunk)
        Y_error = np.concatenate((Y_error, y_interpolated))
        x_after_interpolation_at_multiple_chunks = np.concatenate((x_after_interpolation_at_multiple_chunks, newx))
        y_after_interpolation_at_multiple_chunks = np.concatenate((y_after_interpolation_at_multiple_chunks, newy))
        error_list.append(error_each_chunck)
    error_percent = mean(error_list)
    return x_after_interpolation_at_multiple_chunks, y_after_interpolation_at_multiple_chunks, error_percent, coefficients_each_chunk


def draw_data(x, y, x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, y_extra, error_percent):
    global Main_graph, signal_graph, df, order_value, chunk_num_value, latex_ax, latex_graph

    title = "Error Percentage = {}%".format(round(error_percent, 3) *100)
    Main_graph.set_title(title, fontsize='small')
    latex_ax.cla()
    latex_ax.axis("off")

    if x_after_interpolation_at_1_chunks == [] or y_after_interpolation_at_1_chunks == []:
        Main_graph.plot(x, y, 'r')

    elif y_extra == []:
        latex_equ = latex_equation(order_value.get(), chunk_num_value.get(), False)
        if isinstance(latex_equ, list):
            if chunks.get() == "Chunks":
                chunks.set("Chunk 1")
            chunk_index = int(chunks.get()[-1]) - 1
            Main_graph.plot(x, y, 'r', x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, 'g--')
            Main_graph.stem([x_list_of_chunks[chunk_index][0], x_list_of_chunks[chunk_index][-1]],
                            [y_list_of_chunks[chunk_index][0], y_list_of_chunks[chunk_index][-1]])
            Main_graph.legend(['original signal', 'Interpolated'], loc=4, fontsize='x-small')
            latex_ax.text(-0.15, 0, latex_equ[chunk_index])
        else:
            Main_graph.plot(x, y, 'r', x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, 'g--')
            Main_graph.legend(['original signal', 'Interpolated'], loc=4, fontsize='x-small')
            latex_ax.text(-0.15, 0, latex_equ)
    else:
        latex_equ_extra = latex_equation(order_value.get(), chunk_num_value.get(), True)
        Main_graph.plot(x, y, 'r', x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, 'g--', x,
                        y_extra, 'm-')
        Main_graph.legend(['original signal', 'Interpolated', 'Extrapolated'], loc=4, fontsize='x-small')
        Main_graph.set_ylim(np.min(y), np.max(y))
        latex_ax.text(-0.15, 0, latex_equ_extra)

    Main_graph.set_xlabel(list(df.columns)[0])
    Main_graph.set_ylabel(list(df.columns)[1])
    signal_graph.draw()
    latex_graph.draw()


def latex_equation(order, no_of_chunks, extrapolation_flag):
    global coefficients, coefficients_each_chunk, coefficients_extrapolation
    equations_list = []
    if no_of_chunks == 1:
        if extrapolation_flag:
            # coeff of extrapolation_flag
            coefficients_list = np.flipud(np.array(coefficients_extrapolation)).tolist()
            string = str(coefficients_list.pop(0))
        else:
            coefficients_list = np.flipud(np.array(coefficients)).tolist()
            string = str(round(coefficients_list.pop(0),2))
        for i in range(order):
            if coefficients_list[i] >= 0:
                string += "$+{}x^{}$".format(str(round(coefficients_list[i], 2)), i + 1)
            else:
                string += "${}x^{}$".format(str(round(coefficients_list[i], 2)), i + 1)
        return string

    else:  # no_of_chunks>1:
        for curr_chunk_coeff_list in coefficients_each_chunk:
            curr_chunk_coeff_reversed = (np.flipud(np.array(curr_chunk_coeff_list))).tolist()
            string = str(round(curr_chunk_coeff_reversed.pop(0),2))
            for j in range(order):
                if curr_chunk_coeff_reversed[j] >= 0:
                    string += "$+{}x^{}$".format(str(round(curr_chunk_coeff_reversed[j], 2)), j + 1)

                else:
                    string += "${}x^{}$".format(str(round(curr_chunk_coeff_reversed[j], 2)), j + 1)
            equations_list.append(string)
        return equations_list


def chunks_divider(array, number_of_chunks, percentage):  
    if percentage == 0:
        list_of_chunks = np.array_split(array, number_of_chunks)
        return list_of_chunks
    length = len(array)
    result = []
    start = 0
    chunk_length = int(length / (number_of_chunks - ((percentage / 100) * (number_of_chunks - 1))))
    step = int(chunk_length * (1 - (percentage / 100)) + 0.5)
    for i in range(0, number_of_chunks):
        chunk = array[start:(start + chunk_length)]
        result.append(np.array(chunk))
        start = start + step
    return result


def cancel_process():  
    global start_error_map_button
    start_error_map_button = ttk.Button(root, width=21, text="Start Error Map", command=generate_error_map) \
        .place(x=780 + 30, y=460 + 60 + 80 + 50)
    progress_var.set(0)
    root.update_idletasks()
    back_thread.kill()


def generate_error_matrix(x_data, y_data, who_const, const_value, axis_state): 
    global progress, progress_var, start_error_map_button, back_thread, x_axis_option, \
        y_axis_option, x, y, constant_variable_value, error_map_graph, error_map_fig, error_graph
    x_label = ""
    y_label = ""
    cancel_button = ttk.Button(root, width=21, text="cancel Error Map", command=cancel_process) \
        .place(x=780 + 30, y=460 + 60 + 80 + 50)
    progress_var.set(0)
    root.update_idletasks()
    error_matrix = []
    state_var = True
    order_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    overlap_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    no_ch_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    save_var = None
    if who_const == "number of chunks":
        no_ch_list = [const_value]
        state_var = False
        x_label = "Order"
        y_label = "Overlap Percentage"
    elif who_const == "overlap percentage":
        overlap_list = [const_value]
        x_label = "Order"
        y_label = "Number of Chunks"
    elif who_const == "order":
        order_list = [const_value]
        x_label = "Overlap Percentage"
        y_label = "Number of Chunks"
    for num_chuncks in no_ch_list:
        if state_var:temp = []
        for overlap in overlap_list:
            if not state_var:temp = []
            for order in order_list:
                _, _, error_percent, _ = peicewise_polynomial_interpolation(x_data, y_data,
                                                                            num_chuncks, order, overlap)
                if math.isnan(error_percent): error_percent = save_var
                temp.append(error_percent)
                save_var = error_percent
                progress_var.set(progress_var.get() + 100 / (len(no_ch_list) * len(overlap_list) * len(order_list)))
                root.update_idletasks()
            if not state_var:error_matrix.append(temp)
        if state_var:error_matrix.append(temp)

    if not axis_state:
        error_matrix = np.array(error_matrix).transpose().tolist()
        tempo = y_label
        y_label = x_label
        x_label = tempo
    start_error_map_button = ttk.Button(root, width=21, text="Start Error Map", command=generate_error_map) \
        .place(x=780 + 30, y=460 + 60 + 80 + 50)
    error_map_fig.clear()
    error_map_fig = Figure()
    error_map_graph = error_map_fig.add_subplot(111)
    error_graph = FigureCanvasTkAgg(error_map_fig, master=root)
    error_graph.get_tk_widget().place(x=790, y=10, width=430 + 30 + 35, height=340 + 50)
    a = error_map_graph.imshow(error_matrix,origin='lower')
    error_map_fig.colorbar(a)
    error_map_graph.tick_params(axis='both', labelsize='small')

    error_map_graph.set_xlabel(x_label)
    error_map_graph.set_ylabel(y_label)
    error_graph.draw()
    time.sleep(1)
    progress_var.set(0)
    return error_matrix


def looping():
    global chunk_num_value, x, y, order_value, portion_value, x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, current_chunk_number, chunks_names
    Main_graph.cla()
    error = 0
    y_extra = []

    if x == [] or order_value.get() == 0:
        ynew = []
    elif chunk_num_value.get() == 1 and (portion_value.get() == 100 or portion_value.get() == 0):
        x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, _, error, _ = polynomial_interpolation(x,
                                                                                                                     y,
                                                                                                                     order_value.get())
        y_extra = []
    elif (portion_value.get() != 100 and portion_value.get() != 0):
        chunk_num_value.set(1)
        x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, _, error, _ = polynomial_interpolation(x,
                                                                                                                     y,
                                                                                                                     order_value.get())
        y_extra = polynomial_extrapolation(x, y, order_value.get(), portion_value.get() / 100)

    elif chunk_num_value.get() > 1 and (portion_value.get() == 100 or portion_value.get() == 0):
        x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, error, _ = peicewise_polynomial_interpolation(
            x, y, chunk_num_value.get(), order_value.get(), 0)
        y_extra = []

    draw_data(x, y, x_after_interpolation_at_1_chunks, y_after_interpolation_at_1_chunks, y_extra, error)

    if current_chunk_number != chunk_num_value.get():
        chunks_names = []
        chunks.set("Chunk 1")
        for i in range(chunk_num_value.get()):
            chunks_names.append("Chunk {}".format(i + 1))

    OptionMenu(root, chunks, *chunks_names).place(x=460 + 30, y=320 + 70 + 80 + 20)
    current_chunk_number = chunk_num_value.get()

    root.after(500, looping)


def generate_error_map():  
    global x_axis_option, y_axis_option, x, y, constant_variable_value, error_map_graph, error_map_fig, back_thread
    x_axis = x_axis_option.get()
    y_axis = y_axis_option.get()
    const_str = ""
    state = None

    if x_axis == "Number of Chunks" and y_axis == "Order":
        const_str = "overlap percentage"
        state = 0
    elif x_axis == "Order" and y_axis == "Number of Chunks":
        const_str = "overlap percentage"
        state = 1
    elif x_axis == "Order" and y_axis == "Overlap Percentage":
        const_str = "number of chunks"
        state = 1
    elif x_axis == "Overlap Percentage" and y_axis == "Order":
        const_str = "number of chunks"
        state = 0
    elif x_axis == "Overlap Percentage" and y_axis == "Number of Chunks":
        const_str = "order"
        state = 1
    elif x_axis == "Number of Chunks" and y_axis == "Overlap Percentage":
        const_str = "order"
        state = 0
    elif x_axis == y_axis:
        messagebox.showerror("Warning!", "X and Y can't represent the same parameter!!")

    back_thread = thread_with_trace(target=generate_error_matrix,
                                    args=(x, y, const_str, int(constant_variable_value.get()), state))
    back_thread.start()




root = tk.Tk()
root.title("Curve Fitting Models ")
root.geometry("1297x700")

root.configure(bg="#8CA1A5")

left_down_canva = Canvas(root, bg="#3B5360", width=740 + 30, height=190 + 50, bd=0, highlightthickness=0,
                         relief="ridge")
left_down_canva.place(x=10, y=360 + 50 + 40)

chunk_num_value = IntVar()
chunk_num_value.set(1)
chunk_numbers_Label = Label(root, text="Number of Chunks  ", bg="#3B5360", font="Times 13  bold", fg="#F3F1F5",
                            height=1).place(x=120 + 30, y=320 + 70 + 80 + 20)
chunk_numbers_value = Scale(root, from_=1, to=9, variable=chunk_num_value, resolution=1, orient="horizontal",
                            bg="#3B5360",
                            width=20, bd=0, relief="flat", troughcolor="#E4EFE7", length=125,
                            highlightthickness=0).place(x=300 + 30, y=324 + 50 + 80 + 20)

chunks_options = ["none"]
chunks = StringVar()
chunks.set("Chunks")
chunks_dropdown = OptionMenu(root, chunks, *chunks_options, )
chunks_dropdown.config(width=6)
chunks_dropdown.config(height=1)
chunks_dropdown.config(bg='#E4EFE7')
chunks_dropdown.config(bd=0)
chunks_dropdown.place(x=460 + 30, y=320 + 70 + 80 + 20)

order_value = IntVar()
order_value.set(0)
Polynomial_order_label = Label(root, text="Order of Polynomial ", bg="#3B5360", font="Times 13  bold",
                               fg="#F3F1F5", ).place(x=120 + 30, y=370 + 70 + 80 + 20)
Polynomial_order_value = Scale(root, from_=0, to=9, variable=order_value, resolution=1, orient="horizontal",
                               bg="#3B5360",
                               width=20, bd=0, relief="flat", troughcolor="#E4EFE7", length=125,
                               highlightthickness=0).place(x=300 + 30, y=373 + 50 + 80 + 20)

portion_value = IntVar()
portion_value.set(0)
signal_portion_Label = Label(root, text="Portion of The Signal ", bg="#3B5360", font="Times 13  bold",
                             fg="#F3F1F5", ).place(x=120 + 30, y=420 + 70 + 80 + 20)
Scale(root, from_=-0, to=100, variable=portion_value, resolution=10, orient="horizontal", bg="#3B5360",
      width=20, bd=0, relief="flat", troughcolor="#E4EFE7", length=125, highlightthickness=0).place(x=300 + 30,
                                                                                                    y=407 + 70 + 80 + 20)

Import = ttk.Button(root, width=15, text="Import", command=import_csv_data).place(x=640 + 30, y=460 + 60 + 80 + 50)

# Rigth Side (Error Map)
error_map_fig = Figure(figsize=(4, 4))
error_map_graph = error_map_fig.add_subplot(111)
error_map_graph.axis('off')
error_graph = FigureCanvasTkAgg(error_map_fig, master=root)
error_graph.get_tk_widget().place(x=790, y=10, width=430 + 30 + 35, height=340 + 50)

right_down_canva = Canvas(root, bg="#3B5360", width=430 + 30 + 35, height=190 + 50, bd=0, highlightthickness=0,
                          relief="ridge")
right_down_canva.place(x=760 + 30, y=360 + 50 + 40)

x_axis_label = Label(root, text=" X-axis: ", bg="#3B5360", font="Times 13  bold", fg="#F3F1F5").place(x=770 + 30 + 20,
                                                                                                      y=350 + 65 + 80 + 30)
options = ["Number of Chunks", "Order", "Overlap Percentage"]
x_axis_option = StringVar()
x_axis_option.set("X-axis")
x_axis_dropdown = OptionMenu(root, x_axis_option, *options)
x_axis_dropdown.config(height=1)
x_axis_dropdown.config(bg='#E4EFE7')
x_axis_dropdown.config(bd=0)
x_axis_dropdown.place(x=770 + 75 + 30 + 20, y=350 + 65 + 80 + 30)

y_axis_label = Label(root, text=" Y-axis: ", bg="#3B5360", font="Times 15  bold", fg="#F3F1F5").place(x=770 + 30 + 20,
                                                                                                      y=400 + 60 + 80 + 30)
options = ["Number of Chunks", "Order", "Overlap Percentage"]
y_axis_option = StringVar()
y_axis_option.set("Y-axis")
y_axis_dropdown = OptionMenu(root, y_axis_option, *options)
y_axis_dropdown.config(height=1)
y_axis_dropdown.config(bg='#E4EFE7')
y_axis_dropdown.config(bd=0)
y_axis_dropdown.place(x=770 + 75 + 30 + 20, y=400 + 60 + 80 + 30)

constant_variable_value = StringVar()
constant_variable_value.set(" ")
constant_variable_Label = Label(root, text=" Constant Variable Value:", bg="#3B5360", font="Times 13  bold",
                                fg="#F3F1F5").place(x=770 + 30 + 20, y=380 + 80 + 30)
constant_variable_entry = Entry(root, textvariable=constant_variable_value).place(x=970 + 30 + 20, y=380 + 80 + 30)

start_error_map_button = ttk.Button(root, width=21, text="Start Error Map", command=generate_error_map) \
    .place(x=780 + 30, y=460 + 60 + 80 + 50)

progress_var = DoubleVar()
progress = ttk.Progressbar(root, orient="horizontal", length=150, mode='determinate', variable=progress_var,
                           maximum=100)
progress.place(x=930 + 30, y=462 + 60 + 80 + 50)

fig = Figure(figsize=(5, 5))
Main_graph = fig.add_subplot(111)
Main_graph.axis("off")
signal_graph = FigureCanvasTkAgg(fig, master=root)
signal_graph.get_tk_widget().place(x=10, y=10, width=740 + 30, height=340 + 50)

latex_label = Label(root, text="Fitting Equation: ", bg="#8CA1A5", font="Times 15  bold", fg="#FFFFFF").place(x=10,
                                                                                                              y=360 + 50)

latex_fig = Figure(figsize=(5, 5))
latex_ax = latex_fig.add_subplot(111)
latex_ax.axis("off")
latex_graph = FigureCanvasTkAgg(latex_fig, master=root)
latex_graph.get_tk_widget().place(x=160, y=360 + 50, width=1020, height=30)

root.resizable(False, False)
root.mainloop()

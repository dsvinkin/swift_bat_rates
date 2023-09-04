#! -*- coding: utf-8 -*-

"""
Swift-BAT time history plotter
"""
__author__ = "Dmitry Svinkin"

import matplotlib as mpl
mpl.use('Agg')

import sys
import re
import numpy as np
import matplotlib.pyplot as pl 
from matplotlib.ticker import  MultipleLocator #, FormatStrFormatter

# шрифт
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] ='DejaVu Sans'

# расположение панелей рисунка
left, width = 0.10, 0.8
heigt_channels = 0.15
heigt_sum = 0.25
bottom = 0.1
heigt_gap = 0.075

left_ch_names = 0.85

# размер шрифта подписей 
label_font_size = 14

# вид излома кривой
step = 'steps-post' # если даны начала бинов
#step = 'steps-pre' # если даны концы бинов

# rect [left, bottom, width, height] 
h_sum = bottom + 3* heigt_channels + heigt_gap

rect = [left, bottom, width, width]

dic_x_ticks = {
1000:np.arange(-200,500,50), 
64:np.arange(-50,60,10) 
}

dic_x_minor_ticks = {1000:25, 64:5}

# границы каналов
arr_cuts = np.array([13.125, 50.0, 200.0, 750.0])
arr_ELow = arr_cuts[0:4]
arr_EHi = arr_cuts[1:5]

def get_delta_y(arr):

    y_min, y_max = np.min(arr), np.max(arr)

    dy = int(y_max - y_min)
    mult_dy = 0.99 #1.5

    lst_num = [2, 5, 10]

    delta_y = lst_num[0]
    n_ticks = int(y_max) // delta_y

    i = 0
    while(n_ticks > 4):
        for n in lst_num:
           delta_y = int(n * 10**i)
           y_min_curr = (int(y_min) // delta_y) * delta_y
           y_max_curr = (int(y_max) // delta_y) * delta_y + mult_dy * delta_y
           dy_curr = int(y_max_curr - y_min_curr)
           n_ticks = dy_curr // delta_y + 1
           if n_ticks <= 4:
               break
        i = i + 1
    
    y_max_int = (int(y_max) // delta_y) * delta_y + 1.01 * delta_y
    y_max_ = (int(y_max) // delta_y) * delta_y + mult_dy * delta_y
    y_min_ = int(y_min) // delta_y * delta_y

    return delta_y, y_min_, y_max_, y_max_int


def plot_bat(
    arr_ti, 
    arr_rate,  
    scale_ms, 
    arr_begin_end, 
    fig_file_name, 
    caption=None
    ):
    
    minorLocator_x = MultipleLocator(dic_x_minor_ticks[scale_ms])
    
    fig = pl.figure(figsize=(11.69, 8.27), edgecolor='w', facecolor='w')
    ax = fig.add_axes(rect)
    
    str_label = "counts"
    ax.set_ylabel(str_label, fontsize=label_font_size)
    ax.set_xlabel(r'T-T$_{0}$ (s)',fontsize=label_font_size)

    ax.plot(arr_ti, arr_rate, drawstyle=step, color='k', linewidth=0.5)
    

    arr_bool = np.logical_and(arr_ti < arr_begin_end[1], arr_ti > arr_begin_end[0]) 
    arr_bool_bg = np.logical_and(arr_ti< -10 , arr_ti > arr_begin_end[0]) 

    arr_rate_cur = arr_rate[arr_bool]

    if arr_rate_cur.size == 0 or np.count_nonzero(arr_rate_cur) == 0:
        print('No good data in the interval')
        return

    delta_y, y_min, y_max, y_max_int  = get_delta_y(arr_rate[arr_bool])
    minorLocator_y_sum = MultipleLocator(delta_y/2.0)
 
    bg = np.mean(arr_rate[arr_bool_bg])
    

    ax.axhline(bg, color='k', linestyle ='--', linewidth=0.5)

    # рисуем временной интервал
    #ax.vlines(arr_vlines, [y_min,y_min], [y_max,y_max], linestyles='dashed', color='k', linewidth=0.5)

    ax.set_yticks(np.arange(y_min, y_max + delta_y, delta_y))

    ax.set_ylim(y_min, y_max_int)
    
    ax.tick_params(which='major', length=8, direction='in')
    ax.tick_params(which='minor', length=4, direction='in')
    
    str_e_range = "%.0f - %.0f keV" % (25, 350)
    pl.figtext(left_ch_names, bottom + 0.9 * width, str_e_range, ha='right', fontsize=12)
     
    #print(dic_x_ticks[scale_ms][0], dic_x_ticks[scale_ms][-1])
    #ax.set_xlim(dic_x_ticks[scale_ms][0], dic_x_ticks[scale_ms][-1])
    ax.set_xticks(dic_x_ticks[scale_ms])
    ax.xaxis.set_minor_locator(minorLocator_x)
    #ax.yaxis.set_minor_locator(minorLocator_y_sum)  # y minor ticks
    ax.set_xlim(arr_begin_end[0], arr_begin_end[1])
    
    if(caption):
        ax.set_title(caption, fontsize=18)   

    #pl.savefig(fig_file_name, format='eps', dpi=1000)
    pl.savefig(fig_file_name, format='png', dpi=100)
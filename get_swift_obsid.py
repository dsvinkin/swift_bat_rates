# -*- coding: utf-8 -*-

import os
import shutil

import ftplib
from ftplib import FTP, FTP_TLS
import datetime
import re

import numpy as np

from swift_bat_rate_lc import swift_bat_lc 
from plot_swift_bat import plot_bat
from get_swift_obs_info import get_obsid, get_pointing, download_file
from get_coded_fov import get_fov, get_fov_hpx

import config 

conf = config.read_config('config.yaml')

def get_ipn_name(date, time_utc_sod):
    return "{:s}_T{:05d}".format(date, int(time_utc_sod))

def sod_to_hhmmss(seconds):

    hours = int(seconds / 3600)
    seconds -= 3600.0 * hours
    minutes = int(seconds / 60.0)
    seconds -= int(60.0 * minutes)
    return "{:02d}:{:02d}:{:06.3f}".format(hours, minutes, seconds)

def get_date(date_time):
    """
    date_time eample: 2021-07-04T19:33:24.590
    """

    lst = (date_time.split('T')[0]).split('-')
    return '{:s}{:s}{:s}'.format(lst[0], lst[1], lst[2])

def date_time_sod_to_iso(date_time_sod):
    """
    Convert 'YYYYMMDD SSSSS.sss' to 'YYYY-MM-DDThh:mm:ss.sss'
    """

    date, sod = date_time_sod.split()

    date_iso = "{:s}-{:s}-{:s}".format(date[:4], date[4:6], date[6:8])
    return "{:s}T{:s}".format(date_iso, sod_to_hhmmss(float(sod)))

def move_files(lst_files, str_from, str_to):
    for f in lst_files:
        try:
            shutil.move("{:s}/{:s}".format(str_from,f), "{:s}/{:s}".format(str_to,f))
        except:
            print("Moving of {:s} from {:s} to {:s} failed.".format(f, str_from, str_to))

def nlst(ftp, str_pattern):

    files = []
    try:
        files = sorted(ftp.nlst(str_pattern))
    except ftplib.error_temp:
        print("No {:s} files in directory".format(str_pattern))
    return files

def download(ftp, path, file_ftp, str_pattern):

    path_folder = os.listdir(path)
    file_folder = list(filter(lambda x: x.startswith(str_pattern), path_folder))

    if file_ftp != file_folder:
        for f in sorted(set(file_ftp) - set(file_folder)):
            print(f"Downloading {f}")
            ftp.retrbinary(f'RETR {f}', open(path+'/'+f,'wb').write)
    else:
        print("No new files in format {:s}".format(str_pattern))

def download_swift_heasarc(date, obsid, path):

    print(date, obsid, path)
    server = 'heasarc.gsfc.nasa.gov'
    ftp_dir = "swift/data/obs/{:s}_{:s}/{:s}/bat/rate".format(date[0:4], date[4:6], obsid)

    print("Connecting to {:s}...".format(server))
    ftp = FTP_TLS(server)
    ftp.login()
    ftp.prot_p()


    try:
        ftp.cwd(ftp_dir)
        print("Path of the ftp directory: {:s}".format(ftp_dir))
    
        name = 'sw{:s}'.format(obsid)
        all_files = nlst(ftp, name+'*lc*')
        print(all_files)

        download(ftp, path, all_files, name)

        ftp.quit()
        print("All done, disconnect")
        return all_files

    except ftplib.error_perm:
        print("The folder {:s} does not exist!".format(ftp_dir))
        ftp.quit()
        print("Disconnect")
        return None

def download_swift_orig(date, obsid, path):

    print(date, obsid, path)

    for idx in range(15):
        url = 'https://swift.gsfc.nasa.gov/data/swift/.original/sw{0:s}.{1:03d}/data/bat/rate/sw{0:s}brtms.lc.gz'.format(obsid, idx)
        try:
            file_name = download_file(url, path)
            print(f'{idx} is good, got {file_name}')
            return file_name
            break

        except Exception as e:
            print(str(e))

    return None

def plot(lc, res, path):

    arr_ti, arr_rate = lc.get_lc()
    event_name = lc.get_ipn_name()

    arr_begin_end = np.array([-50,50])
    res_ms = 1000
    if res == 'ms':
        res = '64' + res
        res_ms = 64

    plot_name = "{:s}/{:s}_BAT_{:s}.png".format(path, event_name, res)
    caption = "Swift-BAT {:s}".format(lc.get_date_time())
    plot_bat(arr_ti, arr_rate, res_ms, arr_begin_end, plot_name, caption)

def get_files(date, obsid, res, path_to_down):

    if res == '1s':
        file_name = f'sw{obsid}brt1s.lc.gz' 
    elif res == 'ms':
        file_name = f'sw{obsid}brtms.lc.gz' 
    else:
        print(f'Wrong resolution {res}')
        exit()

    #all_files = download_swift_heasarc(date, obsid, path_to_down)
    all_files = download_swift_orig(date, obsid, path_to_down)

    print(f'Needed {file_name} got {all_files}')

    if all_files is None:
        return None

    return os.path.join(path_to_down, file_name)

def get_data(trigger_time, path_to_down, path_to_save):

    date = get_date(trigger_time)
    obsid, obsid_next = get_obsid(trigger_time)
    
    #res ='1s' 
    res ='ms'

    lc_file = get_files(date, obsid, res, path_to_down)
    if lc_file is None:
        return None
    
    lc = swift_bat_lc(lc_file, trigger_time, res)
    event_name = lc.get_ipn_name()

    ti_lc, tf_lc = lc.get_ti_tf()

    if tf_lc < 0.0 and obsid_next is not None:
        print(f"Lightcurve for obsid {obsid} is short, try obsid {obsid_next}...")
        lc_file = get_files(date, obsid_next, res, path_to_down)
        lc = swift_bat_lc(lc_file, trigger_time, res)

    ascii_lc_file = "{:s}/{:s}_BAT64.thr".format(path_to_save, event_name)
    lc.write_ascii(ascii_lc_file)

    plot(lc, res, path_to_save)
    return event_name


def read_burst_list(file_name):

    lst_date_time = []
    with open(file_name) as f:
        lst_date_time = f.read().split('\n')

    lst_date_time = list(filter(len, lst_date_time))
    lst_date_time = [s for s in lst_date_time if not s.startswith('#')]

    return list(filter(len, lst_date_time))

if __name__ == '__main__':

    #str_date_time = '20110526  61739.032'
    #get_data(str_date_time)

    for s in [conf['save_path'], conf['download_path']]:
        if not os.path.isdir(s):
            os.mkdir(s)


    lst_date_time = read_burst_list(conf['burst_list'])
    path_to_save = conf['save_path']

    coded_frac_level = 0.1 #0.2, 0.5

    for date_time in lst_date_time:

        time_iso = date_time_sod_to_iso(date_time)
        event_name = get_data(time_iso, conf['download_path'], path_to_save)
        if event_name is None:
            print("No data to process!")
            #continue

        event_name = get_ipn_name(date_time.split()[0], float(date_time.split()[1]))
        
        t_utc, lst_ra_dec_roll = get_pointing(time_iso, conf['download_path'], path_to_save)

        file_name = "{:s}/{:s}_bat_fov_cont_cf{:02d}.txt".format(path_to_save, event_name, int(coded_frac_level*100)) 
        get_fov(*lst_ra_dec_roll, coded_frac_level, file_name)

        file_name = "{:s}/{:s}_bat_fov_cf{:02d}_hpx.fits".format(path_to_save, event_name, int(coded_frac_level*100))
        get_fov_hpx(*lst_ra_dec_roll, coded_frac_level, file_name)
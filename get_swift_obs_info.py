import os 

from datetime import datetime
import requests

import numpy as np

from bs4 import BeautifulSoup

from astropy.table import Table
from astropy.io import ascii
from astropy.io import fits

import swiftbat

import clock

import config 

conf = config.read_config('config.yaml')

proxy = {'http': conf['proxy']}
if proxy == '' or proxy == 'None':
    proxy = None

def download_file(url, path):

    file_name = os.path.join(path, url.split('/')[-1]) 

    response = requests.get(url, proxies=proxy, verify=False)
    with open(file_name, 'wb') as f:
        f.write(response.content)

    return file_name

def get_table(date):
 
    url = f'https://www.swift.psu.edu/operations/obsSchedule.php?d={date}&a=1'
    print(url)
 
    r = requests.get(url, proxies=proxy)

    soup = BeautifulSoup(r.text, features="lxml")

    #print(soup)

    # column indexes to use
    #lst_col = [0, 1, 4, 5, 6, 7]
    lst_col = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
 
    data = []
    table = soup.find_all('table')[0]
    
    head = table.find('thead')
    names = head.find_all('th')

    lst_names = [''.join(n.get_text().split()) for n in names]
    
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip().replace(u'\xa0', u'') for ele in cols] # also remove non-breaking space
        if len(lst_col) != len(cols):
            print(cols)
            print('Column number mismatch. Found {:d} cols, expected {:d}. Skipping this row.'.format(len(cols), len(lst_col) ))
            continue
        data.append(cols)
        #data.append([ele for ele in cols if ele]) # Get rid of empty values

    #print(data)
    #exit()

    row_data = []
    for lst_ in data:
        row_data.append([lst_[i] for i in lst_col])


    tab = Table(rows=row_data, names=lst_names, masked=True)      
    arr_bool = tab['TargetName'] == ''
    tab['TargetName'].mask[arr_bool] = True

    return  tab 
    
def get_obs_id(tt, tab):
    """
    Returns 'Target ID' and 'Seg.' for the tt time and the following ones
    """

    for i in range(len(tab)):

        t1 = datetime.strptime(tab['Begin'][i], '%Y-%m-%d %H:%M:%S')
        t2 = datetime.strptime(tab['End'][i], '%Y-%m-%d %H:%M:%S')
        if tt >= t1 and tt <= t2:
            if i < len(tab) - 2:
                return tab['TargetID'][i], tab['Seg.'][i], tab['TargetID'][i+1], tab['Seg.'][i+1]
            else:
                return tab['TargetID'][i], tab['Seg.'][i], None, None

def get_pointing_from_auxil(target_id, seq, tt, path):

    url = "https://www.swift.ac.uk/archive/reproc/{0:08d}{1:03d}/auxil/sw{0:08d}{1:03d}sat.fits.gz".format(int(target_id), int(seq))
    print(url)

    try:
       attfile = download_file(url, path)
    except:
       return [tt, [0,0,0]]

    #attfile = "sw{0:08d}{1:03d}sat.fits.gz".format(int(target_id), int(seq))

    T0 = clock.utc2fermi(tt)

    att = fits.open(attfile)
    att_data = att[1].data
   
    if 'utcfinit' in att[1].header:
        utcf = att[1].header['utcfinit']
        print(f'utcfinit={utcf} was found in {attfile}')
    else:
        utcf = swiftbat.utcf(T0)
        print(f'Use utcfinit={utcf} form caldb')

    print('utcf:', utcf)

    arr_dt =  np.abs(att_data['TIME'] - T0 + utcf)
    idx = np.argmin(arr_dt)

    t_utc = clock.fermi2utc(att_data['TIME'][idx]+utcf)

    return t_utc, att[1].data['POINTING'][idx]

def write_pointing(t_utc, lst_point, file_name):

    with open(file_name, 'w') as f:
        f.write('Date               Time     R.A.     Dec.     Roll\n')
        f.write("{:s} {:8.3f} {:8.3f} {:8.3f}\n".format(t_utc.strftime("%Y-%m-%d %H:%M:%S.%f"), lst_point[0], lst_point[1], lst_point[2]))

def test_get_pointing():
    """
    Pointing from 20180317_bat_pointing.txt
    2018-03-17 16:55:02  2018-03-17 17:05:59     87638     7   2WHSP J105534.3-012616  163.836   -1.411  219.010

    Pointing from sw00087638007sat.fits.gz
    2018-03-17 17:01:23.761920 [163.83601105  -1.41124456 219.0105896 ]
    2018-03-17 17:01:28.761940 [163.83591945  -1.41122996 219.0100708 ]

    They are consistent!!!

    """
    date_time = '2018-03-17T17:01:25'
    target_id, seq = '87638', '7'

    print(date_time)
    print(target_id, seq)

    tt = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S')

    t_utc, lst_ra_dec_roll = get_pointing_from_auxil(target_id, seq, tt, './')
    print("Pointing info:")
    print(t_utc, lst_ra_dec_roll)

def get_pointing(date_time, path_fits, path_to):

    tt = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S.%f')
 
    date = date_time.split('T')[0]
    out_file_name = '{:s}/{:s}_bat_pointing.txt'.format(conf['save_path'], date.replace('-',''))

    tab = get_table(date)
    #print(tab)
    tab.write(out_file_name, overwrite=True, format='ascii.fixed_width', delimiter='', fill_values=[(ascii.masked, '--')]) #
    #print(tab.colnames)

    #exit()

    target_id, seq, _, _ = get_obs_id(tt, tab)
    print(target_id, seq)

    t_utc, lst_ra_dec_roll = get_pointing_from_auxil(target_id, seq, tt, path_fits)

    sod = (tt - tt.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    file_name = '{:s}/{:s}_T{:05d}_bat_pointing_sat.txt'.format(path_to, date.replace('-',''), int(sod))
    write_pointing(t_utc, lst_ra_dec_roll, file_name)

    return t_utc, lst_ra_dec_roll

def get_obsid(date_time):

    tt = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S.%f')
 
    date = date_time.split('T')[0]
    out_file_name = '{:s}/{:s}_bat_pointing.txt'.format(conf['save_path'], date.replace('-',''))

    tab = get_table(date)
    tab.write(out_file_name, overwrite=True, format='ascii.fixed_width', delimiter='', fill_values=[(ascii.masked, '--')])
    
    target_id, seq, target_id_next, seq_next  = get_obs_id(tt, tab)

    obsid = "{0:08d}{1:03d}".format(int(target_id), int(seq))
    
    if target_id_next is not None:
        obsid_next = "{0:08d}{1:03d}".format(int(target_id_next), int(seq_next))
    else:
        obsid_next = None

    print(target_id, seq, obsid)

    return obsid, obsid_next

if __name__ == '__main__':

    date_time = '2021-12-15T17:51:27.2'
    get_obsid(date_time)
    get_pointing(date_time, './', './')

    #test_get_pointing()
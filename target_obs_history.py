"""
Get BAT coding fraction history for given ra, dec
"""
import ftplib
from ftplib import FTP, FTP_TLS
from datetime import datetime, timedelta

from astropy.table import Table, Column, vstack
from astropy.io import ascii

from get_swift_obs_info import get_table
from get_coded_fov import code_ra_dec

def get_full_table():

    date_start = '2006-11-30'
    #date_start = '2007-03-30'

    date_end   = '2007-04-01'

    out_file_name = 'tab_obs_{:s}_{:s}.txt'.format(date_start.replace('-',''), date_end.replace('-',''))

    tt_start = datetime.strptime(date_start, '%Y-%m-%d')
    tt_end   = datetime.strptime(date_end, '%Y-%m-%d')

    delta = tt_end - tt_start + timedelta(1)

    tab = Table(masked=True)

    for tt in (tt_start + timedelta(n) for n in range(delta.days)):
        date = tt.strftime("%Y-%m-%d")
        tab = vstack([tab, get_table(date)])

    tab['TargetName'][:] = [s.replace(' ','') for s in tab['TargetName']]
    tab['Begin'][:] = [s.replace(' ','T') for s in tab['Begin']]
    tab['End'][:] = [s.replace(' ','T') for s in tab['End']]
    tab.write(out_file_name, overwrite=True, format='ascii.fixed_width', delimiter='', fill_values=[(ascii.masked, '--')])
        
def get_exposure(tab):

    t_exp_days = 0
    for i in range(len(tab)):
        dt = datetime.strptime(tab['End'][i], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(tab['Begin'][i], '%Y-%m-%dT%H:%M:%S')
        t_exp_days += dt.total_seconds() / timedelta(days=1).total_seconds()

    return t_exp_days

def get_add_coding_frac():
    """
    SGR M31 box center (RA, Dec): 
    00h44m32s +42d14m21s
    11.133     42.239
    """
    
    src_ra, src_dec = 11.133, 42.239

    tab = ascii.read('tab_obs_20061130_20070401.txt', fill_values=('--','0'))
    #tab = ascii.read('tab_obs_20070330_20070401.txt', fill_values=('--','0'))

    #tab = tab[50:200]

    lst_code_frac = []

    for i in range(len(tab)):
        p_ra, p_dec, p_roll = tab['R.A.'][i], tab['Dec.'][i], tab['Roll'][i]
        s_0 = code_ra_dec(p_ra, p_dec, p_ra, p_dec, p_roll)
        s_src = code_ra_dec(src_ra, src_dec, p_ra, p_dec, p_roll)

        lst_code_frac.append(s_src/s_0)


    col_code_frac = Column(data=lst_code_frac, name='BATCodeFrac')
    tab.add_column(col_code_frac)

    fmt = {'BATCodeFrac':'%.2f'}
    tab.write('tab_full_cf.txt', overwrite=True, format='ascii.fixed_width', formats=fmt, delimiter='', fill_values=[(ascii.masked, '--')])
    print('Full exposire: ', get_exposure(tab))

    tab = tab[tab['BATCodeFrac']>0.5]

    tab.write('tab_full_cf50.txt', overwrite=True, format='ascii.fixed_width', formats=fmt, delimiter='', fill_values=[(ascii.masked, '--')])
    print('Box center exposire: ', get_exposure(tab))

    lst_evt = []    
    for i in range(len(tab)):
        obsid = "{0:08d}{1:03d}".format(int(tab['TargetID'][i]), int(tab['Seg.'][i]))
        lst_ = check_event_data(tab['Begin'][i], obsid)
        lst_evt.append(','.join(lst_))

    col_evt = Column(data=lst_evt, name='EvtData')
    tab.add_column(col_evt)

    tab = tab[tab['EvtData']!='']
    print('Len tab evt: ', len(tab))
    
    if len(tab):
        tab.write('tab_full_cf50_evt.txt', overwrite=True, format='ascii.fixed_width', formats=fmt, delimiter='', fill_values=[(ascii.masked, '--')])
    print('Box center exposire with evt: ', get_exposure(tab))

def get_date(date_time):
    """
    date_time eample: 2021-07-04T19:33:24.590
    """

    lst = (date_time.split('T')[0]).split('-')
    return '{:s}{:s}{:s}'.format(lst[0], lst[1], lst[2])

def nlst(ftp, str_pattern):

    files = []
    try:
        files = sorted(ftp.nlst(str_pattern))
    except ftplib.error_temp:
        print("No {:s} files in directory".format(str_pattern))
    return files

def check_event_data(date_time, obsid):

    date = get_date(date_time)

    server = 'heasarc.gsfc.nasa.gov'
    ftp_dir = "swift/data/obs/{:s}_{:s}/{:s}/bat/event".format(date[0:4], date[4:6], obsid)

    print("Try to find {:s}...".format(ftp_dir))
    ftp = FTP_TLS(server)
    ftp.login()
    ftp.prot_p()

    try:
        ftp.cwd(ftp_dir)
        print("Found evt path: {:s}".format(ftp_dir))
    
        name = 'sw{:s}'.format(obsid)
        all_files = nlst(ftp,'*evt*')
        
        ftp.quit()
        #print("All done, disconnect")
        return all_files

    except ftplib.error_perm:
        #print("The folder {:s} does not exist!".format(ftp_dir))
        ftp.quit()
        #print("Disconnect")
        return []

if __name__ == "__main__":
    #get_full_table()
    get_add_coding_frac()
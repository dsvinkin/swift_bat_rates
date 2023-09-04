# -*- coding: utf-8 -*-

"""
    Convert Swift-BAT lc in fits format to ascii

    Time correction:

    https://swift.gsfc.nasa.gov/analysis/suppl_uguide/time_guide.html

    The reference date for Swift is January 1, 2001, UTC. 
    This is reflected in the reference keywords. The value of MJDREFI + MJDREFF is the epoch January 1.0, 2001, 
    expressed in the TT time system. The integer and fractional keywords are maintained separately 
    for full numerical precision. It is also true that MJDREFF is the offset in days between UTC 
    and TT on January 1, 2001. The keywords appearing in Swift FITS files are shown below.

    TIMESYS = 'TT  ' / indicates the time system of the file
    MJDREFI = 51910
    MJDREFF = 7.4287037E-4
    CLOCKAPP = F / clock correction has not been applied

    Here, CLOCKAPP = F means that no attempt has been made to correct the times in the TIME column of the file.

    It is expected that the spacecraft clock will be set once, soon after launch, and be free-running thereafter. 
    As the clock drifts, the MOC will track the difference between MET on the spacecraft and the true UTC. 
    The difference is uploaded to the spacecraft and referred to as "UTCF" (the UT correction factor). 
    The current value of UTCF onboard Swift is telemetered along with the data and available to the MOC and SDC. 
    If the true UTCF were a well-known (or well-modeled) function of time, 
    then one could correct the MET back to UTC by adding UTCF at each timestep, Thus, for Swift FITS files with TIME in MET:

    UTC (+/- error) = TIME + UTCF
    MJD (UTC) (+/- error) = MJDREFI  + (TIME + UTCF)/86400.0  (in days)
    
    Since the spacecraft clock is more or less well-behaved on short time scales, 
    UTCF can be made to autonomously update regularly onboard, by adding or subtracting 
    one 20-_second tick on a fixed update interval. As the clock drift rate is measured to change, 
    the value of the interval counter onboard the s/c will be updated by the MOC to compensate. 
    The result is that, in some observations, the UTCF value will gradually change 
    from the start time to the stop time.
    
    Swift users can still get a fairly accurate value of the time by using an additional 
    time header keyword, UTCFINIT, which is the value of UTCF at the start of the file. 
    This keyword is placed into the files at the SDC, using the value of UTCF at the start time of the file. 
    Adding this keyword to the time column in the file will align the start time of 
    the file to within the MOC's tolerance on MET+UTCF=UTC. 
    Thus, to correct times in the file such that the start time is within the MOC's tolerance:
    
    MJD (UTC) (+/- error) = MJDREFI  + (TIME + UTCFINIT)/86400.0      (in days)
    
    Should a user wish to quickly align the start time to an accurate value of TT, 
    he/she will need to keep track of any leap seconds that have occurred since the Swift epoch time (Jan 1, 2001). 
    This is because, if a leap second occurs, UTCF will be adjusted by one second 
    in order to keep TIME+UTCF within the MOC tolerance on UTC. 
    The user would then need to consult a leap second log, and perform the following adjustment:
    
    MJD(TT) = MJDREFI + MJDREFF + (TIME + UTCF + leapseconds)/86400.0
    
    Subsequent times in the file will still drift away from true UTC, 
    but the offset will accumulate from a value near zero, as opposed to an arbitrary time offset. 
    This slight drift should be sufficiently small for users who are interested 
    in a rough correction to the time column in lieu of the full correction available 
    once the more accurate measured clock offset file from the MOC is delivered. 

"""

import logging as log
import datetime
import os
import re

import numpy as np

import astropy.io.fits as fits
from astropy.time import Time

import swiftbat

import clock
import plot_swift_bat

class swift_bat_lc:

    def __init__(self, lc_file, T0_utc, res):
        
        lc = fits.open(lc_file)

        self._time = lc['RATE'].data['TIME']
        self._rate = lc['RATE'].data['COUNTS']

        if res == 'ms':
            self._rate = np.sum(self._rate[:,1:], axis=1)
        

        self.time_utc = clock.parsetime(T0_utc)
        self.time_utc_sod = (self.time_utc - self.time_utc.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

        T0_met = clock.utc2fermi(self.time_utc) - clock.leapseconds(clock.fermiref, self.time_utc)
        self._trigger_time = T0_met
        #print("T0_met: ", type(T0_met))
        #exit()

        MJDREFI = lc['PRIMARY'].header['MJDREFI']
        MJDREFF = lc['PRIMARY'].header['MJDREFF']
        UTCFINIT = lc['PRIMARY'].header['UTCFINIT']

        self._start_events = lc['PRIMARY'].header['TSTART']
        self._stop_events = lc['PRIMARY'].header['TSTOP']

        swiftref  = clock.parsetime("Jan 01 2001 00:00:00 UTC")      

        print("MJDREFI+MJDREFF:", clock.mjd2utc(MJDREFI+MJDREFF))

        #log.info("MJDREFI swiftref: {:8.3f} {:8.3f}".format(MJDREFI, clock.utc2mjd(swiftref)))
        if MJDREFI != clock.utc2mjd(swiftref):
            log.error("MJDREFI != utc2mjd(swiftref): {:8.3f} {:8.3f}".format(MJDREFI, clock.utc2mjd(swiftref)))
            exit(0)

        if not lc['PRIMARY'].header['CLOCKAPP']:
            print('CLOCKAPP is F')
            UTCFINIT_T0 = swiftbat.utcf(T0_met)
            print('UTCF for lc start: {:.5f}\nUTCF for T0: {:.5f}'.format(UTCFINIT, UTCFINIT_T0))
            print('Use UTCF for T0!')
            self._time = self._time + UTCFINIT_T0


        self._utc_start = lc['PRIMARY'].header['DATE-OBS']
        self._utc_stop = lc['PRIMARY'].header['DATE-END']

        self._telescope = lc['PRIMARY'].header['TELESCOP']
        self._object = lc['PRIMARY'].header['OBJECT']
        self._ra = lc['PRIMARY'].header['RA_OBJ']
        self._dec = lc['PRIMARY'].header['DEC_OBJ']

    def _swift2utc(self, met, swiftref, UTCFINIT):
        return swiftref + datetime.timedelta(seconds=(met + UTCFINIT))

    def get_lc(self):
        return self._time - self._trigger_time, self._rate

    def get_ti_tf(self):
        return self._time[0] - self._trigger_time, self._time[-1] - self._trigger_time

    def get_ipn_name(self):
        return self.time_utc.strftime('%Y%m%d_T') + "{:05d}".format(int(self.time_utc_sod))

    def get_date_time(self):
        return self.time_utc.strftime('%Y-%m-%d %H:%M:%S.%f')
        
    def write_ascii(self, path):

        Ti, Tf = -1000.0, 5000.0
        Tf_bg = -20.0

        arr_t = self._time - self._trigger_time
        arr_bool = np.logical_and(arr_t >= Ti, arr_t <= Tf)

        arr_t = arr_t[arr_bool]
        rate = self._rate[arr_bool]

        bg = np.mean(rate[arr_t<=Tf_bg])
        if np.isnan(bg):
            bg = 0.0
        header = self.ipn_header(bg)

        with open(path,'w') as f:
            f.write(header)
            for i in range(arr_t.size):
                f.write("{:8.3f} {:8.1f}\n".format(arr_t[i], rate[i]))

    def write_ascii_cnts(self, path):
        self.write_ascii(path)

    def ipn_header(self, bg):
        return "'SWIFT-BAT ' '{:s}'    {:8.3f}\n2.5000E+01 3.5000E+02\n {:.3f}    0.064\n".format(
        self.time_utc.strftime('%d/%m/%y'), self.time_utc_sod, bg)

if __name__ == '__main__':

    T0_utc = '2004-12-19T01:42:20.203'
    grb_name = 'GRB041219'
    res = '64ms'
    arr_begin_end = np.array([-100,500])

    lc_file = '../tmp/sw00100319000brtms.lc.gz'
    
    ascii_lc_file =  "{:s}_{:s}_BAT.thr".format(grb_name, res)
    plot_name = "{:s}_{:s}_BAT.png".format(grb_name, res)

    lc = swift_bat_lc(lc_file, T0_utc, 'ms')
    lc.write_ascii(ascii_lc_file)

    #arr_ti, arr_rate, arr_rate_err = lc.get_lc()
    #print(arr_ti, arr_rate, arr_rate_err)
   
    #caption = "Swift-BAT {:s}".format(lc.get_date_time())
    #plot_swift_bat.plot_bat(arr_ti, arr_rate, 1000, arr_begin_end, plot_name, caption)

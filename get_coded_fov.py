"""
Plot Swift-BAT coded FoV and save coding contours for a given Swift pointing
using David Palmer's code https://github.com/lanl/swiftbat_python 
"""
import os

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.cm as cm
import matplotlib.pyplot as plt

import swiftbat 

def code_ra_dec(ra, dec, p_ra, p_dec, p_roll):
  
    src = swiftbat.source.source(ra, dec)
    coded_area_in_cm2, cosfactor = src.exposure(p_ra, p_dec, p_roll)
    return coded_area_in_cm2

def write_contours(lst_c, file_name):

    with open(file_name, 'w') as f:
        for c in lst_c:
           print("C found")
           for i in range(c.shape[0]):
               f.write("{:8.3f}  {:8.3f}\n".format(c[i,0], c[i,1]))
           f.write("--  --\n")

def get_contours(cs):

    lines = []
    for lines_c in cs.collections:
        print(lines_c)
        for line in lines_c.get_paths():
            lines.append(line.vertices)

    return lines

def test_fov():

    ra = np.arange(-65, 65.0, 1.0)
    dec = np.arange(-65, 65, 1.0)

    X, Y = np.meshgrid(ra, dec)
    #print(X, Y)
    s0 = code_ra_dec(0.0,0.0)
    

    vfumc = np.vectorize(code_ra_dec)
    #print(vfumc([0,60], [0, 20]))
    #exit()
    Z = vfumc(X, Y) / s0
    #print(Z)
   
    fig, ax = plt.subplots(figsize=(5,5))
    im = ax.imshow(Z, extent=(-65, 65, -65, 65), origin='lower') #, interpolation='bilinear', origin='lower', cmap=cm.gray,)

    levels = np.array([0.5, 0.1, 0.2, 0.5])
    CS = ax.contour(X, Y, Z, levels, colors='k')
    #ax.clabel(CS, inline=1, fontsize=10)

    lst_c = get_contours(CS)
    write_contours(lst_c, 'cont.txt')

    ax.set_title('BAT coding fraction')
    ax.set_xlabel('R.A. (deg)')
    ax.set_ylabel('Dec (deg)')

    plt.savefig('bat.png')

def get_fov(p_ra, p_dec, p_roll, level, file_name):

    ra_bounds = (360, 0.0)
    dec_bounds = (-90, 90)

    ra = np.arange(ra_bounds[0], ra_bounds[1], -2.0)
    dec = np.arange(dec_bounds[0], dec_bounds[1], 2.0)

    X, Y = np.meshgrid(ra, dec)
    #print(X, Y)
    
    s0 = code_ra_dec(p_ra, p_dec, p_ra, p_dec, p_roll)

    vfumc = np.vectorize(code_ra_dec, excluded=['p_ra', 'p_dec', 'p_roll'])
    #print(vfumc([0,60], [0, 20]))
    #exit()
    Z = vfumc(X, Y, p_ra, p_dec, p_roll) / s0
    #print(Z)
   
    fig, ax = plt.subplots(figsize=(8,8))
    im = ax.imshow(Z, extent=(ra_bounds[0], ra_bounds[1], dec_bounds[0], dec_bounds[1]), origin='lower') #, interpolation='bilinear', origin='lower', cmap=cm.gray,)

    
    CS = ax.contour(X, Y, Z, levels=[level,], colors='k')
    #ax.clabel(CS, inline=1, fontsize=10)

    lst_c = get_contours(CS)
    write_contours(lst_c, file_name)

    ax.set_title('BAT coding fraction')
    ax.set_xlabel('R.A. (deg)')
    ax.set_ylabel('Dec (deg)')


    plt.savefig("{:s}.png".format(os.path.splitext(file_name)[0]))

def get_fov_hpx(p_ra, p_dec, p_roll, code_frac, file_name):

    from mhealpy import HealpixMap

    # Define the grid
    nside = 64
    scheme = 'nested'
    is_nested = (scheme == 'nested')

    m = HealpixMap(nside = nside, scheme = scheme, dtype = float)

    # Initialize the "map", which is a simple array
    data = np.ones(m.npix)

    m = HealpixMap(data=data, nside = nside, scheme = scheme, dtype = float)

    s0 = code_ra_dec(p_ra, p_dec, p_ra, p_dec, p_roll)

    for i in range(m.npix):

        theta, phi =  m.pix2ang(i)
        ra = np.rad2deg(phi)
        dec = 90.0 - np.rad2deg(theta)

        f = code_ra_dec(ra, dec, p_ra, p_dec, p_roll)
        if f/s0 > code_frac:
            m[i] = 0.0

    m.write_map(file_name, overwrite=True)

def test_src():

    src_ra, src_dec = 62.7894, -51.5326
    p_ra, p_dec, p_roll = 136.181, -57.561, 239.310 

    src = swiftbat.source.source(src_ra, src_dec)
    batExposure = src.exposure(p_ra, p_dec, p_roll)
    print(batExposure)

if __name__ == "__main__":

    """Pointing is given in David's automatic lc letters or 
     at https://www.swift.psu.edu/operations/obsSchedule.php
     Select As-Flown Science Timeline (AFST) and date

     Aaron notice:
     But be careful with the pointing direction (ra,dec,roll) though. 
     Scraping them off the AFST website at penn state (https://www.swift.psu.edu/operations/obsSchedule.php : 
     as both David's code does and you linked to earlier), is sometimes not correct if Swift was slewing around the time of T0.
     The actual pointing info should be taken from the Sattelite attitude file, 
     which can be found eg for GRB 200405B, here: 
     https://swift.gsfc.nasa.gov/data/swift/.original/sw00033856012.006/data/auxil/sw00033856012sat.fits.gz
     if you read this file, it will give you the pointing (ra,dec,roll) down to the second.

    """ 

    #p_ra, p_dec, p_roll =  353.422,   48.819,   91.000
    p_ra, p_dec, p_roll = 1.331, 31.785, 229.08
    file_name = 'bat_fov.txt'

    levels = np.array([0.1,]) #0.2, 0.5
    get_fov(p_ra, p_dec, p_roll, levels, file_name)
    #get_fov_hpx(p_ra, p_dec, p_roll, code_frac=levels[0])
    #test_fov()
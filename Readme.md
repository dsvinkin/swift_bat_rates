# Description
A set of scripts to extract Swift-BAT detector rates and BAT coded FOV for a particular time. 
Scripts depends on https://github.com/lanl/swiftbat_python

# Usage
The Swift-BAT detector rates and the BAT FoV parameters are downloaded by 
`get_swift_bat_rate.py` according to settings given in `config.yaml`, listed below. 
Data are downloaded for the list of date and time stored in ascii `burst_list.txt` file.  
The FITS files are saved to `download_path`, 
ligtcurves processed to the IPN format are saved to `save_path`.
The `data_source` parameter is either `HEASARC` 
(for older burst data stored at https://heasarc.gsfc.nasa.gov/FTP/swift/data/obs/) or
`ORIG` (for recent, up to about few weeks old, bursts stored at https://swift.gsfc.nasa.gov/data/swift/.original/)

Each script in the repository may be used separetely.

# Acknowledgments

I thank David Plamer and Aaron Tohuvavohu for the comments that help to create these scripts.


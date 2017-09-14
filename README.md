# CoolLED_control
Custom python 3 software to run controlled timeseries on CoolLED illumination units (specifically made for pE-2 and pE-4000)

Requires python 3.x, PyQt4, pyqtgraph

Provides a GUI to enter sequences of LED-illumination and wait times(dark). Sequences can be saved and loaded or copy-pasted into the field to reproduce previous timeseries.
Communicates with LED units by CoolLED via the USB connection (virtual COM port). A driver for Windows OS can be found on their hompage (http://www.coolled.com/product-detail/imaging-software/)

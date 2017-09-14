import sys
import serial
import time
from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
from queue import Queue
import os.path
from statistics import mean

app = QtGui.QApplication([])

class WorkingThread(QtCore.QThread):

    def __init__(self, port, boxtext, frametime, queue):
    
        QtCore.QThread.__init__(self)
        self.pEport = port
        self.boxtext = boxtext.upper()
        self.frametime = frametime
        self.q = queue
        print('Thread started with sequence : ' + str(self.boxtext))
        print(self.pEport)
        
    def initport(self):
        print('initport...')
        '''take connected pE-2 or pE-4000 Unit found in main thread and initialize the COM port
        '''
        self.pEunit = serial.Serial(self.pEport, 38400, timeout = 0)

  
    def splitsequence(self):
        print('splitsequence...')
        import re
        self.seqlist = re.findall('[ABCDW]I?[0-9]{1,4}[.,]?[0-9]{0,2}', self.boxtext)
  
    
    def run(self):
        print('run...')
        self.initport()
        self.splitsequence()
        self.light()
        self.deinit()
        
        
    def light(self):
        print(self.seqlist)
        #timelost = 0
        '''now wait/send each command as specified in the GUI field
        the lossarray construct forces the script to keep correct time on different machines by approximating the
        time each action needs by the mean of how long it has taken on previous cycles and subtracting that from wait times.
        Each cycle the actual system time is taken into account so that small mistakes are slowly evened out rather than propagate'''
        lossarray = []
        
        ref = time.perf_counter()
        
        for i, task in enumerate(self.seqlist):
            
            lossarray.append(ref-time.perf_counter())
            
            self.emit(QtCore.SIGNAL('update(QString)'), "Working: " + str(i + 1) + '/' + str(len(self.seqlist)) + '   ')
            if self.q.empty() == False:
                print('Quit on user request!')

                break
            elif task[0] == 'W':
                self.msleep(float(task[1:]) * self.frametime * 1000 + mean(lossarray) * 1000)

            elif task[1] == 'I':
                self.pEunit.write(('C' + task[0:] + '\n').encode('utf-8'))
                task = 'A0'

            else:
                self.pEunit.write(('C' + task[0] + 'N\n').encode('utf-8'))
                self.msleep(float(task[1:]) * self.frametime * 1000 + mean(lossarray) * 1000)
                self.pEunit.write(('C' + task[0] + 'F\n').encode('utf-8'))
            
            ref = ref + float(task[1:]) * self.frametime
            
        print('Done with actions! \n')
        #print(lossarray)
        print(mean(lossarray))

        
        
    def deinit(self):
        self.pEunit.close()
        while self.q.empty() == False:
            self.q.get()
        print("Emptied queue.\n")



		
class GUI (QtGui.QWidget):
    def __init__ (self):
        """Initialize GUI class"""
        super(QtGui.QWidget, self).__init__()

        self.path = False   
        self.pEport = None
        self.initUI()
        self.initport()
        self.q = Queue(1)
        
    def initUI (self):    
        # Do Grid Layout!
        self.setGridLayout()
        
        # Set window     x   y   w   h
        self.setGeometry(100,100,1000,600)
        
        # Set window title
        self.setWindowTitle("CoolLED pe-2 Control")
        
        # Show GUI
        self.show()



    def setGridLayout (self):
        # Create a GridLayout
        self.l = QtGui.QGridLayout()
        
        # Tell GUI to use that GridLayout
        self.setLayout(self.l)
        
        instructions = QtGui.QLabel("LED 1: A \t LED 2: B \t LED 3: C \t LED 4: D \txI###: set intensity for channel x \t W###: wait\nEnter your sequence in the following format: \n\nW20 A2 C2 A2 C2 A2 C2 A5 W100 etc. (freely)")
        
        self.useframes = QtGui.QCheckBox('Use frames instead of seconds')
        self.useframes.setChecked(False)
        self.useframes.stateChanged.connect(self.setframemode)
        
        frameboxl = QtGui.QLabel("frame time (s): ")
        self.framebox = QtGui.QLineEdit()
        self.framebox.setFixedWidth(40)
        self.framebox.setInputMask("99.999")
        self.framebox.setEnabled(False)
        self.frametime = 1
        self.framebox.textChanged.connect(self.framechanged)
        
        self.seqbox = QtGui.QPlainTextEdit()
        self.seqbox.textChanged.connect(self.splitsequence)
        
        self.totaltime = QtGui.QLabel("")
        self.totaltime.setAlignment(QtCore.Qt.AlignCenter)
        self.totaltime.setFont(QtGui.QFont("Arial", 14))
        
        bopen = QtGui.QPushButton("Open...")
        bopen.clicked.connect(self.openfile)
        
        bsave = QtGui.QPushButton("Save")
        bsave.clicked.connect(self.savefile)
        
        self.brun = QtGui.QPushButton("Run!")
        self.brun.clicked.connect(self.runLEDs)
        
        bport = QtGui.QPushButton("Init")
        bport.clicked.connect(self.initport)
        bport.setFixedHeight(50)
        
        bcancel = QtGui.QPushButton("Cancel")
        bcancel.clicked.connect(self.cancel)
        
        
        
        self.p = pg.PlotWidget() # Create plot widget
        self.p.showAxis('left', False)
        #self.p.showAxis('bottom', False)
        self.p.getAxis('bottom').setStyle(tickTextOffset = -15)
        self.p.setFixedHeight(30)
        
        self.sbaredit = QtGui.QLabel("Idle.       ")
              
        self.sbar = QtGui.QStatusBar()
        self.sbar.setFixedHeight(15)
        self.sbar.showMessage("Currently connected: NOTHING")
        
        
        # Add the items to GridLayout
        
        self.l.addWidget(instructions, 0, 0, 2, 1)
        self.l.addWidget(self.useframes, 0, 1, 1, 2)
        self.l.addWidget(frameboxl, 1, 1)
        self.l.addWidget(self.framebox, 1, 2)
        self.l.addWidget(self.seqbox, 2, 0, 3, 1)
        self.l.addWidget(self.totaltime, 2, 1, 1, 2)
        self.l.addWidget(bopen, 4, 2)
        self.l.addWidget(bsave, 3, 2)
        self.l.addWidget(self.brun, 5, 2)
        self.l.addWidget(bport, 3, 1, 2, 1)
        self.l.addWidget(bcancel, 5, 1)
        self.l.addWidget(self.p, 5, 0)
        self.l.addWidget(self.sbar, 6, 0, 1, -1)
        self.sbar.addPermanentWidget(self.sbaredit)
        
        

        
        
    def initport(self):
        '''find connected pE-2 Unit and initialize the COM port
        part of this code I took from responses to stackoverflow questions (so thanks for that!) 
        and adapted it to my needs'''
        
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(10)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        for count, port in enumerate(ports):
            self.sbar.showMessage("Trying port: " + str(count))
            try:
                self.pEunit = serial.Serial(port, timeout = 0.1)
                if self.pEunit.readline()[0:7] == b'CoolLED' or self.pEunit.readline() == 4:
                    self.sbar.showMessage("Connection to pE2-unit found on COM" + str(count+1))
                    self.pEport = port
                    self.pEunit.close()
                    break
                elif self.pEunit.readline() == b'':
                    self.pEunit.write('XVER\n'.encode('utf-8'))
                    out = self.pEunit.read(2000)
                    if out[0:7] == b'XFW_VER':
                        self.sbar.showMessage("Connection to pE-4000? unit found on COM" + str(count+1))
                        self.pEport = port
                        self.pEunit.close()
                        break
                else:
                    self.pEunit.close()

            except (OSError, serial.SerialException):
                pass
            if count == 9:
                self.sbar.showMessage("pE not found. Init for retry.")
        #self.pEport = 'COM3' #uncomment this for testing purposes!
        #self.sbar.showMessage("forced fake pE on port " + self.pEport)
    
    def splitsequence(self):
        import re
        self.seqlistnoint = re.findall('[ABCDW][0-9]{1,4}[.,]?[0-9]{0,2}', self.seqbox.toPlainText().upper())
        self.doplot()                
    
    def doplot(self):
        '''I used pyqtgraph to give a representation of the relative switching times below the edit window. It is a bit slow for massive timeseries.
        The colors used are chosen to fit our installed LEDs. Change that if you have different ones (A was 365, B 425 and C 470)'''
        self.p.clear()
        totalcount = 0
        regions = []
        for count, item in enumerate(self.seqlistnoint):
            if item[0] == 'W':
                totalcount = totalcount + float(item[1:])*self.frametime
            elif item[0] == 'A':
                #here add a colored area to plot of length item[1:] starting at position totalcount
                brushc = (127, 0, 127, 200)
                regions.append(pg.LinearRegionItem(values=[totalcount, totalcount + float(item[1:])*self.frametime], orientation=None, brush=brushc, movable=False, bounds=None))
                totalcount = totalcount + float(item[1:])*self.frametime
                self.p.addItem(regions[-1]) # should access last item in list
            elif item[0] == 'B':
                #LED B (425 nm)
                brushc = (70, 0, 150, 200)
                regions.append(pg.LinearRegionItem(values=[totalcount, totalcount + float(item[1:])*self.frametime], orientation=None, brush=brushc, movable=False, bounds=None))
                totalcount = totalcount + float(item[1:])*self.frametime
                self.p.addItem(regions[-1])
            elif item[0] == 'C':
                #LED C (470 nm)
                brushc = (0, 0, 250, 200)
                regions.append(pg.LinearRegionItem(values=[totalcount, totalcount + float(item[1:])*self.frametime], orientation=None, brush=brushc, movable=False, bounds=None))
                totalcount = totalcount + float(item[1:])*self.frametime
                self.p.addItem(regions[-1])
            elif item[0] == 'D':
                #LED D (currently not installed)
                brushc = (130, 130, 130, 200)
                regions.append(pg.LinearRegionItem(values=[totalcount, totalcount + float(item[1:])*self.frametime], orientation=None, brush=brushc, movable=False, bounds=None))
                totalcount = totalcount + float(item[1:])*self.frametime
                self.p.addItem(regions[-1])
        self.p.setXRange(0, totalcount, padding=0)
        self.totaltime.setText('{:.2f}'.format(totalcount) + 's')
        
    def runLEDs(self):
        self.workingthread = WorkingThread(self.pEport, self.seqbox.toPlainText(), self.frametime, self.q)
        self.workingthread.moveToThread(self.workingthread)
        self.connect(self.workingthread, QtCore.SIGNAL("update(QString)"), self.updatesbar)
        self.workingthread.start()
        
    def updatesbar(self, string):
        self.sbaredit.setText(string)
    
    def setframemode(self):
        if self.framebox.isEnabled():
            self.framebox.setEnabled(False)
            self.frametime = 1
            self.splitsequence()
        else:
            self.framebox.setEnabled(True)
            try:
                self.frametime = float(self.framebox.text())
            except:
                self.frametime = 1
            self.splitsequence()
            
    def framechanged(self):
        if self.framebox.isEnabled():
            try:
                self.frametime = float(self.framebox.text())
            except:
                self.frametime = 1
        else:
            self.frametime = 1
        self.splitsequence()
        
    def openfile(self):
        """Open a file using a FileDialog and only show pE2 files."""
        if self.path:
            f = QtGui.QFileDialog.getOpenFileNameAndFilter(directory= self.path, filter="pE Control files (*.pE2)")[0]
        else:
            if os.path.exists(os.path.normpath('C:/pEsaves/')):
                self.path = os.path.normpath('C:/pEsaves')
            else:
                self.path = os.path.normpath('C:/')
            f = QtGui.QFileDialog.getOpenFileNameAndFilter(directory= self.path, filter="pE Control files (*.pE2)")[0]
               
        print(f) # Print the filename and path to the (i)Python console
        self.path = QtCore.QFileInfo(f).path() # store path for next time
        
        if f:
            file = open(f, "r")
            self.seqbox.setPlainText(file.read())
            file.close()
    
    def savefile(self):
        '''This creates the directory C:/pEsaves/ on windows systems. Please delete if you don't want that to happen'''
        if self.path:
            print(self.path)
            saveloc = self.path
        elif os.path.exists("C:/pEsaves/"):
            saveloc = os.path.normpath('C:/pEsaves/')
        else:
            os.mkdir("C:/pEsaves/")
            saveloc = os.path.normpath('C:/pEsaves/')
        saveobject = open(os.path.normpath(saveloc + "/" + str(time.strftime("%y%m%d_%H-%M")) + "_pE2conf.pE2"), "w")
        saveobject.write(self.seqbox.toPlainText())
        saveobject.close()
        
    def cancel(self):
        if self.q.empty():
            self.q.put('quit')
            print('Exit signal entered Queue.')
        else:
            pass

win = GUI() # Create Widget eq. Window
app.exec_() # Start Application
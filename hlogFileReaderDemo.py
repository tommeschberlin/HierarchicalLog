import tkinter
from tkinter import *
from tkinter.filedialog import *
from tkinter.ttk import *

from hlog.hlog import *
from hlog.hlogText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
# Theme = 'default'
Theme = 'vista'

class HlogFileReaderDemoApp(tkinter.Frame):
    # init vars, create UI, start
    ######################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        self.style = Style(root)
        self.style.theme_use(Theme)
    
        # create logger
        self.logger = logging.getLogger('hlogFileReaderDemo')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        self.title = "hlogFileReaderDemo"

        self.hLogText = HierarchicalLogText( self )
        self.hLogText.DefaultShowSubrecords = True
        self.hLogText.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogText)

        self.logFileReader : HLogFileReader = HLogFileReader( self.logger, '%(asctime)s - %(levelname)8s - %(message)s' )

        menu = Menu(root)
        menu.add_command(label="Read file ...", command=self.readFile)
        root.config(menu=menu)

    def destroy(self):
        self.logger.removeHandler( self.hLogText )
        resetLogHierarchy(self.logger)
        super().destroy()

    def readFile(self):
        self.logger.hierarchyStage = -1
        self.hLogText.clear()
        filePath = tkinter.filedialog.askopenfilename(multiple = False, title = "Select LogFile to track ...")
        if filePath != '':
            self.logFileReader.read( filePath )

    # see https://dev.to/stokry/monitor-files-for-changes-with-python-1npj
    #from watchdog.observers import Observer
    #from watchdog.
    #def readFollow( self, filePath : str ):


# create programm window and start mainloop
Root = Tk()
Root.resizable(True,True)
Root.wm_attributes("-topmost", 1)

if __name__ == '__main__':
    App = HlogFileReaderDemoApp( Root )
    App.pack(fill=BOTH, expand=True)
    Root.update()
    App.mainloop()

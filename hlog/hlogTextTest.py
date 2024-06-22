from tkinter import *
from tkinter.ttk import *
from hlog import *
from hlogText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
Theme = 'winnative'

class App(Frame):
    # init vars, create UI, start
    ######################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        self.root = root

        self.style = Style(root)
        self.style.theme_use(Theme)

        # create logger
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        # create programm window and start mainloop
        self.pack( expand=True, fill=BOTH)
        self.title = "HierarchicalLogTextTest"
        root.resizable(True,True)
        root.wm_attributes("-topmost", 1)
        self.grid_columnconfigure(0, weight = 1)
        self.grid_rowconfigure(0, weight = 1)

        self.hLogText = HierarchicalLogText( self )
        self.hLogText.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogText)

    def start(self):
        self.logger.info("info")
        self.logger.debug("debug")
        self.logger.warning("warning")
        self.logger.error("error")
        self.logger.critical("critical")
        None

# and run
Root = Tk()
App = App( Root )
App.after( 10, App.start() )
App.mainloop()
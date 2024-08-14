import tkinter
from tkinter import *
from tkinter.ttk import *
from hlog import *
from hlogText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
Theme = 'default'

class App(tkinter.Frame):
    # init vars, create UI, start
    ######################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        self.style = Style(root)
        self.style.theme_use(Theme)
    
        # create logger
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        self.title = "HierarchicalLogTextTest"

        self.hLogText = HierarchicalLogText( self )
        self.hLogText.DefaultShowSubrecords = True
        self.hLogText.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogText)

    def start(self):
       # self.logger.info("info")
       # self.logger.debug("debug")
       # self.logger.warning("warning")
       # self.logger.error("error")
       # self.logger.critical("critical")

        with EnterLowerLogHierarchyStage( "Stage 0 -> 1", self.logger ) :
            with EnterLowerLogHierarchyStage( "Stage 1 -> 2", self.logger ) :
                self.logger.debug("something with already lowered log hierarchy stage here")
                with EnterLowerLogHierarchyStage( "Stage 2 -> 3", self.logger ) :
                    self.logger.debug("something with already lowered log hierarchy stage here")
                self.logger.debug("something with already lowered log hierarchy stage here")
            self.logger.warning("something with already lowered log hierarchy stage here")


        for i in range(10):
          self.logger.info("info " + str(i))
          pass


# create programm window and start mainloop
Root = Tk()
Root.resizable(True,True)
Root.wm_attributes("-topmost", 1)
App = App( Root )
App.pack(fill=BOTH, expand=True)
Root.update()
App.after( 10, App.start() )
App.mainloop()

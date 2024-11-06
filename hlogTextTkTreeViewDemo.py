import tkinter
from tkinter import *
from tkinter.ttk import *

from hlog.hlog import *
from hlog.hlogTextTkTreeView import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
Theme = 'default'
# Theme = 'winnative'
# Theme = 'alt'
# Theme = 'vista'

class App(tkinter.Frame):
    # init vars, create UI, start
    ######################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        self.style = Style(root)
        self.style.theme_use(Theme)
    
        # create logger
        self.logger = logging.getLogger('demo')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        self.title = "HierarchicalLogTextDemo"

        self.hLogTextTree = HierarchicalLogTextTree( self )
        self.hLogTextTree.DefaultShowSubrecords = True
        self.hLogTextTree.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogTextTree)

    def destroy(self):
        self.logger.removeHandler( self.hLogTextTree )
        resetLogHierarchy(self.logger)
        super().destroy()

    def start(self):
        self.logger.info("info\nnew line\n   indented new line")
        self.logger.debug("debug")
        self.logger.warning("warning")
        self.logger.error("error")
        self.logger.critical("critical")

        with EnterLowerLogHierarchyStage( "0-0 Stage 0 -> 1", self.logger ) :
            with EnterLowerLogHierarchyStage( "1-0 Stage 1 -> 2", self.logger ) :
                self.logger.debug("2-0 something with already lowered log hierarchy stage here")
                with EnterLowerLogHierarchyStage( "2-1 Stage 2 -> 3", self.logger ) :
                    self.logger.debug("3-0 something with already lowered log hierarchy stage here")
                self.logger.debug("2-2 something with already lowered log hierarchy stage here")
            self.logger.warning("1-1 something with already lowered log hierarchy stage here")

        start = time.time()
        with EnterLowerLogHierarchyStage( "0-1 Stage 0 -> 1", self.logger ) :
            for i in range(1000):
                self.logger.info("info " + str(i))
        print( "insert: %s" % (time.time() - start))

# create programm window and start mainloop
Root = Tk()
Root.resizable(True,True)
Root.wm_attributes("-topmost", 1)

if __name__ == '__main__':
    App = App( Root )
    App.pack(fill=BOTH, expand=True)
    Root.update()
    App.after( 10, App.start() )
    App.mainloop()

from tkinter import *
from tkinter.ttk import *
from hlog import *
from tkinter import font
from tkinter import PhotoImage
import os
from pathlib import Path

class HierarchicalLogText(RecordingHandler, Frame):
    def __init__(self, master=None, logger: logging.Logger = logging.getLogger(),
                 fmt: str = None, maxCntRecords: int =  100000, **kw):
        Frame.__init__(self, master, **kw)
        RecordingHandler.__init__(self, maxCntRecords = maxCntRecords )

        self.scrollX = Scrollbar( self, orient='horizontal' )
        self.scrollY = Scrollbar( self, orient='vertical' )

        self.logText = Text( self, state='disabled', wrap='none',
                             xscrollcommand=self.scrollX.set, yscrollcommand=self.scrollY.set )
        self.scrollX.configure( command=self.logText.xview )
        self.scrollY.configure( command=self.logText.yview )

        self.logText.grid( row=0, column=0, sticky='news' )
        self.scrollX.grid( row=1, column=0, sticky='ew' )
        self.scrollY.grid( row=0, column=1, sticky='ns')

        self.fmt = fmt
        if not self.fmt:
            self.fmt = ""

        # color tags
        
        highlightFont = self.logText.cget("font")
        if isinstance(highlightFont, str):
            highlightFont = font.Font(family = highlightFont)
        highlightFont.configure(weight = 'bold')

        self.logText.tag_config("ERROR", foreground="red" )
        self.logText.tag_config("CRITICAL", foreground="red", font=highlightFont )
        self.logText.tag_config("INFO", foreground="black" )
        self.logText.tag_config("DEBUG", foreground="darkgrey" )
        self.logText.tag_config("WARNING", foreground="orange" )

        # update
        self.bind('<Configure>', self._adjust)
        self.bind('<Map>', self._adjust)

        ScriptDir = os.path.dirname(__file__)
        self.plusImage = PhotoImage(file=os.path.join(ScriptDir, "plus.png"))
        self.minusImage = PhotoImage(file=os.path.join(ScriptDir, "minus.png"))

        self.logText.image_create( 'end', image=self.plusImage )
        self.logText.image_create( 'end', image=self.minusImage )


    def destroy(self):
        super().destroy()
        self.label = None
        self.scale = None

    def emit(self, record)->None:
        RecordingHandler.emit( self, record)
        begin = self.logText.index(INSERT)
        view = self.logText.yview()
        self.logText.configure( state='normal' )
        self.logText.insert( 'end', record.msg + '\n' )
        if ( view[1] == 1.0 ):
            self.logText.see( 'end' )
        end = self.logText.index(INSERT)
        self.logText.tag_add(record.levelname, begin, end )
        self.logText.configure( state='disabled' )
        self.update() 


    def _adjust(self, *args):
        """Adjust scroll position according to the scale."""
        def adjust():
            self.update_idletasks() # "force" redraw

            #x, y = self.scale.coords()
            #if self._label_top:
            #    y = self.scale.winfo_y() - self.label.winfo_reqheight()
            #else:
            #    y = self.scale.winfo_reqheight() + self.label.winfo_reqheight()
            #self.label.place_configure(x=x, y=y)

        self.after_idle(adjust)

    @property
    def value(self):
        """Return current scale value."""
        return self._variable.get()

    @value.setter
    def value(self, val):
        """Set new scale value."""
        self._variable.set(val)
       







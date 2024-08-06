from tkinter import *
from tkinter.ttk import *
from hlog import *
from tkinter import font
from tkinter import PhotoImage
import os
from pathlib import Path
import re


class HierarchicalLogText(RecordingHandler, Frame):
    defaultShowSubrecords = False
    
    firstPageIdx = 0
    pageSize = 0

    def __init__(self, master=None, logger: logging.Logger = logging.getLogger(),
                 fmt: str = None, maxCntRecords: int =  100000, **kw):
        Frame.__init__(self, master, **kw)
        RecordingHandler.__init__(self, maxCntRecords = maxCntRecords )

        self.activeIdx = maxCntRecords

        self.grid_columnconfigure(0, weight = 1)
        self.grid_rowconfigure(0, weight = 1)

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
        self.logText.tag_config("CRITICAL", foreground="white", background="red", font=highlightFont )
        self.logText.tag_config("INFO", foreground="black" )
        self.logText.tag_config("DEBUG", foreground="darkgrey" )
        self.logText.tag_config("WARNING", foreground="orange" )

        activeBackground = 'darkgray'
        self.logText.tag_config("ERROR_ACTIVE", foreground="red", background=activeBackground )
        self.logText.tag_config("CRITICAL_ACTIVE", foreground="white", background="darkred", font=highlightFont )
        self.logText.tag_config("INFO_ACTIVE", foreground="black", background=activeBackground )
        self.logText.tag_config("DEBUG_ACTIVE", foreground="darkgrey", background=activeBackground )
        self.logText.tag_config("WARNING_ACTIVE", foreground="orange", background=activeBackground )

        # update
        self.bind('<Configure>', self.onConfigureOrMap)
        self.bind('<Map>', self.onConfigureOrMap)

        self.logText.bind('<Button-1>', self.onMouseLeft)

        scriptDir = os.path.dirname(__file__)
        self.plusImage = PhotoImage(file=os.path.join(scriptDir, "plus.png"))
        self.minusImage = PhotoImage(file=os.path.join(scriptDir, "minus.png"))

        self.logText.configure( state='normal' )
        self.logText.image_create( 'end', image=self.plusImage )
        self.logText.image_create( 'end', image=self.minusImage )
        self.logText.delete(1.0,1.2)
        #self.logText.insert( 'end', "\n\nblacccccccccccccss\n\n" )
        self.logText.configure( state='disabled' )

    def insertRecord( self, line: int, record ):
        assert self.logText.mark_names().count(record.idx) == 0 
        begin = str(line) + '.0'
        self.logText.mark_set( record.idx, begin )
        self.logText.mark_gravity(record.idx, 'right')
        self.logText.insert( begin, record.msg + '\n', record.levelname )

    def updateView(self):
        activeIdx = self.activeIdx()
        # firstVisibleIdx =
        # l 
        view = self.logText.yview()

        begin = self.logText.index(INSERT)
        self.logText.configure( state='normal' )
        self.logText.insert( 'end', record.msg + '\n' )
        if ( view[1] == 1.0 ):
            self.logText.see( 'end' )
        end = self.logText.index(INSERT)
        self.logText.tag_add(record.levelname, begin, end )
        self.logText.configure( state='disabled' )

    def destroy(self):
        super().destroy()
        self.label = None
        self.scale = None

    def parentIdx( self, idx )->int:
        self.at( idx )

    # find showState recursive
    def isShow( self, idx ):
        parentIdx = self.parentIdx( idx )
        if not parentIdx:
            return True
        parent = self.record( parentIdx )
        if parent.showSubRecords == False:
            return False
        return self.isShow( parentIdx )

    def emit(self, record)->None:
        record.idx = self.entireAdded
        record.showSubrecords = self.defaultShowSubrecords
        RecordingHandler.emit( self, record )

        # check if to show at end of current visible page
        if record.idx >= self.firstPageIdx and record.idx <= (self.firstPageIdx + self.pageSize):
            if self.isShow( record.idx ):
                self.logText.configure( state='normal' )
                line = self.logText.index(END).split('.')[0]
                self.insertRecord(line, record)
                if self.activeIdx > record.idx:
                    self.logText.see(END)
                self.logText.configure( state='disabled' )

    # inserts a group of records at index 
    def insertAt(self, index, records):
        self.logText.configure( state='normal' )
        for record in records:
            self.logText.insert( index, record.msg + '\n' )
        self.logText.configure( state='disabled' )
        #begin = self.logText.index(INSERT)
        #view = self.logText.yview()
        #self.logText.configure( state='normal' )
        #self.logText.insert( 'end', record.msg + '\n' )
        #if ( view[1] == 1.0 ):
        #    self.logText.see( 'end' )
        #end = self.logText.index(INSERT)
        #self.logText.tag_add(record.levelname, begin, end )
        #self.logText.configure( state='disabled' )

        self.update() 


    def onConfigureOrMap(self, *args):
        self.pageSize = self.logText.cget( 'height' )
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

    def onMouseLeft(self, event):
        if self.activeIdx < self.maxCntRecords:
            self.unsetActiveIndex()
        else:       
            textIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") + " linestart")
            textLine = int(textIndex.split('.')[0])
            self.setActiveIndex( self.firstPageIdx + textLine )

    def unsetActiveIndex( self ):
        if self.activeIdx >= self.maxIdx():
            return
        record = self.record( self.activeIdx )
        begin = self.logText.index( self.activeIdx )
        end = self.logText.index( begin + ' lineend')
        self.logText.tag_delete( begin, end, record.levelname + "_ACTICE" )
        self.logText.tag_add( begin, end, record.levelname )

    def setActiveIndex( self, line ):
        self.unsetActiveIndex()
        if line:
            record = self.record( line )
            self.activeIdx = line
            if line < self.firstPageIdx:
                pass

            marks = self.logText.mark_next( f"{line}.0" )

            begin = self.logText.index( self.activeIdx )
            end = self.logText.index( f"{begin.split('.')[0]}.end")
            end = self.logText.index( begin + " lineend")
            self.logText.tag_add( begin, end, record.levelname + "_ACTIVE" )
            self.logText.tag_delete( begin, end, record.levelname )

    def showEnd(self):
        self.activeIdx = self.maxCntRecords

    @property
    def value(self):
        """Return current scale value."""
        return self._variable.get()

    @value.setter
    def value(self, val):
        """Set new scale value."""
        self._variable.set(val)
       







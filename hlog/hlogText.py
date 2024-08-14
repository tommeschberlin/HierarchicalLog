from tkinter import *
from tkinter.ttk import *
from hlog import *
from tkinter import font
from tkinter import PhotoImage
import os
from pathlib import Path
import re

class HierarchicalLogText(RecordingHandler, Frame):
    DefaultShowSubrecords = False

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
        self.logText.tag_config("DEBUG_ACTIVE", foreground="white", background=activeBackground )
        self.logText.tag_config("WARNING_ACTIVE", foreground="orange", background=activeBackground )

        for stage in range(0,10):
            self.logText.tag_config("STAGE%s" % stage, lmargin1=[stage * 15])

        # update
        self.bind('<Configure>', self.onConfigureOrMap)
        self.bind('<Map>', self.onConfigureOrMap)

        self.logText.bind('<Button-1>', self.onMouseLeft)
        self.logText.bind('<Key-Up>', self.onKeyUp)
        self.logText.bind('<Key-Down>', self.onKeyDown)

        scriptDir = os.path.dirname(__file__)
        self.plusImage = PhotoImage(file=os.path.join(scriptDir, "plus.png"))
        self.minusImage = PhotoImage(file=os.path.join(scriptDir, "minus.png"))

        self.logText.configure( state='normal' )
        #self.logText.image_create( 'end', image=self.plusImage )
        #self.logText.image_create( 'end', image=self.minusImage )
        #self.logText.delete(1.0,1.2)
        #self.logText.insert( 'end', "\n\nblacccccccccccccss\n\n" )
        self.logText.configure( state='disabled' )

    def markFromIdx( self, idx ):
        return "Record%s" % idx

    def markFromIndex( self, index ):
        return self.logText.mark_next( self.logText.index( index + " linestart" ) )
        
    def idxFromMark( self, mark ):
        return int(mark.split("Record")[1])
    
    def indexFromIdx( self, idx ):
        return self.logText.index( "Record%s" % idx )

    def appendRecord( self, record ):
        assert self.logText.mark_names().count(self.markFromIdx( record.idx)) == 0 
        hierarchyStageTag = "STAGE%s" % record.hierarchyStage
        begin = self.logText.index("end - 1c") 
        self.logText.insert( begin, record.msg + '\n', [record.levelname, hierarchyStageTag] )
        markName = self.markFromIdx( record.idx )
        self.logText.mark_set( markName, begin )
        self.logText.mark_gravity(markName, 'left')
        # print(self.logText.dump("1.0", "end", mark=True) )
        #print(self.logText.index( markName ))
        print(self.logText.tag_names(begin))

    def updateView(self):
        #activeIdx = self.activeIdx()
        # firstVisibleIdx =
        # l 
        #view = self.logText.yview()

        #begin = self.logText.index(INSERT)
        #self.logText.configure( state='normal' )
        #self.logText.insert( 'end', record.msg + '\n' )
        #if ( view[1] == 1.0 ):
        #    self.logText.see( 'end' )
        #end = self.logText.index(INSERT)
        #self.logText.tag_add(record.levelname, begin, end )
        #self.logText.configure( state='disabled' )
        pass

    def destroy(self):
        super().destroy()
        self.label = None
        self.scale = None

    # find showState recursive
    def isShow( self, idx ):
        parentIdx = self.parentIdx( idx )
        if parentIdx is None:
            return True
        parent = self.record( parentIdx )
        if parent.showSubrecords == False:
            return False
        return self.isShow( parentIdx )

    def emit(self, record)->None:
        record.idx = self.entireAdded
        record.showSubrecords = self.DefaultShowSubrecords
        RecordingHandler.emit( self, record )
        
        parentIdx = self.parentIdx( record.idx )
        isShow = True
        if not parentIdx is None:
            # need + or -
            parent = self.record( parentIdx )
            parentIsShow = self.isShow( parentIdx )
            isShow = parent.showSubrecords and parentIsShow
            if parentIsShow:
                # new child, need to show +/- images
                if self.cntChildren( parent ) == 1:
                    if isShow:
                        image = self.minusImage
                    else:
                        image = self.plusImage
                    mark = self.markFromIdx( parent.idx )
                    begin = self.logText.index( mark  )
                    self.logText.image_create( begin, image=image, padx=2 )
                    hierarchyStageTag = "STAGE%s" % parent.hierarchyStage
                    self.logText.tag_add( hierarchyStageTag, begin, begin + " lineend" )
                    self.logText.tag_add( parent.levelname, begin, begin + " lineend" )

        if isShow:
            self.logText.configure( state='normal' )
            self.appendRecord(record)
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
        textIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") + " linestart")
        mark = self.logText.mark_next( textIndex )
        idx = self.idxFromMark( mark )
        self.alterActiveRecord( idx )

    def onKeyUp(self, event):
        if self.activeIdx <= self.maxIdx() and self.activeIdx > 0:
            markIndex = self.logText.index( self.markFromIdx( self.activeIdx ) )
            prevLineIndex = self.logText.index( markIndex + " -1 line")
            prevIdx = self.idxFromMark( self.markFromIndex( prevLineIndex ) )
            self.alterActiveRecord( prevIdx )

    def onKeyDown(self, event):
        if self.activeIdx < self.maxIdx() and self.activeIdx >= 0:
            markIndex = self.logText.index( self.markFromIdx( self.activeIdx ) )
            nextLineIndex = self.logText.index( markIndex + " +1 line")
            nextIdx = self.idxFromMark( self.markFromIndex( nextLineIndex ) )
            self.alterActiveRecord( nextIdx )

    def unsetActiveRecord( self ):
        if self.activeIdx > self.maxIdx():
            return
        record = self.record( self.activeIdx )
        markIndex = self.indexFromIdx( self.activeIdx )
        begin = self.logText.index( markIndex + " linestart")
        end = self.logText.index( begin + " + 1 line" )
        self.logText.tag_remove( record.levelname + "_ACTIVE", begin, end )
        self.logText.tag_add( record.levelname, begin, end )
        self.activeIdx = self.maxIdx() + 1

    def alterActiveRecord( self, idx ):
        lastActiveIdx = self.activeIdx
        if self.activeIdx <= self.maxIdx():
            self.unsetActiveRecord()
        if idx == lastActiveIdx:
            return
        record = self.record( idx )
        markIndex = self.indexFromIdx( idx )
        begin = self.logText.index( markIndex + " linestart")
        end = self.logText.index( begin + " + 1 line" )
        self.logText.tag_remove( record.levelname, begin, end )
        self.logText.tag_add( record.levelname + "_ACTIVE", begin, end )
        self.activeIdx = idx
        
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
       

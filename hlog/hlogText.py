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

    # characters for the tree view control handles
    # ├ \u251C
    # └ \u2514
    # ⏵ \u23F5
    # ⏷ \u23F7
    # ⯈ \u2BC8
    # ⯆ \u2BC6

    CharacterShowSubrecords = '⯈'
    CharacterHideSubrecords =  '⯆'
    CharacterSubrecordMiddle = '├'
    CharacterSubrecordEnd    = '└'
    ScriptDir = os.path.dirname(__file__)
    ImageShowSubrecords = None
    ImageHideSubrecords = None

    def __init__(self, master=None, logger: logging.Logger = logging.getLogger(),
                 fmt: str = None, maxCntRecords: int =  100000, **kw):
        Frame.__init__(self, master, **kw)
        RecordingHandler.__init__(self, maxCntRecords = maxCntRecords )

        HierarchicalLogText.ImageShowSubrecords = PhotoImage(file=os.path.join(HierarchicalLogText.ScriptDir, "plus.png"))
        HierarchicalLogText.ImageHideSubrecords = PhotoImage(file=os.path.join(HierarchicalLogText.ScriptDir, "minus.png"))

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
        self.logText.bind('<Double-Button-1>', self.onMouseLeftDouble)
        self.logText.bind('<Key-Up>', self.onKeyUp)
        self.logText.bind('<Key-Down>', self.onKeyDown)

        self.AlterShowSubrecordsTag = "ALTER_SHOW_SUBRECORDS_TAG"
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Enter>', self.showAlterShowSubrecordsCursor )
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Leave>', self.hideAlterShowSubrecordsCursor )
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Button-1>', self.alterShowSubrecords )

    def destroy(self):
        super().destroy()
        self.label = None
        self.scale = None

    def showAlterShowSubrecordsCursor( self, event ):
        self.logText.config(cursor="hand2")

    def hideAlterShowSubrecordsCursor( self, event ):
        self.logText.config(cursor="")
        
    def markFromIdx( self, idx ):
        return "Record%s" % idx

    def markFromIndex( self, index ):
        tagNames = self.logText.tag_names( self.logText.index( index + " lineend - 1c" ) )
        for tagName in tagNames:
            if tagName.startswith("Record"):
                return tagName
        return None
        
    def idxFromMark( self, mark ):
        return int(mark.split("Record")[1])
    
    def indexFromIdx( self, idx ):
        return str( self.logText.tag_ranges( "Record%s" % idx )[0] )

    def indexFromMark( self, mark ):
        return self.logText.index( str(self.logText.tag_ranges( mark )[0]) + " linestart" )
    
    def updateParent( self, parent ):
        # children?, need to show +/- images
        if self.cntChildren( parent.idx ) > 0:
            if parent.showSubrecords == True:
                image = self.ImageHideSubrecords
                #alterChar = self.CharacterHideSubrecords
                pass
            else:
                #alterChar = self.CharacterShowSubrecords
                image = self.ImageShowSubrecords
                pass
            
            markTag = self.markFromIdx( parent.idx )
            begin = self.indexFromMark( markTag )
            images = self.logText.dump( image=True, index1=begin )

            if len(images) and images[0] != image.name:
                self.logText.delete( begin, begin + " + 1c" )
                images = []

            if len(images) == 0:
                self.logText.image_create( begin, image=image, padx=2 )
            
            #self.logText.insert( begin, alterChar )
            
            self.logText.tag_add( self.AlterShowSubrecordsTag, begin, begin + " + 1c" )

            end = self.logText.index( begin  + " lineend")
            self.logText.tag_add( markTag, begin, end )
            self.logText.tag_add( "STAGE%s" % parent.hierarchyStage, begin, end )
            self.logText.tag_add( parent.levelname, begin, end )

    # inserts a group of records at index 
    def insertRecordsAt(self, indicees, index, parent = None):
        cntInserted = 0
        if parent != None:
            self.updateParent( parent )

        for idx in indicees:
            record = self.record( idx )
            assert self.logText.tag_names().count( self.markFromIdx( record.idx) ) == 0 

            begin = self.logText.index( index + " + %s lines linestart" % cntInserted )
            self.logText.insert( begin, record.msg + '\n', )
            end = self.logText.index( begin + " lineend" )
            self.logText.tag_add( record.levelname, begin, end )
            self.logText.tag_add( "STAGE%s" % record.hierarchyStage, begin, end )
            self.logText.tag_add( self.markFromIdx( record.idx ), begin, end )

            cntInserted += 1
            cntInserted += self.insertRecordsAt(self.getChildren( record.idx ), begin, record )
        
        return cntInserted

    def emit(self, record)->None:
        record.idx = self.entireAdded
        record.showSubrecords = self.DefaultShowSubrecords
        RecordingHandler.emit( self, record )
        parent = self.parentRecord( record.idx )
        isShow = True
        if not parent is None:
            # need + or -
            parentIsShow = self.isShow( parent.idx )
            isShow = parent.showSubrecords and parentIsShow
        if isShow:
            self.logText.configure( state='normal' )
            self.insertRecordsAt([ record.idx ], self.logText.index(END + " -1c"), parent)
            if self.activeIdx > record.idx:
                self.logText.see(END)
            self.logText.configure( state='disabled' )

    # find showState recursive
    def isShow( self, idx ):
        parentIdx = self.parentIdx( idx )
        if parentIdx is None:
            return True
        parent = self.record( parentIdx )
        if parent.showSubrecords == False:
            return False
        return self.isShow( parentIdx )

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
        mouseIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") )
        textIndex = self.logText.index( mouseIndex + " linestart")
        # if over +/- button no de/activation 
        if self.AlterShowSubrecordsTag in self.logText.tag_names( mouseIndex ):
            return
        self.alterActiveRecord( self.idxFromMark( self.markFromIndex( textIndex ) ) )

    def alterShowSubrecords(self, event):
        textIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") + " linestart" )
        record = self.record( self.idxFromMark( self.markFromIndex( textIndex ) ) )

        showSubrecords = record.showSubrecords
        record.showSubrecords = not record.showSubrecords
        self.logText.configure( state='normal' )
        if showSubrecords:
            self.removeSubrecords( record )
        else:
            self.insertRecordsAt( self.getChildren( record ), self.logText.index( textIndex  + " + 1 line" ), None )
        self.logText.configure( state='disabled' )

    def remove( self, idx ):
        record = self.record( idx )
        assert self.logText.tag_names().count(self.markFromIdx( idx)) != 0
        if record.showSubrecords:
            for childIdx in self.getChildren( idx ):
                self.remove( childIdx )
        mark = self.markFromIdx( idx )
        begin = self.logText.index( self.indexFromMark( mark ) + " linestart" )
        end = self.logText.index( begin + " + 1 line")
        self.logText.delete( begin, end )
        self.logText.tag_delete( mark )
        self.updateParent( self.parentRecord( idx ) )

    def removeSubrecords( self, record ):
        self.logText.configure( state='normal' )
        for childIdx in self.getChildren( record.idx ):
            self.remove( childIdx )
        self.logText.configure( state='disabled' )

    def onMouseLeftDouble(self, event):
        mouseIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") )
        if self.AlterShowSubrecordsTag in self.logText.tag_names( mouseIndex ):
            return

    def onKeyUp(self, event):
        if self.activeIdx <= self.maxIdx() and self.activeIdx > 0:
            markIndex = self.indexFromIdx( self.activeIdx )
            prevLineIndex = self.logText.index( markIndex + " -1 line")
            prevIdx = self.idxFromMark( self.markFromIndex( prevLineIndex ) )
            self.alterActiveRecord( prevIdx )

    def onKeyDown(self, event):
        if self.activeIdx < self.maxIdx() and self.activeIdx >= 0:
            markIndex = self.indexFromIdx( self.activeIdx )
            nextLineIndex = self.logText.index( markIndex + " +1 line")
            nextIdx = self.idxFromMark( self.markFromIndex( nextLineIndex ) )
            self.alterActiveRecord( nextIdx )

    def unsetActiveRecord( self ):
        if self.activeIdx > self.maxIdx():
            return
        record = self.record( self.activeIdx )
        markIndex = self.indexFromIdx( self.activeIdx )
        begin = self.logText.index( markIndex + " linestart")
        end = self.logText.index( begin + " lineend" )
        self.logText.tag_remove( record.levelname + "_ACTIVE", begin, end )
        self.logText.tag_add( record.levelname, begin, end )
        self.activeIdx = self.maxCntRecords

    def alterActiveRecord( self, idx ):
        lastActiveIdx = self.activeIdx
        if self.activeIdx <= self.maxIdx():
            self.unsetActiveRecord()
        if idx == lastActiveIdx:
            return
        record = self.record( idx )
        markIndex = self.indexFromIdx( idx )
        begin = self.logText.index( markIndex + " linestart")
        end = self.logText.index( begin + " lineend" )
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

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

        # tagnames for levelnames
        self.levelTagNames : dict[str,str] = {}
        for levelName in logging.getLevelNamesMapping().keys():
            self.levelTagNames[levelName] = "Level" + levelName

        self.levelTagActiveSuffix = "_ACTIVE"

        self.logText.tag_config(self.levelTagNames["ERROR"], foreground="red" )
        self.logText.tag_config(self.levelTagNames["CRITICAL"], foreground="white", background="red", font=highlightFont )
        self.logText.tag_config(self.levelTagNames["INFO"], foreground="black" )
        self.logText.tag_config(self.levelTagNames["DEBUG"], foreground="darkgrey" )
        self.logText.tag_config(self.levelTagNames["WARNING"], foreground="orange" )

        self.activeBackground = 'darkgray'
        self.logText.tag_config(self.levelTagNames["ERROR"] + self.levelTagActiveSuffix , foreground="red", background=self.activeBackground )
        self.logText.tag_config(self.levelTagNames["CRITICAL"] + self.levelTagActiveSuffix, foreground="white", background="darkred", font=highlightFont )
        self.logText.tag_config(self.levelTagNames["INFO"] + self.levelTagActiveSuffix, foreground="black", background=self.activeBackground )
        self.logText.tag_config(self.levelTagNames["DEBUG"] + self.levelTagActiveSuffix, foreground="white", background=self.activeBackground )
        self.logText.tag_config(self.levelTagNames["WARNING"] + self.levelTagActiveSuffix, foreground="orange", background=self.activeBackground )

        for stage in range(0,10):
            self.logText.tag_config("STAGE%s" % stage, lmargin1=[stage * 15])

        # update
        self.bind('<Configure>', self.onConfigureOrMap)
        self.bind('<Map>', self.onConfigureOrMap)

        self.logText.bind('<Button-1>', self.onMouseLeft)
        self.logText.bind('<Double-Button-1>', self.onMouseLeftDouble)
        self.logText.bind('<Key-Up>', self.onKeyUp)
        self.logText.bind('<Key-Down>', self.onKeyDown)
        self.logText.bind('<Key-Left>', self.onKeyLeft)
        self.logText.bind('<Key-Right>', self.onKeyRight)

        self.AlterShowSubrecordsTag = "ALTER_SHOW_SUBRECORDS_TAG"
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Enter>', self.showAlterShowSubrecordsCursor )
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Leave>', self.hideAlterShowSubrecordsCursor )
        self.logText.tag_bind(self.AlterShowSubrecordsTag, '<Button-1>', self.alterShowSubrecords )

        self.mouseLeftWasProcessedByAlterShowSubrecords = False

        # some chaching
        self.lastHandledRecordHierarchyStage = -1
        self.lastHandledParentIdx = -1
        self.lastActivePos = dict()

        self.clearCache()

    def destroy(self):
        super().destroy()
        self.label = None
        self.scale = None

    def addCustomLevel(self, levelId, levelName, tagConfig = None, tagActiveConfig = None):
        super().addCustomLevel(levelId, levelName)
        self.levelTagNames[levelName] = "Level" + levelName
        if tagConfig is not None:
            self.logText.tag_config(self.levelTagNames[levelName], tagConfig)
            if tagActiveConfig is None:
                tagActiveConfig = tagConfig
            self.logText.tag_config(self.levelTagNames[levelName] + self.levelTagActiveSuffix, tagActiveConfig)

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
        
    def levelTagNameFromIndex( self, index ):
        tagNames = self.logText.tag_names( self.logText.index( index + " lineend - 1c" ) )
        for tagName in tagNames:
            if tagName.startswith("Level"):
                return tagName
        return None
    
    def idxFromMark( self, mark ):
        return int(mark.split("Record")[1])
    
    def indexFromIdx( self, idx ):
        return str( self.logText.tag_ranges( "Record%s" % idx )[0] )
    
    def idxFromIndex( self, index ):
        tagNames = self.logText.tag_names( self.logText.index( index + " lineend - 1c" ) )
        for tagName in tagNames:
            if tagName.startswith("Record"):
                return int( tagName[len("Record"):] )
        return None

    def rangeFromMark( self, mark ):
        tagRanges = self.logText.tag_ranges( mark )
        if not tagRanges:
            return None,None
        return self.logText.index( str(tagRanges[0]) + " linestart" ), str(tagRanges[1])
    
    def updateParent( self, parent : HLogRecord ):
        # children?, need to show +/- images
        if self.cntFilteredChildren( parent.idx ) > 0:
            if parent.showSubrecords == True:
                image = self.ImageHideSubrecords
                #alterChar = self.CharacterHideSubrecords
                pass
            else:
                #alterChar = self.CharacterShowSubrecords
                image = self.ImageShowSubrecords
                pass
            
            begin,end = self.rangeFromMark( self.markFromIdx( parent.idx ) )
            images = self.logText.dump( image=True, index1=begin, index2=begin + " +1c" )

            if len(images) and not images[0][1].startswith( image.name ):
                self.logText.delete( begin, begin + " + 1c" )
                images = []

            if len(images) == 0:
                self.logText.image_create( begin, image=image, padx=2 )
            
            #self.logText.insert( begin, alterChar )
            
            self.logText.tag_add( self.AlterShowSubrecordsTag, begin, begin + " + 1c" )
            self.setDefaultRecordTags( begin, end, parent )
            self.updateRecordLevelTag( begin, end, parent, True )

    def updateRecordLevelTag( self, begin, end, record : HLogRecord, force = False ):
        """ To show WARNING,ERROR and CRITCAL colors at parents """
        newLevelName = record.levelname
        if record.maxChildLevelNo > 0:
            newLevelName = logging.getLevelName( record.maxChildLevelNo )

        newLevelTagName = self.levelTagNames[ newLevelName ]
        isActive = False
        if self.activeIdx == record.idx:
            newLevelTagName += self.levelTagActiveSuffix
            isActive = True

        currentLevelTagName = self.levelTagNameFromIndex( begin )
        if currentLevelTagName == newLevelTagName and not force:
            return
        
        currentEnd = newEnd = self.logText.index( end + " lineend" )

        if currentLevelTagName is not None:
            if currentLevelTagName.endswith(self.levelTagActiveSuffix):
                currentEnd = self.logText.index( currentEnd + " +1c" )
            self.logText.tag_remove( currentLevelTagName, begin, currentEnd )

        if isActive:
            newEnd = self.logText.index( newEnd + " +1c" )

        self.logText.tag_add( newLevelTagName, begin, newEnd )

    def setDefaultRecordTags( self, begin, end, record : HLogRecord):
        self.logText.tag_add( "STAGE%s" % record.hierarchyStage, begin, end )
        self.logText.tag_add( self.markFromIdx( record.idx ), begin, end )

    def countLines( self, index1, index2 ) -> int:
        cntLines = self.logText.count( index1, index2, 'lines')
        if cntLines is None:
            return 0
        return cntLines[0]

    # inserts a group of records at index 
    def insertRecordsAt(self, indicees, index, parent : HLogRecord = None):
        cntInsertedLines = 0
        maxChildLevelNo = -1

        if parent != None:
            # no parent treatment needed if already done for a previous record
            if parent.idx != self.lastHandledParentIdx:
                self.updateParent( parent )
            if not parent.showSubrecords:
                return 0
            maxChildLevelNo = parent.maxChildLevelNo

        for idx in indicees:
            record = self.record( idx )
            if record.levelno > maxChildLevelNo:
                maxChildLevelNo = record.levelno
            if not self.passedFilter( record ):
                continue

            #  assert self.logText.tag_names().count( self.markFromIdx( record.idx) ) == 0 

            begin = self.logText.index( index + " + %s lines linestart" % cntInsertedLines )
            self.logText.mark_set( INSERT, begin )
            self.logText.insert( begin, record.msg + '\n', )
            end = self.logText.index(INSERT + " - 1c")
            self.setDefaultRecordTags( begin, end, record )
            self.updateRecordLevelTag( begin, end, record )
            cntInsertedLines += ( self.countLines( begin, end ) + 1 )

            # only not last element can have children
            if record.idx < self.maxIdx():
                begin = self.logText.index( index + " + %s lines linestart" % cntInsertedLines )
                cntInsertedLines += self.insertRecordsAt(self.getFilteredChildren( record.idx ), begin, record )

        if parent != None and maxChildLevelNo > parent.levelno and maxChildLevelNo > parent.maxChildLevelNo:
            begin,end = self.rangeFromMark(self.markFromIdx(parent.idx))
            parent.maxChildLevelNo = maxChildLevelNo
            self.updateRecordLevelTag( begin, end, parent )
        
        return cntInsertedLines

    def emit(self, record : HLogRecord)->None:
        RecordingHandler.emit( self, record )

        # no parent retrieving needed if already done for a previous record
        if self.lastHandledRecordHierarchyStage == record.hierarchyStage:
            parent = self.at( self.lastHandledParentIdx )
        else:
            parent = self.parentRecord( record.idx )

        isShow = self.passedFilter( record )
        if isShow and ( not parent is None ):
            if parent.showSubrecords is None:
                parent.showSubrecords = self.DefaultShowSubrecords

            # need + or -
            parentIsShow = self.isShow( parent.idx )
            isShow = parent.showSubrecords and parentIsShow
            if not isShow and parentIsShow:
                if parent.idx != self.lastHandledParentIdx:
                    self.logText.configure( state='normal' )
                    self.updateParent( parent )
                    self.logText.configure( state='disabled' )

        if isShow:
            self.logText.configure( state='normal' )
            self.insertRecordsAt([ record.idx ], self.logText.index(END + " -1c"), parent)
            if self.activeIdx > record.idx:
                self.logText.see(END)
            self.logText.configure( state='disabled' )

        if isShow:
            self.lastHandledRecordHierarchyStage = record.hierarchyStage
        else:
            self.lastHandledRecordHierarchyStage = -1

        if parent and isShow:
            self.lastHandledParentIdx = parent.idx
        else:
            self.lastHandledParentIdx = -1

    # find showState recursive
    def isShow( self, idx ):
        if not self.passedFilter( self.record( idx ) ):
            return False
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
        # if +/- button was pressed
        if self.mouseLeftWasProcessedByAlterShowSubrecords:
            self.mouseLeftWasProcessedByAlterShowSubrecords = False
            return 
        mark = self.markFromIndex( textIndex )
        if mark is not None:
            self.alterActiveRecord( self.idxFromMark( mark ) )

    def clearCache( self ):
        self.lastHandledParentIdx = -1
        self.lastHandledRecordHierarchyStage = -1

    def storeLastActivePos( self, recordToRestore : HLogRecord ):
        upperViewIndex = self.logText.index( self.logText.index(f"@{0},{0}") )
        if not recordToRestore.hierarchyStage in self.lastActivePos.keys():
            self.lastActivePos[recordToRestore.hierarchyStage] = dict()
        self.lastActivePos[recordToRestore.hierarchyStage][self.parentIdx( recordToRestore.idx )] =\
            { 'idx': recordToRestore.idx, 'upperViewIndex': upperViewIndex }

    def onKeyLeft(self, event):
        if self.activeIdx <= self.maxIdx():
            record = self.record( self.activeIdx )
            recordToRestore = record
            if record.showSubrecords is None:
                record = self.at(  self.parentIdx( record.idx ) )
                if not record:
                    return
            if not record.showSubrecords:
                record = self.at( self.parentIdx( record.idx ) )
                if not record:
                    return
            if record.showSubrecords:
                # store last active in subdir
                self.storeLastActivePos( recordToRestore ) 
                self.clearCache()
                record.showSubrecords = False
                self.logText.configure( state='normal' )
                self.removeRecords( self.getVisibleChildren( record.idx ), record.idx )
                self.logText.configure( state='disabled' )
                self.clearCache()
                if self.activeIdx != record.idx:
                    self.alterActiveRecord(record.idx)

    def restoreLastActivePos(self, parentRecord : HLogRecord ):
        """ Restores last active entry """
        hierarchyStage = parentRecord.hierarchyStage + 1
        parentIdx = parentRecord.idx
        if hierarchyStage in self.lastActivePos.keys():
            if parentIdx in self.lastActivePos[ hierarchyStage ]:
                self.alterActiveRecord( self.lastActivePos[hierarchyStage][parentIdx]['idx'] )
                self.logText.yview( self.lastActivePos[hierarchyStage][parentIdx]['upperViewIndex'] )
                self.logText.mark_set( INSERT,self.indexFromIdx( self.lastActivePos[hierarchyStage][parentIdx]['idx'] ))

    def onKeyRight(self, event):
        if self.activeIdx <= self.maxIdx():
            record = self.record( self.activeIdx )
            if not record.showSubrecords:
                self.clearCache()
                self.logText.configure( state='normal' )
                record.showSubrecords = True
                self.insertRecordsAt( self.getFilteredChildren( record.idx ),
                                      self.logText.index( self.indexFromIdx( record.idx )  + " + 1 line" ), record )
                self.logText.configure( state='disabled' )
                self.clearCache()
                # restore last active
                self.logText.after_idle( self.restoreLastActivePos, record )

    def alterShowSubrecords(self, event):
        self.mouseLeftWasProcessedByAlterShowSubrecords = True
        self.clearCache()
        textIndex = self.logText.index( self.logText.index(f"@{event.x},{event.y}") + " linestart" )
        mark = self.markFromIndex( textIndex )
        idx = self.idxFromMark( mark )
        record = self.record( idx )

        showSubrecords = record.showSubrecords
        record.showSubrecords = not record.showSubrecords
        if showSubrecords:
            self.logText.configure( state='normal' )
            self.removeRecords( self.getVisibleChildren( record.idx ), record.idx )
            self.logText.configure( state='disabled' )
        else:
            begin,end = self.rangeFromMark( mark )
            self.logText.configure( state='normal' )
            self.insertRecordsAt( self.getFilteredChildren( idx ), self.logText.index( end  + "linestart + 1 line" ), record )
            self.logText.configure( state='disabled' )
        self.logText.update()
        self.clearCache()

    def removeRecords( self, indicees, parentIdx ):
        groupBegin = ''
        groupEnd = ''
        
        if self.activeIdx in indicees:
            self.alterActiveRecord(self.activeIdx)

        for idx in indicees:
            record = self.record( idx )
            # assert self.logText.tag_names().count(self.markFromIdx( idx)) != 0
            if not record.showSubrecords is None and record.showSubrecords:
                if groupBegin:
                    self.logText.delete( groupBegin, groupEnd )
                    groupBegin = ''
                self.removeRecords( self.getVisibleChildren( idx ), idx )
            mark = self.markFromIdx( idx )
            recordBegin,recordEnd = self.rangeFromMark( mark )
            groupEnd = self.logText.index( recordEnd + " + 1 c")

            if not groupBegin:
                groupBegin = recordBegin
            
            # no parent treatment needed if alrady done for a previous child
            if record.hierarchyStage != self.lastHandledRecordHierarchyStage:
                self.updateParent( self.record( parentIdx ) )
                self.lastHandledRecordHierarchyStage = record.hierarchyStage

        if groupBegin:
            self.logText.delete( groupBegin, groupEnd )

    def getVisibleChildren( self, idx = None ):
        if idx != None:
            relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
            record = self.records[ relIdx ]
            parentHierarchyStage = record.hierarchyStage
            childIndex = self.logText.index( self.indexFromIdx( idx ) + "linestart +1 line" )
        else:
            parentHierarchyStage = -1
            childIndex = "2.0"

        children = []
        childIdx = self.idxFromIndex( childIndex )
        while childIdx != None:
            child = self.records[ childIdx - self.minIdx() ]
            if child.hierarchyStage <= parentHierarchyStage:
                break
            if (child.hierarchyStage == parentHierarchyStage + 1):
                children.append( childIdx )
            childIndex = self.logText.index( childIndex + " +1 line")
            childIdx = self.idxFromIndex( childIndex )
        return children

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
            begin,end = self.rangeFromMark( self.markFromIdx( prevIdx ) )
            self.logText.mark_set(INSERT, begin)

    def onKeyDown(self, event):
        if self.activeIdx < self.maxIdx() and self.activeIdx >= 0:
            begin,end = self.rangeFromMark( self.markFromIdx( self.activeIdx ) )
            nextMarkIndex = self.logText.index( end + " +1 c")
            nextIdx = self.idxFromMark( self.markFromIndex( nextMarkIndex ) )
            self.alterActiveRecord( nextIdx )
            begin,end = self.rangeFromMark( self.markFromIdx( nextIdx ) )
            self.logText.mark_set(INSERT, end)

    def alterActiveRecord( self, idx ):
        currentActiveIdx = self.activeIdx
        if currentActiveIdx <= self.maxIdx():
            self.activeIdx = self.maxCntRecords
            begin,end = self.rangeFromMark(self.markFromIdx(currentActiveIdx))
            self.updateRecordLevelTag( begin, end, self.record(currentActiveIdx) )
        if idx == currentActiveIdx:
            """ only deactivated the current active one"""
            return

        self.activeIdx = idx
        begin,end = self.rangeFromMark(self.markFromIdx( idx ) )
        self.updateRecordLevelTag( begin, end, self.record( idx ) )
        
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

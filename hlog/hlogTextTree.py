from tkinter import *
from tkinter.ttk import *
import logging
from hlog import *
from tkinter import font
from tkinter import PhotoImage
from tkinter import ttk
import os
from pathlib import Path
import re
from datetime import datetime

SHOW_DETAILS_OFF = 0
SHOW_DETAILS_AT_ENTRY_IF_ACTIVE = 1
SHOW_DETAILS_AT_WIDGET_IF_ACTIVE = 2
SHOW_DETAILS_AS_TOOLTIP = 3

class ButtonPressEvent:
    x : int
    y : int

class HLogTextTreeRecord(HLogRecord):
    """ Log record to use in HierarchicalLogTextTree """
    def __init__(self):
        self.itemId = ''

class HierarchicalLogTextTree(RecordingHandler, Frame):
    CntCreated : int = 0
    DefaultShowSubrecords = False

    def __init__(self, master=None, logger: logging.Logger = logging.getLogger(),
                 fmt: str = None, maxCntRecords: int =  100000, **kw):
        Frame.__init__(self, master, **kw)
        RecordingHandler.__init__(self, maxCntRecords = maxCntRecords )
        HierarchicalLogTextTree.CntCreated += 1

        self.name = kw.get( 'name', f"HierarchicalLogTextTree{HierarchicalLogTextTree.CntCreated}")

        self.activeIdx = maxCntRecords

        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=0)
        self.grid_rowconfigure(0, weight = 1)

        self.scrollX = Scrollbar( self, orient='horizontal' )
        self.scrollY = Scrollbar( self, orient='vertical' )


        self.style = ttk.Style()
        #style.theme_use("default")
        #style.configure("Treeview",background="Black", foreground="White",fieldbackground="red")
        #style.map('Treeview', background=[('selected','green')],foreground=[('selected','white')])

        self.logTextTree = ttk.Treeview( self, xscrollcommand=self.scrollX.set, yscrollcommand=self.scrollY.set, show="tree headings", selectmode="browse",
                                         columns=['Text','More', 'Time'], style=f"{self.name}.Treeview" )

        self.scrollX.configure( command=self.logTextTree.xview )
        self.scrollY.configure( command=self.logTextTree.yview )

        self.timeFormat = "%Y-%m-%d %H:%M:%S"
        timeString = datetime.now().strftime(self.timeFormat)
        # self.dateText.configure( width = len(timeString))

        self.logTextTree.grid( row=0, column=0, sticky='news' )
        self.scrollY.grid( row=0, column=1, sticky='news')
        self.scrollX.grid( row=1, column=0, sticky='ew' )

        self.fmt = fmt
        if not self.fmt:
            self.fmt = ""

        # tagnames for levelnames
        self.levelTagNames : dict[str,str] = {}
        for levelName in logging.getLevelNamesMapping().keys():
            self.levelTagNames[levelName] = "Level" + levelName

        self.levelTagActiveSuffix = "_ACTIVE"

        self.logTextTree.tag_configure(self.levelTagNames["ERROR"], foreground="red" )
        self.logTextTree.tag_configure(self.levelTagNames["CRITICAL"], foreground="white", background="red" )
        self.logTextTree.tag_configure(self.levelTagNames["INFO"], foreground="black" )
        self.logTextTree.tag_configure(self.levelTagNames["DEBUG"], foreground="darkgrey" )
        self.logTextTree.tag_configure(self.levelTagNames["WARNING"], foreground="orange" )

        self.activeBackground = 'darkgray'
        self.logTextTree.tag_configure(self.levelTagNames["ERROR"] + self.levelTagActiveSuffix , foreground="red", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["CRITICAL"] + self.levelTagActiveSuffix, foreground="white", background="darkred" )
        self.logTextTree.tag_configure(self.levelTagNames["INFO"] + self.levelTagActiveSuffix, foreground="black", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["DEBUG"] + self.levelTagActiveSuffix, foreground="white", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["WARNING"] + self.levelTagActiveSuffix, foreground="orange", background=self.activeBackground )

        # update
        self.bind('<Configure>', self.onConfigureOrMap)
        self.bind('<Map>', self.onConfigureOrMap)

        # self.logTextTree.bind('<Button-1>', self.onMouseOver)

        self.logTextTree.bind('<<TreeviewSelect>>', self.onSelect)

        # some chaching
        self.lastHandledRecordHierarchyStage = -1
        self.lastHandledParentIdx = -1
        self.lastActivePos = dict()

        self.clearCache()

        self.cntEnableRequests = 0
        self.showDetails = SHOW_DETAILS_AT_ENTRY_IF_ACTIVE

    def destroy(self):
        super().destroy()

    def addCustomLevel(self, levelId, levelName, tagConfig = None, tagActiveConfig = None):
        super().addCustomLevel(levelId, levelName)
        self.levelTagNames[levelName] = "Level" + levelName
        if tagConfig is not None:
            self.logTextTree.tag_configure(self.levelTagNames[levelName], tagConfig)
            if tagActiveConfig is None:
                tagActiveConfig = tagConfig
            self.logTextTree.tag_configure(self.levelTagNames[levelName] + self.levelTagActiveSuffix, tagActiveConfig)

    def levelTagNameFromIdx( self, idx ):
        tagNames = self.logTextTree.item( idx, 'tags' )
        for tagName in tagNames:
            if tagName.startswith("Level"):
                return tagName
        return None
    
    def updateParent( self, parent : HLogTextTreeRecord ):
        # children?
        if self.cntFilteredChildren( parent.idx ) > 0:
            self.updateRecordLevelTag( parent, True )

    def updateRecordLevelTag( self, record : HLogTextTreeRecord, force = False ):
        """ To show WARNING,ERROR and CRITCAL colors at parents """
        newLevelName = record.levelname
        if record.maxChildLevelNo > 0:
            newLevelName = logging.getLevelName( record.maxChildLevelNo )

        newLevelTagName = self.levelTagNames[ newLevelName ]
        if self.activeIdx == record.idx:
            newLevelTagName += self.levelTagActiveSuffix

        currentLevelTagName = self.levelTagNameFromIdx( record.idx )
        if currentLevelTagName == newLevelTagName and not force:
            return

        tags = list(self.logTextTree.item( record.idx, 'tags'))
        
        if currentLevelTagName is not None:
            tags.remove(currentLevelTagName)

        tags.append( newLevelTagName )
        self.logTextTree.item( record.idx, tags=tags )

    def insertRecordAt( self, parentId, indexAtParent, record : HLogTextTreeRecord, showDetails : bool = False ) -> int:
        msg = self.format( record )
        if '\n' in msg:
            parts = msg.split('\n')
            msg = parts[0]
            if showDetails:
                for i in range(1,len(parts)):
                    msg += '\n' + parts[i]

        record.itemId = self.logTextTree.insert( parentId, indexAtParent, iid=record.idx, text = msg + '\n' )
        self.updateRecordLevelTag( record )
        return record.itemId

#        record.asctime
#        self.timeFormat = "%Y-%m-%d %H:%M:%S"
#        timeString = datetime.now().strftime(self.timeFormat)

    # inserts a group of records at index 
    def insertRecordsAt(self, indicees, index, parent : HLogTextTreeRecord = None):
        insertedIds = []
        maxChildLevelNo = -1
        parentId = ''

        if parent != None:
            # no parent treatment needed if already done for a previous record
            if parent.idx != self.lastHandledParentIdx:
                self.updateParent( parent )
            if not parent.showSubrecords:
                return 0
            maxChildLevelNo = parent.maxChildLevelNo
            parentId = parent.itemId

        for idx in indicees:
            record = self.record( idx )
            if record.levelno > maxChildLevelNo:
                maxChildLevelNo = record.levelno
            if not self.passedFilter( record ):
                continue

            #  assert self.logText.tag_names().count( self.markFromIdx( record.idx) ) == 0 
            insertedIds += self.insertRecordAt( parentId, index + len(insertedIds), record, self.showDetails == SHOW_DETAILS_AT_ENTRY )

            # insert children
            # only not last element can have children
            if record.idx < self.maxIdx():
                insertedIds += self.insertRecordsAt(self.getFilteredChildren( record.idx ), index + len(insertedIds), record )

        if parent != None and maxChildLevelNo > parent.levelno and maxChildLevelNo > parent.maxChildLevelNo:
            parent.maxChildLevelNo = maxChildLevelNo
            self.updateRecordLevelTag( parent )
        
        return insertedIds

    def emit(self, record : HLogTextTreeRecord)->None:
        RecordingHandler.emit( self, record )

        # no parent retrieving needed if already done for a previous record
        parent : HLogTextTreeRecord
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
                    self.updateParent( parent )

        if isShow:
            parentItemId = ''
            if not parent is None:
                parentItemId = parent.itemId
            posAtParent = len(self.logTextTree.get_children( parentItemId ))
            self.insertRecordsAt([ record.idx ], posAtParent, parent )
            if self.activeIdx > record.idx:
                children = self.logTextTree.get_children()
                self.logTextTree.see( children[-1] )

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
        self.pageSize = self.logTextTree.cget( 'height' )
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

    def onMouseOver(self, event : ButtonPressEvent ):
        region = self.logTextTree.identify_region( event.x, event.y)
        if region != 'tree':
            return
        idx = int(self.logTextTree.identify_row( event.y))
        self.alterActiveRecord( idx )

    def clearCache( self ):
        self.lastHandledParentIdx = -1
        self.lastHandledRecordHierarchyStage = -1

    def onSelect( self, event ):
        selIdx = int(self.logTextTree.selection()[0])
        self.alterActiveRecord( selIdx )

        record = self.record( selIdx )
        newLevelName = record.levelname
        if record.maxChildLevelNo > 0:
            newLevelName = logging.getLevelName( record.maxChildLevelNo )
        tagConfig = self.logTextTree.tag_configure(self.levelTagNames[newLevelName] + self.levelTagActiveSuffix )
        self.style.map(f"{self.name}.Treeview", background=[('selected',tagConfig['background'])],foreground=[('selected',tagConfig['foreground'])])

    def alterActiveRecord( self, idx : int ):
        showDetails = ( self.showDetails == SHOW_DETAILS_AT_ENTRY_IF_ACTIVE 
                        or self.showDetails == SHOW_DETAILS_AT_WIDGET_IF_ACTIVE )
        currentActiveIdx = self.activeIdx
        if currentActiveIdx <= self.maxIdx():
            self.activeIdx = self.maxCntRecords
            if showDetails:
                # hide details
                record = self.record(currentActiveIdx)
                msg = self.format( record )
                if '\n' in msg:
                    parts = msg.split('\n')
                    msg = parts[0]
                self.logTextTree.item(currentActiveIdx, text=msg)
                self.updateParent( self.record(currentActiveIdx) )
                self.updateRecordLevelTag( self.record(currentActiveIdx) )
                
        if idx == currentActiveIdx:
            """ only deactivated the current active one"""
            return

        self.activeIdx = idx
        if self.showDetails == SHOW_DETAILS_AT_ENTRY_IF_ACTIVE:
            record = self.record(idx)
            # show details
            msg = self.format( record )
            self.logTextTree.item(idx, text=msg)
            self.updateParent( record )
            self.updateRecordLevelTag( record )
        
    def clear(self):
        super().clear()
        self.activeIdx = self.maxCntRecords
        self.lastActivePos.clear()
        self.clearCache()
        self.logTextTree.delete( self.logTextTree.get_children() )

    def parentRecord( self, idx )->HLogTextTreeRecord:
        return RecordingHandler.parentRecord( self, idx )

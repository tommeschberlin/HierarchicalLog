from tkinter import *
from tkinter.ttk import *
import logging
from hlog.hlog import *
from tkinter import font
from tkinter import PhotoImage
from tkinter import ttk
from tkinter import Tk
import os
from pathlib import Path
import re
from datetime import datetime
from markdown2 import Markdown
from tkinterweb import HtmlLabel 

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
        self.showSubrecords : bool | None = None
        self.maxChildLevelNo = -1

    @classmethod
    def ensure_HLogRecord(cls, record : HLogRecord | HLogTextTreeRecord) -> HLogTextTreeRecord:
        if isinstance(record, HLogTextTreeRecord):
            return record
        record.__class__ = HLogTextTreeRecord
        record.__dict__.update(record.__dict__)
        assert isinstance(record, HLogTextTreeRecord)
        return record

    @classmethod
    def from_HLogRecord(cls, record : HLogRecord | HLogTextTreeRecord | None) -> HLogTextTreeRecord | None:
        if record is None:
            return None
        return cls.ensure_HLogRecord(record)


def _create_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Zeichnet ein abgerundetes Rechteck auf einem Canvas."""
    points = []
    # gegen Uhrzeigersinn, beginnend oben links
    points += [x1+r, y1, x2-r, y1,
               x2, y1, x2, y1+r,
               x2, y2-r, x2, y2,
               x2-r, y2, x1+r, y2,
               x1, y2, x1, y2-r,
               x1, y1+r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)

class HLogTextTkTreeView(RecordingHandler, Frame):
    CntCreated : int = 0
    DefaultShowSubrecords = False

    def __init__(self, master=None, logger: logging.Logger = logging.getLogger(),
                 fmt: str = '', maxCntRecords: int =  100000, **kw):
        Frame.__init__(self, master, **kw)
        RecordingHandler.__init__(self, maxCntRecords = maxCntRecords )
        HLogTextTkTreeView.CntCreated += 1

        self.name = kw.get( 'name', f"HierarchicalLogTextTree{HLogTextTkTreeView.CntCreated}")
        self.treeBackground = ttk.Style().lookup("Treeview", "background")

        self.activeIdx = maxCntRecords

        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=0)
        self.grid_rowconfigure(0, weight = 1)

        self.scrollX = Scrollbar( self, orient='horizontal' )
        self.scrollY = Scrollbar( self, orient='vertical' )

        self.style = ttk.Style()

        self.logTextTree = ttk.Treeview( self, xscrollcommand=self.scrollX.set, yscrollcommand=self.scrollYCmd, show="tree headings", selectmode="browse",
                                         columns=['Text','More', 'Time'], style=f"{self.name}.Treeview" )

        self.scrollX.configure( command=self.logTextTree.xview )
        self.scrollY.configure( command=self.logTextTree.yview )

        self.timeFormat = "%Y-%m-%d %H:%M:%S"
        timeString = datetime.now().strftime(self.timeFormat)

        self.logTextTree.grid( row=0, column=0, sticky='news' )
        self.scrollY.grid( row=0, column=1, sticky='news')
        self.scrollX.grid( row=1, column=0, sticky='ew' )

        self.fmt = fmt

        # tagnames for levelnames
        self.levelTagNames : dict[str,str] = {}
        for levelName in logging.getLevelNamesMapping().keys():
            self.levelTagNames[levelName] = "Level" + levelName

        self.levelTagActiveSuffix = "_ACTIVE"

        self.foreground = 'black'
        self.logTextTree.tag_configure(self.levelTagNames["ERROR"], foreground="red" )
        self.logTextTree.tag_configure(self.levelTagNames["CRITICAL"], foreground="white", background="red" )
        self.logTextTree.tag_configure(self.levelTagNames["INFO"], foreground="black" )
        self.logTextTree.tag_configure(self.levelTagNames["DEBUG"], foreground="darkgrey" )
        self.logTextTree.tag_configure(self.levelTagNames["WARNING"], foreground="orange" )

        self.activeBackground = 'darkgray'
        self.activeForeground = 'black'
        self.logTextTree.tag_configure(self.levelTagNames["ERROR"] + self.levelTagActiveSuffix , foreground="red", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["CRITICAL"] + self.levelTagActiveSuffix, foreground="white", background="darkred" )
        self.logTextTree.tag_configure(self.levelTagNames["INFO"] + self.levelTagActiveSuffix, foreground="black", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["DEBUG"] + self.levelTagActiveSuffix, foreground="white", background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["WARNING"] + self.levelTagActiveSuffix, foreground="orange", background=self.activeBackground )

        # update
        self.bind('<Configure>', self.onConfigureOrMap)
        self.bind('<Map>', self.onConfigureOrMap)

        self.logTextTree.bind('<<TreeviewSelect>>', self.onSelect)
        self.logTextTree.bind('<<TreeviewOpen>>', self.onOpen)
        self.logTextTree.bind('<<TreeviewClose>>', self.onClose)

        # some chaching
        self.lastHandledRecordHierarchyStage = -1
        self.lastHandledParentIdx = -1
        self.lastActivePos = dict()

        self.clearCache()

        self.cntEnableRequests = 0
        self.showDetails = SHOW_DETAILS_AT_ENTRY_IF_ACTIVE
        self.canShowDetailsInRow = False

        myFont = self.style.configure(f"{self.name}.Treeview", 'font')
        if myFont == '':
            myFont = font.nametofont("TkDefaultFont").actual()

        self.font = font.Font( family=myFont['family'], size=myFont['size'], overstrike=myFont['overstrike'],
                               slant=myFont['slant'], underline=myFont['underline'], weight=myFont['weight'])

        # Sprechblase (Details-Popup) mit abgerundeten Ecken via Canvas
        self.detailsCanvas = Canvas(self.logTextTree, highlightthickness=0, borderwidth=0, background=self.treeBackground)
        self.detailsLabel = HtmlLabel(self.detailsCanvas, relief='flat', borderwidth=0)
        self._detailsWindowId = self.detailsCanvas.create_window(0, 0, window=self.detailsLabel, anchor='nw')
        self.detailsCanvas.place_forget()
        self.md2html = Markdown(extras=['tables'])

    def scrollYCmd(self, *args):
        self.scrollY.set(*args)
        self.updateActiveRecordDetails()

    def destroy(self):
        super().destroy()

    def select(self, idx):
        self.logTextTree.selection_set(idx)

    def addCustomLevel(self, levelId, levelName, tagConfig : dict[str,str] | None = None, tagActiveConfig : dict[str,str] | None = None):
        super().addCustomLevel(levelId, levelName)
        self.levelTagNames[levelName] = "Level" + levelName
        if tagConfig is not None:
            if tagConfig.get( 'foreground') is None:
                tagConfig['foreground'] = self.foreground
            self.logTextTree.tag_configure(self.levelTagNames[levelName], option=None, **tagConfig)
            if tagActiveConfig is None:
                tagActiveConfig = tagConfig
            if tagActiveConfig.get( 'foreground') is None:
                tagActiveConfig['foreground'] = self.foreground
            self.logTextTree.tag_configure( self.levelTagNames[levelName] + self.levelTagActiveSuffix, option=None, **tagActiveConfig)

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
        if not parent.showSubrecords is None and \
           parent.showSubrecords != (self.logTextTree.item( parent.idx )['open'] != 0):
            self.logTextTree.item( parent.idx, open=parent.showSubrecords )

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

    def insertRecordAt( self, parentId, indexAtParent, record : HLogTextTreeRecord, showDetails : bool = False ) -> str:
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

    def insertRecordsAt(self, indicees, index, parent : HLogTextTreeRecord | None = None):
        """ inserts a group of records at index """
        insertedIds : list[str] = []
        maxChildLevelNo = -1
        parentId = ''

        if parent != None:
            # no parent treatment needed if already done for a previous record
            if parent.idx != self.lastHandledParentIdx:
                self.updateParent( parent )
            if not parent.showSubrecords:
                return []
            maxChildLevelNo = parent.maxChildLevelNo
            parentId = parent.itemId

        for idx in indicees:
            record = HLogTextTreeRecord.ensure_HLogRecord(self.record( idx ))
            if record.levelno > maxChildLevelNo:
                maxChildLevelNo = record.levelno
            if not self.passedFilter( record ):
                continue

            insertedIds += self.insertRecordAt( parentId, index + len(insertedIds), record, 
                                                self.showDetails == (SHOW_DETAILS_AT_ENTRY_IF_ACTIVE and self.canShowDetailsInRow and self.activeIdx == idx) )

            # insert children
            # only not last element can have children
            if record.idx < self.maxIdx():
                insertedIds.extend(self.insertRecordsAt(self.getFilteredChildren( record.idx ),\
                                                        index + len(insertedIds), record))

        if parent != None and maxChildLevelNo > parent.levelno and maxChildLevelNo > parent.maxChildLevelNo:
            parent.maxChildLevelNo = maxChildLevelNo
            self.updateRecordLevelTag( parent )
        
        return insertedIds

    def emit(self, record : HLogRecord)->None:
        RecordingHandler.emit( self, record )

        # no parent retrieving needed if already done for a previous record
        parent : HLogTextTreeRecord | None
        if self.lastHandledRecordHierarchyStage == record.hierarchyStage:
            parent = HLogTextTreeRecord.from_HLogRecord(self.at( self.lastHandledParentIdx ))
        else:
            parent = HLogTextTreeRecord.from_HLogRecord(self.parentRecord( record.idx ))

        isShow = self.passedFilter( record )
        if isShow and parent:
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
        parent = HLogTextTreeRecord.ensure_HLogRecord(self.record( parentIdx ))
        if parent.showSubrecords == False:
            return False
        return self.isShow( parentIdx )

    def onConfigureOrMap(self, *args):
        self.pageSize = self.logTextTree.cget( 'height' )
        def adjust():
            """Adjust scroll position according to the scale."""
            self.updateActiveRecordDetails()
            self.update_idletasks() # "force" redraw
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

        record = HLogTextTreeRecord.ensure_HLogRecord(self.record( selIdx ))
        newLevelName = record.levelname
        if record.maxChildLevelNo > 0:
            newLevelName = logging.getLevelName( record.maxChildLevelNo )
        tagConfig = self.logTextTree.tag_configure(self.levelTagNames[newLevelName] + self.levelTagActiveSuffix )
        self.style.map(f"{self.name}.Treeview", background=[('selected',tagConfig['background'])],foreground=[('selected',tagConfig['foreground'])])

    def onOpen(self, event):
        selIdx = int(self.logTextTree.selection()[0])
        record = HLogTextTreeRecord.ensure_HLogRecord(self.record( selIdx ))
        record.showSubrecords = True

    def onClose(self, event):
        selIdx = int(self.logTextTree.selection()[0])
        record = HLogTextTreeRecord.ensure_HLogRecord(self.record( selIdx ))
        record.showSubrecords = False

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
                self.updateParent( HLogTextTreeRecord.ensure_HLogRecord(self.record(currentActiveIdx)) )
                self.updateRecordLevelTag( HLogTextTreeRecord.ensure_HLogRecord(self.record(currentActiveIdx)) )
                
        if idx == currentActiveIdx:
            # only deactivated the current active one
            return

        self.activeIdx = idx
        record = HLogTextTreeRecord.ensure_HLogRecord(self.record(idx))
        msg = self.format( record )
        if '\n' in msg:
            parts = msg.split('\n')
            msg = parts[0]

        self.logTextTree.item(idx, text=msg)
        self.updateParent( record )
        self.updateRecordLevelTag( record )
        self.updateActiveRecordDetails()

    def updateActiveRecordDetails( self ):
        if self.showDetails != SHOW_DETAILS_AT_ENTRY_IF_ACTIVE or self.activeIdx == self.maxCntRecords:
            self.detailsCanvas.place_forget()
            return

        # Use bbox of the entry's tree column (column '#0') to determine the left edge,
        # then extend the popup from the right side of the entry to the scrollbar
        boxTuple = self.logTextTree.bbox( self.activeIdx, column='#0' )
        if not len(boxTuple):
            self.detailsCanvas.place_forget()
            return

        record = HLogTextTreeRecord.ensure_HLogRecord(self.record(self.activeIdx))
        msg = self.format( record )
        # details are expected after heading, separated by \n
        if not '\n' in msg: 
            self.detailsCanvas.place_forget()
            return

        # extract/show details
        msg = msg.replace("\t", "") # tabs ersetzen
        parts = msg.split('\n')
        #details = "```" + '\n'.join( parts[1:len(parts)] ) + "```"
        details = '\n'.join( parts[1:len(parts)] )

        # calc position: left edge = right side of the entry's bbox (tree column)
        # width = from there to the right edge of the treeview
        class boxT:
            def __init__(self):
                self.x : int = 0
                self.y : int = 0
                self.w : int = 0
                self.h : int = 0

        box = boxT()
        assert isinstance(boxTuple, tuple)
        box.x, box.y, box.w, box.h = boxTuple
        x = box.x + box.w
        width = self.logTextTree.winfo_width() - x

        # set colors                        
        tagName = self.levelTagNameFromIdx( self.activeIdx )
        fg = 'black'
        if tagName is not None:
            fg = self.logTextTree.tag_configure(tagName, 'foreground')
            if isinstance(fg, tuple):
                fg = fg[4]

        # Label vor dem Messen auf volle Breite setzen, damit Text nicht umbricht
        self.detailsCanvas.place(x=0, y=-1000, width=1000, height=1000)
        self.detailsCanvas.itemconfig(self._detailsWindowId, width=2000, height=2000)
        self.update()

        # insert markdown
        html = self.md2html.convert( details ).strip()
        html = html.replace("\n\n", "\n")
        html = f"<div style='color: {fg};'>{html}</div>"
        print('-------')
        print(html)
        self.detailsLabel.load_html(html)

        # Ab hier alles in after_idle, damit alle Änderungen durchgelaufen sind
        def _update():
            maxLineWidth  = self.detailsLabel.html.winfo_reqwidth()

            # Höhe aus Textzeilen
            textPadX = int(self.detailsLabel.cget('borderwidth'))
            textPadY = int(self.detailsLabel.cget('borderwidth'))

            textHeight = self.detailsLabel.winfo_reqheight() + 2 * textPadY
            textWidth = maxLineWidth + 2 * textPadX

            r = 8
            rectBorder = r/2
            canvasHeight = textHeight + 2*rectBorder
            canvasWidth = textWidth + 2*rectBorder

            self.detailsCanvas.itemconfig(self._detailsWindowId, width=textWidth, height=textHeight)

            self.detailsCanvas.delete('roundrect')
            _create_rounded_rect(self.detailsCanvas, 1, 1, textWidth + textPadX -1, textHeight + textPadY -1, r,
                                 fill=self.activeBackground,
                                 outline='gray', width=1,
                                 tags='roundrect')
            self.detailsCanvas.tag_lower('roundrect')

            self.detailsCanvas.coords(self._detailsWindowId, rectBorder, rectBorder)

            y = box.y
            if y + canvasHeight > self.logTextTree.winfo_height():
               y = self.logTextTree.winfo_height() - canvasHeight

            self.detailsCanvas.itemconfig(self._detailsWindowId, width=textWidth, height=textHeight)
            self.detailsCanvas.place(x=x, y=y, width=canvasWidth, height=canvasHeight)
        
        self.after_idle(_update)
      
    def clear(self):
        super().clear()
        self.activeIdx = self.maxCntRecords
        self.lastActivePos.clear()
        self.clearCache()
        self.logTextTree.delete( *self.logTextTree.get_children() )

    def parentRecord( self, idx ):
        return RecordingHandler.parentRecord( self, idx )

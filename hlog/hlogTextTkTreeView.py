from tkinter import Frame,Scrollbar,Canvas
import logging
from hlog.hlog import *
from tkinter import font
from tkinter import ttk
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
        self.showTimeCol = kw.get( 'showTimeCol', True)
        kw.pop('showTimeCol', None)
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

        columns = ['Time'] if self.showTimeCol else []

        self.logTextTree = ttk.Treeview( self, xscrollcommand=self.scrollX.set, yscrollcommand=self.scrollYCmd,
                                         show="tree headings", selectmode="browse",
                                         columns=columns, style=f"{self.name}.Treeview" )
        ttk.Style().configure("Treeview", indent = 20)

        # Spaltenüberschriften setzen
        self.logTextTree.heading('#0', text='Entry')
        if self.showTimeCol:
            self.logTextTree.heading('Time', text='Time')

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
        self.logTextTree.tag_configure(self.levelTagNames["ERROR"] + self.levelTagActiveSuffix , foreground="red",
                                       background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["CRITICAL"] + self.levelTagActiveSuffix, foreground="white",
                                       background="darkred" )
        self.logTextTree.tag_configure(self.levelTagNames["INFO"] + self.levelTagActiveSuffix, foreground="black",
                                       background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["DEBUG"] + self.levelTagActiveSuffix, foreground="white",
                                       background=self.activeBackground )
        self.logTextTree.tag_configure(self.levelTagNames["WARNING"] + self.levelTagActiveSuffix, foreground="orange",
                                       background=self.activeBackground )

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
        self.detailsCanvas = Canvas(self.logTextTree, highlightthickness=0, borderwidth=0,
                                    background=self.treeBackground)
        self.detailsLabel = HtmlLabel(self.detailsCanvas, relief='flat', borderwidth=0)
        self._detailsWindowId = self.detailsCanvas.create_window(0, 0, window=self.detailsLabel, anchor='nw')
        self.detailsCanvas.place_forget()
        self.md2html = Markdown(extras=['tables'])
        # Stylt das <pre>-Tag (oder das <code>-Tag) für eine schöne Code-Box
        self.htmlStyle =  ("""
        <style>
            body {
                margin: 2px;
                padding: 0;
            }
            pre, code { 
                background-color: #f5f5f5; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                padding: 4px; 
                font-family: monospace; 
                white-space: pre;
                display: block;
                margin: 2;
            }
        </style>
        """)        


    def scrollYCmd(self, *args):
        self.scrollY.set(*args)
        self.updateActiveRecordDetails()

    def destroy(self):
        super().destroy()

    def select(self, idx):
        self.logTextTree.selection_set(idx)

    def addCustomLevel(self, levelId, levelName, tagConfig : dict[str,str] | None = None,
                       tagActiveConfig : dict[str,str] | None = None):
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
            self.logTextTree.tag_configure( self.levelTagNames[levelName] + self.levelTagActiveSuffix, option=None,
                                           **tagActiveConfig)

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

    def insertRecordAt( self, parentId, indexAtParent, record : HLogTextTreeRecord,
                       showDetails : bool = False ) -> str:
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
                                                self.showDetails == (SHOW_DETAILS_AT_ENTRY_IF_ACTIVE \
                                                                     and self.canShowDetailsInRow \
                                                                     and self.activeIdx == idx) )

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
        self.style.map(f"{self.name}.Treeview", background=[('selected',tagConfig['background'])],
                       foreground=[('selected',tagConfig['foreground'])])

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

    def getItemIndent(self, itemId):
        """Berechnet die exakte Einrückung des Textes für ein Element in Pixeln."""
        # 1. Ebene (Tiefe) im Baum bestimmen
        depth = 0
        current = itemId
        while True:
            current = self.logTextTree.parent(current)
            if current == "":  # Die oberste Wurzel ist erreicht
                break
            depth += 1
            
        # 2. Den systemweiten Einzugswert (Indent) in Pixeln ermitteln
        # Holt den 'indent'-Wert des Treeviews. Standardwert ist meist 20, falls nicht definiert.
        indent_setting = ttk.Style().lookup("Treeview", "indent")
        
        indent_per_level = int(indent_setting) if isinstance(indent_setting, int) else 20
        
        # 3. Reine Einrückung berechnen
        pure_indent = depth * indent_per_level

        padding = 4
        
        # Optional: Konstanten für Pfeil (Expand-Icon) und Grafik-Padding aufschlagen
        # Ein Aufklapp-Pfeil benötigt in den meisten Standard-Themes ca. 16 Pixel Platz.
        arrow_space = 16
        
        return pure_indent + arrow_space + 2 * padding

    def updateActiveRecordDetails( self ):
        if self.showDetails != SHOW_DETAILS_AT_ENTRY_IF_ACTIVE or self.activeIdx == self.maxCntRecords:
            self.detailsCanvas.place_forget()
            return

        # Use bbox of the entry's tree column (column '#0') to determine the left edge,
        # then extend the popup from the right side of the entry to the scrollbar
        column0BoxTuple = self.logTextTree.bbox( self.activeIdx, column='#0' )
        if not len(column0BoxTuple):
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
        msgParts = msg.split('\n')
        details = '\n'.join( msgParts[1:len(msgParts)] )

        # calc position: left edge = right side of the entry's bbox (tree column)
        # width = from there to the right edge of the treeview
        class boxT:
            def __init__(self, boxTuple):
                assert isinstance(boxTuple, tuple)
                self.x, self.y, self.w, self.h = boxTuple

        box = boxT(column0BoxTuple)
        maxX = self.logTextTree.winfo_width()
        minDetailsWidth = 50
        minDetailsX = 15
        maxDetailsX = max(min(box.x + box.w - minDetailsWidth, maxX - minDetailsWidth), minDetailsX)
        maxDetailsWidth = maxX - minDetailsX

        # set colors                        
        tagName = self.levelTagNameFromIdx( self.activeIdx )
        fg = 'black'
        if tagName is not None:
            fg = self.logTextTree.tag_configure(tagName, 'foreground')
            if isinstance(fg, tuple):
                fg = fg[4]

        # Label vor dem Messen auf volle Breite setzen, damit Text nicht umbricht
        #self.detailsCanvas.place(x=0, y=-1000, width=1000, height=1000)
        #self.detailsCanvas.itemconfig(self._detailsWindowId, width=2000, height=2000)
        #self.update()

        # insert markdown
        html = self.md2html.convert( details ).strip()

        # Entfernt das umschließende <p> und </p>, falls vorhanden
        html = re.sub(r'^<p>(.*?)</p>$', r'\1', html, flags=re.DOTALL)
        # style hinzufügen
        html = f"{self.htmlStyle}<div style='color: {fg};'>{html}</div>"
        self.detailsLabel.load_html(html)
        self.update() # wichtig für korrekte Größenanpassung

        # Ab hier alles in after_idle, damit alle Änderungen durchgelaufen sind
        def _update():
            maxHtmlWidth = self.detailsLabel.html.winfo_reqwidth()
            maxHtmlHeight = self.detailsLabel.winfo_reqheight()

            textPadX = int(self.detailsLabel.cget('borderwidth'))
            textPadY = int(self.detailsLabel.cget('borderwidth'))
            textHeight = maxHtmlHeight + 2 * textPadY
            textWidth = maxHtmlWidth + 2 * textPadX

            offset = -5
            r = 8
            rectBorder = r/2
            canvasHeight = textHeight + rectBorder + 1
            canvasWidth = textWidth + rectBorder + 1

            self.detailsCanvas.itemconfig(self._detailsWindowId, width=textWidth, height=textHeight)

            self.detailsCanvas.delete('roundrect')
            _create_rounded_rect(self.detailsCanvas, 0, 0, textWidth + textPadX + r/2 ,
                                 textHeight + textPadY + r/2, r,
                                 fill=self.activeBackground,
                                 outline='gray', width=1,
                                 tags='roundrect')
            self.detailsCanvas.tag_lower('roundrect')

            self.detailsCanvas.coords(self._detailsWindowId, r/4, r/4)

            y = box.y + offset
            if y < 0:
                y = 0
            if y + canvasHeight > self.logTextTree.winfo_height():
               y = self.logTextTree.winfo_height() - canvasHeight

            logTextWidth = self.font.measure(msgParts[0])
            x = logTextWidth + self.getItemIndent(record.itemId)
            canvasWidth = min(canvasWidth, maxDetailsWidth)
            if x + canvasWidth > maxX:
                x = maxX - canvasWidth
                if x < minDetailsX:
                    x = minDetailsX
                    canvasWidth = minDetailsWidth

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

import pytest, tkinter, sys, warnings, os
from tkinter import *
from tkinter.ttk import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from hlog import *
from hlog.hlogTextTkText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
#Theme = 'default'

class App(tkinter.Frame):
    # init vars, create UI, start
    ####################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        # create logger
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        self.title = "HierarchicalLogTextTest"

        self.hLogText = HierarchicalLogText( self )
        self.hLogText.DefaultShowSubrecords = True
        self.hLogText.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogText)

    def destroy(self):
        self.logger.removeHandler( self.hLogText )
        resetLogHierarchy(self.logger)
        super().destroy()

class TestHlogTkText():
    def setup_method(self):
        self.Root = Tk()
        self.Root.resizable(True,True)
        self.Root.wm_attributes("-topmost", 1)
        self.Root.geometry("-3100+0")
        self.Root.winfo_screen

        self.app = App( self.Root )
        self.app.pack(fill=BOTH, expand=True)
        self.Root.update()
        self.hLogText : HierarchicalLogText = self.app.hLogText
        self.fillLog()

    def teardown_method(self):
        self.app.destroy()
        self.Root.destroy()

    def expectEqual(self, first, second, msg=None):
        if not msg:
            msg = f"{first} is not equal to {second} at {sys.exc_info()}"
        if first != second:
            warnings.warn(msg)

    def expectTrue(self, expression, msg=None):
        if not msg:
            msg = f"Expression {expression} is not True, at {sys.exc_info()}"
        if not expression:
            warnings.warn(msg)

    def expectFalse(self, expression, msg=None):
        if msg:
            msg = f"Expression {expression} is not False, at {sys.exc_info()}"
        if expression:
            warnings.warn(msg)

    def assertEqual(self, first, second, msg = None):
        assert first == second, msg

    def assertTrue(self, expression, msg = None):
        assert expression, msg

    def assertFalse(self, expression, msg = None):
        assert not expression, msg

    def fillLog(self):
        with EnterLowerLogHierarchyStage( "00", self.app.logger ) :
            with EnterLowerLogHierarchyStage( "10", self.app.logger ) :
                self.app.logger.debug("20")
            self.app.logger.warning("11")
        self.app.logger.error("01")
        
    def getPosAtParent(self, idx):
        parentIdx = self.hLogText.parentIdx( idx )
        pos = 0
        for childIdx in self.hLogText.getFilteredChildren( parentIdx ):
            if childIdx == idx:
                return pos
            pos += 1
        return None
    
    def getPreviousNotShownCount( self, idx ):
        testIdx = 0
        cntNotShown = 0
        while testIdx < idx:
            if not self.hLogText.isShow( testIdx ):
                cntNotShown += 1
            testIdx += 1
        return cntNotShown

    def checkEntry( self, idx ):
        textWidget = self.hLogText.logText

        parent = self.hLogText.parentRecord( idx )
        if parent != None:
            if parent.showSubrecords == False or not self.hLogText.isShow( idx):
                markTag = self.hLogText.markFromIdx( idx )
                begin,end = self.hLogText.rangeFromMark( markTag )
                self.assertEqual( begin, None, f"Idx {idx}: No marktags expected, if not shown" )
                return

        # test idx
        record = self.hLogText.record( idx )
        self.assertEqual( record.idx , idx )

        # text pos/index
        begin = self.hLogText.indexFromIdx( idx )
        end = textWidget.index( begin + " lineend" )

        # get count of previous suppressed ones
        cntNotShownCount = self.getPreviousNotShownCount( idx )
        expectedLine = idx - cntNotShownCount + 1
        self.assertEqual( int( begin.split('.')[0] ), expectedLine, "Idx %s: Line for should be %s" % (idx, expectedLine) )
        self.assertEqual( int( begin.split('.')[1] ), 0, "Idx %s: Col should be %s" % (idx, 0) )

        # test mark
        expectedMark = "Record%s" % idx
        mark = self.hLogText.markFromIdx(idx)
        self.assertEqual( mark, expectedMark, "Idx %s: Mark wrong for idx" % idx )

        # test text / hierarchy
        hierarchy = self.hLogText.record( idx ).hierarchyStage
        posAtParent = self.getPosAtParent( idx )
        text = textWidget.get(begin, end)
        expectedText = "%s%s" % (hierarchy,posAtParent)
        self.assertEqual( text, expectedText, f"Idx {idx}: Text/Pos at Parent, Hierarchy wrong" )
        self.assertEqual( text, record.msg )
        endCol = int(end.split('.')[1])
        expectedEndCol = len(text)
        if self.hLogText.cntFilteredChildren( idx ) > 0:
            expectedEndCol += 1 # because of shon icon
        self.assertEqual( expectedEndCol, endCol, f"Idx {idx}: col of last message letter should match endpos" )
            
        dump = textWidget.dump( image=True, tag=True, index1=begin, index2= textWidget.index(end + " +1c"))
        tagon = []
        tagoff = []
        for entry in dump:
            type,name,index = entry[0],entry[1],entry[2]
            line = int(index.split('.')[0])
            col = int(index.split('.')[1])
            if type == "image":
                self.assertEqual( col, 0)
            elif type == "tagon":
               self.assertEqual( col, 0, f"{type} for tag {name} at idx {idx} should be at col 0 not at col {col}" )
               # some creepy exception for ACTIVE
               if name.endswith("_ACTIVE"):
                   tagoff.append(name)
               tagon.append(name)
            elif type == "tagoff":
                expectedTagEndCol = expectedEndCol
                # some creepy exception for ACTIVE
                if name.endswith("_ACTIVE"):
                    continue
                if name == self.hLogText.AlterShowSubrecordsTag:
                    expectedTagEndCol = 1
                self.assertEqual( col, expectedTagEndCol, f"Idx {idx}: Endcolcheck for tag {name}" )
                tagoff.append(name)

        if self.hLogText.cntFilteredChildren( idx ) == 0:
             # Type-Tag, Idx-Tag, Stage-Tag
            self.assertEqual( 3, len(tagon), f"Idx {idx}: Record without children should have 3 tags" )
        else:
             # additional "ALTER_SHOW_RECORDS"-Tag
            self.assertEqual( 4, len(tagon), f"Idx {idx}: Record with children should have 4 tags" )

        for tag in tagon:
            self.assertTrue( ( tag in tagoff ), "Idx %s: Tag %s not in tagoff %s" %(idx,tag,tagoff) )
    
        for tag in tagoff:
            self.assertTrue( ( tag in tagon ), "Idx %s: Tag %s not in tagon %s" %(idx,tag,tagon) )


    def checkAllEntries(self):
        idx = 0
        while idx <= self.hLogText.maxIdx():
            self.checkEntry(idx)
            idx += 1

    def getEventForIdx( self, idx ):
        index = self.hLogText.indexFromIdx( idx )
        self.Root.update()
        bbox = self.hLogText.logText.bbox( index )
        event = Event()
        self.Root.update()
        event.x = bbox[0]
        event.y = bbox[1]
        return event

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_initialFilled(self):
        self.checkAllEntries()

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterActiveRecord( self ):
        self.checkAllEntries()
        # emulate mouse event
        self.hLogText.alterActiveRecord( 1 )
        self.checkAllEntries()
        self.assertEqual( self.hLogText.activeIdx, 1 )
        self.hLogText.alterActiveRecord( 1 )
        self.checkAllEntries()
        self.assertEqual( self.hLogText.activeIdx, self.hLogText.maxCntRecords )

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterShowSubrecordsDepth1( self ):
        event = self.getEventForIdx( 1 )

        # emulate mouse event
        self.hLogText.alterShowSubrecords( event )
        self.expectTrue( self.hLogText.isShow( 0 ) )
        self.expectTrue( self.hLogText.isShow( 1 ) )
        self.expectFalse( self.hLogText.isShow( 2 ) )
        self.expectTrue( self.hLogText.isShow( 3 ) )
        self.expectTrue( self.hLogText.isShow( 4 ) )
        self.checkAllEntries()

        # and back
        self.hLogText.alterShowSubrecords( event )
        self.expectTrue( self.hLogText.isShow( 0 ) )
        self.expectTrue( self.hLogText.isShow( 1 ) )
        self.expectTrue( self.hLogText.isShow( 2 ) )
        self.expectTrue( self.hLogText.isShow( 3 ) )
        self.expectTrue( self.hLogText.isShow( 4 ) )
        self.checkAllEntries()

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterShowSubrecordsDetph2( self ):
        event = self.getEventForIdx( 0 )

        # emulate mouse event
        self.hLogText.alterShowSubrecords( event )
        self.expectTrue( self.hLogText.isShow( 0 ) )
        self.expectFalse( self.hLogText.isShow( 1 ) )
        self.expectFalse( self.hLogText.isShow( 2 ) )
        self.expectFalse( self.hLogText.isShow( 3 ) )
        self.expectTrue( self.hLogText.isShow( 4 ) )
        self.checkAllEntries()

        # and back
        self.hLogText.alterShowSubrecords( event )
        self.expectTrue( self.hLogText.isShow( 0 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 0 ), '1.0', "Idx 0 should have Index 1.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("1.0")), 0,
                          "Idx at Index 1.0 should be 0")
        self.expectTrue( self.hLogText.isShow( 1 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 1 ), '2.0', "Idx 1 should have Index 2.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("2.0")), 1,
                          "Idx at Index 2.0 should be 1")
        self.expectTrue( self.hLogText.isShow( 2 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 2 ), '3.0', "Idx 2 should have Index 3.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("3.0")), 2,
                          "Idx at Index 3.0 should be 2")
        self.expectTrue( self.hLogText.isShow( 3 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 3 ), '4.0', "Idx 3 should have Index 4.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("4.0")), 3,
                          "Idx at Index 4.0 should be 3")
        self.expectTrue( self.hLogText.isShow( 4 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 4 ), '5.0', "Idx 4 should have Index 5.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("5.0")), 4,
                          "Idx at Index 5.0 should be 4")
        self.checkAllEntries()

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterShowSubrecordsTwice( self ):
        self.hLogText.alterShowSubrecords( self.getEventForIdx( 1 ) )
        self.checkAllEntries()

        event = self.getEventForIdx( 0 )
        self.hLogText.alterShowSubrecords( event )
        self.checkAllEntries()

        self.hLogText.alterShowSubrecords( event )
        self.checkAllEntries()

        self.hLogText.alterShowSubrecords( event )
        self.hLogText.alterShowSubrecords( event )

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterActivceRecordIfAHiddenIsActive( self ):
        self.hLogText.alterActiveRecord( 2 )
        self.hLogText.alterShowSubrecords( self.getEventForIdx( 1 ) )

        # record which was marked active was removeod bei alterShowSubrecords, therefore the acitveIdx shoud be reset
        self.assertEqual( self.hLogText.activeIdx, self.hLogText.maxCntRecords,
                          "If hiding active records, activeIdx should be resetted")
        
        self.hLogText.alterActiveRecord( 0 )

    def test_customLogLevel( self ):
        newLevelId = logging.INFO + 1
        newLevelName = "NEW"
        newLevelFont = self.hLogText.logText.cget("font")
        if isinstance(newLevelFont, str):
            newLevelFont = font.Font(family = newLevelFont)
        newLevelFont.configure(weight = 'bold')

        self.hLogText.addCustomLevel( newLevelId, newLevelName,
                                     { 'foreground':"white", 'background':"red",'font' : newLevelFont},
                                     { 'foreground':"white", 'background':"red",'font' : newLevelFont}  )

        self.app.logger.log( newLevelId, "02")
        newLevelRecordIdx = self.hLogText.maxIdx()
        self.checkAllEntries()

        lowerHierarchyStage = LowerLogHierarchyStage( self.app.logger )
        self.app.logger.info('10')
        self.checkAllEntries()

        tagLevelName = self.hLogText.levelTagNameFromIndex( self.hLogText.indexFromIdx( newLevelRecordIdx ) )
        self.assertEqual( tagLevelName, self.hLogText.levelTagNames[newLevelName],
                          f"TagLevelname {self.hLogText.levelTagNames[newLevelName]} expected, found {tagLevelName}!")

        range = self.hLogText.rangeFromMark( self.hLogText.markFromIdx( newLevelRecordIdx ) )
        objRanges = self.hLogText.logText.tag_ranges( self.hLogText.levelTagNames[newLevelName] )
        ranges = ()
        for e in objRanges:
            ranges = ranges + (str(e),)
        self.assertEqual( range, ranges, "Ranges for new tag and for last entry should match")


    # Test 
    # @unittest.skip("skipped temporarily")
    def test_activateSecondRecord( self ):
        self.Root.update_idletasks()
        indexEnd0 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.hLogText.alterActiveRecord( 1 )
        self.Root.update_idletasks()
        indexEnd1 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.assertEqual( indexEnd0, indexEnd1 )        
        self.hLogText.alterShowSubrecords( self.getEventForIdx( 0 ) )
        self.Root.update_idletasks()
        self.assertFalse( self.hLogText.isShow(1) )
        indexEnd2 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.assertEqual( indexEnd2, "2.0")

    def test_markFromIndex( self ):
        pass

    def test_updateParentLevelTag( self ):
        pass

# create programm window
if __name__ == '__main__':
    import pytest, sys
    pytest.main([sys.argv[0], "-v"])

import unittest
import tkinter
import sys
import time
from tkinter import *
from tkinter.ttk import *
from hlog import *
from hlogText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
#Theme = 'default'

class App(tkinter.Frame):
    # init vars, create UI, start
    ######################################################################################################################
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

class TestHlogText(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
    
    def setUp(self):
        self.app = App( Root )
        self.app.pack(fill=BOTH, expand=True)
        Root.update()
        self.hLogText = self.app.hLogText
        self.fillLog()

    def tearDown(self):
        self.app.destroy()

    def run(self, result=None):
        if result is None:
            self.result = self.defaultTestResult()
        else:
            self.result = result

        return unittest.TestCase.run(self, result)

    def expect(self, val, msg=None):
        '''
        Like TestCase.assert_, but doesn't halt the test.
        '''
        try:
            self.assert_(val, msg)
        except:
            self.result.addFailure(self, sys.exc_info())

    def expectEqual(self, first, second, msg=None):
        try:
            self.assertEqual(first, second, msg)
        except:
            self.result.addFailure(self, sys.exc_info())

    def expectTrue(self, expression, msg=None):
        try:
            self.assertTrue(expression, msg)
        except:
            self.result.addFailure(self, sys.exc_info())

    def expectFalse(self, expression, msg=None):
        try:
            self.assertFalse(expression, msg)
        except:
            self.result.addFailure(self, sys.exc_info())

    expect_equal = expectEqual

    assert_equal = unittest.TestCase.assertEqual
    assert_raises = unittest.TestCase.assertRaises        

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
                self.assertEqual( begin, None, "Idx %s: No marktags expected, if not shown" % idx)
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
        self.assertEqual( text, expectedText, "Idx %s: Text/Pos at Parent, Hierarchy wrong" % idx )
        self.assertEqual( text, record.msg )
        endCol = int(end.split('.')[1])
        expectedEndCol = len(text)
        if self.hLogText.cntFilteredChildren( idx ) > 0:
            expectedEndCol += 1 # because of shon icon
        self.assertEqual( expectedEndCol, endCol, "Idx %s: col of last message letter should match endpos" % idx )
            
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
               self.assertEqual( col, 0, "%s for tag %s at idx %s should be at col 0 not at col %s" %(type,name,idx,col))
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
                self.assertEqual( col, expectedTagEndCol, "Idx %s: Endcolcheck for tag %s" % (idx,name))
                tagoff.append(name)

        if self.hLogText.cntFilteredChildren( idx ) == 0:
            self.assertEqual( 3, len(tagon), "Idx %s: Record without children should have 3 tags"  % idx ) # Type-Tag, Idx-Tag, Stage-Tag
        else:
            self.assertEqual( 4, len(tagon), "Idx %s: Record with children should have 4 tags" % idx ) # additional "ALTER_SHOW_RECORDS"-Tag

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
        Root.update()
        bbox = self.hLogText.logText.bbox( index )
        event = Event()
        Root.update()
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
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("1.0")), 0, "Idx at Index 1.0 should be 0")
        self.expectTrue( self.hLogText.isShow( 1 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 1 ), '2.0', "Idx 1 should have Index 2.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("2.0")), 1, "Idx at Index 2.0 should be 1")
        self.expectTrue( self.hLogText.isShow( 2 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 2 ), '3.0', "Idx 2 should have Index 3.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("3.0")), 2, "Idx at Index 3.0 should be 2")
        self.expectTrue( self.hLogText.isShow( 3 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 3 ), '4.0', "Idx 3 should have Index 4.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("4.0")), 3, "Idx at Index 4.0 should be 3")
        self.expectTrue( self.hLogText.isShow( 4 ) )
        self.expectEqual( self.hLogText.indexFromIdx( 4 ), '5.0', "Idx 4 should have Index 5.0")
        self.expectEqual( self.hLogText.idxFromMark( self.hLogText.markFromIndex("5.0")), 4, "Idx at Index 5.0 should be 4")
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
        self.assertEqual( self.hLogText.activeIdx, self.hLogText.maxCntRecords, "If hiding active records, activeIdx should be resetted")
        
        self.hLogText.alterActiveRecord( 0 )

    def test_customLogLevel( self ):
        newLevelId = logging.INFO + 1
        newLevelName = "NEW"
        newLevelFont = self.hLogText.logText.cget("font")
        if isinstance(newLevelFont, str):
            newLevelFont = font.Font(family = newLevelFont)
        newLevelFont.configure(weight = 'bold')

        self.hLogText.addCustomLevel( newLevelId, newLevelName, { 'foreground':"white", 'background':"red",'font' : newLevelFont},
                                     { 'foreground':"white", 'background':"red",'font' : newLevelFont}  )

        self.app.logger.log( newLevelId, "02")
        newLevelRecordIdx = self.hLogText.maxIdx()
        self.checkAllEntries()

        lowerHierarchyStage = LowerLogHierarchyStage( self.app.logger )
        self.app.logger.info('10')
        self.checkAllEntries()

        tagLevelName = self.hLogText.levelTagNameFromIndex( self.hLogText.indexFromIdx( newLevelRecordIdx ) )
        self.assert_equal( tagLevelName, self.hLogText.levelTagNames[newLevelName],
                           "TagLevelname %s expected, found %s" % (self.hLogText.levelTagNames[newLevelName],tagLevelName) )

        range = self.hLogText.rangeFromMark( self.hLogText.markFromIdx( newLevelRecordIdx ) )
        objRanges = self.hLogText.logText.tag_ranges( self.hLogText.levelTagNames[newLevelName] )
        ranges = ()
        for e in objRanges:
            ranges = ranges + (str(e),)
        self.assert_equal( range, ranges, "Ranges for new tag and for last entry should match")


    # Test 
    # @unittest.skip("skipped temporarily")
    def test_activateSecondRecord( self ):
        Root.update_idletasks()
        indexEnd0 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.hLogText.alterActiveRecord( 1 )
        Root.update_idletasks()
        indexEnd1 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.assertEqual( indexEnd0, indexEnd1 )        
        self.hLogText.alterShowSubrecords( self.getEventForIdx( 0 ) )
        Root.update_idletasks()
        self.assertFalse( self.hLogText.isShow(1) )
        indexEnd2 = self.hLogText.indexFromIdx( self.hLogText.maxIdx())
        self.assertEqual( indexEnd2, "2.0")

    def test_markFromIndex( self ):
        pass

    def test_updateParentLevelTag( self ):
        pass

# create programm window and start mainloop
Root = Tk()
Root.resizable(True,True)
Root.wm_attributes("-topmost", 1)
Root.geometry("-3100+0")
Root.winfo_screen

if __name__ == '__main__':
    unittest.main(failfast=True)

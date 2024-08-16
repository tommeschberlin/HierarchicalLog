import unittest
import tkinter
import sys
from tkinter import *
from tkinter.ttk import *
from hlog import *
from hlogText import *

# themes 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
Theme = 'default'

class App(tkinter.Frame):
    # init vars, create UI, start
    ######################################################################################################################
    def __init__(self, root):
        super().__init__(root)

        self.style = Style(root)
        self.style.theme_use(Theme)
    
        # create logger
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        initLogHierarchy(self.logger)

        self.title = "HierarchicalLogTextTest"

        self.hLogText = HierarchicalLogText( self )
        self.hLogText.DefaultShowSubrecords = True
        self.hLogText.pack(fill=BOTH, expand=True)
        self.logger.addHandler(self.hLogText)

    def start(self):
       # self.logger.info("info")
       # self.logger.debug("debug")
       # self.logger.warning("warning")
       # self.logger.error("error")
       # self.logger.critical("critical")

        with EnterLowerLogHierarchyStage( "0-0 Stage 0 -> 1", self.logger ) :
            with EnterLowerLogHierarchyStage( "1-0 Stage 1 -> 2", self.logger ) :
                self.logger.debug("2-0 something with already lowered log hierarchy stage here")
                with EnterLowerLogHierarchyStage( "2-1 Stage 2 -> 3", self.logger ) :
                    self.logger.debug("3-0 something with already lowered log hierarchy stage here")
                self.logger.debug("2-2 something with already lowered log hierarchy stage here")
            self.logger.warning("1-1 something with already lowered log hierarchy stage here")

        for i in range(10):
        #  self.logger.info("info " + str(i))
          pass

class TestHlogText(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
    
    def setUp(self):
        self.app = App( Root )
        self.app.pack(fill=BOTH, expand=True)
        Root.update()
        Root.iconify()
        self.fillLog()
        self.app.update()
        self.hLogText = self.app.hLogText

    def tearDown(self):
        self.app.quit()

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
        self.app.logger.warning("01")
        
    def getPosAtParent(self, idx):
        parentIdx = self.hLogText.parentIdx( idx )
        pos = 0
        for childIdx in self.hLogText.getChildren( parentIdx ):
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
            if self.hLogText.parentRecord( idx ).showSubrecords == False or not self.hLogText.isShow( parent.idx):
                markTag = self.hLogText.markFromIdx( idx )
                self.assertEqual( 0, textWidget.tag_names().count( markTag ), "No marktags if not schown")
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
        self.assertEqual( int( begin.split('.')[0] ), expectedLine, "Correct lineindex expected" )
        self.assertEqual( int( begin.split('.')[1] ), 0, "Correct colindex expected" )

        # test mark
        mark = self.hLogText.markFromIdx(idx)
        self.assertEqual( mark, ( "Record%s" % idx ), "Correct mark expected" )

        # test text / hierarchy
        hierarchy = self.hLogText.record( idx ).hierarchyStage
        posAtParent = self.getPosAtParent( idx )
        text = textWidget.get(begin, end)
        self.assertEqual( text, ( "%s%s" % (hierarchy,posAtParent) ), "Text/Pos at Parent, Hierarchy expected" )
        self.assertEqual( text, record.msg )
        endCol = int(end.split('.')[1])
        expectedEndCol = len(text)
        if self.hLogText.cntChildren( idx ) > 0:
            expectedEndCol += 1 # because of shon icon
        self.assertEqual( expectedEndCol, endCol, "col of lass message letter should match enpos" )
            
        dump = textWidget.dump( image=True, tag=True, index1=begin, index2=(end + " +1c"))
        tagon = []
        tagoff = []
        for entry in dump:
            type,name,index = entry[0],entry[1],entry[2]
            line = int(index.split('.')[0])
            col = int(index.split('.')[1])
            if type == "image":
                self.assertEqual( col, 0)
            elif type == "tagon":
               self.assertEqual( col, 0)
               tagon.append(name)
            elif type == "tagoff":
                expectedTagEndCol = expectedEndCol
                if name == self.hLogText.AlterShowSubrecordsTag:
                    expectedTagEndCol = 1
                self.assertEqual( col, expectedTagEndCol, "Endcolcheck")
                tagoff.append(name)

        if self.hLogText.cntChildren( idx ) == 0:
            self.assertEqual( 3, len(tagon), "Record without children should have 3 tags" ) # Type-Tag, Idx-Tag, Stage-Tag
        else:
            self.assertEqual( 4, len(tagon), "Record with children should have 4 tags" ) # additional "ALTER_SHOW_RECORDS"-Tag

        for tag in tagon:
            self.assertTrue( ( tag in tagoff ), "Tag %s not in tagoff %s" %(tag,tagoff) )
    
        for tag in tagoff:
            self.assertTrue( ( tag in tagon ), "Tag %s not in tagon %s" %(tag,tagon) )


    def checkAllEntries(self):
        idx = 0
        while idx <= self.hLogText.maxIdx():
            self.checkEntry(idx)
            idx += 1


    # Test 
    # @unittest.skip("skipped temporarily")
    def test_initialFilled(self):
        self.checkAllEntries()

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_alterActiveRecord( self ):
        # emulate mouse event
        self.hLogText.alterActiveRecord( 1 )
        self.checkAllEntries()
        self.assertEqual( self.hLogText.activeIdx, 1 )
        self.hLogText.alterActiveRecord( 1 )
        self.checkAllEntries()
        self.assertEqual( self.hLogText.activeIdx, self.hLogText.maxCntRecords )

    def test_alterShowSubrecordsDepth1( self ):
        index = self.hLogText.indexFromIdx( 1 )
        Root.deiconify()
        Root.update()
        bbox = self.hLogText.logText.bbox( index )
        Root.iconify()
        event = Event()
        Root.update()
        event.x = bbox[0]
        event.y = bbox[1]
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

    def test_alterShowSubrecordsDetph2( self ):
        index = self.hLogText.indexFromIdx( 0 )
        Root.deiconify()
        Root.update()
        bbox = self.hLogText.logText.bbox( index )
        Root.iconify()
        event = Event()
        Root.update()
        event.x = bbox[0]
        event.y = bbox[1]

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


# create programm window and start mainloop
Root = Tk()
Root.resizable(True,True)
Root.wm_attributes("-topmost", 1)

def main():
    global App
    App = App( Root )
    App.pack(fill=BOTH, expand=True)
    Root.update()
    App.after( 10, App.start() )
    App.mainloop()

if __name__ == '__main__':
    # unittest.main(failfast=True)
    main()

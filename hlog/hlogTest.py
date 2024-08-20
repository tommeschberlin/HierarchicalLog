import logging.handlers
import os
import unittest
import logging
import re

from hlog import *

class TestHierarchicalLog(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.workDir = os.path.join( 'c:/', 'tmp' )
        if not os.path.exists( self.workDir ):
            raise Exception( 'Error', 'No workDir \"%s\" found!' % self.workDir )
    
    def setUp(self):
        self.logFile = os.path.join( self.workDir, 'test.log' )
        if os.path.isfile(self.logFile):
            os.remove(self.logFile)
        #self.logToConsole = LogToConsole( globalLog )
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        self.fileHandler = logging.FileHandler(self.logFile)
        # fileHandler.setFormatter(logFormatter)
        self.logger.addHandler(self.fileHandler)

        self.recordingHandler = RecordingHandler()
        self.logger.addHandler(self.recordingHandler)

    def tearDown(self):
        self.logger.removeHandler(self.fileHandler)
        self.fileHandler = None
        self.logger.removeHandler(self.recordingHandler)
        self.recordingHandler = None

    def logFileContent(self):
        with open(self.logFile) as f:
            return f.readlines()

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_basic(self):
        self.logger.info('Started')
        self.logger.info('Finished')
        self.fileHandler.close()
        content = '\n'.join( self.logFileContent() )
        self.assertTrue( re.search("Started", content ), "Check Started" )
        self.assertTrue( re.search("Finished", content ), "Check Finished" )

    # Test RecordingHandler
    # @unittest.skip("skipped temporarily")
    def test_RecordingHandler(self):
        initLogHierarchy(self.logger)
        recordingHandler = RecordingHandler(10)
        self.logger.addHandler(recordingHandler)

        for i in range(10):
            self.logger.info(str(i))

        self.assertEqual( recordingHandler.at( 0 ).message, "0", "Check Handler record 0" )
        self.assertEqual( recordingHandler.at( 9 ).message, "9", "Check Handler record 9" )
        self.logger.info(str(10))
        self.assertEqual( recordingHandler.at( 0 ), None, "Check Handler record 0 is None" )
        self.assertEqual( recordingHandler.at( 1 ).message, "1", "Check Handler record 1" )
        self.assertEqual( recordingHandler.at( 10 ).message, "10", "Check Handler record 10" )

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_EnterLowerLogHierarchyStage(self):
        initLogHierarchy(self.logger)

        self.logger.info('Started')

        def function():
            self.logger.info('Function ist doing something')
        
        with EnterLowerLogHierarchyStage("Function hier", self.logger):
            function()

        self.logger.info('Finished')

        self.assertEqual( self.recordingHandler.at(0).hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(1).hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(2).hierarchyStage, 1 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(3).hierarchyStage, 0 , "Check Hierarchy stage" )

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_LowerLogHierarchyStage(self):
        initLogHierarchy(self.logger)

        self.logger.info('Started')

        def function():
            lowerHierarchyStage = LowerLogHierarchyStage( self.logger )
            self.logger.info('Function ist doing something')
        
        function()

        self.logger.info('Finished')

        self.assertEqual( self.recordingHandler.at(0).hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(1).hierarchyStage, 1 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(2).hierarchyStage, 0 , "Check Hierarchy stage" )
    
    def fillLog(self):
        with EnterLowerLogHierarchyStage( "00", self.logger ) :
            with EnterLowerLogHierarchyStage( "10", self.logger ) :
                self.logger.debug("20")
            self.logger.warning("11")
        self.logger.warning("01")

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_maxIdx(self):
        self.fillLog()
        self.assertEqual( self.recordingHandler.maxIdx(), 4 )

    def test_minIdx(self):
        self.fillLog()
        self.assertEqual( self.recordingHandler.minIdx(), 0 )
    
    def test_at(self):
        self.fillLog()
        self.assertEqual( self.recordingHandler.at( 5 ), None)
        self.assertEqual( self.recordingHandler.at( 3 ).message, "11"  )
    
    def test_record( self):
        self.fillLog()
        self.assertEqual( self.recordingHandler.record( 4 ).message, "01"  )

    def test_getChildren( self ):
        self.fillLog()
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 0 ) ), 2  )
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 1 ) ), 1  )
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 2 ) ), 0  )
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 3 ) ), 0  )
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 4 ) ), 0  )

    def test_cntChildren( self):
        self.fillLog()
        self.assertEqual( self.recordingHandler.cntFilteredChildren( 0 ), 2  )
        self.assertEqual( self.recordingHandler.cntFilteredChildren( 1 ), 1  )
        self.assertEqual( self.recordingHandler.cntFilteredChildren( 2 ), 0  )
        self.assertEqual( self.recordingHandler.cntFilteredChildren( 3 ), 0  )
        self.assertEqual( self.recordingHandler.cntFilteredChildren( 4 ), 0  )

    def test_parentIdx( self ):
        self.fillLog()
        self.assertEqual( self.recordingHandler.parentIdx( 0 ), None  )
        self.assertEqual( self.recordingHandler.parentIdx( 1 ), 0 )
        self.assertEqual( self.recordingHandler.parentIdx( 2 ), 1 )
        self.assertEqual( self.recordingHandler.parentIdx( 3 ), 0 )
        self.assertEqual( self.recordingHandler.parentIdx( 4 ), None )


    def test_parentRecord( self ):
        self.fillLog()
        self.assertEqual( self.recordingHandler.parentRecord( 0 ), None  )
        self.assertEqual( self.recordingHandler.parentRecord( 1 ).message, "00" )
        self.assertEqual( self.recordingHandler.parentRecord( 2 ).message, "10" )
        self.assertEqual( self.recordingHandler.parentRecord( 3 ).message, "00" )
        self.assertEqual( self.recordingHandler.parentRecord( 4 ), None )
    
if __name__ == '__main__':
    unittest.main()

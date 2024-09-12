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
        initLogHierarchy( self.logger )
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
        resetLogHierarchy(self.logger)

    def logFileContent(self, logFile):
        with open(logFile) as f:
            return f.readlines()

    def fillLog(self):
        with EnterLowerLogHierarchyStage( "00", self.logger ) :
            with EnterLowerLogHierarchyStage( "10", self.logger ) :
                self.logger.debug("20")
            self.logger.warning("11")
        self.logger.warning("01")

    # Test 
    # @unittest.skip("skipped temporarily")
    def test_basic(self):
        self.logger.info('Started')
        self.logger.info('Finished')
        self.fileHandler.close()
        content = '\n'.join( self.logFileContent( self.logFile ) )
        self.assertTrue( re.search("Started", content ), "Check Started" )
        self.assertTrue( re.search("Finished", content ), "Check Finished" )

    # Test RecordingHandler
    # @unittest.skip("skipped temporarily")
    def test_RecordingHandler(self):
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

    # Test HierarchyFormatter
    # @unittest.skip("skipped temporarily")
    def test_HierarchyFormatter(self):
        hierarchyLogFile = os.path.join( self.workDir, 'testHierarchyFormatter.log' )
        if os.path.isfile(hierarchyLogFile):
            os.remove(hierarchyLogFile)
        logger = logging.getLogger('testHierarchyLogFile')
        logger.setLevel(logging.DEBUG)
        initLogHierarchy( logger )
        fileHandler = logging.FileHandler(hierarchyLogFile, 'w', 'utf-8' )
        logFormatter = HLogFormatter('%(asctime)s - %(levelname)8s - %(message)s', '%y-%m-%d %H:%M:%S')
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)

        with EnterLowerLogHierarchyStage("00", logger):
            for i in range(1,5):
                logger.warning(f"0{i}")

        logger.info(f"10\n   Next Line")

        fileHandler.close()
        content = self.logFileContent(hierarchyLogFile)

        dateTimeMatch = "[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"
        branchMatch = lambda hLevel : "%s%s%s" % (" "*hLevel, "\\|\\-", " "*(HLogFormatter.maxHierarchy-hLevel))
        
        match = "^%s %s -     INFO - 00\n$" % (branchMatch(0), dateTimeMatch)
        res = re.fullmatch(match, content[0])
        self.assertIsNotNone(res)

        for i in range(1,5):
            match = "^%s %s -  WARNING - 0%s\n$" % (branchMatch(1), dateTimeMatch, i)
            res = re.fullmatch(match, content[i])
            self.assertIsNotNone(res)


        logFileReader : HLogFileReader = HLogFileReader( logger, logFormatter._fmt )
        logFileReader.read( hierarchyLogFile )




    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_EnterLowerLogHierarchyStage(self):
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
        self.logger.info('Started')

        def function():
            lowerHierarchyStage = LowerLogHierarchyStage( self.logger )
            self.logger.info('Function ist doing something')
        
        function()

        self.logger.info('Finished')

        self.assertEqual( self.recordingHandler.at(0).hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(1).hierarchyStage, 1 , "Check Hierarchy stage" )
        self.assertEqual( self.recordingHandler.at(2).hierarchyStage, 0 , "Check Hierarchy stage" )
    
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

    def test_getFilteredChildren( self ):
        self.fillLog()
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( None ) ), 2  )
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 1 ) ), 1  )

        self.recordingHandler.levelNamesFilter["WARNING"] = False
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( None ) ), 1  )

        self.recordingHandler.levelNamesFilter["DEBUG"] = False
        self.assertEqual( len( self.recordingHandler.getFilteredChildren( 1 ) ), 0  )

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

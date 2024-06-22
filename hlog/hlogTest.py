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
    
    
if __name__ == '__main__':
    unittest.main()
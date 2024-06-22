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

    def tearDown(self):
        self.logger.removeHandler(self.fileHandler)
        self.fileHandler = None

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

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_EnterLowerLogHierarchyStage(self):
        initLogHierarchy(self.logger)
        records = []

        class recordingHandler( logging.Handler ):
            def __init__(self )-> None:
                logging.Handler.__init__(self=self)
            
            def emit(self, record)->None:
                records.append( record )

        self.logger.addHandler(recordingHandler())

        self.logger.info('Started')

        def function():
            self.logger.info('Function ist doing something')
        
        with EnterLowerLogHierarchyStage("Function hier", self.logger):
            function()

        self.logger.info('Finished')

        self.assertEqual( records[0].hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( records[1].hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( records[2].hierarchyStage, 1 , "Check Hierarchy stage" )
        self.assertEqual( records[3].hierarchyStage, 0 , "Check Hierarchy stage" )

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_LowerLogHierarchyStage(self):
        initLogHierarchy(self.logger)
        records = []

        class recordingHandler( logging.Handler ):
            def __init__(self )-> None:
                logging.Handler.__init__(self=self)
            
            def emit(self, record)->None:
                records.append( record )

        self.logger.addHandler(recordingHandler())

        self.logger.info('Started')

        def function():
            lowerHierachyStage = LowerLogHierarchyStage( self.logger )
            self.logger.info('Function ist doing something')
        
        function()

        self.logger.info('Finished')

        self.assertEqual( records[0].hierarchyStage, 0 , "Check Hierarchy stage" )
        self.assertEqual( records[1].hierarchyStage, 1 , "Check Hierarchy stage" )
        self.assertEqual( records[2].hierarchyStage, 0 , "Check Hierarchy stage" )
    


#def function1():
#    stage = increaseHierarchyStage( "Function 1" )
#log( LogLevel.INFO, "Bla")


if __name__ == '__main__':
    unittest.main()
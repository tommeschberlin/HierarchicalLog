import os, sys, pytest, logging, re, tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hlog import *

class TestHierarchicalLog:
    def setup_method(self):
        self.workDir = tempfile.gettempdir()
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

    def teardown_method(self):
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
        assert re.search("Started", content ), "Check Started"
        assert re.search("Finished", content ), "Check Finished"

    # Test RecordingHandler
    # @unittest.skip("skipped temporarily")
    def test_RecordingHandler(self):
        recordingHandler = RecordingHandler(10)
        self.logger.addHandler(recordingHandler)

        for i in range(10):
            self.logger.info(str(i))

        assert recordingHandler.at( 0 ).message == "0", "Check Handler record 0"
        assert recordingHandler.at( 9 ).message == "9", "Check Handler record 9"
        self.logger.info(str(10))
        assert recordingHandler.at( 0 ) == None, "Check Handler record 0 is None"
        assert recordingHandler.at( 1 ).message == "1", "Check Handler record 1"
        assert recordingHandler.at( 10 ).message == "10", "Check Handler record 10"

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_EnterLowerLogHierarchyStage(self):
        self.logger.info('Started')

        def function():
            self.logger.info('Function ist doing something')
        
        with EnterLowerLogHierarchyStage("Function hier", self.logger):
            function()

        self.logger.info('Finished')

        assert self.recordingHandler.at(0).hierarchyStage == 0 , "Check Hierarchy stage"
        assert self.recordingHandler.at(1).hierarchyStage == 0 , "Check Hierarchy stage"
        assert self.recordingHandler.at(2).hierarchyStage == 1 , "Check Hierarchy stage"
        assert self.recordingHandler.at(3).hierarchyStage == 0 , "Check Hierarchy stage"

    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_LowerLogHierarchyStage(self):
        self.logger.info('Started')

        def function():
            lowerHierarchyStage = LowerLogHierarchyStage( self.logger )
            self.logger.info('Function ist doing something')
        
        function()

        self.logger.info('Finished')

        assert self.recordingHandler.at(0).hierarchyStage == 0 , "Check Hierarchy stage"
        assert self.recordingHandler.at(1).hierarchyStage == 1 , "Check Hierarchy stage"
        assert self.recordingHandler.at(2).hierarchyStage == 0 , "Check Hierarchy stage"
    
    # Test if, hierarchy stage can be set in python logging system
    # @unittest.skip("skipped temporarily")
    def test_maxIdx(self):
        self.fillLog()
        assert self.recordingHandler.maxIdx() == 4

    def test_minIdx(self):
        self.fillLog()
        assert self.recordingHandler.minIdx() == 0
    
    def test_at(self):
        self.fillLog()
        assert self.recordingHandler.at( 5 ) == None
        assert self.recordingHandler.at( 3 ).message == "11"
    
    def test_record( self):
        self.fillLog()
        assert self.recordingHandler.record( 4 ).message == "01"

    def test_getChildren( self ):
        self.fillLog()
        assert len( self.recordingHandler.getFilteredChildren( 0 ) ) == 2
        assert len( self.recordingHandler.getFilteredChildren( 1 ) ) == 1
        assert len( self.recordingHandler.getFilteredChildren( 2 ) ) == 0
        assert len( self.recordingHandler.getFilteredChildren( 3 ) ) == 0
        assert len( self.recordingHandler.getFilteredChildren( 4 ) ) == 0

    def test_getFilteredChildren( self ):
        self.fillLog()
        assert len( self.recordingHandler.getFilteredChildren( None ) ) == 2
        assert len( self.recordingHandler.getFilteredChildren( 1 ) ) == 1

        self.recordingHandler.levelNamesFilter["WARNING"] = False
        assert len( self.recordingHandler.getFilteredChildren( None ) ) == 1

        self.recordingHandler.levelNamesFilter["DEBUG"] = False
        assert len( self.recordingHandler.getFilteredChildren( 1 ) ) == 0

    def test_cntChildren( self):
        self.fillLog()
        assert self.recordingHandler.cntFilteredChildren( 0 ) == 2
        assert self.recordingHandler.cntFilteredChildren( 1 ) == 1
        assert self.recordingHandler.cntFilteredChildren( 2 ) == 0
        assert self.recordingHandler.cntFilteredChildren( 3 ) == 0
        assert self.recordingHandler.cntFilteredChildren( 4 ) == 0

    def test_parentIdx( self ):
        self.fillLog()
        assert self.recordingHandler.parentIdx( 0 ) == None
        assert self.recordingHandler.parentIdx( 1 ) == 0
        assert self.recordingHandler.parentIdx( 2 ) == 1
        assert self.recordingHandler.parentIdx( 3 ) == 0
        assert self.recordingHandler.parentIdx( 4 ) == None

    def test_parentRecord( self ):
        self.fillLog()
        assert self.recordingHandler.parentRecord( 0 ) == None
        assert self.recordingHandler.parentRecord( 1 ).message == "00"
        assert self.recordingHandler.parentRecord( 2 ).message == "10"
        assert self.recordingHandler.parentRecord( 3 ).message == "00"
        assert self.recordingHandler.parentRecord( 4 ) == None

    # Test HierarchyFormatter
    # @unittest.skip("skipped temporarily")
    def test_HLogIO(self):
        hierarchyLogFile = os.path.join( self.workDir, 'testHierarchyIO.log' )
        if os.path.isfile(hierarchyLogFile):
            os.remove(hierarchyLogFile)
        logger = logging.getLogger('testHierarchyIO')
        logger.setLevel(logging.DEBUG)
        initLogHierarchy( logger )
        fileHandler = logging.FileHandler(hierarchyLogFile, 'w', 'utf-8' )
        logFormatter = HLogFormatter('%(asctime)s - %(levelname)8s - %(message)s', '%y-%m-%d %H:%M:%S')
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
        recordingHandler = RecordingHandler()
        logger.addHandler(recordingHandler)

        with EnterLowerLogHierarchyStage("00", logger):
            for i in range(1,5):
                logger.warning(f"0{i}")

        logger.info(f"10\n   Next Line")

        fileHandler.close()

        # read already written logfile and check the textline
        content = self.logFileContent(hierarchyLogFile)

        dateTimeMatch = "[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"
        branchMatch = lambda hLevel : "%s%s%s" % (" "*hLevel, "\\|\\-", " "*(HLogFormatter.maxHierarchy-hLevel))
        
        match = "^%s %s -     INFO - 00\n$" % (branchMatch(0), dateTimeMatch)
        res = re.fullmatch(match, content[0])
        assert res != None

        for i in range(1,5):
            match = "^%s %s -  WARNING - 0%s\n$" % (branchMatch(1), dateTimeMatch, i)
            res = re.fullmatch(match, content[i])
            assert res != None

        # parse the already written logile and create a new log 
        fileInputLogger = logging.getLogger('testHierarchyIO-FromFile')
        initLogHierarchy( fileInputLogger )

        fileInputRecordingHandler = RecordingHandler()
        fileInputLogger.addHandler(fileInputRecordingHandler)
        logFileReader : HLogFileReader = HLogFileReader( fileInputLogger, logFormatter._fmt )
        logFileReader.read( hierarchyLogFile )

        assert len(recordingHandler.records) == len(fileInputRecordingHandler.records), "Created and read mustbe the same!"

        for i in range(0, len(recordingHandler.records)):
            origRecord : HLogRecord = recordingHandler.records[i]
            readRecord : HLogRecord = fileInputRecordingHandler.records[i]
            assert int(origRecord.created) == readRecord.created, "Has to be equal"
            assert origRecord.levelno == readRecord.levelno
            assert origRecord.hierarchyStage == readRecord.hierarchyStage
            assert origRecord.msg == readRecord.msg

if __name__ == '__main__':
    import pytest, sys
    pytest.main([sys.argv[0], "-v"])

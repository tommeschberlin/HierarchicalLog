from enum import Enum
from collections import deque
import logging

formerLogFactory = None

# initialises the log hierarchy for python logger
#  add member hierarchyStage and init its value to 0
#  lower hierachy stages have higher numbers
#  after initLogHierarchy log entries will be created with member hierachyStage set from the current hierachy level
#  of the logger
def initLogHierarchy(logger: logging.Logger = logging.getLogger()):
    global formerLogFactory
    
    assert formerLogFactory == None

    logger.hierarchyStage = 0

    if not formerLogFactory:
        formerLogFactory = logging.getLogRecordFactory()

        def logFactory(*args, **kwargs):
            logger = logging.getLogger( args[0] )
            record = formerLogFactory(*args, **kwargs)
            record.hierarchyStage = __getHierarchyStage(logger)
            return record

        logging.setLogRecordFactory(logFactory)

def resetLogHierarchy():
    global formerLogFactory
    if formerLogFactory:
        logging.setLogRecordFactory(formerLogFactory)
    formerLogFactory = None

def __getHierarchyStage(logger):
    try:
        return logger.hierarchyStage
    except:
        logger.hierarchyStage = -1
        return -1
    
# lowers the level of hierarchy
def lowerHierarchyStage(logger: logging.Logger = logging.getLogger()):
    logger.hierarchyStage += 1

# raises level of hierarchy
def raiseHierarchyStage(logger = logging.getLogger()):
    assert logger.hierarchyStage > 0, "Hierarchy stage must be greater 0 for this!"
    logger.hierarchyStage -= 1

# lowers the log hierarchy stage and automatically raieses on leaving the "with" context
# usage:
# with EnterLowerLogHierarchyStage( "Message text with previous log hierarchy stage here", logger ) :
#     logger.info("something with already lowered log hierarchy stage here")
#
# logger.info("something with again raised hierarchy stage here")
class EnterLowerLogHierarchyStage():
    def __init__(self, msg: str, logger: logging.Logger = logging.getLogger() ):
        assert isinstance( msg, str ),  "Arg msg has to be of type str!"
        self.logger = logger
        self.logger.info( msg )

    def __enter__(self):
        lowerHierarchyStage(self.logger)

    def __exit__(self ,type, value, traceback):
        raiseHierarchyStage( self.logger )

# 
class HLogRecord( logging.LogRecord ):
    """
    A specialized Record class for Hierarchical Log, to hold additional properties about the hierarchy
    and to be useful for filling model-view based UI
    It also supports the intellisense features of vscode python module
    """

    def __init__(self):
        self.hierarchyStage = -1
        self.idx = -1
        self.showSubrecords = False

# lowers the log hierarchy stage and automatically raises on leaving the function context
# usage:
# def function():
#   lowerHierachyStage = LowerLogHierarchyStage( "Message text with previous log hierarchy stage here", logger ) :
#   logger.info("something with already lowered log hierarchy stage here")
#
# logger.info("something with again raised hierarchy stage here")
class LowerLogHierarchyStage():
    def __init__(self, logger: logging.Logger = logging.getLogger() ):
        self.logger = logger
        lowerHierarchyStage(self.logger)

    def __del__(self ):
        raiseHierarchyStage( self.logger )

# log handler to collect and store log records up to a certain amount
#   records are accessible by their unique index
class RecordingHandler( logging.Handler ):
    def __init__(self, maxCntRecords: int =  100000 )->None:
        logging.Handler.__init__(self=self)
        self.maxCntRecords = maxCntRecords
        self.records = deque( maxlen=self.maxCntRecords )  # type: deque[HLogRecord]
        self.entireAdded = 0

    def emit(self, record : HLogRecord )->None:
        self.entireAdded += 1
        self.records.append( record )

    def maxIdx(self):
        return self.entireAdded - 1

    def minIdx(self):
        return max( 0, self.entireAdded - self.maxCntRecords )
    
    def at(self, idx)->HLogRecord:
        if idx == None:
            return None
        relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
        if relIdx < len( self.records ) and relIdx >= 0:
            return self.records[ relIdx ]
        return None
    
    def record( self, idx )->HLogRecord:
        relIdx = idx - self.minIdx()
        assert relIdx >= 0 and relIdx < self.maxCntRecords
        return self.records[ relIdx ]

    def getChildren( self, idx = None ):
        if idx != None:
            relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
            record = self.records[ relIdx ]
            parentHierarchyStage = record.hierarchyStage
            relChildIdx = relIdx + 1
        else:
            parentHierarchyStage = -1
            relChildIdx = 0
        children = []
        while relChildIdx <= (self.maxIdx() - self.minIdx()):
            child = self.records[ relChildIdx ]
            if child.hierarchyStage <= parentHierarchyStage:
                break
            if child.hierarchyStage == parentHierarchyStage + 1:
                children.append( relChildIdx + self.minIdx() )
            relChildIdx += 1
        return children

    def cntChildren( self, idx ):
        if idx != None:
            relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
            record = self.records[ relIdx ]
            parentHierarchyStage = record.hierarchyStage
            relChildIdx = relIdx + 1
        else:
            parentHierarchyStage = -1
            relChildIdx = 0
        cnt = 0
        while relChildIdx <= (self.maxIdx() - self.minIdx()):
            child = self.records[ relChildIdx ]
            if child.hierarchyStage <= parentHierarchyStage:
                break
            if child.hierarchyStage == parentHierarchyStage + 1:
                cnt += 1
            relChildIdx += 1
        return cnt

    def parentIdx( self, idx ):
        relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
        record = self.records[ relIdx ]
        if record.hierarchyStage <= 0:
            return None
        relIdx -= 1
        while relIdx >= 0:
            if self.records[ relIdx ].hierarchyStage < record.hierarchyStage:
                return self.minIdx() + relIdx
            relIdx -= 1

        return None

    def parentRecord( self, idx )->HLogRecord:
        parentIdx = self.parentIdx( idx )
        if parentIdx != None:
            return self.record( parentIdx )
        return None

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
    
    logger.hierarchyStage = 0

    if not formerLogFactory:
        formerLogFactory = logging.getLogRecordFactory()

        def logFactory(*args, **kwargs):
            logger = logging.getLogger( args[0] )
            record = formerLogFactory(*args, **kwargs)
            record.hierarchyStage = __getHierarchyStage(logger)
            return record

        logging.setLogRecordFactory(logFactory)

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
#     log("something with already lowered log hierarchy stage here")
#
# log("something with again raised hierarchy stage here")
class EnterLowerLogHierarchyStage():
    def __init__(self, msg: str, logger: logging.Logger = logging.getLogger() ):
        assert isinstance( msg, str ),  "Arg msg has to be of type str!"
        self.logger = logger
        self.logger.info( msg )

    def __enter__(self):
        lowerHierarchyStage(self.logger)

    def __exit__(self ,type, value, traceback):
        raiseHierarchyStage( self.logger )

# lowers the log hierarchy stage and automatically raises on leaving the function context
# usage:
# def function():
#   lowerHierachyStage = LowerLogHierarchyStage( "Message text with previous log hierarchy stage here", logger ) :
#   log("something with already lowered log hierarchy stage here")
#
# log("something with again raised hierarchy stage here")
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
        self.records = deque( maxlen=self.maxCntRecords )
        self.entireAdded = 0

    def emit(self, record)->None:
        self.entireAdded += 1
        self.records.append( record )

    def maxIdx(self):
        return self.entireAdded - 1

    def minIdx(self):
        return max( 0, self.entireAdded - self.maxCntRecords )
    
    def at(self, idx):
        relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
        if relIdx < len( self.records ) and relIdx >= 0:
            return self.records[ relIdx ]
        return None
    
    def record( self, idx ):
        relIdx = idx - self.minIdx()
        assert relIdx >= 0 and relIdx < self.maxCntRecords
        return self.records[ relIdx ]

    def parentIdx( self, idx ):
        record = self.record( idx )
        if record.hierarchyStage <= 0:
            return None
        relIdx = idx - self.minIdx() - 1
        while relIdx >= 0:
            if self.records[ relIdx ].hierarchyStage < record.hierarchyStage:
                return self.minIdx() + relIdx
            relIdx = relIdx - 1

        return None


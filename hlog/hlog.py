from enum import Enum
from collections import deque
import logging

formerLogFactory = None
initializedLoggers : set[str] = set()

def initLogHierarchy(logger: logging.Logger = logging.getLogger()):
    """
    initialises the log hierarchy for python logger
      add member hierarchyStage and init its value to 0
      lower hierachy stages have higher numbers
      after initLogHierarchy log entries will be created with member hierachyStage set from the current hierachy level
      of the logger
    """
    global formerLogFactory
    
    assert not logger.name in initializedLoggers

    logger.hierarchyStage = 0
    initializedLoggers.add( logger.name )

    if not formerLogFactory:
        formerLogFactory = logging.getLogRecordFactory()

        def logFactory(*args, **kwargs):
            logger = logging.getLogger( args[0] )
            record : HLogRecord = formerLogFactory(*args, **kwargs)
            record.hierarchyStage = __getHierarchyStage(logger)
            return record

        logging.setLogRecordFactory(logFactory)

def resetLogHierarchy(logger: logging.Logger = logging.getLogger()):
    """
    Removes the log hierarchy functionality from logging
    """
    global formerLogFactory
    global initializedLoggers

    assert logger.name in initializedLoggers

    initializedLoggers.remove( logger.name )

    if not len(initializedLoggers):
        logging.setLogRecordFactory(formerLogFactory)
        formerLogFactory = None

def __getHierarchyStage(logger):
    try:
        return logger.hierarchyStage
    except:
        logger.hierarchyStage = -1
        return -1
    
def lowerHierarchyStage(logger: logging.Logger = logging.getLogger()):
    """ lowers the level of hierarchy """
    logger.hierarchyStage += 1

def raiseHierarchyStage(logger = logging.getLogger()):
    """ raises level of hierarchy """
    assert logger.hierarchyStage > 0, "Hierarchy stage must be greater 0 for this!"
    logger.hierarchyStage -= 1

class EnterLowerLogHierarchyStage():
    """
    lowers the log hierarchy stage and automatically raieses on leaving the "with" context
    usage:
    with EnterLowerLogHierarchyStage( "Message text with previous log hierarchy stage here", logger ) :
        logger.info("something with already lowered log hierarchy stage here")
    
    logger.info("something with again raised hierarchy stage here")
    """
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
        self.idx = -1
        self.hierarchyStage = -1 
        """the lower the number is, the higher in hierarchy"""
        self.showSubrecords = None
        self.maxChildLevelNo = -1

class LowerLogHierarchyStage():
    """
    lowers the log hierarchy stage and automatically raises on leaving the function context
    usage:
    def function():
       lowerHierachyStage = LowerLogHierarchyStage( "Message text with previous log hierarchy stage here", logger ) :
       logger.info("something with already lowered log hierarchy stage here")
    logger.info("something with again raised hierarchy stage here")
    """
    def __init__(self, logger: logging.Logger = logging.getLogger() ):
        self.logger = logger
        lowerHierarchyStage(self.logger)

    def __del__(self ):
        raiseHierarchyStage( self.logger )

class RecordingHandler( logging.Handler ):
    """
    log handler to collect and store log records up to a certain amount
    records are accessible by their unique absolute index
    """

    def __init__(self, maxCntRecords: int =  100000 )->None:
        logging.Handler.__init__(self=self)
        self.maxCntRecords = maxCntRecords
        self.records = deque( maxlen=self.maxCntRecords )  # type: deque[HLogRecord]
        self.entireAdded = 0
        self.levelNamesFilter : dict[str,bool] = {}

        # initializes filter for levelname
        for name,id in logging.getLevelNamesMapping().items():
            self.levelNamesFilter[name] = True

    def addCustomLevel(self, levelId, levelName):
        """
        Creates a new level with id and name
        """
        logging.addLevelName(levelId, levelName)
        self.levelNamesFilter[levelName] = True

    def emit(self, record : HLogRecord )->None:
        """
        emit method, see logging.Handler

        inits/fills the new members for hlog functionality
        """

        # fill HLogRecord members
        record.idx = self.entireAdded
        
        # record.hierarchyStage = -1 
        """already set by logFactory"""

        record.showSubrecords = None
        record.maxChildLevelNo = -1

        self.entireAdded += 1
        self.records.append( record )

    def maxIdx(self):
        """Retrieves the maximal available absolute idx"""
        return self.entireAdded - 1

    def minIdx(self):
        """Retrieves the minimal available absolute idx"""
        return max( 0, self.entireAdded - self.maxCntRecords )
    
    def at(self, idx)->HLogRecord:
        """Retrieves a record by its idx, returns None if not found"""
        if idx == None:
            return None
        relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
        if relIdx < len( self.records ) and relIdx >= 0:
            return self.records[ relIdx ]
        return None
    
    def record( self, idx )->HLogRecord:
        """Retrieves a record by its idx, asserts if not found"""
        relIdx = min( idx, idx - (self.entireAdded - self.maxCntRecords) )
        assert relIdx >= 0 and relIdx < self.maxCntRecords
        return self.records[ relIdx ]
    
    def idxToRelIdx( self, idx: int )->int:
        """Calculates the relative idx from absolute idx"""
        return min( idx, idx - (self.entireAdded - self.maxCntRecords) )

    def passedFilter( self, record : HLogRecord ):
        """Filters by levelname """
        if not self.levelNamesFilter[ record.levelname ]:
            return False
        return True

    def getFilteredChildren( self, idx = None ):
        """Retrieves children for an idx, uses the passedFilter method to filter out only the wanted children"""
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
            if (child.hierarchyStage == parentHierarchyStage + 1) and self.passedFilter( child ) :
                children.append( relChildIdx + self.minIdx() )
            relChildIdx += 1
        return children

    def cntFilteredChildren( self, idx = None ):
        """Retrieves count of children for an idx, uses the passedFilter method to filter out only the wanted children"""
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
            if (child.hierarchyStage == parentHierarchyStage + 1) and self.passedFilter( child ) :
                cnt += 1
            relChildIdx += 1
        return cnt

    def parentIdx( self, idx ):
        """Retrieves the parent idx record for the idx"""
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
        """Retrieves the parent record for the idx"""
        parentIdx = self.parentIdx( idx )
        if parentIdx != None:
            return self.record( parentIdx )
        return None


class HierarchicalLogFormatter(logging.Formatter):
    """Logging file formatter for hierarchical log to files or console"""

    characterSubrecordMiddle = '├'
    characterSubrecordEnd    = '└'
    maxHierarchy = 6

    def __init__(self, fmt):
        super().__init__(fmt)

    def format(self, record : HLogRecord):
        cntSpacesBefore = record.hierarchyStage
        cntSpacesAfter = max(0, HierarchicalLogFormatter.maxHierarchy - cntSpacesBefore - 1)

        spaceBefore = " "*cntSpacesBefore
        spaceAfter = " "*cntSpacesAfter
        preText = spaceBefore + HierarchicalLogFormatter.characterSubrecordMiddle + spaceAfter

        return preText + super().format(record)

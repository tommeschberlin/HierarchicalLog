from enum import Enum
from collections import deque
import logging
import re
from datetime import datetime
import copy
import time

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
    
    def clear(self):
        self.entireAdded = 0
        self.records.clear()

class HLogIO():
    branchMarker = '|-'
    maxHierarchy = 6

class HLogFormatter(HLogIO, logging.Formatter):
    """Logging file formatter for hierarchical log to files or console"""

    def format(self, record : HLogRecord):
        cntSpacesBefore = record.hierarchyStage
        cntSpacesAfter = max(0, HLogIO.maxHierarchy - cntSpacesBefore)
        spaceBefore = " "*cntSpacesBefore
        spaceAfter = " "*cntSpacesAfter
        preText = spaceBefore + HLogIO.branchMarker + spaceAfter + " "

        return preText + super().format(record)

class HLogFileReader(HLogIO):
    """Reads a logfile which was written by Hierarchical Log Formatter"""

    class parser:
        def __init__( self ):
            self.tail = ''

        def parseFormat( self, fmt : str ) -> tuple[int,int]:
            return None

        def parse(self, c, iter ):
            pass

        def readTail( self, c : str, iter ):
            if len(self.tail):
                for i in range(0,len(self.tail)):
                    if c != self.tail[i]:
                        return False, c, iter
                    c = next(iter)
            return True, c, iter
        
        def value(self):
            pass


    class hierarchyParser(parser):
        formatRe = '(%\\(hierarchy\\))([0-9]{0,2})(s{0,1})([^%]*)'

        def parseFormat( self, fmt : str ):
            matches = re.search( self.formatRe, fmt )
            if not len(matches.regs):
                return None
            self.tail = fmt[matches.regs[4][0] : matches.regs[4][1]]
            self.len = int(fmt[matches.regs[2][0] : matches.regs[2][1]])
            return (matches.regs[0][0],matches.regs[0][1])

        def parse( self, c : str, iter ) -> int:
            self.hierarchyLevel = 0
            while c==' ':
                self.hierarchyLevel += 1
                c = next(iter)
            if c != HLogIO.branchMarker[0]:
                return False, c, iter
            c = next(iter)
            if c != HLogIO.branchMarker[1]:
                return False, c, iter
            
            for i in range(0, self.len - ( self.hierarchyLevel + len(HLogIO.branchMarker))):
                c = next(iter)
                if c != ' ':
                    return False, c, iter

            return self.readTail( next(iter), iter )

        def value(self):
            return self.hierarchyLevel

    class asctimeParser(parser):
        formatRe = '(%\\(asctime\\))([0-9]{0,2})(s{0,1})([^%]*)'
        dateFormat = '%y-%m-%d'

        def __init__(self):
            self.setDateFormat( self.dateFormat )

        def parseFormat( self, fmt : str ):
            matches = re.search( self.formatRe, fmt )
            if not len(matches.regs):
                return None
            self.tail = fmt[matches.regs[4][0] : matches.regs[4][1]]
            return (matches.regs[0][0],matches.regs[0][1])
        
        def setDateFormat( self, fmt : str ):
            now = datetime.now()
            self.dateFormat = fmt
            self.ascTimeExample = now.strftime( fmt )

        def parse( self, c : str, iter ) -> int:
            while c == ' ':
                c = next(iter)

            ascTime = c
            for i in range(1, len(self.ascTimeExample)):
                ascTime += next(iter)

            self.dateTime = time.strptime( ascTime, self.dateFormat )
            self.time = time.mktime(self.dateTime)
            if self.dateTime is None:
               return False, c, iter
            
            return self.readTail( next(iter), iter )

        def value(self):
            return self.time


    class levelnameParser(parser):
        formatRe = '(%\\(levelname\\))([0-9]{0,2})(s{0,1})([^%]*)'

        def parseFormat( self, fmt : str ):
            matches = re.search( self.formatRe, fmt )
            if not len(matches.regs):
                return None
            self.tail = fmt[matches.regs[4][0] : matches.regs[4][1]]
            self.len = int(fmt[matches.regs[2][0] : matches.regs[2][1]])
            return (matches.regs[0][0],matches.regs[0][1])

        def parse( self, c : str, iter ) -> int:
            while c == ' ':
                c = next(iter)

            self.levelName = ''
            while c != ' ':
                self.levelName += c
                c = next(iter)

            return self.readTail( c, iter )

        def value(self):
            return self.levelName

    class messageParser(parser):
        formatRe = '(%\\(message\\))([0-9]{0,2})(s{0,1})([^%]*)'

        def parseFormat( self, fmt : str ):
            matches = re.search( self.formatRe, fmt )
            if not len(matches.regs):
                return None
            self.tail = fmt[matches.regs[4][0] : matches.regs[4][1]]
            return (matches.regs[0][0],matches.regs[0][1])

        def parse( self, c : str, iter ) -> int:
            self.message = ''
            while c != '\n':
                self.message += c
                c = next(iter)

            return self.readTail( c, iter )

        def value(self):
            return self.message
        
    parserClasses : list[parser] = [ asctimeParser, levelnameParser, messageParser, hierarchyParser ]

    def __init__(self, logger : logging.Logger, fmt : str, datefmt : str ='%y-%m-%d %H:%M:%S', style : str = '%' ):
        assert style == '%'

        hierarchyLen = HLogIO.maxHierarchy + len(HLogIO.branchMarker)
        fmt = f"%(hierarchy){hierarchyLen}s " + fmt

        self.logger = logger
        assert logger.name in initializedLoggers, f"Logger {logger.name} must be initialized for hierarchy logging, with hlog.initLogHierarchy!"

        self.lineParsers : list[HLogFileReader.parser] = list()
        lineParsers = {}
        for parserClass in HLogFileReader.parserClasses:
            parser : HLogFileReader.parser = parserClass()
            found = parser.parseFormat( fmt )
            if found is not None:
                lineParsers[ found[0] ] = parser
                if type(parser).__name__ == HLogFileReader.asctimeParser.__name__:
                    parser.setDateFormat( datefmt )

        # sort by found pos
        lineParsers = dict( sorted(lineParsers.items()) )
        self.lineParsers = lineParsers.values()

        self.lastReadEnd = 0

    def parseLine(self, line : str) -> dict[str,any]:
        recordEntry : dict[str,any] = dict()
        lineIter = iter(line)
        c = next(lineIter)
        for parser in self.lineParsers:
            startIter =  copy.deepcopy( lineIter )
            startC = c
            try:
                success, c, lineIter = parser.parse( c, lineIter )
            except:
                success = False

            if success:
                recordEntry[type(parser).__name__] = parser.value()
            else:
                lineIter = copy.deepcopy( startIter )
                c = startC

        return recordEntry

    def makeRecord( self, recordEntry ):
        time = recordEntry[HLogFileReader.asctimeParser.__name__]
        hierarchyStage = recordEntry[HLogFileReader.hierarchyParser.__name__]
        levelName = recordEntry[HLogFileReader.levelnameParser.__name__]
        msg = recordEntry[HLogFileReader.messageParser.__name__]
        level = logging._nameToLevel[levelName]
        self.logger.hierarchyStage = hierarchyStage
        args = ''
        fn, lno, func = self.filePath, 0, "(unknown function)"
        record = self.logger.makeRecord(self.logger.name, level, fn, lno, msg, args,
                                        None, func, None, None)
        # replace time
        record.created = time
        record.msecs = int((time - int(time)) * 1000) + 0.0  # from LogRecord.__init__

        # handle standard
        self.logger.handle( record )


    def read(self, filePath : str, seekPos : int = 0 ) -> int:
        self.filePath = filePath
        with open( filePath ) as f:
            f.seek( seekPos )
            # because of possible pure message lines, we can only complete a record, if a valid next one was received
            lastRecordEntry : dict[str,any] = None 
            while True:
                line = f.readline()
                if line is None or len(line) <= 0:
                    break
                recordEntry = self.parseLine( line )
                keys = recordEntry.keys()
                if HLogFileReader.hierarchyParser.__name__ in keys:
                    if lastRecordEntry is not None:
                        self.makeRecord( lastRecordEntry )
                        self.lastReadEnd = f.tell()
                    lastRecordEntry = recordEntry
                elif HLogFileReader.messageParser.__name__ in keys:
                    lastRecordEntry[HLogFileReader.messageParser.__name__] += '\n' + recordEntry[HLogFileReader.messageParser.__name__]
                else:
                    raise ImportError

            if lastRecordEntry is not None:
                self.makeRecord( lastRecordEntry )
                self.lastReadEnd = f.tell()

        return self.lastReadEnd

   
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













class ConsoleFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# log levels
class LogLevel(Enum):
    TRACE = 0
    DEBUG = 1
    INFO  = 2
    WARN  = 3
    ERROR = 4
    FATAL = 5

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other):
        return isinstance(other, LogLevel) and self.value == other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __le__(self, other):
        return self.value <= other.value

    def __lt__(self, other):
        return self.value < other.value

class Entry():
    def __init__(self, level: LogLevel, msg: str ) -> None:
        self.level = level
        self.msg = msg

    def setHierarchyStage(self,stage):
        self.hierarchyStage = stage

globalLog = None

# class for a hierarchical log
# hStage - hierachy - 0 means lowest
class Log():
    maxCntEntries = 200000

    def __init__(self ):
        self.hierarchyStage = 0
        self.entries = deque( maxlen=self.maxCntEntries )
        self.cntAdded = 0
        self.sinkEntries = []
   
    def __del__(self):
        assert(self.hierarchyStage == 0)

    def addEntry( self, entry ):
        entry.hierarchyStage = self.hierarchyStage
        self.cntAdded += 1
        self.entries.append( entry )
        for sink in self.sinkEntries:
            sink.entryArrived( entry )

    def addSink( self, sink ):
        self.sinkEntries.append(sink)

    def removeSink( self, sink ):
        self.sinkEntries.remove( sink )

    # increases level of hierarchy
    def incrStage(self):
        self.hierarchyStage += 1

    # decreases level of hierarchy
    def decrStage(self):
        assert(self.hierarchyStage > 0)
        self.hierarchyStage -= 1

    def maxIdx(self):
        return self.cntAdded - 1

    def minIdx(self):
        return max( 0, self.cntAdded - self.maxCntEntries )
    
    def at(self, idx):
        qIdx = min( idx, idx - (self.cntAdded - self.maxCntEntries) )
        if qIdx < len( self.entries ) & qIdx >= 0:
            return self.entries[ qIdx ]

# at least one log is needed
globalLog = Log()

# class for log receivers, can be derived for own log recievers
class LogSink():
    def __init__( self, log : Log, level: LogLevel ):
        self.level = level
        self.log = log
        self.log.addSink( self )

    def __del__( self ):
        self.log.removeSink( self )

    def setLevel( self, level ):
        assert( level >= LogLevel.TRACE & level <= LogLevel.Fatal )
        self.level = level
    
    def formatEntry( self, entry ):
        None

    def propagateEntry( self, entry ):
        None

    def entryArrived(self, entry):
        if entry.level >= self.level:
            self.propagateEntry( entry )

class LogToFile(LogSink):
    def __init__( self, log : Log, fileName: str, level: LogLevel = LogLevel.INFO ):
        super().__init__( log, level )

    def propagateEntry( self, entry ):
        None

class LogToConsole(LogSink):
    def __init__( self, log : Log, level: LogLevel = LogLevel.INFO):
        super().__init__( log, level )

    def propagateEntry( self, entry ):
        print( str(entry.level) + entry.msg + "\n")
        None
       
# simple logging functions
def log( level: LogLevel, msg: str, log: Log = globalLog ):
    global globalLog
    log.addEntry( Entry(level, msg ) )



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# In this prototype/example a QTreeView is created. Then it's populated with
# three containers and all containers are populated with three rows, each 
# containing three columns.
# Then the last container is expanded and the last row is selected.
# The container items are spanned through the all columns.
# Note: this requires > python-3.2
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import sys, os, pprint, time
from PySide6.QtCore import *
from PySide6.QtWidgets import *

from hlog.hlog import *
from hlog.hLogTextQtTreeView import *


class MyApp(QApplication):
    def __init__(self, argv: list[str]):
        super().__init__( argv )
        
        self.logTreeView = hLogTreeView()

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # expand third container
        #index =  logTreeView .indexFromItem(parent1)
        #view.expand(index)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # select last row
        #selmod = view.selectionModel()
        #index2 = model.indexFromItem(child3)
        #selmod.select(index2, QItemSelectionModel.Select|QItemSelectionModel.Rows)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.logTreeView.show()


app = MyApp(sys.argv)
sys.exit(app.exec())

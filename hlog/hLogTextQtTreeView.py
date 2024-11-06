from hlog import *
import os
from pathlib import Path
import re
from datetime import datetime

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

class hLogTreeView(QTreeView):
    def __init__(self,  parent: QWidget | None= ... ):
        super().__init__()

        self.model : QStandardItemModel

        # init widgets
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['col1', 'col2', 'col3'])
        self.setModel(self.model)
        self.setUniformRowHeights(False)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # populate data
        for i in range(3):
            parent1 = QStandardItem('Family {}. Some long status text for sp'.format(i))
            for j in range(3):
                child1 = QStandardItem('Child {}\nBlabla'.format(i*3+j))
                child2 = QStandardItem('row: {}, col: {}'.format(i, j+1))
                child2.setTextAlignment( Qt.AlignmentFlag.AlignTop )
                child3 = QStandardItem('row: {}, col: {}'.format(i, j+2))
                parent1.appendRow([child1, child2, child3])
            self.model.appendRow(parent1)
            # span container columns
            self.setFirstColumnSpanned(i, self.rootIndex(), True)


        self.row

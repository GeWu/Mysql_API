#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# heatMap export
#               -- get data from heatmap and generate information 
#
# deleteData.py: #TODO DESC HERE
#
#--------------------------------------------------------------
#
# Date:     2015-06-24
#
# Author:   gewu@baidu.com
#
#
import time
from HeatMapExport import HeatMapExport
#--------------------------------------------------------------
# Globl Constants & Functions
#--------------------------------------------------------------

#--------------------------------------------------------------
# Classes
#--------------------------------------------------------------
class DeleteData(HeatMapExport):
    
    def __init__(self):
        super(DeleteData, self).__init__()

    def getDate(self, dateBegin, dateEnd):
        """the format is %Y-%m-%d"""
        begin = int(time.mktime(time.strptime(dateBegin, '%Y-%m-%d')))
        end = int(time.mktime(time.strptime(dateEnd, '%Y-%m-%d')))
        ret = []
        leave = []
        with open("timestamp", "r+") as t:
            for line in t:
                if int(line) >= begin and int(line) < end:
                    ret.append(int(line))
                else:
                    leave.append(line)
            t.seek(0)
            t.truncate()
            t.writelines(leave)
        return ret

    def deleteTime(self, timestamp):
        self.deleteInfo(timestamp)

if __name__ == "__main__":
    dd = DeleteData()
    timeList = dd.getDate("2015-06-23", "2015-06-24")
    print timeList
    for tL in timeList:
        dd.deleteTime(tL)

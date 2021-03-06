#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# heatMap export
#               -- get data from heatmap and generate csv file 
#
# HeatMapExport.py: #TODO DESC HERE
#
#--------------------------------------------------------------
#
# Date:     2015-06-18
#
# Author:   gewu@baidu.com
#
#
import os
import MySQLdb
import json
import urllib
import urllib2
import logging
import logging.config
import cPickle as pickle
import zlib
import time
import base64

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF_DIR = os.path.join(BASE_DIR, 'conf')
OUT_DIR = os.path.join(BASE_DIR, 'outcome')
os.sys.path.insert(0, CONF_DIR)

from config import CONFIG

#--------------------------------------------------------------
# Globl Constants & Functions
#--------------------------------------------------------------
HOTBYUID = "http://host/getSpotHotByUid.php"
HOTBYPOI = "http://host/getSpotHot.php"

#--------------------------------------------------------------
# Classes
#--------------------------------------------------------------
class HeatMapExport(object):
    
    def __init__(self):
        logging.config.fileConfig("../conf/logging.conf")
        self.logger_e = logging.getLogger('heatmap')
        self.conn = None
        self.cur = None
        self.connect()

    def connect(self):
        try:
            self.conn = MySQLdb.connect(**CONFIG['database'])
            self.cur = self.conn.cursor(MySQLdb.cursors.DictCursor)
            self.conn.autocommit(True)
        except MySQLdb.Error, e:
            errno = e.args[0]
            errmsg = e.args[1]
            self.logger_e.critical("Error %d: %s" % (errno, errmsg))

    def safeExecute(self, sql_str, param=None):
        if self.conn is None or self.cur is None:
            self.connect()
        try:
            if param:
                self.cur.execute(sql_str, param)
            else:
                self.cur.execute(sql_str)
        except Exception, e:
            errno = e.args[0]
            errmsg = e.args[1]
            self.logger_e.critical("Error %d: %s" % (errno, errmsg))

    def dumpCityPoi(self):
        result = []
        with open("viewList_encode.txt") as f:
            for line in f:
                lineTemp = tuple(line.split(",")[:3])
                result.append("%s_%s_%s" % lineTemp)
        pickle.dump(result, open("city_poi_uid", "wb"))

    def showCityPoi(self):
        cityPoi = pickle.load(open("city_poi_uid","rb"))
        cityPoi.sort(key=len)
        return cityPoi

    def getHotUid(self, paramD):
        """uid, time is necessary, city is optional"""
        url = "%s?%s" % (HOTBYPOI, urllib.urlencode(paramD))
        try_times = 5
        rtn = None
        while try_times > 0:
            try:
                res = urllib2.urlopen(url)
                rtn = json.loads(res.read())
                break
            except:
                try_times -= 1
                self.logger_e.error('%s_%s HotUid apiRequest failed [try_times: %d]'\
                                 % (paramD['city'], paramD['uid'], 5-try_times))
        return rtn

    def getHotPoi(self, paramD):
        """poiname, time is necessary, city is optional"""
        url = "%s?%s" % (HOTBYPOI, urllib.urlencode(paramD))
        try_times = 5
        rtn = None
        while try_times > 0:
            try:
                res = urllib2.urlopen(url)
                rtn = json.loads(res.read())
                break
            except:
                try_times -= 1
                self.logger_e.error('%s_%s HotPoi apiRequest failed [try_times: %d]'\
                                 % (paramD['city'], paramD['poiname'], 5 - try_times))
        return rtn

    def _hPackDumps(self, jDicts):
        """hPack dump json obj"""
        ret = []
        ret.append(",".join(jDicts[0].keys()))
        for j in jDicts:
            ret.append(",".join(str(v) for v in j.values()))
        return "|".join(ret)

    def _hPackLoads(self, hStr):
        """hPack load json obj"""
        hList = hStr.split("|")
        dictList = []
        keys = hList[0].split(",")
        for h in hList[1:]:
            values = h.split(",")
            mzip = zip(keys, values)
            dictList.append(dict(mzip))
        return dictList
    
    def showtable(self, info):
        "show tables"
        sql_show = "show tables";
        self.cur.execute(sql_show)
        print self.cur.fetchall()

    def storeInfo(self, info):
        "store zip info to mysql"
        try:
            zlibData = zlib.compress(self._hPackDumps(info["data"]))
            baseData = base64.b64encode(zlibData)      #we must zip the data
            sql_insert = "INSERT INTO poi_heatmap (city_poi, timestamp, hot) VALUES(%s, %s, %s)"
            params = (info['city_poi'], info['time'], baseData)
            self.safeExecute(sql_insert, params)
        except Exception, e:
            self.logger_e.error("%s store data fail" % info['city_poi'])

    def deleteInfo(self, timestamp):
        sql_delete = "delete from poi_heatmap where timestamp = %s"
        params = timestamp,
        self.safeExecute(sql_delete, params)

    def getInfo(self, info):
        "get info from mysql"
        if 'city_poi' in info:
            sql_select = "select * from poi_heatmap where city_poi = %s and timestamp = %s"
        elif 'city' in info or 'poi' in info or 'uid' in info:
            sql_select = "select * from poi_heatmap where city_poi like %s and timestamp = %s"
        else:
            sql_select = "select * from poi_heatmap where timestamp = %s"

        params = tuple(info.values())
        infos = []
        try:
            self.safeExecute(sql_select, params)
            rows = self.cur.fetchall()
            if rows:
                for row in rows:
                    tmpDict = {}
                    tmpDict['city_poi'] = row['city_poi']
                    tmpDict['time'] = row['timestamp']
                    decodeData = base64.b64decode(row['hot'])
                    tmpDict['data'] = self._hPackLoads(zlib.decompress(decodeData))
                    infos.append(tmpDict)
        except Exception, e:
            self.logger_e.error("%s get data fail! %s" % (",".join(str(m) for m in info.values()), e))
        return infos

    def writeCsv(self, infos, timestamp):
        timeStr = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(timestamp)))
        fileName = timeStr.split()[0]
        with open("%s/%s" % (OUT_DIR, fileName), "a+") as result:
            for info in infos:
                for value in info["data"]:
                    strValue = json.dumps(value).replace("{", "").replace("}", "")
                    result.write("%s, %s, %s\n" % (info['city_poi'].encode('utf-8'), strValue, timeStr))

    def getStoreInfo(self, cityPoi, timestamp):
        for cl in cityPoi:
            clList = cl.split("_")
            p = dict(poiname=clList[1], time=timestamp, city=clList[0])
            hotData = None
            hotJson = self.getHotPoi(p)
            if hotJson:
                hotData = hotJson['data']
            if hotData:
                info = dict(city_poi="_".join(clList[:-1]), time=timestamp, data=hotData)
                self.storeInfo(info)
            else:
                self.logger_e.warn("%s %s get data NULL" % (cl, timestamp))



if __name__ == "__main__":
    hme = HeatMapExport()
    #hme.dumpCityPoi()
    
    #cityPoi = hme.showCityPoi()
    #hme.getStoreInfo(cityPoi, 1435021200)

    #city = ["杭州市_超山梅怡陵_"]
    #hme.getStoreInfo(city, 1435021200)
    #ret = dict(timestamp=1435021200, city_poi="杭州市_超山梅怡陵")

    ret = dict(timestamp=1435021200)
    infos = hme.getInfo(ret)
    hme.writeCsv(infos, ret['timestamp'])

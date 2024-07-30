import os
import glob
import locale
import sys
import getopt
import csv
import statistics
import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime as dt

# some filenames
strScriptName   = os.path.basename(sys.argv[0])
strScriptBase   = strScriptName.replace(".py","")
strScriptPath   = os.path.dirname(os.path.realpath(sys.argv[0]))
csvFilePing     = ""
csvFileSftp     = ""
csvFileStatPing = strScriptBase.replace("_Stats", "_Ping_Stats_{0}.csv".format(dt.now().strftime("%Y-%m")))
csvFileStatSftp = strScriptBase.replace("_Stats", "_Sftp_Stats_{0}.csv".format(dt.now().strftime("%Y-%m")))

DOLAST   = True
DOONE    = False
DOALL    = False
DOGRAPHS = False

filename = ""

locale.setlocale(locale.LC_ALL, 'nl_NL')  # Use '' for auto, or force e.g. to 'en_US.UTF-8'

#------------------------------------------------------------------------------
def getargs(argv):

    global DOLAST, DOONE, DOALL, DOGRAPHS
    global filename
    
    try:
        opts, args = getopt.getopt(argv,"LOAG")
        
    except getopt.GetoptError:
        print(strScriptName + ".py [-L or -O or -A or -G]")
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-L':
            DOLAST = True
            DOONE  = False
            DOALL  = False
            break
            
        elif opt == '-O':
            DOLAST = False
            DOALL  = False
            DOONE  = True
            filename = arg
            break
            
        elif opt == '-A':
            DOLAST = False
            DOONE  = False
            DOALL  = True
            break
            
        elif opt == '-G':
            DOGRAPHS = True
            break
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def statsCheck():
    if not os.path.isfile(csvFileStatPing):
            with open(csvFileStatPing, 'a') as file:
                file.write('"date","time (ms)","late (#)","loss (#)"\n')
                
    if not os.path.isfile(csvFileStatSftp):
        with open(csvFileStatSftp, 'a') as file:
            file.write('"date","up avg (kbps)","up stdev (kbps)","down avg (kbps)","down stdev (kbps)"\n')
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
#grab last 4 characters of the file name:
def last_4chars(x):
    return(x[-4:])
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def dostats_ping(filename):

    outname = filename[:-3] + "txt"

    f = open(outname, "w")

    f.write("================================================\n")
    f.write("=== " + filename.replace("InternetSpeed_", "") + "\n")
    f.write("================================================\n")
    f.write("\n")

    list_max  = []
    list_avg  = []
    list_loss = []

    cnt_los = 0
    tot = 0
    f.write("Pings with losses\n")
    f.write("------------------------------------------------\n")

    input_file = csv.DictReader(open(filename))
    for row in input_file:
        list_loss.append(int(row['loss']))
        tot = tot + 1
        loss = int(row['loss'])
        if loss == 33:
            f.write("{0}  {1:<18} loss: 1 of 3 = {2:3d}%\n".format(row['Date-Time'][11:], row['host'][2:-1], int(row['loss'])))
            cnt_los = cnt_los + 1
        else:
            if loss == 66:
                f.write("{0}  {1:<18} loss: 2 of 3 = {2:3d}%\n".format(row['Date-Time'][11:], row['host'][2:-1], int(row['loss'])))
                cnt_los = cnt_los + 1
            else:
                if loss == 100:
                    f.write("{0}  {1:<18} loss: 3 of 3 = {2:3d}%\n".format(row['Date-Time'][11:], row['host'][2:-1], int(row['loss'])))
                    cnt_los = cnt_los + 1
        list_max.append(int(row['max (ms)']))
        list_avg.append(int(row['avg (ms)']))

    pct = (cnt_los / tot) * 100
    f.write("------------------------------------------------\n")
    f.write("Total losses :         {0:6n} of {1:6n} ({2:5.2f}%)\n".format(cnt_los, tot, pct))
    f.write("------------------------------------------------\n")


    avg_max = int(statistics.mean(list_max))
    dev_max = int(statistics.stdev(list_max))
    max_bad = avg_max + (5 * dev_max)

    avg_avg = int(statistics.mean(list_avg))
    dev_avg = int(statistics.stdev(list_avg))
    avg_950 = avg_avg + (2 * dev_avg)
    avg_997 = avg_avg + (3 * dev_avg)
    avg_bad = avg_avg + (5 * dev_avg)

    f.write("\n")

    cnt_avg = 0
    cnt_950 = 0
    cnt_997 = 0
    cnt_999 = 0
    cnt_lat = 0
    tot = 0
    
    f.write("Exceeding max average time of {:3d} ms\n".format(avg_bad))
    f.write("------------------------------------------------\n")
    input_file = csv.DictReader(open(filename))
    for row in input_file:
        tot = tot + 1
        if int(row['avg (ms)']) <= avg_avg:
            cnt_avg = cnt_avg + 1
        else:
            if int(row['avg (ms)']) <= avg_950:
                cnt_950 = cnt_950 + 1
            else:
                if int(row['avg (ms)']) <= avg_997:
                    cnt_997 = cnt_997 + 1
                else:
                    if int(row['avg (ms)']) <= avg_bad:
                        cnt_999 = cnt_999 + 1
                    else:
                        if int(row['avg (ms)']) > avg_bad:
                            f.write("{0}  {1:<18}           {2:6n} ms\n".format(row['Date-Time'][11:], row['host'][2:-1], int(row['avg (ms)'])))
                            cnt_lat = cnt_lat + 1

    pct = (cnt_lat / tot) * 100
    f.write("------------------------------------------------\n")
    f.write("Total >  {0:3d} ms:       {1:6n} of {2:6n} ({3:5.2f})%\n".format(avg_bad, cnt_lat, tot, pct))
    f.write("------------------------------------------------\n")

    f.write("\n")

    f.write("Extra performance info\n")
    f.write("------------------------------------------------\n")
    pct = (cnt_avg / tot) * 100
    f.write("Total <= {0:3d} ms:       {1:6n} of {2:6n} ({3:5.2f}%)\n".format(avg_avg, cnt_avg,                               tot, pct))
    pct = ((cnt_avg + cnt_950) / tot) * 100
    f.write("Total <= {0:3d} ms:       {1:6n} of {2:6n} ({3:5.2f}%)\n".format(avg_950, cnt_avg + cnt_950,                     tot, pct))
    pct = ((cnt_avg + cnt_950 + cnt_997) / tot) * 100
    f.write("Total <= {0:3d} ms:       {1:6n} of {2:6n} ({3:5.2f}%)\n".format(avg_997, cnt_avg + cnt_950 + cnt_997,           tot, pct))
    pct = ((cnt_avg + cnt_950 + cnt_997 + cnt_999) / tot) * 100
    f.write("Total <= {0:3d} ms:       {1:6n} of {2:6n} ({3:5.2f}%)\n".format(avg_bad, cnt_avg + cnt_950 + cnt_997 + cnt_999, tot, pct))
    f.write("------------------------------------------------\n")
    f.close()

    return filename[-14:-4], avg_997, cnt_lat, cnt_los
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def dostats_sftp(filename):

    list_up = []
    list_dn = []
    list_tt = []
    list_us = []
    list_ds = []
    
    input_file = csv.DictReader(open(filename))
    for row in input_file:
        if int(row['success']) == 1:
            list_up.append(int(row["up (ms)"]))
            list_dn.append(int(row["down (ms)"]))
            list_tt.append(int(row["total (ms)"]))
            list_us.append(int(row["up speed (kbps)"]))
            list_ds.append(int(row["down speed (kbps)"]))

    up_avg = int(statistics.mean(list_up))
    up_std = int(statistics.stdev(list_up))
    dn_avg = int(statistics.mean(list_dn))
    dn_std = int(statistics.stdev(list_dn))
    tt_avg = int(statistics.mean(list_tt))
    tt_std = int(statistics.stdev(list_tt))
    us_avg = int(statistics.mean(list_us))
    us_std = int(statistics.stdev(list_us))
    ds_avg = int(statistics.mean(list_ds))
    ds_std = int(statistics.stdev(list_ds))

    return filename[-14:-4], us_avg, up_std, ds_avg, ds_std
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def dograph_ping():

    global csvFileStatPing

    # init vars
    datel = []
    datal = { 'time (ms)': [],
              'late [#)' : [],  
              'loss [#)' : [],
            }
    datat = {}
    max   = 0
    
    # read file into vars           
    input_file = csv.DictReader(open(csvFileStatPing))
    for row in input_file:
        datel.append(row["date"])
        
        data = int(row["time (ms)"])
        if max < data:
            max = data
        datal['time (ms)'].append(data)
        data = int(row["late (#)"])
        if max < data:
            max = data
        datal['late [#)'].append(data)
        data = int(row["loss (#)"])
        if max < data:
            max = data
        datal['loss [#)'].append(data)
        
    # convert lists to tuples
    datet = tuple(datel)
    for key, value in datal.items():
        datat[key] = tuple(value)

    # the label locations
    x = np.arange(len(datel))  
    # the width of the bars
    width = 0.25 
    multiplier = 0

    # create graph - figsize are in inch
    xlen = len(datat) * 3 + 5
    ylen = 6 if (xlen / 4) < 6 else (xlen / 4) 
    fig, ax = plt.subplots(layout='constrained', figsize=(xlen, 6))
    for attribute, measurement in datat.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        ax.bar_label(rects, padding=3)
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel(' ')
    ax.set_title('Ping Information')
    ax.set_xticks(x + width, datet, rotation=90)
    ax.legend(loc='upper left', ncols=len(datat))
    max = (int(max/10) + 5) * 10
    ax.set_ylim(0, max)

    # plt.show()
    plt.savefig(csvFileStatPing.replace(".csv", ".jpg"))
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def dograph_sftp():

    global csvFileStatSftp

    # init vars
    datel = []
    datal = { 'up avg'   : [],
              'down avg' : []
            }
    datat = {}
    max   = 0
            
    # read file into vars           
    input_file = csv.DictReader(open(csvFileStatSftp))
    for row in input_file:
        datel.append(row["date"])
        
        data = int(row["up avg (kbps)"])
        if max < data:
            max = data
        datal['up avg'].append(data)
        data = int(row["down avg (kbps)"])
        if max < data:
            max = data
        datal['down avg'].append(data)
        
    # convert lists to tuples
    datet = tuple(datel)
    for key, value in datal.items():
        datat[key] = tuple(value)

    # the label locations
    x = np.arange(len(datet))  
    # the width of the bars
    width = 0.25
    multiplier = 0

    # create graph - figsize are in inch
    xlen = len(datat) * 3 + 5
    ylen = 6 if (xlen / 4) < 6 else (xlen / 4) 
    fig, ax = plt.subplots(layout='constrained', figsize=(xlen, 6))
    for attribute, measurement in datat.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        ax.bar_label(rects, padding=3)
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('kbps')
    ax.set_title('Secure FTP Speeds')
    ax.set_xticks(x + width, datet, rotation=90)
    ax.legend(loc='upper left', ncols=len(datat))
    max = (int(max/100) + 100) * 100
    ax.set_ylim(0, max)

    # plt.show()
    plt.savefig(csvFileStatSftp.replace(".csv", ".jpg"))
#------------------------------------------------------------------------------

#==============================================================================
### Main 
#==============================================================================
if __name__ == "__main__":

    if len(sys.argv) > 1:
        getargs(sys.argv[1:])
        
        
    if DOGRAPHS:
        print("Running DOGRAPHS")
        dograph_ping()        
        dograph_sftp()
        
    elif DOLAST:
        print("Running DOLAST")
        
        statsCheck()
        
        files_list   = glob.glob("InternetSpeed_Ping_*.csv")
        files_sorted = sorted(files_list, key = last_4chars)
        filename = files_sorted.pop()
        dte, tim, lat, los = dostats_ping(filename)
        with open(csvFileStatPing, 'a') as file:
            file.write('"' + dte + '",' + str(tim) + ',' + str(lat) + ',' + str(los) + "\n")
        dograph_ping()
            
        files_list   = glob.glob("InternetSpeed_Sftp_*.csv")
        files_sorted = sorted(files_list, key = last_4chars)
        filename = files_sorted.pop()
        dte, up_avg, up_std, ds_avg, ds_std = dostats_sftp(filename)
        with open(csvFileStatSftp, 'a') as file:
            file.write('"' + dte + '",' + str(up_avg) + ',' + str(up_std) + ',' + str(ds_avg) + ',' + str(ds_std) + "\n")
        dograph_sftp()


    elif DOONE:
        print("Running DOONE")
        if not os.path.isfile(filename):
            print("  >>> Error <<< : {0} does not exist".format(filename))
            sys.exit(1)
            
        statsCheck()
        
        dte, tim, lat, los = dostats_ping(filename)
        with open(csvFileStatPing, 'a') as file:
            file.write('"' + dte + '",' + str(tim) + ',' + str(lat) + ',' + str(los) + "\n")
        dograph_ping()

        dte, up_avg, up_std, ds_avg, ds_std = dostats_sftp(filename)
        with open(csvFileStatSftp, 'a') as file:
            file.write('"' + dte + '",' + str(up_avg) + ',' + str(up_std) + ',' + str(ds_avg) + ',' + str(ds_std) + "\n")
        dograph_sftp()


    elif DOALL:
        print("Running DOALL")
        
        if os.path.isfile(csvFileStatPing):
            os.remove(csvFileStatPing)
        if os.path.isfile(csvFileStatSftp):
            os.remove(csvFileStatSftp)            
        statsCheck()
        
        files_list   = glob.glob("InternetSpeed_Ping_*.csv")
        files_sorted = sorted(files_list, key = last_4chars)
        for filename in files_sorted:
            if filename == csvFileStatPing:
                continue
            dte, tim, lat, los = dostats_ping(filename)
            with open(csvFileStatPing, 'a') as file:
                file.write('"' + dte + '",' + str(tim) + ',' + str(lat) + ',' + str(los) + "\n")
        dograph_ping()

        files_list   = glob.glob("InternetSpeed_SFTP_*.csv")
        files_sorted = sorted(files_list, key = last_4chars)
        for filename in files_sorted:
            if filename == csvFileStatSftp:
                continue
            dte, up_avg, up_std, ds_avg, ds_std = dostats_sftp(filename)
           
            with open(csvFileStatSftp, 'a') as file:
                file.write('"' + dte + '",' + str(up_avg) + ',' + str(up_std) + ',' + str(ds_avg) + ',' + str(ds_std) + "\n")          
        dograph_sftp()
                
#==============================================================================


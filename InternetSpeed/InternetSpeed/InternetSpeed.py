#!/usr/bin/python
# -*- coding: utf-8 -*-
import os.path
import pysftp
import sys, getopt
import os
import smtplib, ssl
import socket
import struct
import time
import select
import traceback
import netifaces
import dns.resolver
import yaml

from requests             import get
from datetime             import datetime        as dt
from datetime             import timedelta
from email                import encoders
from email.mime.base      import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from pathlib              import Path

#------------------------------------------------------------------------------

VERSION         = "2.00"

Debug           = True

#------------------------------------------------------------------------------

# some filenames
strScriptName   = os.path.basename(sys.argv[0])
strScriptBase   = strScriptName.replace(".py","")
strScriptPath   = os.path.dirname(os.path.realpath(sys.argv[0]))
yamlFilename    = strScriptPath + "/" + strScriptBase + '.yaml'
csvFilePing     = ""
csvFileSftp     = ""
sftpFilename    = ""

logPath         = strScriptPath + "/log"
logFileName     = logPath + "/" + strScriptName.replace(".py", "_")

# ping stuff
ping_count      = "3"
ping_size       = "256"
ping_timeout    = 300       # in milliseconds

# Date - Time stuff
dteNow          = dt.now()
dteSave         = dteNow
dteSFTP         = dteNow
dteMail         = dteNow
dtePrev         = dteNow

resultsPing     = []
resultsSftp     = []

# YAML stuff
location        = ""
provider_domain = ""
provider_name   = ""
smtp_enabled    = False
smtp_server     = ""
smtp_port       = ""
smtp_TLS        = ""
smtp_CA         = ""
smtp_login      = ""
smtp_password   = ""
smtp_from       = ""
smtp_to         = ""

sftp_enabled    = False
sftp_server     = ""
sftp_port       = ""
sftp_login      = ""
sftp_password   = ""
stfp_remotedir  = ""
sftp_filesize   = 0
sftp_interval   = 0

###############################################################################
# Classes
###############################################################################

#------------------------------------------------------------------------------
ICMP_ECHO_REQUEST = 8     # Platform specific
DEFAULT_COUNT     = 3
DEFAULT_SIZE      = 64
DEFAULT_TIMEOUT   = 300   # in milliseconds

class Pinger(object):
    """ Pings to a host -- the Pythonic way"""

    def __init__(self, target_host, count=DEFAULT_COUNT, size=DEFAULT_SIZE, timeout=DEFAULT_TIMEOUT, debug=False):
        self.target_host = target_host
        self.count = count
        self.timeout = timeout / 1000  # convert to seconds - select uses seconds
        self.size = size
        self.debug = debug


    def do_checksum(self, source_string):
        """  Verify the packet integritity """
        sum = 0
        max_count = (len(source_string)/2)*2
        count = 0
        while count < max_count:
            val = source_string[count + 1]*256 + source_string[count]
            sum = sum + val
            sum = sum & 0xffffffff
            count = count + 2

        if max_count<len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
            sum = sum & 0xffffffff

        sum = (sum >> 16)  +  (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return answer

    def receive_pong(self, sock, ID, timeout):
        """
        Receive ping from the socket.
        """
        time_remaining = timeout
        while True:
            start_time = time.time()
            readable = select.select([sock], [], [], time_remaining)
            time_spent = (time.time() - start_time)
            if readable[0] == []: # Timeout
                return

            time_received = time.time()
            recv_packet, addr = sock.recvfrom(1024)
            icmp_header = recv_packet[20:28]
            type, code, checksum, packet_ID, sequence = struct.unpack("bbHHh", icmp_header)
            if packet_ID == ID:
                bytes_In_double = struct.calcsize("d")
                time_sent = struct.unpack("d", recv_packet[28:28 + bytes_In_double])[0]
                return time_received - time_sent

            time_remaining = time_remaining - time_spent
            if time_remaining <= 0:
                return


    def send_ping(self, sock,  ID):
        """
        Send ping to the target host
        """
        target_addr  =  socket.gethostbyname(self.target_host)

        my_checksum = 0

        # Create a dummy heder with a 0 checksum.
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
        bytes_In_double = struct.calcsize("d")
        data = (192 - bytes_In_double) * "Q"
        data = struct.pack("d", time.time()) + bytes(data.encode('utf-8'))

        # Get the checksum on the data and the dummy header.
        my_checksum = self.do_checksum(header + data)
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1)
        packet = header + data
        sock.sendto(packet, (target_addr, 1))


    def ping_once(self):
        """
        Returns the delay (in seconds) or none on timeout.
        """
        icmp = socket.getprotobyname("icmp")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except socket.error as e:
            if e.errno == 1:
                # Not superuser, so operation not permitted
                e.msg +=  "ICMP messages can only be sent from root user processes"
                raise socket.error(e.msg)
        except Exception as e:
            if self.debug:
                print("Exception: %s" %(e))

        my_ID = os.getpid() & 0xFFFF

        self.send_ping(sock, my_ID)
        delay = self.receive_pong(sock, my_ID, self.timeout)
        sock.close()
        return delay


    def ping(self):
        """
        Run the ping process
        """

        max=0
        min=0
        los=0
        tot=0

        for i in range(self.count):
            try:
                delay  =  self.ping_once()
            except socket.gaierror as e:
                if self.debug:
                    print("Ping failed. (socket error: '%s')" % e[1])
                    break

            if delay  ==  None:
                # print("Ping failed. (timeout within %ssec.)" % self.timeout)
                if self.debug:
                    print("Request timed out.")
                delay = int(self.timeout * 1000)
                los = los+1

            else:
                delay  =  int(delay * 1000)
                if self.debug:
                    print("Reply from %s" % self.target_host,end = '')
                    print(" time=%0.0fms" % delay)

            if delay > max:
                max=delay
            if delay < min:
                min=delay
            tot = tot + delay

        los = int((los/self.count)*100)
        return max, min, int(tot/self.count), los
#------------------------------------------------------------------------------

###############################################################################
# Functions
###############################################################################

#------------------------------------------------------------------------------
#read configuation settings from YAML file
def readConfig():

    global yamlFilename
    global location, provider_domain, provider_name
    global smtp_enabled, smtp_server, smtp_port, smtp_TLS, smtp_CA, smtp_login, smtp_password, smtp_from, smtp_to
    global sftp_enabled, sftp_server, sftp_port, sftp_login, sftp_password, sftp_remotedir, sftp_filesize, sftp_interval

    try:
        # read yaml file
        with open(yamlFilename) as file:
            config = yaml.full_load(file)

        # # get data from yaml file
        location        = config["LOCATION"]["Location"]
        provider_domain = config["PROVIDER"]["Domain"]
        provider_name   = config["PROVIDER"]["Name"]

        # # --- SMTP ---
        smtp_enabled = config["SMTP"]["Enabled"]
        if smtp_enabled:
            smtp_server    = config["SMTP"]["Server"]
            smtp_port      = config["SMTP"]["Port"]
            smtp_TLS       = config["SMTP"]["TLS"]
            smtp_CA        = config["SMTP"]["CA"]
            if config["SMTP"]["Login"]:
                smtp_login     = config["SMTP"]["Login"]
            else:
                smtp_login     = ""
            if config["SMTP"]["Password"]:
                smtp_password  = config["SMTP"]["Password"]
            else:
                smtp_password  = ""
            smtp_from      = config["SMTP"]["From"]
            smtp_to        = config["SMTP"]["To"]
            # setup ssl
            if smtp_TLS:
                try:
                    ssl._create_unverified_https_context = ssl._create_unverified_context
                except AttributeError:
                    # Legacy Python that doesn't verify HTTPS certificates by default
                    pass

        # --- Secure FTP ---
        sftp_enabled = config["SFTP"]["Enabled"]
        if sftp_enabled:
            sftp_server    = config["SFTP"]["Server"]
            sftp_port      = config["SFTP"]["Port"]
            sftp_login     = config["SFTP"]["Login"]
            sftp_password  = config["SFTP"]["Password"]
            sftp_remotedir = config["SFTP"]["RemoteDir"]
            sftp_filesize  = int(config["SFTP"]["FileSize"]) * 1024
            sftp_interval  = int(config["SFTP"]["TimeInterval"])

    except:
        sys.exit()
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def doping(Host, Count, Size, Timeout):

    min=Timeout
    max=Timeout
    avg=Timeout
    los=100
    ip=""

    if Host.find(";") != -1:
        host,ip = Host.split(";")
    else:
        host = Host

    try:
        if ip == '':
            target_addr  =  socket.gethostbyname(host)
            ip = target_addr

        pinger = Pinger(target_host=ip, count=Count, size=Size, timeout=Timeout)
        max, min, avg, los = pinger.ping()
        suc = 100 - los

    except:
       print("%s not resolvable" % host)

    return min, max, avg, suc, los, ip
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def PingHost(Host):

    global ping_count, ping_size, ping_timeout

    if Host.find(";") != -1:
        host,ip = Host.split(";")
    else:
        host = Host

    min, max, avg, success, loss, ip = doping(Host, int(ping_count), int(ping_size), int(ping_timeout))

    return min, max, avg, success, loss, ip
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def dosftp():

    global sftp_server, sftp_port, sftp_login, sftp_password, sftp_remotedir
    global sftpFilename
    global dteNow, dteSFTP

    dteSFTP = dteNow + timedelta(minutes = sftp_interval)

    if Debug:
        print("Uploading to web")

    remote = sftp_remotedir + sftpFilename

    result = False
    st = time.process_time()
    up = time.process_time()
    dn = time.process_time()

    try:

        # Load .ssh/known_hosts
        cnopts = pysftp.CnOpts()

        with pysftp.Connection(sftp_server, username=sftp_login, password=sftp_password, cnopts=cnopts) as sftp:

            if Debug:
                print("Logged in")

            remotepath, remotefile = os.path.split(remote)
            curdir = sftp.pwd
            if curdir != remotepath:
                sftp.cwd(remotepath)
            local = remotefile.replace("txt", "tmp")

            up = time.process_time()
            if Debug:
                print("Uploading " + sftpFilename)
            sftp.put(sftpFilename)
            if Debug:
                print("Uploaded  " + remote)
            up = int((time.process_time() - up) * 1000)

            dn = time.process_time()
            if Debug:
                print("Downloading " + local)
            sftp.get(remote, local)
            if Debug:
                print("Downloaded  " + local)
            dn = int((time.process_time() - dn) * 1000)

            if Debug:
                print("Removing  " + remote)
            sftp.remove(remote)
            if Debug:
                print("Removed   " + remote)

            if Debug:
                print("Removing  " + local)
            if os.path.exists(local):
                os.remove(local)
            if Debug:
                print("Removed   " + local)

            # Close the connection
            sftp.close()

        if Debug:
            print("Uploading successful")

        result = True

    except Exception as e:
        if Debug:
            print(str(e))
            print("Uploading failed")

    tt = int((time.process_time() - st) * 1000)

    return result, up, dn, tt

#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
# general routine to send mails
def sendmail(From, To, Subject, Body, Attach = ""):

    global smtp_server, smtp_port, smtp_TLS, smtp_CA, smtp_login, smtp_password, sslcontext

    msg            = MIMEMultipart()
    msg['From']    = From
    msg['To']      = To
    msg['Subject'] = Subject

    msg.attach(MIMEText(Body, 'plain'))

    if Attach != "":
        attachment = open(Attach, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % Attach)
        msg.attach(part)

    server = smtplib.SMTP(smtp_server, smtp_port)
    try:
        if smtp_TLS and not smtp_CA:
            server.starttls()           # Secure the connection
        elif smtp_TLS and smtp_CA:
            server.starttls(sslcontext) # Secure the connection
        if smtp_login != "":
            server.login(smtp_login, smtp_password)
        text = msg.as_string()
        server.sendmail(From, To, text)

    except Exception as e:
        pass

    finally:
        server.quit()

#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
# general routine to send mails
def sendmail(From, To, Subject, Body, Attach=[]):

    global smtp_server, smtp_port, smtp_TLS, smtp_CA, smtp_login, smtp_password, sslcontext

    msg            = MIMEMultipart()
    msg['From']    = From
    msg['To']      = To
    msg['Subject'] = Subject

    msg.attach(MIMEText(Body, 'html'))

    if Attach:
        for f in Attach:  # add files to the message
            attachment = open(f, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment", filename=f)
            msg.attach(part)

    server = smtplib.SMTP(smtp_server, smtp_port)
    try:
        if smtp_TLS and not smtp_CA:
            server.starttls()           # Secure the connection
        elif smtp_TLS and smtp_CA:
            server.starttls(sslcontext) # Secure the connection
        if smtp_login != "":
            server.login(smtp_login, smtp_password)
        text = msg.as_string()
        server.sendmail(From, To, text)

    except Exception as e:
        pass

    finally:
        server.quit()
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def csvCheck():

    global csvFilePing, csvFileSftp

    if not Path(csvFilePing).is_file():
        with open(csvFilePing,'a') as file:
            file.write('"Date-Time","host","min (ms)","max (ms)","avg (ms)","success","loss"\n')

    if not Path(csvFileSftp).is_file():
        with open(csvFileSftp,'a') as file:
            file.write('"Date-Time","host","up (ms)","down (ms)","total (ms)","success","up speed (kbps)","down speed (kbps)"\n')

#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def csvSave():

    global dteNow, dteSave
    global csvFilePing, csvFileSftp
    global resultsPing, resultsSftp

    dteSave = dteNow + timedelta(minutes = 5)
    csvCheck()
    with open(csvFilePing,'a') as file:
        for line in resultsPing:
            file.write(str(line)[1:-1].replace("'", '"') + "\n")
    resultsPing.clear()

    with open(csvFileSftp,'a') as file:
        for line in resultsSftp:
            file.write(str(line)[1:-1].replace("'", '"') + "\n")
    resultsSftp.clear()
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
def csvSend():

    global dteNow, dteSave, dteMail, dtePrev
    global csvFilePing
    global smtp_from, smtp_to

    dteMail = dteNow
    body = ""
    body = body + "Date-Time Now:   {0}\n".format(dteNow.strftime("%Y-%m-%d %H:%M:%S"))
    body = body + "Date-Time Save:  {0}\n".format(dteSave.strftime("%Y-%m-%d %H:%M:%S"))
    body = body + "Date-Time SFTP:  {0}\n".format(dteSFTP.strftime("%Y-%m-%d %H:%M:%S"))
    body = body + "Date-Time Mail:  {0}\n".format(dteMail.strftime("%Y-%m-%d %H:00:00"))
    body = body + "File to save to: {0}\n".format(csvFilePing)
    body = body + "File to save to: {0}\n".format(csvFileSftp)

    at = []
    csvPath, csvFile = os.path.split(csvFilePing)
    at.append(csvFile)
    csvPath, csvFile = os.path.split(csvFileSftp)
    at.append(csvFile)
    sendmail(smtp_from, smtp_to, "InternetSpeed Results (" + dteNow.strftime("%Y-%m-%d %H:%M:%S") + ")", body, at)
    # sendmail(smtp_from, smtp_to, "InternetSpeed Ping Results (" + dteNow.strftime("%Y-%m-%d %H:%M:%S") + ")", body, csvFile)
    # sendmail(smtp_from, smtp_to, "InternetSpeed SFTP Results (" + dteNow.strftime("%Y-%m-%d %H:%M:%S") + ")", body, csvFile)
#----------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def check_exp_log():

    global logFileName
    global smtp_from, smtp_to

    dteNow  = dt.now()
    logFile = logFileName + "exp_" + dteNow.strftime("%Y%m%d") + ".log"

    if os.path.exists(logFile):
        if os.path.getsize(logFile) > 0:
            data = ""
            with open(logFile, 'r') as log:
                data = log.read()
            sendmail(smtp_from, smtp_to, "Exception file found", data, logFile)
        os.remove(logFile)
#------------------------------------------------------------------------------

###############################################################################
# Main program loop
###############################################################################
# general stuff

readConfig()

# check for any exception log = error in program
if smtp_enabled:
    check_exp_log()

dteNow   = dt.now()
dteSave  = dteNow + timedelta(minutes =  5)
dteSFTP  = dteNow + timedelta(minutes = sftp_interval)
dteMail  = dteNow
dtePrev  = dteNow

csvFilePing = strScriptPath + "/" + strScriptBase + "_Ping_" + location + "_" + provider_name + "_" + dteNow.strftime("%Y-%m-%d") + ".csv"
csvFileSftp = strScriptPath + "/" + strScriptBase + "_SFTP_" + location + "_" + provider_name + "_" + dteNow.strftime("%Y-%m-%d") + ".csv"
csvCheck()

# get all network gateways on this device
gws=netifaces.gateways()
gateway = gws['default'][2][0]

# find first nameserver of provider
provider_ns = ""
nameservers = dns.resolver.resolve(provider_domain,'NS')
for data in nameservers:
    ns = data.to_text()
    ip = dns.resolver.resolve(ns,'A')
    for ipval in ip:
        provider_ns = ipval.to_text()
        break

# create file to be sent/received
sftpFilename = strScriptBase + "_" + location + "_" + provider_name + ".txt"
if not os.path.isfile(sftpFilename):
    with open(sftpFilename, 'wb') as f:
        f.write(os.urandom(sftp_filesize))

# create body for mail
body = ""
body = body + "Date-Time Now:   {0}\n".format(dteNow.strftime("%Y-%m-%d %H:%M:%S"))
body = body + "Date-Time Save:  {0}\n".format(dteSave.strftime("%Y-%m-%d %H:%M:%S"))
body = body + "Date-Time SFTP:  {0}\n".format(dteSFTP.strftime("%Y-%m-%d %H:%M:%S"))
body = body + "Date-Time Mail:  {0}\n".format(dteMail.strftime("%Y-%m-%d %H:00:00"))
body = body + "File to save to: {0}\n".format(csvFilePing)
body = body + "File to save to: {0}\n".format(csvFileSftp)

if smtp_enabled:
    sendmail(smtp_from, smtp_to, strScriptBase + " Starts (" + dteNow.strftime("%Y-%m-%d %H:%M:%S") + ")", body)

#endless loop
try:

    while True:
        dteNow = dt.now()

        #time to save?
        if dteNow > dteSave:
            csvSave()

        #time to sftp?
        if sftp_enabled and dteNow > dteSFTP:
            res, up, dn, tot = dosftp()
            timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            if res:
                upspeed = int((sftp_filesize * 8) / up )
                dnspeed = int((sftp_filesize * 8) / dn )
                if Debug:
                    print("{0} -  {1:<15} ; up: {2:2d} ; down: {3:2d} ; tot: {4:2d} ; success: {5:1d}, upspeed: {6:7d} kbps, downspeed: {7:7d} kbps".format(timestamp, sftp_server, up, dn, tot, 1, upspeed, dnspeed))
                resultsSftp.append([timestamp, sftp_server, up, dn, tot, 1, upspeed, dnspeed])
            else:
                if Debug:
                    print("{0} -  {1:<15} ; up: {2:2d} ; down: {3:2d} ; tot: {4:2d} ; success: {5:1d}, upspeed: {6:5d} kbps, downspeed: {7:5d} kbps".format(timestamp, sftp_server, up, dn, tot, 0, 0, 0))
                resultsSftpPing.append([timestamp, sftp_server, up, dn, tot, 0, 0, 0])

        # newday starts, save first, send final resultsPing of prev day, and start new file
        if dteNow.strftime("%Y-%m-%d") != dtePrev.strftime("%Y-%m-%d"):
            # save first
            csvSave()
            # now send
            if smtp_enabled:
                csvSend()
            # start new file
            dtePrev = dteNow
            csvFilePing   = strScriptPath + "/" + strScriptBase + "_Ping_" + location + "_" + provider_name + "_" + dteNow.strftime("%Y-%m-%d") + ".csv"
            csvFileSftp   = strScriptPath + "/" + strScriptBase + "_SFTP_" + location + "_" + provider_name + "_" + dteNow.strftime("%Y-%m-%d") + ".csv"
            csvCheck()

        # Gateway
        host = gateway
        min, max, avg, success, loss, ip = PingHost(host)
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        if Debug:
            print("{0} -  {1:<15} ; min: {2:2d} ; max: {3:2d} ; avg: {4:2d} ; success: {5:2d} ; loss: {6:2d}".format(timestamp, host, min, max, avg, success, loss))
        resultsPing.append([timestamp, host, min, max, avg, success, loss])

        # Provider DNS
        host = provider_ns
        min, max, avg, success, loss, ip = PingHost(host)
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        if Debug:
            print("{0} -  {1:<15} ; min: {2:2d} ; max: {3:2d} ; avg: {4:2d} ; success: {5:2d} ; loss: {6:2d}".format(timestamp, host, min, max, avg, success, loss))
        resultsPing.append([timestamp, host, min, max, avg, success, loss])

        # Google well_known DNS
        host = "8.8.8.8"
        min, max, avg, success, loss, ip = PingHost(host)
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        if Debug:
            print("{0} -  {1:<15} ; min: {2:2d} ; max: {3:2d} ; avg: {4:2d} ; success: {5:2d} ; loss: {6:2d}".format(timestamp, host, min, max, avg, success, loss))
        resultsPing.append([timestamp, host, min, max, avg, success, loss])

        time.sleep(10)

except KeyboardInterrupt:
    dteNow     = dt.now()
    timestamp  = dteNow.strftime("%Y-%m-%d %H:%M:%S")
    strMessage = timestamp + " - Detected Ctrl-C interruption"

except:
    logFile = logFileName + "exp_" + dteNow.strftime("%Y%m%d") + ".log"
    with open(logFile, "a") as log:
        log.write("%s: Exception occurred:\n" % dteNow.strftime('%Y-%m-%d %H:%M:%S'))
        traceback.print_exc(file=log)

finally:
    csvCheck()
    csvSave()
    sys.exit()

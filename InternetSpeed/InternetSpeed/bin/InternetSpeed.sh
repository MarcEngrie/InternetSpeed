#! /bin/sh
### BEGIN INIT INFO
# Provides:          InternetSpeed.sh
# Required-Start:    $local_fs $network
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO
DAEMON="InternetSpeed.py"
PROGRAM="python3"
PARAM=" 2>&1 &"
NAME="InternetSpeed"
DESC="InternetSpeed"

set -e
export TERM=linux

cd /home/pi/InternetSpeed/

case "$1" in
    start)
        echo -n "Starting $DESC: $DAEMON $PARAM"
        for i in `ls ./www/logs/*.rrd`; do rrdtool dump $i > $i.xml; done
        $PROGRAM $DAEMON $PARAM
    ;;
    stop)
        echo -n "Stopping $DESC: "
        killall -e -i -9 -q -w $DAEMON || true
        echo "Killed."
    ;;
    restart)
        echo -n "Stopping $DESC: "
        killall -e -i -9 -q -w $DAEMON || true
        echo "Killed."
        sleep 1
        echo -n "Starting $DESC: "
        for i in `ls ./www/logs/*.rrd`; do rrdtool dump $i > $i.xml; done
        $PROGRAM $DAEMON $PARAM
    ;;
    *)
        N=/etc/init.d/$NAME
        echo "Usage: $N {start|stop|restart}" >&2
        exit 1
    ;;
esac

exit 0

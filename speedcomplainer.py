import os
import sys
import time
from datetime import datetime
import daemon
import signal
import threading
import json 
import random
from logger import Logger

shutdownFlag = False

def main(filename, argv):
    print "======================================"
    print " Starting Speed Reporter!             "
    print "======================================"

    global shutdownFlag
    signal.signal(signal.SIGINT, shutdownHandler)

    monitor = Monitor()

    while not shutdownFlag:
        try:

            print("monitor run")
            monitor.run()

            for i in range(0, 5):
                if shutdownFlag:
                    break
                time.sleep(1)

        except Exception as e:
            print 'Error: %s' % e
            sys.exit(1)

    sys.exit()

def shutdownHandler(signo, stack_frame):
    global shutdownFlag
    print 'Got shutdown signal (%s: %s).' % (signo, stack_frame)
    shutdownFlag = True

class Monitor():
    def __init__(self):
        self.lastSpeedTest = None

    def run(self):
        if not self.lastSpeedTest or (datetime.now() - self.lastSpeedTest).total_seconds() >= 1800:
            self.runSpeedTest()
            self.lastSpeedTest = datetime.now()

    def runSpeedTest(self):
        speedThread = SpeedTest()
        speedThread.start()

class SpeedTest(threading.Thread):
    def __init__(self):
        super(SpeedTest, self).__init__()
        self.config = json.load(open('./config.json'))
        self.logger = Logger(self.config['log']['type'], { 'filename': self.config['log']['files']['speed'] })

    def run(self):
        speedTestResults = self.doSpeedTest()
        self.logSpeedTestResults(speedTestResults)

    def doSpeedTest(self):
        # run a speed test
        result = os.popen("python /home/pi/speedtest/speedtest_cli.py --simple").read()

        print '-------------'
        print result
        print '-------------'

        if 'Cannot' in result:
            return { 'date': datetime.now(), 'uploadResult': 0, 'downloadResult': 0, 'ping': 0 }

        # Result:
        # Ping: 529.084 ms
        # Download: 0.52 Mbit/s
        # Upload: 1.79 Mbit/s

        resultSet = result.split('\n')
        pingResult = resultSet[0]
        downloadResult = resultSet[1]
        uploadResult = resultSet[2]

        pingResult = float(pingResult.replace('Ping: ', '').replace(' ms', ''))
        downloadResult = float(downloadResult.replace('Download: ', '').replace(' Mbit/s', ''))
        uploadResult = float(uploadResult.replace('Upload: ', '').replace(' Mbit/s', ''))

        return { 'date': datetime.now(), 'uploadResult': uploadResult, 'downloadResult': downloadResult, 'ping': pingResult }

    def logSpeedTestResults(self, speedTestResults):
        self.logger.log([ speedTestResults['date'].strftime('%Y-%m-%d %H:%M:%S'), str(speedTestResults['ping']), str(speedTestResults['downloadResult']), str(speedTestResults['uploadResult']) ])


class DaemonApp():
    def __init__(self, pidFilePath, stdout_path='/dev/null', stderr_path='/dev/null'):
        self.stdin_path = '/dev/null'
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.pidfile_path = pidFilePath
        self.pidfile_timeout = 1

    def run(self):
        main(__file__, sys.argv[1:])

if __name__ == '__main__':
    main(__file__, sys.argv[1:])

    workingDirectory = os.path.basename(os.path.realpath(__file__))
    stdout_path = '/dev/null'
    stderr_path = '/dev/null'
    fileName, fileExt = os.path.split(os.path.realpath(__file__))
    pidFilePath = os.path.join(workingDirectory, os.path.basename(fileName) + '.pid')
    from daemon import runner
    dRunner = runner.DaemonRunner(DaemonApp(pidFilePath, stdout_path, stderr_path))
    dRunner.daemon_context.working_directory = workingDirectory
    dRunner.daemon_context.umask = 0o002
    dRunner.daemon_context.signal_map = { signal.SIGTERM: 'terminate', signal.SIGUP: 'terminate' }
    dRunner.do_action()


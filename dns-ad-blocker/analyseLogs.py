import matplotlib.pyplot as plt
import argparse
import json


parser = argparse.ArgumentParser(
    description='Analyse logs produced by the associated Recursive DNS Resolver.'
)

parser.add_argument('-b', '--banned-domain-logs', required=True, type=str, dest='banningLogFile', help='json file', metavar='BANNED-DOMAIN-LOGS')
parser.add_argument('-c', '--cache-logs', required=True, type=str, dest='cachingLogFile', help='json file', metavar='CACHE-LOGS')

arguments = parser.parse_args()


with open(arguments.banningLogFile, 'r') as f:
    banningLogs = json.load(f)

with open(arguments.cachingLogFile, 'r') as f:
    cachingLogs = json.load(f)

specificBanningLogs = {'google': 0, 'facebook': 0, 'microsoft': 0, 'firefox/mozilla': 0, 'total': 0}
for banningLog in banningLogs:
    if 'google' in banningLog:
        specificBanningLogs['google'] += banningLogs[banningLog]

    if 'facebook' in banningLog:
        specificBanningLogs['facebook'] += banningLogs[banningLog]

    if 'microsoft' in banningLog or 'msft' in banningLog:
        specificBanningLogs['microsoft'] += banningLogs[banningLog]

    if 'firefox' in banningLog or 'mozilla' in banningLog:
        specificBanningLogs['firefox/mozilla'] += banningLogs[banningLog]

    specificBanningLogs['total'] += banningLogs[banningLog]

figure = plt.figure(figsize=(10, 6))     # change window size
figure.suptitle('Banned Domains')
plt.bar(list(specificBanningLogs.keys()), list(specificBanningLogs.values()), color='firebrick', width=0.4)
plt.show()

figure = plt.figure(figsize=(3, 6))
figure.suptitle('Cache')
plt.bar(list(cachingLogs.keys()), list(cachingLogs.values()), color='cadetblue', width=0.4)
plt.show()

import requests

coinMinerDomains = requests.request('GET', 'https://raw.githubusercontent.com/anudeepND/blacklist/master/CoinMiner.txt').text.split('\n')[9:]
adDomains = requests.request('GET', 'https://raw.githubusercontent.com/anudeepND/blacklist/master/adservers.txt').text.split('\n')[10:]
facebookDomains = requests.request('GET', 'https://raw.githubusercontent.com/anudeepND/blacklist/master/facebook.txt').text.split('\n')[8:]

with open('blocked.txt', 'w') as f:
    for coinMinerDomain in coinMinerDomains:
        if coinMinerDomain:
            f.write(coinMinerDomain.split()[1] + '\n')

    for adDomain in adDomains:
        if adDomain:
            f.write(adDomain.split()[1] + '\n')

    for facebookDomain in facebookDomains:
        if facebookDomain:
            f.write(facebookDomain.split()[1] + '\n')

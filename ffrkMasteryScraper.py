import praw, re, string
from collections import Counter


def cleanSbNames(sbNameList):
    cleanList = []
    for sbName in sbNameList:
        sbNameCheck = sbName.lower()
        if 'lbo' in sbNameCheck:
            cleanList.append('LBO')
        elif 'limit' in sbNameCheck:
            cleanList.append('LBO')
        elif 'sync' in sbNameCheck:
            cleanList.append('SASB')
        elif 'sasb' in sbNameCheck:
            cleanList.append('SASB')
        elif 'aasb' in sbNameCheck:
            cleanList.append('AASB')
        elif 'awake' in sbNameCheck:
            cleanList.append('AASB')
        elif 'woke' in sbNameCheck:
            cleanList.append('AASB')
        elif 'glint+' in sbNameCheck:
            cleanList.append('GSB+')
        elif 'g+' in sbNameCheck:
            cleanList.append('GSB+')
        elif 'csb' in sbNameCheck:
            cleanList.append('CSB')
        elif 'chain' in sbNameCheck:
            cleanList.append('CSB')
        elif 'aosb' in sbNameCheck:
            cleanList.append('AOSB')
        elif 'usb' in sbNameCheck:
            cleanList.append('USB')
        elif 'osb' in sbNameCheck:
            cleanList.append('OSB')
        elif 'glint' in sbNameCheck:
            cleanList.append('GSB')
        elif 'bsb' in sbNameCheck:
            cleanList.append('BSB')
        elif 'burst' in sbNameCheck:
            cleanList.append('BSB')
        elif 'ssb' in sbNameCheck:
            cleanList.append('SSB')
        elif 'unique' in sbNameCheck:
            cleanList.append('Unique')
    return cleanList


def parseTeamTable(commentBody):
    heroRowOffset = 2
    numHeroRows = 5
    heroIdx = 1
    lmIdx = 4
    sbIdx = -2

    bodyLines = commentBody.split('\n')
    tableStartIdx = [idx for idx, text in enumerate(bodyLines) if text[0:5].lower() == '|hero']
    if tableStartIdx == []:
        return {}  # return empty sb dict if this comment has no mastery team table we can detect
    else:
        try:
            # print(bodyLines)
            tableStartIdx = tableStartIdx[0]
            tableLines = bodyLines[tableStartIdx+heroRowOffset:tableStartIdx+heroRowOffset+numHeroRows]
            splitTable = [line.split('|') for line in tableLines]
            heroNames = [re.split('[, ]', line[heroIdx])[0] for line in splitTable]
            sbNamesRaw = [re.sub(r'\([^)]*\)', '', line[sbIdx]).replace(',', ' ').replace('/', ' ').split() for line in splitTable]  # remove stuff inside parens
            sbNamesClean = [cleanSbNames(sbNamesList) for sbNamesList in sbNamesRaw]
            sbDict = {re.sub('[^A-Za-z0-9]+', '', k).lower().capitalize():v for (k, v) in zip(heroNames, sbNamesClean)}  # standardize hero name formatting some
            return sbDict
        except:
            return {}


def writeTableHeader(fileObj, sbTypes):
    titleString = ''.join(['|Hero|Used|', '|'.join(sbTypes), '|\n'])
    fileObj.write(titleString)
    alignmentStringList = [':-:' for item in titleString.split('|')]
    alignmentString = '|'.join(alignmentStringList)
    fileObj.write(''.join([alignmentString[3:-3], '\n']))  # trim off ends
    return


def writeHeroRow(fileObj, heroName, sbTypes, nameCounts, sbCountDict):
    heroCount = str(nameCounts[heroName])
    heroSbCountDict = sbCountDict[heroName]
    sbCounts = [str(heroSbCountDict[sbType]) if sbType in heroSbCountDict.keys() else '0' for sbType in sbTypes]
    fileObj.write(''.join(['|{}|{}|'.format(heroName, heroCount), '|'.join(sbCounts), '|\n']))
    return


def writeAveragesRow(fileObj, sbTypes, sbCounts, totalTeams):
    sbAverages = ['**{:.2f}**'.format(sbCounts[sbType]/totalTeams) if sbType in sbCounts.keys() else '**0**' for sbType in sbTypes]
    fileObj.write(''.join(['|{}|{}|'.format('**Average**', '**n/a**'), '|'.join(sbAverages), '|\n']))
    return


# You'll need to get your own client id and secret from Reddit - it's quick:
# https://www.geeksforgeeks.org/how-to-get-client_id-and-client_secret-for-python-reddit-api-registration/
reddit = praw.Reddit(
     client_id="<add client ID here>",
     client_secret="<add client secret here>",
     user_agent="FFRK mastery scraper by /u/mutlibottlerocket"
)

threadIds = ['jkj12l', 'idrf6n', 'jxb735', 'i12tyd', 'iqk212', 'jc5k7a', 'h7ybrg', 'i97f4x', 'j7kwp4', 'hshnwo']
sbTypes = ['LBO', 'SASB', 'AASB', 'GSB+', 'CSB', 'AOSB', 'USB', 'OSB', 'GSB', 'BSB', 'SSB', 'Unique']  # cleanSbNames() maps to these

for threadId in threadIds:
    submission = reddit.submission(id=threadId)  # hard-coded to one thread to start
    print(submission.title)  # Output: reddit will soon only be available ...
    topLevelComments = list(submission.comments)
    sbDicts = [parseTeamTable(comment.body) for comment in topLevelComments]
    flatNames = [item for dict in sbDicts for item in dict.keys()]
    nameCounts = Counter(flatNames)

    sbCountDict = {}
    for name in nameCounts.keys():
        flatSbs = [item for dict in sbDicts if name in dict.keys() for item in dict[name]]
        sbCountDict[name] = Counter(flatSbs)

    globalFlatSbs = [item for dict in sbDicts for key in dict.keys() for item in dict[key]]  # for averages
    sbCounts = Counter(globalFlatSbs)
    totalTeams = len(['' for dict in sbDicts if dict != {} ])

    # write output to text file
    with open('output.txt', 'a') as f:
        f.write('{}\n\n'.format(''.join(['#', ''.join(filter(lambda x: x in string.printable, submission.title))])))
        writeTableHeader(f, sbTypes)
        namesByFreq = [pair[0] for pair in nameCounts.most_common()]
        for heroName in namesByFreq:
            writeHeroRow(f, heroName, sbTypes, nameCounts, sbCountDict)
        writeAveragesRow(f, sbTypes, sbCounts, totalTeams)
        f.write('\n\n\n')

print('Script finished!')
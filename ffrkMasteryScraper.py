import praw, re, string, requests, numpy
from collections import Counter
from strsimpy.jaro_winkler import JaroWinkler

##########################
#  Functions
##########################
def getHeroNameList():
    r = requests.get('https://www.ffrktoolkit.com/ffrk-api/api/v1.0/IdLists/Character')
    heroNameList = [entry['Value'] for entry in r.json()]
    removeNames = ['Red Mage', 'Thief (Core)', 'Thief (I)', 'Cloud of Darkness', 'Cecil (Dark Knight)', 'Cecil (Paladin)',
                   'Cid (IV)', 'Gogo (V)', 'Gogo (VI)', 'Cid (VII)', 'Cid Raines', 'Cid (XIV)', 'Shadowsmith', 'Shared']
    addNames = ['Thief', 'CoD', 'Decil', 'Pecil', 'Cid', 'Gogo']
    addNicknames = ['OK', 'Greg', 'Nanaki', 'Laugh', 'Kitty', 'Raines', 'TGC']
    for name in removeNames:
        heroNameList.remove(name)
    heroNameList.extend(addNames)
    heroNameList.extend(addNicknames)
    return heroNameList

def cleanHeroName(heroName, heroNameList, strsim):
    slangDict = {'OK':'Onion Knight', 'Greg':'Gilgamesh', 'Nanaki':'Red XIII', 'Laugh':'Tidus', 'Raines':'Cid', 'TGC':'Orlandeau'}
    matchTuples = sorted([(name, strsim.similarity(name, heroName)) for name in heroNameList], key=lambda tup: tup[1], reverse=True)
    matchScores = numpy.array([tuple[1] for tuple in matchTuples])
    matchCandidate = matchTuples[0]
    if ((matchCandidate[1] >= 0.85) or (matchCandidate[1] >= (numpy.mean(matchScores) + 2*numpy.mean(matchScores)))):
        if matchCandidate[0] in slangDict.keys():
            cleanedHeroName = slangDict[matchCandidate[0]]
        else:
            cleanedHeroName = matchCandidate[0]
    else:
        cleanedHeroName = 'ParseFail'
    # print(matchTuples) # debug
    # print('Match score mean: {}'.format(numpy.mean(matchScores)))
    # print('Match score median: {}'.format(numpy.median(matchScores)))
    # print('Match score std dev: {}'.format(numpy.std(matchScores)))
    return cleanedHeroName

def cleanSbNames(sbNameList):
    cleanList = []
    for sbName in sbNameList:
        sbNameCheck = sbName.lower()
        if 'lbo' in sbNameCheck:
            cleanList.append('LBO')
        elif 'limit' in sbNameCheck:
            cleanList.append('LBO')
        elif 'lbg' in sbNameCheck:
            cleanList.append('LBG')
        elif 'dyad' in sbNameCheck:
            cleanList.append('ADSB')
        elif 'adsb' in sbNameCheck:
            cleanlist.append('ADSB')
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
        elif 'gsb+' in sbNameCheck:
            cleanList.append('GSB+')
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
        elif 'gsb' in sbNameCheck:
            cleanList.append('GSB')
        elif 'glint' in sbNameCheck:
            cleanList.append('GSB')
        elif 'g' in sbNameCheck:
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


def parseTeamTable(comment, heroNameList, strsim):
    heroRowOffset = 2
    numHeroRows = 5

    bodyLines = comment.body.replace('*','').split('\n')
    tableStartIdx = [idx for idx, text in enumerate(bodyLines) if text[0:5].lower() == '|hero']
    if tableStartIdx == []:
        # print('Comment {} passed over due to no team table detected'.format(comment))
        # print('Text passed: {}'.format(bodyLines))
        return {}  # return empty sb dict if this comment has no mastery team table we can detect
    else:
        try:
            tableStartIdx = tableStartIdx[0]
            tableHeader = bodyLines[tableStartIdx].split('|')
            heroIdx = [idx for idx, s in enumerate(tableHeader) if 'hero' in s.lower()][0]
            sbIdx = [idx for idx, s in enumerate(tableHeader) if ('sb' in s.lower() or 'soul' in s.lower())][0]
            tableLines = bodyLines[tableStartIdx+heroRowOffset:tableStartIdx+heroRowOffset+numHeroRows]
            splitTable = [line.split('|') for line in tableLines]
            heroNames = [re.split('[, ]', line[heroIdx])[0] for line in splitTable]
            heroNames = [cleanHeroName(name, heroNameList, strsim) for name in heroNames]
            sbNamesRaw = [re.split('[;,/ ]' ,re.sub(r'\([^)]*\)', '', line[sbIdx])) for line in splitTable]  # remove stuff inside parens
            sbNamesClean = [cleanSbNames(sbNamesList) for sbNamesList in sbNamesRaw]
            sbDict = {re.sub('[^A-Za-z0-9]+', '', k).lower().capitalize():v for (k, v) in zip(heroNames, sbNamesClean)}  # standardize hero name formatting some

            # extra stuff for exporting to /u/DropeRj
            fullTableLines = bodyLines[tableStartIdx:tableStartIdx+heroRowOffset+numHeroRows]
            tableText = ["{}\n".format(line.replace('|', "\t'")) for line in fullTableLines]
            tableText.insert(0, "'{}\n".format(comment.author.name))
            return (sbDict, tableText)
        except:
            print('Comment {} passed over due to exception parsing table'.format(comment))
            print('Text passed: {}'.format(bodyLines))
            return {}


def appendTableHeader(outputLines, sbTypes):
    titleString = ''.join(['|Hero|Used|', '|'.join(sbTypes), '|\n'])
    outputLines.append(titleString)
    alignmentStringList = [':-:' for item in titleString.split('|')]
    alignmentString = '|'.join(alignmentStringList)
    outputLines.append(''.join([alignmentString[3:-3], '\n']))  # trim off ends
    return


def appendHeroRow(outputLines, heroName, sbTypes, nameCounts, sbCountDict):
    heroCount = str(nameCounts[heroName])
    heroSbCountDict = sbCountDict[heroName]
    sbCounts = [str(heroSbCountDict[sbType]) if sbType in heroSbCountDict.keys() else '0' for sbType in sbTypes]
    outputLines.append(''.join(['|{}|{}|'.format(heroName, heroCount), '|'.join(sbCounts), '|\n']))
    return


def appendAveragesRow(outputLines, sbTypes, sbCounts, totalTeams):
    sbAverages = ['**{:.2f}**'.format(sbCounts[sbType]/totalTeams) if sbType in sbCounts.keys() else '**0**' for sbType in sbTypes]
    outputLines.append(''.join(['|{}|{}|'.format('**Average**', '**n/a**'), '|'.join(sbAverages), '|\n']))
    return


# takes in a list of PRAW comments containing /u/jadesphere format mastery survey posts and updates
# outputLines and summaryLines for eventual text output
def parseMasterySubmissions(commentsList, sectionTitle, postUrl, outputLines, summaryLines, teamTableTextLines, sbTypes, heroNameList, strsim):
    parsedTuples = [parseTeamTable(comment, heroNameList, strsim) for comment in commentsList]
    sbDicts = [item[0] for item in parsedTuples if len(item) > 0]
    teamTableText = [line for item in parsedTuples if len(item) > 0 for line in item[1]]
    flatNames = [item for dict in sbDicts for item in dict.keys()]
    nameCounts = Counter(flatNames)

    sbCountDict = {}
    for name in nameCounts.keys():
        flatSbs = [item for dict in sbDicts if name in dict.keys() for item in dict[name]]
        sbCountDict[name] = Counter(flatSbs)

    globalFlatSbs = [item for dict in sbDicts for key in dict.keys() for item in dict[key]]  # for averages
    sbCounts = Counter(globalFlatSbs)
    totalTeams = len(['' for dict in sbDicts if dict != {} ])

    # write output to buffer list
    if len(postUrl) == 1:
        for url in postUrl:
            outputLines.append('#[{}]({})\n\n'.format(sectionTitle, url))
    else:
        surveyNumber = 1
        for url in postUrl:
            outputLines.append('#[{} - Survey {}]({})\n\n'.format(sectionTitle, surveyNumber, url))
            surveyNumber += 1
    outputLines.append('Number of clears parsed: {}\n\n\n'.format(totalTeams))
    for url in postUrl:
        teamTableText.insert(0, '*******{} {}*******\n'.format(sectionTitle, url))
    appendTableHeader(outputLines, sbTypes)
    namesByFreq = [pair[0] for pair in nameCounts.most_common()]
    for heroName in namesByFreq:
        appendHeroRow(outputLines, heroName, sbTypes, nameCounts, sbCountDict)
    appendAveragesRow(outputLines, sbTypes, sbCounts, totalTeams)
    appendAveragesRow(summaryLines, sbTypes, sbCounts, totalTeams)
    # summaryLines[-1] = summaryLines[-1].replace('Average', realm).replace('|**n/a**', '').replace('**','')
    outputLines.append('\n\n\n')
    for line in teamTableText:
        teamTableTextLines.append(line)
    return (outputLines, summaryLines, teamTableTextLines)

##########################
#  Main
##########################

## Common stuff
# You'll need to get your own client id and secret from Reddit - it's quick:
# https://www.geeksforgeeks.org/how-to-get-client_id-and-client_secret-for-python-reddit-api-registration/
# Put them into the "redditClientInfo.txt" file that should live in the same directoy as the script.
with open('redditClientInfo.txt', 'r') as f:
    rawText = f.readlines()
clientId = rawText[0].split('=')[-1].replace(' ','')[:-1]
clientSecret = rawText[1].split('=')[-1].replace(' ','')
reddit = praw.Reddit(
     client_id=clientId,
     client_secret=clientSecret,
     user_agent="FFRK mastery scraper by /u/mutlibottlerocket"
)

# still missing XII and core
dbThreadIds = [['l7eleg'], ['jkj12l'], ['idrf6n'], ['jxb735'], ['i12tyd'],
               ['l2cchd'], ['iqk212'], ['jc5k7a'], ['h7ybrg', 'kjz26x'], ['kj1cp9'],
               ['k66l27'], ['i97f4x', 'lgszoq'], ['j7kwp4'], ['kxjd5p'], ['hshnwo', 'lgqz1h'],
               ['kffviy']]  # this has to be updated as new Dreambreakers release AND as new survey threads are posted
wodinCommentIds = [['gc4m5xz'], ['gc4m761'], ['gc4ma38'], ['gc4mb1b']]  # comment IDs of parent comments in WOdin mastery threads for wind and earth-weak
wodinThreadIds = [['k8pd7q'], ['k8petf'],  # thread IDs for individual phys/mag weak threads for lighting-weak
                  ['kj1gdp'], ['kj1fcw'],  # water-weak
                  ['lc3fe6'], ['lc3fey']]  # fire-weak
sbTypes = ['LBO', 'LBG', 'ADSB', 'SASB', 'AASB', 'GSB+', 'CSB', 'AOSB', 'USB', 'OSB', 'GSB', 'BSB', 'SSB', 'Unique']  # cleanSbNames() maps to these
heroNameList = getHeroNameList()
strsim = JaroWinkler()  # string similarity module for catching typos/abbreviations


## Run for Dreambreaker
outputLines = []  # buffer to put output strings into
summaryLines = ['#Summary table\n\n\n']
appendTableHeader(summaryLines, sbTypes)
summaryLines[-2] = summaryLines[-2].replace('|Hero|Used', '|Realm')
summaryLines[-1] = summaryLines[-1][4:]
teamTableTextLines = []
for threadId in dbThreadIds:
    submission = reddit.submission(id=threadId[0])
    threadTitle = submission.title
    realm = threadTitle[threadTitle.find("(")+1:threadTitle.find(")")]
    print('\n*****************\n{}\n*****************\n'.format(threadTitle))
    commentsList = []
    postUrl = []
    for individual_threadId in threadId:
        submission = reddit.submission(id=individual_threadId)
        postUrl.append(submission.url)
        for comment in submission.comments:
            commentsList.append(comment)
    sectionTitle = ''.join(filter(lambda x: x in string.printable, threadTitle))
    parseMasterySubmissions(commentsList, sectionTitle, postUrl, outputLines, summaryLines, teamTableTextLines, sbTypes, heroNameList, strsim)
    summaryLines[-1] = summaryLines[-1].replace('Average', realm).replace('|**n/a**', '').replace('**','')


# prepend SB averages summary table
summaryLines.append('\n\n\n')
outputLines[:0] = summaryLines
# write output to text file
with open('dbPostText.txt', 'w') as f:
    f.writelines(outputLines)
with open('dbTeamTableText.txt', 'w') as f:
    f.writelines(teamTableTextLines)

## Run for master-thread WOdins (Earth & Lightning)
outputLines = []  # buffer to put output strings into
summaryLines = ['#Summary table\n\n\n']
appendTableHeader(summaryLines, sbTypes)
summaryLines[-2] = summaryLines[-2].replace('|Hero|Used', '|Version')
summaryLines[-1] = summaryLines[-1][4:]
teamTableTextLines = []
for postId in wodinCommentIds:
    parentComment = reddit.comment(id=postId[0])
    postUrl = []
    postUrl.append('https://www.reddit.com{}'.format(parentComment.permalink))
    parentComment.refresh()
    parentComment.replies.replace_more()
    commentsList = parentComment.replies.list()
    # print(parentComment.body)
    threadTitle = ' '.join(parentComment.body.split('\n')[0].split(' ')[-3:]).replace('**', '')
    print('\n*****************\n{}\n*****************\n'.format(threadTitle))
    parseMasterySubmissions(commentsList, threadTitle, postUrl, outputLines, summaryLines, teamTableTextLines, sbTypes, heroNameList, strsim)
    summaryLines[-1] = summaryLines[-1].replace('Average', threadTitle).replace('|**n/a**', '').replace('**','')
## Run for dmg type-thread WOdins (Water, Fire, Ice)
for threadId in wodinThreadIds:
    submission = reddit.submission(id=threadId[0])
    threadTitle = submission.title
    print('\n*****************\n{}\n*****************\n'.format(threadTitle))
    commentsList = []
    postUrl = []
    for individual_threadId in threadId:
        submission = reddit.submission(id=individual_threadId)
        postUrl.append(submission.url)
        for comment in submission.comments:
            commentsList.append(comment)
    threadTitle = ' '.join(threadTitle.split(' ')[-3:]).replace('**', '')
    sectionTitle = ''.join(filter(lambda x: x in string.printable, threadTitle))
    parseMasterySubmissions(commentsList, sectionTitle, postUrl, outputLines, summaryLines, teamTableTextLines, sbTypes, heroNameList, strsim)
    summaryLines[-1] = summaryLines[-1].replace('Average', threadTitle).replace('|**n/a**', '').replace('**','')
# prepend SB averages summary table
summaryLines.append('\n\n\n')
outputLines[:0] = summaryLines
# write output to text file
with open('wodinPostText.txt', 'w') as f:
    f.writelines(outputLines)
with open('wodinTeamTableText.txt', 'w') as f:
    f.writelines(teamTableTextLines)

print('\n\nScript finished!')

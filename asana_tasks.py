""" Script to connect to Asana projects, read data from Notes field of tasks, and update custom fields with values contained in the data."""
import sys
import asana
import datetime
import threading

#### globals ####
# personal access token from asana developers portal: https://app.asana.com/0/1101638289721813/board
# keep the PAT in an external file that is excluded from versioning (add to .gitignore)
with open('asana-pat.txt', 'r') as f: 
    pat = f.readline()

# construct an Asana client
client = asana.Client.access_token(pat)

# specify the project IDs
pycProjectId = 1101667914088903
agolProjectId = 1101638289721813
nrdbProjectId = 1107827681827126
communicationsId = 1109168845883071

# make a list of project Ids to iterate
projectIds = [
    ('PYC Apps Requests', pycProjectId), 
    ('AGOL Requests', agolProjectId), 
    ('NRDB App Requests', nrdbProjectId), 
    ('Communications Requests', communicationsId)
]

# we're only concerned with tasks in the 'New Requests' board (for board layouts)
sectionName = 'New Requests'

# field names
sectionNameField = 'name'
gidField = 'gid'
resourceSubtypeField = 'resource_subtype'
nameField = 'name'  
enumValueField = 'enum_value'
customField = 'custom_field'
customFields = 'custom_fields'
notesField = 'notes'
apiUpdatedField = 'api_updated'
enumOptionsField = 'enum_options'
typeField = 'type'
customIdField = 'customFieldId'
customValueIdField = 'customFieldValueId'
ticketIdField = 'TicketId'

# event field names
evtActionField = 'action'
evtActionVal = 'added'
evtResourceField = 'resource'
evtResourceTypeField = 'resource_type'
evtResourceTypeVal = 'task'
evtParentField = 'parent'
evtSectionVal = 'section'
evtNameField = 'name'

#### helper functions ####
def _getLayout(projectId):
    # get the current project by Id
    currentProject = client.projects.find_by_id(projectId)
    # get the current project's layout, e.g. 'board' or 'list'
    layout = currentProject['layout']
    return layout


def _getSectionGid(projectId):
    # get all sections associated with the project
    sections = client.sections.find_by_project(projectId)
    # get only the section we care about -- 'New Requests'
    section = [section for section in sections if section[sectionNameField] == sectionName][0]
    # return the section global Id
    if len(section) > 0:
        return section[gidField]
    raise Exception ('Did not find appropriate Section!')


def _padTicketId(fieldValue):
    splitValues = fieldValue.split('-')
    if len(splitValues) < 2:
        raise Exception('The field value for TicketId is malformed: {fieldValue}'.format(fieldValue = fieldValue))
    else:
        projectValue = splitValues[0]
        idValue = splitValues[1].zfill(6)

    newFieldValue = projectValue + '-' + idValue
    return newFieldValue

#### main functions ####
def main():
    # loop through each project
    for project in projectIds:
        # get the project name and Id
        projectName = project[0]
        projectId = project[1]

        # call main function
        processTasks(projectName, projectId)
        
        eventThread = threading.Thread(target=getEvents, args=(projectName, projectId, None,))
        eventThread.start()


def processTasks(projectName, projectId, taskGID=None):
    # start logging 
    print('Processing {proj}.'.format(proj = projectName))
    log(projectName, 'Processing {proj}.'.format(proj = projectName))

    ## check to see if there are tasks that need updating
    # get the current project's layout, e.g. 'board' or 'list'
    layout = _getLayout(projectId)

    # first check if taskGID is set
    if taskGID is not None:
        tasks = [client.tasks.find_by_id(taskGID)]
    # if board layout...
    elif (layout == 'board'):
        # get the section global Id (using global projectId)
        sectionGid = _getSectionGid(projectId)

        # now find all tasks in the section
        # returns minimal information about tasks
        tasks = client.tasks.find_by_section(sectionGid)

    else: # otherwise access all tasks in the list
        # returns minimal information about tasks
        tasks = client.tasks.find_by_project(projectId)
    
    # extract tasks that have not been updated by this script and store results in array
    updateableTasks = getUpdateableTasks(tasks)
            
    # if we have tasks to update
    if len(updateableTasks) > 0:
        # get the project's custom field settings
        customFieldSettings = client.custom_field_settings.find_by_project(projectId)
        # create a dict based on custom field Id's and value Id's
        customFieldDict = parseCustomFieldSettings(customFieldSettings)    
    
        # iterate over each task
        for task in updateableTasks:
            # get the task global Id
            taskGid = task[gidField]
            
            # get the custom field Id and value for the 'api_updated' custom field
            apiCustomFieldId = customFieldDict[apiUpdatedField]['yes'][customIdField]
            apiCustomFieldValueId = customFieldDict[apiUpdatedField]['yes'][customValueIdField]
            
            # get the Notes associated with the task - the data we need is stored here
            notes = client.tasks.find_by_id(taskGid)[notesField]
            
            # store results as dict
            notesDict = parseNotes(notes)
            # for key in notesDict.keys():
            #     print('{key}, {value}').format(key = key, value = notesDict[key])

            # check that notesDict has at least one key (prevents errors when tasks are made via the Asana interface)
            if len(notesDict.keys()) > 0:
                # get the custom field data
                customFieldData = getCustomFieldData(notesDict, customFieldDict)
                customFieldData[apiCustomFieldId] = apiCustomFieldValueId

                # set up the data object to pass to the PUT/Update request
                apiData = { notesField: notesDict[notesField],  customFields: customFieldData }

                # for key in data.keys():
                #     print('{key}, {value}').format(key = key, value = data[key])
            else:
                # get the custom field data
                customFieldData = getCustomFieldData(notesDict, customFieldDict)
                customFieldData[apiCustomFieldId] = apiCustomFieldValueId
                
                # set up the data object to pass to the PUT/Update request
                apiData = { customFields: customFieldData }
            
            # update the current task's fields with data from the Notes area
            try:
                client.tasks.update(taskGid, apiData)

                if 'ticketId' in notesDict.keys():
                    print('The task ({ticketId}) was updated!').format(ticketId = notesDict[ticketIdField])
                    log(projectName, 'The task ({ticketId}) was updated!'.format(ticketId = notesDict[ticketIdField]))
                else:
                    print('The task was updated!')
                    log(projectName, 'The task was updated!')

            except Exception as e:
                print(e)
                print('There was a problem updating the fields in task via the API')
                log(projectName, 'There was a problem updating the fields in task via the API')
                for key in apiData[customFields].keys():
                    print('{key}, {value}').format(key = key, value = apiData[customFields][key])
                    log(projectName, '{key}, {value}'.format(key = key, value = apiData[customFields][key]))
    else:
        print('There were no tasks to update!')
        log(projectName, 'There were no tasks to update!')


def getUpdateableTasks(tasks):
    # a list to store all tasks that need to be updated
    taskList = []

    # iterate through each task ('tasks' contains limited info on each task)
    for task in tasks:
        # get the task Id
        taskGid = task[gidField]

        # get full information about the task
        t = client.tasks.find_by_id(taskGid)
        
        # search the cutom fields of the task for the api_updated field
        # if found and value is None then add to list
        isUpdateable = list(filter(
            lambda x: 
                x[resourceSubtypeField] == 'enum' and 
                x[nameField] == apiUpdatedField and 
                x[enumValueField] is None,  t[customFields]))
        
        # if isUpdateable contains at least one element, then task needs to be updated
        if len(isUpdateable) > 0:
            taskList.append(t)
    
    return taskList


def parseCustomFieldSettings(customFieldSettings):
    # use a temporary dict to store custom field information
    cfDict = {}

    # loop through each custom field setting
    for cf in customFieldSettings:
        # the type of custom field: text, number, enum
        resourceSubtype = cf[customField][resourceSubtypeField]
        # the name of the custom field
        name = cf[customField][nameField]
        # the global id of the custom field
        gid = cf[customField][gidField]

        # the top-level keys are the custom field names
        cfDict[name] = {}

        # if the custom field is an enum, track both custom field Id and custom field value Id
        if enumOptionsField in cf[customField].keys():
            for enum in cf[customField][enumOptionsField]:
                val = enum[nameField]
                enumId = enum[gidField]
                cfDict[name][val] = { customIdField: gid, customValueIdField: enumId }
                cfDict[name][typeField] = resourceSubtype
        # if custom field is text or number, just track the custom field Id
        else:
            cfDict[name] = { typeField: resourceSubtype, customIdField: gid }
    
    return cfDict


def parseNotes(notes):
    # first deal with ||| if any - caused by fields in Forms with no values
    # by adding a space between first and second |
    newNotes = notes.replace('|||', '| ||')
    # create a list of strings of the key/value pairs
    notesList = newNotes.split('||')
    # temporary dict to be returned
    tmpDict = {}

    # iterate over each string
    for line in notesList:
        # split on vertical bar to separate field/value
        tmpList = line.split('|')

        # if we've parsed a field/value, add it to the dict: key=field name, value=field value
        if len(tmpList) > 1:
            fieldLabel = tmpList[0].strip()
            fieldValue = tmpList[1].strip()
            if fieldLabel == ticketIdField:
                fieldValue = _padTicketId(fieldValue)
            tmpDict[fieldLabel] = fieldValue

    return tmpDict


def getCustomFieldData(notesDict, customFieldDict):
    # initialize dict to hold custom field data
    data = {}
    # iterate over each field extracted from the Notes
    for fieldName in notesDict.keys():
        # ensure that the field name from Notes is valid
        if (fieldName != notesField and fieldName in customFieldDict.keys()):
            # get the associated custom field settings for the current field
            currentSettings = customFieldDict[fieldName]

            # if the custom field resource subtype is enum, handle as special case
            if currentSettings[typeField] == 'enum':
                # need the custom field Id as well as the custom field value Id
                cidf = currentSettings[notesDict[fieldName]][customIdField]
                cidv = currentSettings[notesDict[fieldName]][customValueIdField]        
            else:
                # just need the custom field Id, get the value directly from Notes data
                cidf = currentSettings[customIdField]
                cidv = notesDict[fieldName]

            data[cidf] = cidv
            #print('cid %s, cidv %s' % (customFieldIdField, customFieldValueId))
    
    # add the custom field info for the api_updated field
    # data[apiCustomFieldId] = apiCustomFieldValueId
    
    # add a due date -- this is done in Forms now
    # due_on = datetime.now().date() + timedelta(days=7)
    # due_on = due_on.strftime('%Y-%m-%d')
    # data['due_on'] = due_on

    return data


def log(projectName, text):
    logFile = './logs/asana-log.txt'
    timestamp = datetime.datetime.now()
    with open(logFile, 'a+') as log:
        logText = '{ts}\t{proj}\t{t}\n'.format(ts = timestamp, proj=projectName, t = text)
        log.write(logText)


def getEvents(projectName, projectId, sync):
    print('Starting {proj} thread!'.format(proj=projectName))
    log(projectName, 'Starting {proj} thread!'.format(proj=projectName))

    if sync is None:
        result = client.events.get_next({ 'resource': projectId })
    else:
        result = client.events.get_next({ 'resource': projectId, 'sync': sync })
    
    if (len(result) == 2):
        # get the events from the first item in the tuple
        events = result[0]
        # get the sync token from the second item in the tuple
        sync = result[1]

        # get the layout of the project
        layout = _getLayout(projectId)

        # if board layout, filter for parent == section to reduce duplicates
        if (layout == 'board'):
            addedTaskEvents = [
                event for event in events if event[evtActionField] == evtActionVal 
                and event[evtResourceField][evtResourceTypeField] == evtResourceTypeVal 
                and event[evtParentField][evtResourceTypeField] == evtSectionVal 
                and event[evtParentField][evtNameField] == sectionName
            ]
        # otherwise list layout - cannot filter by sections
        else:
            addedTaskEvents = [
                event for event in events if event[evtActionField] == evtActionVal
                and event[evtResourceField][evtResourceTypeField] == evtResourceTypeVal 
            ]

        if len(addedTaskEvents) > 0:
            taskGIDs = [event[evtResourceField][gidField] for event in addedTaskEvents]
            log(projectName, 'The following task GID(s) will be updated {tasks}.'.format(tasks=taskGIDs))
            print(taskGIDs)
            print(addedTaskEvents)
            for tGID in taskGIDs:
                processTasks(projectName, projectId, tGID)
        else:
            log(projectName, 'There were no added tasks to update!')
            log(projectName, '{events}'.format(events=events))
    else:
        print('Not able to get events data or sync token from results: {results}'.format(results=result))
        log(projectName, 'Not able to get events data or sync token from results: {results}'.format(results=result))
        log(projectName, '{info}'.format(info=sys.exc_info()))

    eventThread = threading.Thread(target=getEvents, args=(projectName, projectId, sync))
    eventThread.start()


""" PyInstaller
    Instructions:
        - find warnings: C:\Users\ccardinal\source\repos\python\asana-custom-fields\build\update-new-tasks\warn-update-new-tasks.txt
        - build a single executable file:
        pyinstaller --onefile --clean --noconfirm --paths "C:\Users\ccardinal\source\repos\python\asana-custom-fields\venv\Lib\site-packages" asana_tasks.py
"""

if __name__ == '__main__':
    main()
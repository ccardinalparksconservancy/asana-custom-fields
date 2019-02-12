import asana
import datetime
import re

def getSectionGid():
    # get all sections associated with the project
    sections = client.sections.find_by_project(projectId)
    # get only the section we care about -- 'New Requests'
    section = [section for section in sections if section[sectionNameField] == sectionName][0]
    # return the section global Id
    if len(section) > 0:
        return section[gidField]
    raise Exception ('Did not find appropriate Section!')

def getUpdateableTasks():
    tmpList = []
    for task in tasks:
        taskGid = task[gidField]
        t = client.tasks.find_by_id(taskGid)
        #isUpdateable = [field for field in t['custom_fields'] if field['resource_subtype'] == 'enum' and field['name'] == apiUpdatedField and field['enum_value'] is None]
        isUpdateable = list(filter(lambda x: 
            x[resourceSubtypeField] == 'enum' and 
            x[nameField] == apiUpdatedField and 
            x[enumValueField] is None,  t[customFields]))
        if len(isUpdateable) > 0:
            tmpList.append(t)
    return tmpList

def parseCustomFieldSettings():
    # use a temporary dict to store custom field information
    tmpDict = {}

    # loop through each custom field setting
    for cf in customFieldSettings:
        # the type of custom field: text, number, enum
        resourceSubtype = cf[customField][resourceSubtypeField]
        # the name of the custom field
        name = cf[customField][nameField]
        # the global id of the custom field
        gid = cf[customField][gidField]

        # the top-level keys are the custom field names
        tmpDict[name] = {}

        # if the custom field is an enum, track both custom field Id and custom field value Id
        if enumOptionsField in cf[customField].keys():
            for enum in cf[customField][enumOptionsField]:
                val = enum[nameField]
                enumId = enum[gidField]
                tmpDict[name][val] = { customIdField: gid, customValueIdField: enumId }
                tmpDict[name][typeField] = resourceSubtype
        # if custom field is text or number, just track the custom field Id
        else:
            tmpDict[name] = { typeField: resourceSubtype, customIdField: gid }
    
    return tmpDict

def parseNotes():
    # create a list of strings of the key/value pairs
    notesList = notes.split('||')
    # temporary dict to be returned
    tmpDict = {}

    # iterate over each string
    for line in notesList:
        # split on colon to separate field/value
        tmpList = line.split('|')

        # if we've parsed a field/value, add it to the dict: key=field name, value=field value
        if len(tmpList) > 1:
            fieldLabel = tmpList[0].strip()
            fieldValue = tmpList[1].strip()
            if fieldLabel == ticketIdField:
                fieldValue = padTicketId(fieldValue)
            tmpDict[fieldLabel] = fieldValue

    return tmpDict

def padTicketId(fieldValue):
    splitValues = fieldValue.split('-')
    if len(splitValues) < 2:
        raise Exception('The field value for TicketId is malformed: {fieldValue}'.format(fieldValue = fieldValue))
    else:
        projectValue = splitValues[0]
        idValue = splitValues[1].zfill(6)
        # if len(idValue) < 5:
        #     idValue = '0' * (5 - len(idValue)) + idValue
        # else:
        #     raise Exception('There is something wrong with the numerical part of the TicketId value: {idValue}'.format(idValue = idValue))

    newFieldValue = projectValue + '-' + idValue
    return newFieldValue

def getCustomFieldData(data):
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

            data[customFields][cidf] = cidv
            #print('cid %s, cidv %s' % (customFieldIdField, customFieldValueId))
    
    # add the custom field info for the api_updated field
    data[customFields][apiCustomFieldId] = apiCustomFieldValueId
    
    # add a due date -- this is done in Forms now
    # due_on = datetime.now().date() + timedelta(days=7)
    # due_on = due_on.strftime('%Y-%m-%d')
    # data['due_on'] = due_on

    return data

def log(text):
    logFile = './logs/asana-log.txt'
    timestamp = datetime.datetime.now()
    with open(logFile, 'a+') as log:
        logText = '{ts}\t{t}\n'.format(ts = timestamp, t = text)
        log.write(logText)
'''
PyInstaller:
    - find warnings: C:\Users\ccardinal\source\repos\python\asana-custom-fields\build\update-new-tasks\warn-update-new-tasks.txt
    - build a single executable file:
        pyinstaller --onefile --clean --noconfirm --paths "C:\Users\ccardinal\source\repos\python\asana-custom-fields\venv\Lib\site-packages" update-new-tasks.py
'''

if __name__ == '__main__':
    # personal access token from asana developers portal: https://app.asana.com/0/1101638289721813/board
    with open('asana-pat.txt', 'r') as f: 
        pat = f.readline()

    # construct an Asana client
    client = asana.Client.access_token(pat)

    # specify the project IDs
    pycProjectId = 1101667914088903
    agolProjectId = 1101638289721813
    nrdbProjectId = 1107827681827126

    # make an array of project Ids to iterate
    projectIds = [('PYC Apps Requests', pycProjectId), ('AGOL Requests', agolProjectId), ('NRDB App Requests', nrdbProjectId)]

    # we're only concerned with tasks in the 'New Requests' board
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

    # keep track of current value of TicketId
    currentTicket = ''

    # loop through each project
    for project in projectIds:
        # get the project name and Id
        projectName = project[0]
        projectId = project[1]

        print('Processing {proj}.'.format(proj = projectName))
        log('Processing {proj}.'.format(proj = projectName))
        ## check to see if there are tasks that need updating
        # first get the section global Id (using global projectId)
        sectionGid = getSectionGid()

        # now find all tasks in the section
        tasks = client.tasks.find_by_section(sectionGid)
        
        # extract tasks that have not been updated by this script and store results in array
        updateableTasks = getUpdateableTasks()
                
        # if we have tasks to update
        if len(updateableTasks) > 0:
            # get the project's custom field settings
            customFieldSettings = client.custom_field_settings.find_by_project(projectId)
            # create a dict based on custom field Id's and value Id's
            customFieldDict = parseCustomFieldSettings()    
        
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
                notesDict = parseNotes()
                # for key in notesDict.keys():
                #     print('{key}, {value}').format(key = key, value = notesDict[key])

                # check that notesDict has at least one key (prevents errors when tasks are made via the Asana interface)
                if len(notesDict.keys()) > 0:
                    # set up the data object to pass to the PUT/Update request
                    apiData = { notesField: notesDict[notesField],  customFields: {} }
                    data = getCustomFieldData(apiData)
                    # for key in data.keys():
                    #     print('{key}, {value}').format(key = key, value = data[key])
                else:
                    apiData = { customFields: {} }
                    data = getCustomFieldData(apiData)
                
                # update the current task's fields with data from the Notes area
                try:
                    client.tasks.update(taskGid, data)
                
                    print('The task ({ticketId}) was updated!').format(ticketId = notesDict[ticketIdField])
                    log('The task ({ticketId}) was updated!'.format(ticketId = notesDict[ticketIdField]))
                    # print('The task was updated!')

                except:
                    print('There was a problem updating the fields in task via the API')
                    log('There was a problem updating the fields in task via the API')
                    for key in data[customFields].keys():
                        print('{key}, {value}').format(key = key, value = data[customFields][key])
                        log('{key}, {value}'.format(key = key, value = data[customFields][key]))
        else:
            print('There were no tasks to update!')
            log('There were no tasks to update!')
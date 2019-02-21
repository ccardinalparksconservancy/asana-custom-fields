# coding: utf-8

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

def parseCustomFieldSettings():
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

def parseNotes():
    # create a list of strings of the key/value pairs
    notesList = notes.split('||')
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

    newFieldValue = projectValue + '-' + idValue
    return newFieldValue

def getCustomFieldData():
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
    data[apiCustomFieldId] = apiCustomFieldValueId
    
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
        ('Communications Requests', communicationsId)]

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

    # keep track of current value of TicketId
    # currentTicket = ''

    # loop through each project
    for project in projectIds:
        # get the project name and Id
        projectName = project[0]
        projectId = project[1]

        print('Processing {proj}.'.format(proj = projectName))
        log('Processing {proj}.'.format(proj = projectName))

        ## check to see if there are tasks that need updating
        # first check if project is a list or a board
        # get the current project by Id
        currentProject = client.projects.find_by_id(projectId)

        # get the current project's layout, e.g. 'board' or 'list'
        layout = currentProject['layout']

        # if board layout...
        if (layout == 'board'):
            # get the section global Id (using global projectId)
            sectionGid = getSectionGid()

            # now find all tasks in the section
            # returns minimal information about tasks
            tasks = client.tasks.find_by_section(sectionGid)

        else: # otherwise access all tasks in the list
            # returns minimal information about tasks
            tasks = client.tasks.find_by_project(projectId)
        
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
                    # get the custom field data
                    customFieldData = getCustomFieldData()

                    # set up the data object to pass to the PUT/Update request
                    apiData = { notesField: notesDict[notesField],  customFields: customFieldData }

                    # for key in data.keys():
                    #     print('{key}, {value}').format(key = key, value = data[key])
                else:
                    # get the custom field data
                    customFieldData = getCustomFieldData()
                    
                    # set up the data object to pass to the PUT/Update request
                    apiData = { customFields: customFieldData }
                
                # update the current task's fields with data from the Notes area
                try:
                    client.tasks.update(taskGid, apiData)

                    if 'ticketId' in notesDict.keys():
                        print('The task ({ticketId}) was updated!').format(ticketId = notesDict[ticketIdField])
                        log('The task ({ticketId}) was updated!'.format(ticketId = notesDict[ticketIdField]))
                    else:
                        print('The task was updated!')
                        log('The task was updated!')

                except Exception as e:
                    print(e)
                    print('There was a problem updating the fields in task via the API')
                    log('There was a problem updating the fields in task via the API')
                    for key in apiData[customFields].keys():
                        print('{key}, {value}').format(key = key, value = apiData[customFields][key])
                        log('{key}, {value}'.format(key = key, value = apiData[customFields][key]))
        else:
            print('There were no tasks to update!')
            log('There were no tasks to update!')
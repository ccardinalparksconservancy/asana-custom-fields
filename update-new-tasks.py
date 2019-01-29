import asana
from datetime import datetime, timedelta

def getSectionGID(projectId, sectionName):
    # get all sections associated with the project
    sections = client.sections.find_by_project(projectId)
    # get only the section we care about -- 'New Requests'
    section = [section for section in sections if section['name'] == sectionName][0]
    # return the section global Id
    return section['gid']

def getUpdateableTasks(tasks):
    tmpList = []
    for task in tasks:
        taskGid = task['gid']
        t = client.tasks.find_by_id(taskGid)
        isUpdateable = [field for field in t['custom_fields'] if field['resource_subtype'] == 'enum' and field['name'] == apiUpdatedField and field['enum_value'] is None]
        if len(isUpdateable) > 0:
            tmpList.append(t)
    return tmpList

def getCustomFieldDict(customFieldSettings):
    # use a temporary dict to store custom field information
    tmpDict = {}

    # loop through each custom field setting
    for cf in customFieldSettings:
        # the type of custom field: text, number, enum
        resourceSubtype = cf['custom_field']['resource_subtype']
        # the name of the custom field
        name = cf['custom_field']['name']
        # the global id of the custom field
        gid = cf['custom_field']['gid']

        # the top-level keys is the custom field name
        tmpDict[name] = {}

        # if the custom field is an enum, track both custom field Id and custom field value Id
        if 'enum_options' in cf['custom_field'].keys():
            for enum in cf['custom_field']['enum_options']:
                val = enum['name']
                enumId = enum['gid']
                tmpDict[name][val] = { 'customFieldId': gid, 'customFieldValueId': enumId }
                tmpDict[name]['type'] = resourceSubtype
        # if custom field is text or number, just track the custom field Id
        else:
            tmpDict[name] = { 'type': resourceSubtype,'customFieldId': gid }
    
    return tmpDict

def getNotesAsDict(notes):
    # create a list of strings of the key/value pairs
    notesList = notes.split('\n')
    # temporary dict to be returned
    tmpDict = {}

    # iterate over each string
    for line in notesList:
        # split on colon to separate field/value
        tmpList = line.split('|')
        # if we've parsed a field/value, add it to the dict: key=field name, value=field value
        if len(tmpList) > 1:
            tmpDict[tmpList[0].strip()] = tmpList[1].strip()

    return tmpDict

def getCustomFieldData(notesDict, customFieldDict, customFieldSettings):
    data = { 'custom_fields': {} }
    # iterate over each field extracted from the Notes
    for fieldName in notesDict.keys():
        # ensure that the field name from Notes is valid
        if (fieldName in customFieldDict.keys()):
            # get the associated custom field settings for the current field
            customFieldSettings = customFieldDict[fieldName]

            # if the custom field resource subtype is enum, handle as special case
            if customFieldSettings['type'] == 'enum':
                # need the custom field Id as well as the custom field value Id
                customFieldId = customFieldSettings[notesDict[fieldName]]['customFieldId']
                customFieldValueId = customFieldSettings[notesDict[fieldName]]['customFieldValueId']        
            else:
                # just need the custom field Id, get the value directly from Notes data
                customFieldId = customFieldSettings['customFieldId']
                customFieldValueId = notesDict[fieldName]

            data['custom_fields'][customFieldId] = customFieldValueId
            #print('cid %s, cidv %s' % (customFieldId, customFieldValueId))
    
    # add the custom field info for the api_updated field
    data['custom_fields'][apiCustomFieldId] = apiCustomFieldValueId
    
    # add a due date
    due_on = datetime.now().date() + timedelta(days=7)
    due_on = due_on.strftime('%Y-%m-%d')
    data['due_on'] = due_on

    return data

if __name__ == "__main__":
    # personal access token from asana developers portal
    with open('asana-pat.txt', 'r') as f: 
        pat = f.readline()

    # construct an Asana client
    client = asana.Client.access_token(pat)

    # specify the project IDs
    pycProjectId = 1101667914088903
    gisProjectId = 0
    nrdbProjectId = 0

    # make an array of project Ids to iterate
    projectIds = [pycProjectId]

    # we're only concerned with tasks in the 'New Requests' board
    sectionName = 'New Requests'

    # api field
    apiUpdatedField = 'api_updated'

    # specify the project IDs
    pycProjectId = 1101667914088903
    gisProjectId = 0
    nrdbProjectId = 0

    # make an array of project Ids to iterate
    projectIds = [pycProjectId]

    # loop through each project
    for projectId in projectIds:
        # check to see if there are tasks that need updating

        # first get the section global Id
        sectionGid = getSectionGID(projectId, sectionName)

        # now find all tasks in the section
        tasks = client.tasks.find_by_section(sectionGid)
        
        # extract tasks that have not been updated by this script
        # store results in array
        updateableTasks = getUpdateableTasks(tasks)
                
        # check to see if we have tasks to update
        if len(updateableTasks) > 0:
            # get the project's custom field settings
            customFieldSettings = client.custom_field_settings.find_by_project(projectId)

            customFieldDict = getCustomFieldDict(customFieldSettings)    
        
            # iterate over each task
            for task in updateableTasks:
                # get the task global Id
                taskGid = task['gid']
                
                # get the custom field Id and value for the api_updated custom field
                apiCustomFieldId = customFieldDict[apiUpdatedField]['yes']['customFieldId']
                apiCustomFieldValueId = customFieldDict[apiUpdatedField]['yes']['customFieldValueId']
                
                # get the Notes associated with the task - the data we need is stored here
                notes = client.tasks.find_by_id(taskGid)['notes']
                
                # store results as dict
                notesDict = getNotesAsDict(notes)

                # set up the data object to pass to the PUT/Update request
                data = getCustomFieldData(notesDict, customFieldDict, customFieldSettings)
                
                # update the current task's field if the field name from Notes is present in the custom field settings
                client.tasks.update(taskGid, data)
                #print(data)
                print('All tasks were updated!')
        else:
            print('There were no tasks to update!')
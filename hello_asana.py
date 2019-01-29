import asana

# replace with your personal access token.
# personal access token from asana developers portal
with open('asana-pat.txt', 'r') as f: 
    pat = f.readline()

# Construct an Asana client
client = asana.Client.access_token(pat)
# Set things up to send the name of this script to us to show that you succeeded! This is optional.
client.options['client_name'] = "hello_world_python"

# Get your user info
me = client.users.me()
workspaceId = me['workspaces'][0]['id']

# Print out your information
print "Hello world! " + "My name is " + me['name'] + " and my primary Asana workspace is " + me['workspaces'][0]['name'] + "."
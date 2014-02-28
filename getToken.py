#!/usr/bin/python
import sys, simplejson, requests
json = simplejson

print ""
print "**************************************************************"
print "* This script generates an access token for your dropbox app *"
print "**************************************************************"
print ""

app_key = raw_input("1.) Enter your 'App key': ").strip()
app_secret = raw_input("2.) Enter your 'App secret': ").strip()
print "3.) Now open this url and confirm the requested permission."
print ""
print "https://www.dropbox.com/1/oauth2/authorize?response_type=code&client_id=" + app_key
print ""
code = raw_input("4.) Enter the given access code': ").strip()

# Start to communicate with dropbox api.
args = {
	'code' : code,
	'grant_type' : 'authorization_code',
	'client_id' : app_key,
	'client_secret' : app_secret
}
try:
	r = requests.post('https://api.dropbox.com/1/oauth2/token/', params=args)
except Exception, e:
	print "ERROR! Could not fetch access token from dropbox: " + str(e)
	sys.exit(-1)

# Handle reply.
json_data = ""
try:
	json_data = json.loads(r.text)
except Exception, e:
	print "ERROR! Could not handle request reply from dropbox: " + str(e)
	sys.exit(-1)

# Check wether the reply contains a valid access_token.
if json_data.has_key('error'):
	print "ERRRO! " + json_data['error_description']
	sys.exit(-1)

print ""
print "This access token allows your app to access your dropbox:"
print json_data['access_token'] 
print ""

# Make a testrequest and show userinformations.
try:
	headers = {"Authorization": "Bearer " + json_data['access_token']}
	r = requests.post('https://api.dropbox.com/1/account/info', None, headers=headers)
	json_userdata = json.loads(r.text)

	print "- Your account -"
	print "Display name : " + json_userdata['display_name']
	print "Email        : " + json_userdata['email']
	print "Userid       : " +  str(json_userdata['uid'])
	print "Country      : " + json_userdata['country']
	print "Referral link: " + json_userdata['referral_link']
except Exception, e:
	print str(e)
	sys.exit(-1)


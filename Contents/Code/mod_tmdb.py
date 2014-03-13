#!/usr/bin/python
import urllib, urllib2, simplejson, re
json = simplejson
debug = True

def apiRequestTMDB(token, call, args = None):
	headers = {"Accept": "application/json"}
	url = "http://api.themoviedb.org/3/" + call

	# Prepare request.
	data = None
	if args != None:
		url = url + "?api_key=" + token + "&" + urllib.urlencode(args)

	#req = urllib2.Request(url, data, headers)
	req = urllib2.Request(url, None, headers)

	# Execute request.
	response = urllib2.urlopen(req)
	result = response.read()
	return result

####################################################################################################

def tmdbSearchMovie(token, language, title):
	m = re.search('(.*) \((.*)\)', title)
	year = ''
	try:
		title = m.group(1)
		year = m.group(2)
	except:
		if Prefs['debug_log'] == True: Log('Clip not in a compatible naming scheme. No TMDb lookup.')
		return False

	args = {
		'query': title,
		'language': language,
		'year': year, 
		'include_adult': 'true'
	}
	try:
		tmp = apiRequestTMDB(token, "search/movie", args)
		json_data = json.loads(tmp)

		# Analyze result.
		if json_data['total_results'] > 0:
			return tmdbGetMovie(token, language, json_data['results'][0]['id'])
		else:
			return False
	except Exception, e:
		if Prefs['debug_log'] == True: Log("ERROR tmdbSearchMovie(): " + str(e))
		return False
	return False

####################################################################################################

def tmdbGetMovie(token, language, id):
	args = {
		'language': language 
	}
	try:
		tmp = apiRequestTMDB(token, "movie/" + str(id), args)
		json_data = json.loads(tmp)
		return json_data
	except Exception, e:
		if Prefs['debug_log'] == True: Log("ERROR tmdbGetMovie(): " + str(e))
		return False
	return False

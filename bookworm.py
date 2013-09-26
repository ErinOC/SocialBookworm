import os
from flask import Flask, render_template, session, request, redirect, jsonify, url_for
import urllib2
import plistlib
from xml.etree import ElementTree as ET
import oauth2 as oauth
import urlparse
from xml.dom.minidom import parseString
import math
from time import gmtime, strftime

app = Flask(__name__)
app.secret_key = os.environ['secret_key']

BASE_URL = "http://www.goodreads.com"
AUTHORIZE_URL = '%s/oauth/authorize' % BASE_URL
REQUEST_TOKEN_URL = '%s/oauth/request_token' % BASE_URL
ACCESS_TOKEN_URL = '%s/oauth/access_token' % BASE_URL
API_KEY = "key=" + os.environ['api_key']
API_KEY_SHORT = os.environ['api_key']
API_SECRET_KEY = os.environ['api_secret_key']

#Upon accessing the index page, run a check to see if the user has already given authorization.
@app.route('/')
def index():
	if not session.has_key('access_token') and not session.has_key('access_token_secret'):
		return redirect('/request_oauth')
	else: 
		return redirect('/get_preliminary_goodreads_data')
 
#If the user needs to give authorization, request a request token and create a link to Goodreads.
@app.route('/request_oauth')
def request_oauth():
	client = setup_oauth()
	#Get a request token which will later be paired with the user token.
	print "request token url", REQUEST_TOKEN_URL
	response, content = client.request(REQUEST_TOKEN_URL, 'GET')
	print "content", content
    #Fetch the token and parse it. 
	request_token = dict(urlparse.parse_qsl(content)) #this is coming up empty.
	print "request_token", request_token
	session['request_token'] = request_token['oauth_token']
	session['request_token_secret'] = request_token['oauth_token_secret']
	#Create a Goodreads link containing the request token.
	authorize_link = '%s?oauth_token=%s' % (AUTHORIZE_URL,
	                                        request_token['oauth_token'])
	return render_template("request_oauth.html", auth=authorize_link)

#After the user has authorized, Goodreads will generate another token and redirect back to this route.
@app.route('/access')
def get_access():
	oauth_token = request.args['oauth_token']
	if not oauth_token == session['request_token']:
		raise Exception("request tokens do not match.\nsession: %s\noauth response: %s\n")
	request_token = oauth.Token(session['request_token'],
								session['request_token_secret'])
	access_token = fetch_access_token_with_request_token(request_token)	
 	session['access_token'] = access_token.key
 	session['access_token_secret'] = access_token.secret
 	return redirect('/')

@app.route('/get_preliminary_goodreads_data')
def get_preliminary_goodreads_data():
	print "First running get_preliminary", strftime("%Y-%m-%d %H:%M:%S", gmtime())
	access = session['access_token']
	secret = session['access_token_secret']
	token = oauth.Token(access, secret)
	client = setup_oauth(token)
	response, content = client.request('%s/api/auth_user' % "http://www.goodreads.com",
	                                   'GET')
	if response['status'] != '200':
		return render_template("error.html")
	    # raise Exception('Did not work')
	else:
	    print "Got the info!" 
	print "After first API call", strftime("%Y-%m-%d %H:%M:%S", gmtime())
	user = str(parseString(content).getElementsByTagName("GoodreadsResponse")[0].childNodes[3].getAttribute("id"))
	user_name = str(parseString(content).getElementsByTagName("name")[0].firstChild.nodeValue)
	print "After parsing", strftime("%Y-%m-%d %H:%M:%S", gmtime())
	session['user_name'] = user_name 
	session['user'] = user 
	session['friends'] = get_friends_info(token, user)
	return render_template("search.html", name=user_name)

@app.route('/goodreads/<string:zip>')
def goodreads(zip):
	print "running fetch route"
	access = session['access_token']
	secret = session['access_token_secret']
	token = oauth.Token(access, secret)
	user = session['user']
	friends = session['friends']
	session['friends_authors'] = get_friends_shelves(token, session['friends'])  #returns total friends authors
	events = get_events(token, zip, session['friends_authors'], friends)
	print events
	return events

def setup_oauth(token=None):
	consumer = oauth.Consumer(key= API_KEY_SHORT,
                          	  secret= API_SECRET_KEY)
	return oauth.Client(consumer, token)

def fetch_access_token_with_request_token(request_token):
	client = setup_oauth(token=request_token)	
	response, token_content = client.request(ACCESS_TOKEN_URL, 'POST')
	if response['status'] != '200':
	    raise Exception('Invalid response: %s' % response['status'])
	access_token = dict(urlparse.parse_qsl(token_content))
	user_token = oauth.Token(access_token['oauth_token'],
	                    	 access_token['oauth_token_secret'])
	return user_token

def get_friends_info(oauth_token, user):
	friends = []
	client = setup_oauth(token = oauth_token)
	response, content = client.request('http://www.goodreads.com/friend/user/%s?format=xml' % user,
	                                   'GET')
	if response['status'] != '200':
	    return render_template("error.html")
	friend_list = parseString(content).getElementsByTagName("user")
	for i in range(friend_list.length):
		name = (friend_list[i].getElementsByTagName("name")[0].firstChild.nodeValue).encode('utf8')
		print name
		friend_id = int(friend_list[i].getElementsByTagName("id")[0].firstChild.nodeValue)
		image = (friend_list[i].getElementsByTagName("small_image_url")[0].firstChild.nodeValue).encode('utf8')
		i = {"name":name, "friend_id":friend_id, "image": image}
		friends.append(i)
	return friends

def get_friends_shelves(oauth_token, friends):
	total_friends_authors = []
	client = setup_oauth(token = oauth_token)
	for friend in friends:  
		friend_id = friend["friend_id"]
		response, content = client.request('http://www.goodreads.com/review/list/%i.xml?%s&v=2&sort=date_added&per_page=100' % (friend_id, API_KEY),
		                                   'GET')
		author_set = []
		#If it's not necessary to page through the user's shelves, then just add all the authors on this page.
		authors = parseString(content).getElementsByTagName("author") 
		for i in range(len(authors)): 
			author_id = authors[i].getElementsByTagName("id")[0].firstChild.nodeValue
			author_set.append(author_id)
		print author_set
		total_friends_authors.append(author_set)
	return total_friends_authors

def get_events(oauth_token, zip, total_friends_authors, friends):
	client = setup_oauth(token = oauth_token)
	response, content = client.request("http://www.goodreads.com/event.xml?%s&search[postal_code]=%s" % (API_KEY, zip),
	                                   'GET')
	author_events = parseString(content).getElementsByTagName("event")
	# print author_events
	event_json = {}
	match_tally = 0
	for i in range(len(author_events)):
		author_id = author_events[i].getElementsByTagName("resource_id")[0].firstChild.nodeValue
		print event_json
		for j in range(len(total_friends_authors)):
			if author_id in total_friends_authors[j]:
				title = (author_events[i].getElementsByTagName("title")[0].firstChild.nodeValue).encode('utf8')
				date = (author_events[i].getElementsByTagName("start_at")[0].firstChild.nodeValue).encode('utf8')
				# description = author_events[i].getElementsByTagName("title")[0].firstChild.nodeValue
				link = (author_events[i].getElementsByTagName("link")[0].firstChild.nodeValue).encode('utf8')
				if author_events[i].getElementsByTagName("address")[0].firstChild:
					address = (author_events[i].getElementsByTagName("address")[0].firstChild.nodeValue).encode('utf8')
				else:
					address = ""
				if author_events[i].getElementsByTagName("city")[0].firstChild:
					city = (author_events[i].getElementsByTagName("city")[0].firstChild.nodeValue).encode('utf8')
				else:
					city = ""
				if author_events[i].getElementsByTagName("venue")[0].firstChild:
					venue = (author_events[i].getElementsByTagName("venue")[0].firstChild.nodeValue).encode('utf8')
				else:
					venue = ""
				potential_event = {"friend": {"friend_name":friends[j]["name"], "image":friends[j]["image"]}, "author_event": {"event_title":title, "date":date, "event_link":link, "venue":venue, "city":city, "address":address}}
				event_json[match_tally] = potential_event
				match_tally += 1
	print event_json
	if event_json != {}:
		return jsonify(event_json)
	else:
		return "No results found."

if __name__ == "__main__":
  app.config['STATIC_FOLDER'] = 'static'
  # Set environment variable in Heroku; if that key doesn't exist, it means
  # I'm running locally and can use debug=True
  if os.environ.has_key('debug_status'):
  	app.run(debug = False)
  else:
  	app.run(debug = True)

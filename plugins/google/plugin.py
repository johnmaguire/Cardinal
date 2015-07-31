from bs4 import BeautifulSoup
import requests
import re
#python3
#from urllib.parse import quote_plus
#python2
from urllib import quote_plus

class GoogleSearch(object):
    def get_search_result(self, cardinal, user, channel, msg):
        #gets search string from message, and makes it url safe
        try:
            search_string = msg.split(' ', 1)[1:]
            if len(search_string) < 1: #makes sure there is a value for <search string>
                cardinal.sendMsg(channel, 'Syntax: {0} <search string>'.format(msg.split(' ')[0]))
                return
            search_string = " ".join(search_string)
            search_string = quote_plus(search_string)
        except IndexError:
            cardinal.sendMsg(channel, 'Syntax: google <search string>')
            return
        
        try:
            #gets the html of the goole search page, and passes it in to beautiful soup
            google_search = requests.get('https://www.google.com/search?q={0}'.format(search_string))
            soup = BeautifulSoup(google_search.content,'html.parser')
            #google search result urls are really weird, this pulls the proper url out of google's <a> tags
            url= re.compile(r'.*(https?:\/\/.+?)\&')
            ols = soup.findAll("ol")
            #iterates through <ol> elements on the page looking for one that looks like
            #<ol>
            #  <li class="g">
            #      <div class="r">
            #           <a> <----- this is the link you're looking for
            #      <div class="s">
            #           #other stuff we don't care about, but this div doesn't exist for add or news elements,
            #               but The div.r exists for those elements.
            for olist in ols:
            	for result in olist.findAll("li",{"class":"g"}): #finds all elements the are likely search results
            		if result.find("div",{"class":"s"}): #finds all elements that contain <div class="s"> and are therfore a search result
            			href = result.find("a")['href']
            			result = url.match(href).group(1)
            			cardinal.sendMsg(channel,"top result is: ({0})".format(result))
            			return
            			
            cardinal.sendMsg(channel, "Could find a search result on requested page")
            return
        
        except:
            cardinal.sendMsg(channel, "Could not sucesfully find a result")
            
    get_search_result.commands = ['lmgtfy','google','search-for']
    get_search_result.help = ['Returns the url of the top result for a given string']

def setup():
    return GoogleSearch()

# class HelloWorldPlugin(object):
#     def hello(self, cardinal, user, channel, msg):
#         nick, ident, vhost = user.group(1), user.group(2), user.group(3)
#         cardinal.sendMsg(channel, "Hello %s!" % nick)
#     hello.commands = ['hello', 'hi']
#     hello.help = ["Responds to the user with a greeting.",
#                   "Syntax: .hello [user to greet]"]

# def setup():
#     return HelloWorldPlugin()
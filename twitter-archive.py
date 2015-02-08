import twitter
import json
import pymongo
import os
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
from pandas import DataFrame, Series
from datetime import datetime
import var


CONSUMER_KEY = var.CONSUMER_KEY
CONSUMER_SECRET = var.CONSUMER_SECRET
OAUTH_TOKEN = var.OAUTH_TOKEN
OAUTH_TOKEN_SECRET = var.OAUTH_TOKEN_SECRET
ACCOUNTS = var.ACCOUNTS
IMPORT_JSON_TO_MONGO = False
REMOVE_COLLECTION = False


def load_tweets(folder):
	tweets = []

	for filename in os.listdir(folder):
		f = open(folder + '/' + filename, 'r')
		lines = f.readlines()
		content = ''
		for line in lines[1:]:
			content += line
		tweets.extend(json.loads(content))
	return tweets

def save_to_mongo(tweets, collection):
	client = pymongo.MongoClient()
	db = client.twitter
	coll = db[collection]
	post_id = coll.insert(tweets)

def get_from_mongo(collection):
	client = pymongo.MongoClient()
	db = client.twitter
	coll = db[collection]
	tweets = []
	for post in coll.find():
		post
		tweets.append(post)

	return tweets

def remove_collection(collection):
	client = pymongo.MongoClient()
	db = client.twitter
	coll = db[collection]
	coll.remove()	

def save_to_File(json, filename):
	text_file = open(filename, "w")
	text_file.write(json)
	text_file.close()

def search_twitter_api(query):
	# XXX: Go to http://dev.twitter.com/apps/new to create an app and get values
	# for these credentials, which you'll need to provide in place of these
	# empty string values that are defined as placeholders.
	# See https://dev.twitter.com/docs/auth/oauth for more information 
	# on Twitter's OAuth implementation.

	auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
	                           CONSUMER_KEY, CONSUMER_SECRET)
	twitter_api = twitter.Twitter(auth=auth)

	# Nothing to see by displaying twitter_api except that it's now a
	# defined variable
	search_results = twitter_api.search.tweets(q=query)

	return search_results

def save_tweets(tweets, filename):
	text_file = open(filename, "w")
	text_file.write(json.dumps(tweets, indent=2))
	text_file.close()

def extract_tokens(tweets):
	tokens = [token for tweet in tweets for token in tweet.split()]
	return tokens

def lexical_diversity(tokens):
	# statistical measure for diversity of used tokens
	# 1 = every token is uniquely used, 0 = only one token used
	return 1.0 * len(set(tokens)) / len(tokens)

def average_tokens(status_texts):
	# avg. number of tokens used in a tweet
	total_tokens = sum([ len(text.split()) for text in status_texts ])
	return 1.0 * total_tokens / len(status_texts)

def average_characters(status_texts):
	# avg. number of characters used in a tweet
	total_characters = sum([ len(text) for text in status_texts ])
	return 1.0 * total_characters / len(status_texts)

def save_plot(filename, fileformats=['png']):
    for fileformat in fileformats:
		plt.savefig(filename+'.'+fileformat, bbox_inches='tight', format=fileformat)

def analyse_tweets(tweets, label):
	metrics = {}

	status_texts = [ tweet['text'] for tweet in tweets ]
	timestamp = [ tweet['created_at'] for tweet in tweets ]
	screen_names = [ user_mention['screen_name'] for tweet in tweets for user_mention in tweet['entities']['user_mentions'] ]
	# media = [ user_mention['screen_name'] for tweet in tweets for user_mention in tweet['entities']['media']]
	# urls = [ urls['screen_name'] for tweet in tweets for urls in tweet['entities']['urls']]
	hashtags = [ hashtag['text'] for tweet in tweets for hashtag in tweet['entities']['hashtags'] ]
	tokens = extract_tokens(status_texts)

	token_counts = sorted(Counter(tokens).values(), reverse=True)
	plt.loglog(token_counts, label=label)
	
	top10 = {}
	top10_list = []
	for item in [tokens, hashtags, screen_names]:
		c = Counter(item)
		top10_list.append(c.most_common()[:10]) # top 10
	metrics['top10-tokens'] = top10_list[0]
	metrics['top10-hashtags'] = top10_list[1]
	metrics['top10-mentions'] = top10_list[2]
	metrics['ld-tokens'] = lexical_diversity(tokens)
	metrics['ld-screennames'] = lexical_diversity(screen_names)
	metrics['ld-hashtags'] = lexical_diversity(hashtags)
	metrics['avg-tokens'] = average_tokens(status_texts)
	metrics['avg-characters'] = average_characters(status_texts)
	return token_counts, metrics

def extract_data(tweets):
	id = [ int(tweet['id']) for tweet in tweets ]
	length = [ len(tweet['text']) for tweet in tweets ]
	tokens = [ len(tweet['text'].split()) for tweet in tweets ]
	hashtags = [ len(tweet['entities']['hashtags']) for tweet in tweets ]
	mentions = [ len(tweet['entities']['user_mentions']) for tweet in tweets ]
	created_at = [ datetime.strptime(tweet['created_at'][:-6], '%Y-%m-%d %H:%M:%S') for tweet in tweets ]
	data = {	'id': id, 
				#'created_at': created_at, 
				'tokens': tokens, 
				'length': length, 
				'hashtags': hashtags, 
				'mentions': mentions}
	return DataFrame(data, index=created_at)


for account in ACCOUNTS:
	if REMOVE_COLLECTION:
		remove_collection(account)
	if IMPORT_JSON_TO_MONGO:
		tweets = load_tweets('data/'+account+'/data/js/tweets/')
		save_to_mongo(tweets, account)

for account in ACCOUNTS:
	tweets = get_from_mongo(account)

	all_token_counts, metrics_all = analyse_tweets(tweets, 'all-tweets')
	plt.ylabel("Freq")
	plt.xlabel("Word Rank")
	plt.title('Token Frequencies @'+account+' (All Tweets)')
	plt.legend(loc="best", fontsize="x-small")
	save_plot('figures/frequencies-all-'+account)
	plt.close()

	own_tweets = [ tweet for tweet in tweets if 'retweeted_status' in tweet ]
	my_token_counts, metrics_own = analyse_tweets(own_tweets, 'own-tweets')
	plt.ylabel("Freq")
	plt.xlabel("Word Rank")
	plt.title('Token Frequencies @'+account+' (Own Tweets)')
	plt.legend(loc="best", fontsize="x-small")
	save_plot('figures/frequencies-own-'+account)
	plt.close()

	save_to_File(json.dumps({'all-tweets': metrics_all, 'own-tweets': metrics_own}, indent=2), 'metrics-'+account+'.json')
	tweets = extract_data(tweets)

	# plotting
	tweets['length'].resample('M', how='mean')[1:-1].plot(logy=True, label='length')
	tweets['tokens'].resample('M', how='mean')[1:-1].plot(logy=True, label='tokens')
	tweets['hashtags'].resample('M', how='mean')[1:-1].plot(logy=True, label='hashtags')
	tweets['mentions'].resample('M', how='mean')[1:-1].plot(logy=True, label='mentions')
	plt.ylabel('Actions (sum)')
	plt.xlabel("Time")
	plt.title("Average Activity per Tweet - @"+account)
	plt.legend(loc="best", fontsize="x-small")
	save_plot('figures/avg-activity-'+account)
	plt.close()

	tweets['length'].resample('M', how='sum')[1:-1].plot(logy=True, label='length')
	tweets['tokens'].resample('M', how='sum')[1:-1].plot(logy=True, label='tokens')
	tweets['hashtags'].resample('M', how='sum')[1:-1].plot(logy=True, label='hashtags')
	tweets['mentions'].resample('M', how='sum')[1:-1].plot(logy=True, label='mentions')
	plt.ylabel('Actions (avg)')
	plt.xlabel("Time")
	plt.title("Activity @"+account)
	plt.legend(loc="best", fontsize="x-small")
	save_plot('figures/sum-activity-'+account)
	plt.close()



